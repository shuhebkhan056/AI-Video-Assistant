# Codebase Deep Dive

The project is organized as a single-process Python application with two entry points: Streamlit (`app.py`) and a terminal interface (`main.py`). The important logic lives in functions, not custom classes. It has no dedicated controller/service classes, middleware, or background task system. LangChain supplies classes such as `ChatPromptTemplate`, `ChatMistralAI`, `Document`, and `Chroma`; the project composes these into functions and runnable chains.

## Main call path

```text
app.py Analyze handler ─┐
                        ├─> utils.audio_processor.process_input
main.py run_pipeline ───┘       ↓
                         core.transcriber.transcribe_all
                                ↓
                 summarizer + extractor functions
                                ↓
                      rag_engine.build_rag_chain
                                ↓
             app renders output / CLI prints output
                                ↓
                 rag_engine.ask_question (chat)
```

## Entry points and orchestration

### `app.py`: Streamlit application and pipeline controller

- **Purpose / why:** Provides the interactive UI and coordinates the processing sequence. The Analyze button handler is the closest equivalent to a controller, though it is ordinary top-level Streamlit code rather than a controller class.
- **Inputs / outputs:** Reads `source` from `st.text_input()` and `language` from a select box; produces a result dictionary in `st.session_state.result` and UI elements.
- **How it works:** Initializes session state keys (`result`, `chat_history`, `processing`, `pipeline_done`, `pipeline_steps`); validates nonempty input; resets old result and chat; invokes the stages serially, updating the status map; stores the outputs and RAG chain; calls `st.rerun()` so results are rendered.
- **Callers / callees:** Streamlit executes the script on its normal rerun model. The Analyze block calls `process_input`, `transcribe_all`, `generate_title`, `summarize`, three extractor functions, and `build_rag_chain`. The chat block calls `ask_question`.
- **External services / database:** Indirectly uses Whisper/Sarvam, Mistral, Hugging Face embeddings, and Chroma through the core functions.
- **Conditions / loops / edge cases:** Empty/whitespace source is rejected. The UI stores state per Streamlit session. The pipeline is synchronous, so long calls occupy the interaction until each returns. A broad `try/except Exception` surrounds analysis, but not the chat request path. There is an initialized `processing` key, but the shown workflow does not update it.
- **Relevant code:** `app.py`, particularly the session state initialization, Analyze block, results section, and chat handler.

Core orchestration excerpt:

```python
chunks = process_input(source)
transcript = transcribe_all(chunks, language)
title = generate_title(transcript)
summary = summarize(transcript)
action_items = extract_action_items(transcript)
rag_chain = build_rag_chain(transcript)
```

### `main.py:run_pipeline(source, language="english")`: reusable CLI pipeline

- **Purpose / why:** Runs the full processing sequence outside Streamlit and returns a dictionary that the CLI can print and use for chat.
- **Inputs / outputs:** `source` is a URL or path; `language` selects transcription routing. Returns keys `title`, `transcript`, `summary`, `action_items`, `key_decisions`, `open_questions`, and `rag_chain`.
- **How it works:** Calls the same feature functions used by the UI, sequentially. It also prints the first 300 transcript characters as a progress/debug message.
- **Callers / callees:** Called by the `if __name__ == "__main__"` block. Calls every pipeline module except the UI. The main block prints outputs and repeatedly invokes `ask_question()` until an exit word is entered.
- **External services / database:** Same as the main pipeline: Mistral calls for text generation and extraction; Chroma indexing when creating the RAG chain; selected speech recognizer during transcription.
- **Conditions / loops / edge cases:** The CLI defaults an empty language prompt to `english`, but otherwise passes the typed string through. `transcribe_chunk()` treats only case-insensitive `hinglish` as Sarvam; any other value routes to Whisper. There is no exception handler around `run_pipeline()` or its chat loop.
- **Relevant code:** `main.py:run_pipeline`, then `main.py`'s main guard and chat loop.

### `app.py:step_status()` and `render_step_bar()`

These are UI helpers rather than business logic. `step_status(steps, key)` maps `active` to `dot-active`, `done` to `dot-done`, and every other/missing value to `dot-pending`. `render_step_bar(label, key, icon)` reads the Streamlit step dictionary and renders HTML. They have no database or external service interactions; `render_step_bar()` is used by the sidebar status list.

## Media preparation

### `utils/audio_processor.py:process_input(source)`

- **Purpose / why:** Provides a normalized handoff from user-provided media to transcription: a list of WAV chunk paths.
- **Inputs / outputs:** One string URL/path in; list of local WAV file paths out.
- **How it works:** Checks whether the string begins with `http://` or `https://`. URL input calls `download_youtube_audio()`. Any other string calls `convert_to_wav()`. Both then call `chunk_audio()`.
- **Callers / callees:** Called by `app.py`'s Analyze handler and `main.py:run_pipeline`. Calls one of the conversion/download functions, then chunking.
- **External services / database:** URL path uses yt-dlp to reach YouTube. Media conversion uses Pydub/FFmpeg. No database.
- **Conditions / loops / edge cases:** The URL check does not validate that the host is YouTube; any HTTP(S) URL is handed to yt-dlp. Local path validity and supported formats are delegated to Pydub/FFmpeg. Exceptions propagate. It does not remove generated files.

### `download_youtube_audio(url)`

- **Purpose:** Downloads best available audio, runs yt-dlp's `FFmpegExtractAudio` postprocessor, requests WAV, and returns the expected WAV path.
- **Inputs / outputs:** URL string → local path string.
- **Internal steps:** Sets output template under `downloades/`; constructs `yt_dlp.YoutubeDL` with format/postprocessor options; calls `extract_info(..., download=True)`; derives a filename from metadata and replaces `.webm` or `.m4a` suffixes with `.wav`.
- **Call relations:** Called only by `process_input()`.
- **Services/storage:** YouTube/yt-dlp, local disk, external FFmpeg executable. No database.
- **Edge cases:** Filename extension replacement only explicitly handles `.webm` and `.m4a`; failures from downloader or FFmpeg are not caught here. `downloades/` is created at module import.

### `convert_to_wav(input_path)` and `chunk_audio(wav_path, chunk_minutes=10)`

- **`convert_to_wav`:** Pydub opens a local media file, sets one channel and 16 kHz frame rate, exports a sibling path ending `_converted.wav`, and returns it. Invalid paths/unsupported formats raise from Pydub/FFmpeg.
- **`chunk_audio`:** Opens WAV input, computes a chunk duration in milliseconds, loops over starts spaced by that duration, writes each segment as `<wav_path>_chunk_<index>.wav`, and returns those paths. The default chunk is ten minutes. Empty/zero-duration inputs can return an empty list; the code does not explicitly reject that before transcription.
- **Call relations:** Both are called by `process_input()` (conversion conditionally, chunking always).
- **Services/storage:** Pydub and local filesystem only.

## Transcription

### `core/transcriber.py:transcribe_all(chunks, language="english")`

- **Purpose / why:** Serially transcribes all audio chunks and joins their text in order.
- **Inputs / outputs:** List of audio paths and language string → transcript string.
- **How it works:** Prints a selected engine label, loops through chunk paths, invokes `transcribe_chunk()` for each, appends each result plus a space, then strips the final string.
- **Callers / callees:** Called by both `app.py` and `main.py:run_pipeline`. Calls `transcribe_chunk()`.
- **External services / database:** Indirectly calls local Whisper or Sarvam; none in this function directly. No database.
- **Conditions / loops / edge cases:** Only equality with casefolded `hinglish` selects Sarvam. Empty `chunks` yields an empty transcript; the next AI calls are still attempted by the caller. Chunk failures stop the loop; there is no partial-result recovery or retry.

### `transcribe_chunk(chunk_path, language="english")`

This is the router: case-insensitive `hinglish` calls `transcribe_chunk_sarvam()`, all other language values call `transcribe_chunk_whisper()`. It is a simple strategy-like conditional, not a configurable strategy object.

### `load_model()` and `transcribe_chunk_whisper(chunk_path)`

- **Purpose:** Load the Whisper model on first use, cache it in module global `_model`, and transcribe one chunk locally.
- **Inputs / outputs:** `load_model()` returns a Whisper model; `transcribe_chunk_whisper()` accepts a path and returns the `text` field from `model.transcribe(..., task="transcribe")`.
- **Call relations:** `transcribe_chunk_whisper()` calls `load_model()`, which is invoked only along the English route.
- **External services / database:** Local Whisper/PyTorch. Model acquisition may require environment/model cache; no HTTP call is implemented in this module for English transcription.
- **Important logic / edge cases:** Model loading is lazy and cached for the process, avoiding a reload for every chunk. The selected `WHISPER_MODEL` is read at module import and defaults to `small`. File/model/inference errors propagate.

### `transcribe_chunk_sarvam(chunk_path)`, `_send_to_sarvam(piece_path)`

- **Purpose:** Adapt longer chunk audio to Sarvam's synchronous endpoint and collect translated transcript text.
- **Inputs / outputs:** WAV chunk path → transcript string. `_send_to_sarvam` takes a short WAV piece path and returns its response's `transcript` field (or empty string if absent).
- **Internal steps:** Checks `SARVAM_API_KEY`; opens the chunk with Pydub; slices into 25-second ranges; exports each to `<chunk>_sv_<i>.wav`; sends each with multipart `requests.post()` and model form field; concatenates response text; deletes each temporary piece in `finally`.
- **Call relations:** Called by `transcribe_chunk()` for Hinglish. `_send_to_sarvam()` is called once per short piece.
- **External services / database:** Sarvam endpoint `https://api.sarvam.ai/speech-to-text-translate`; no database.
- **Important conditions / edge cases:** API key is captured into `SARVAM_API_KEY` when module imports, so `.env` must be loaded before this import. Requests time out after 120 seconds. Non-OK responses log status/body and call `raise_for_status()`. Failures stop remaining pieces, but the current temporary file is cleaned up.

## LLM summarization and extraction

### `core/summarizer.py:split_transcript(transcript)`

- **Purpose:** Split long text into overlapping pieces so each summarization call handles a bounded amount of text.
- **Inputs / outputs:** Transcript string → list of strings.
- **How:** `RecursiveCharacterTextSplitter` uses `chunk_size=3000` and `chunk_overlap=200`.
- **Callers / services:** Called by `summarize()`; no external service or database.
- **Edge cases:** Very short input becomes a small number of pieces; empty input may provide no pieces and then lead to an empty combine input in `summarize()`.

### `get_llm()` in `core/summarizer.py` and `core/extractor.py`

Each module defines its own helper returning `ChatMistralAI` configured with `mistral-small-latest`, `MISTRAL_API_KEY`, and a temperature (0.3 for summarization, 0.2 for extraction). They are not a shared singleton; each feature builds a model wrapper. Credential and network errors surface when chains are invoked.

### `core/summarizer.py:summarize(transcript)`

- **Purpose / why:** Creates a long-transcript summary through a map-then-combine procedure.
- **Inputs / outputs:** Full transcript string → final bullet-point summary string.
- **Internal steps:** Gets an LLM; builds a map prompt and chain (`prompt | llm | StrOutputParser()`); splits the transcript; invokes the chain once per chunk in a list comprehension; joins partial summaries with blank lines; builds a combine prompt/chain; invokes it once on the joined text.
- **Callers / callees:** Called by `app.py` and `main.py:run_pipeline`; calls `get_llm()`, `split_transcript()`, and LangChain's invoke methods.
- **External services / database:** Multiple Mistral calls; no database.
- **Conditions / loops / edge cases:** Number of map calls grows with transcript length, sequentially. There is no batching, concurrency, retry, or catch. A failure on one chunk aborts final summary.

### `core/summarizer.py:generate_title(transcipt)`

- **Purpose:** Ask Mistral for a concise title.
- **Inputs / outputs:** Transcript string → generated title string.
- **How:** Builds a chain mapping input text into a prompt and runs it on `transcipt[:2000]`.
- **Callers / external:** Called by UI and CLI; calls Mistral. No database.
- **Edge cases:** Only first 2,000 characters influence title; for shorter transcripts Python slicing returns the whole string. The parameter is spelled `transcipt` in source, but callers pass positionally.

### `core/extractor.py:build_chain(system_prompt)` and extraction functions

- **Purpose:** Reuse a common prompt→Mistral→string-parser chain shape for the three extraction tasks.
- **Inputs / outputs:** `build_chain` receives a system prompt and returns a runnable chain; each extractor accepts transcript text and returns a string.
- **Internal steps:** Creates a Mistral model; uses `RunnablePassthrough` then `RunnableLambda` to map input into `{ "text": ... }`; fills system/human messages; calls LLM; parses output as string. Each public extractor supplies its own prompt and invokes the chain once.
- **Callers / callees:** `app.py` and `main.py` call `extract_action_items`, `extract_key_decisions`, and `extract_questions`; each uses `build_chain()`.
- **External services / database:** Three independent Mistral requests per completed analysis; no database.
- **Business logic:** Action prompt asks for task, owner, deadline (or “Not specified”); other prompts ask for decisions and unresolved follow-ups. “None found” is prompt guidance; there is no structured schema validation.
- **Edge cases:** Model output is plain text and can vary in formatting. Full transcript is sent for each task, which can create long requests. Exceptions propagate.

## Vector storage and question answering

### `core/vector_store.py:get_embeddings()`

- **Purpose:** Construct the embedding adapter used for transcript indexing and query retrieval.
- **Inputs / outputs:** No input → `HuggingFaceEmbeddings` configured with `all-MiniLM-L6-v2` and CPU device.
- **Callers / services:** Called by `build_vector_store()` and `load_vector_store()`. It may need the model available from local cache or downloaded through the Hugging Face ecosystem.
- **Edge cases:** Model loading/download errors propagate. No embedding cache or custom model validation is implemented.

### `core/vector_store.py:build_vector_store(transcript)`

- **Purpose / why:** Convert transcript into semantically searchable Chroma documents.
- **Inputs / outputs:** Transcript string → Chroma vector store.
- **Internal steps:** Splits text into chunks of 500 characters with overlap 50; creates `Document` objects carrying `chunk_index`; gets embeddings; calls `Chroma.from_documents()` with collection `meeting_transcript` and persistence directory `vector_db`.
- **Callers / callees:** Called from `core/rag_engine.py:build_rag_chain`; calls `get_embeddings()` and Chroma APIs.
- **Database operations:** Creates/writes embedded documents to local persistent Chroma. No explicit delete, upsert ID, or collection reset appears in the function.
- **Edge cases:** Repeated analyses write to the same named collection without explicit cleanup. Empty transcript may produce an empty document list; behavior then depends on Chroma integration. Filesystem/model errors propagate.

### `core/vector_store.py:get_retriever(vector_store, k=4)`

Returns `vector_store.as_retriever(search_type="similarity", search_kwargs={"k": k})`. `build_rag_chain()` calls it with `k=4`. It is a thin adapter over Chroma retrieval; it does no custom ranking or filtering.

### `core/rag_engine.py:build_rag_chain(transcript)`

- **Purpose / why:** Create the per-analysis pipeline that retrieves transcript context and produces grounded answers.
- **Inputs / outputs:** Transcript string → LangChain runnable chain.
- **Internal steps:** Calls `build_vector_store()`; creates a retriever with four-result similarity search; builds a Mistral LLM at temperature 0.3; makes a system prompt requiring answers based only on provided transcript context; composes a mapping where `context` runs retriever then `format_docs`, while `question` passes through; pipes values through prompt, LLM, and `StrOutputParser`.
- **Callers / callees:** Called at the end of Streamlit analysis and `main.py:run_pipeline`. Calls vector-store module, `get_llm()`, and LangChain components.
- **External/database:** Writes to Chroma during construction; Mistral is called later when a question invokes the chain.
- **Edge cases:** Chain construction requires successful embedding/vector-store setup. The instruction to only use context is a prompt, not programmatic enforcement.

Small excerpt of the actual chain composition:

```python
{
    "context": retriever | RunnableLambda(format_docs),
    "question": RunnablePassthrough(),
} | prompt | llm | StrOutputParser()
```

### `format_docs(docs)` and `ask_question(rag_chain, question)`

- **`format_docs`:** Joins each retrieved `Document.page_content` with two newlines. It is called inside the context branch of the RAG chain.
- **`ask_question`:** Logs the question, calls `rag_chain.invoke(question)`, logs the resulting answer, and returns it. It is called by the UI Send action and CLI loop.
- **Inputs / outputs:** Question string plus already-built chain → answer string.
- **Database/service interaction:** The invoked chain embeds/searches the question through the retriever, reads matching Chroma documents, then calls Mistral with context and question.
- **Edge cases:** No explicit catch, retry, conversation memory, or answer validation. UI stores the exchanges for display, but prior messages are not fed to the chain. Errors propagate to caller.

### `load_rag_chain()` — declared but broken alternate path

`core/rag_engine.py:load_rag_chain()` loads a vector store, then calls `get_retriever()` without the required `vector_store` positional argument. As written, it raises a `TypeError` before constructing the chain. The UI and CLI use `build_rag_chain(transcript)` instead, so this function is not on their normal path. This is an incomplete persistence-reopen path, not a working workflow.

## Classes, controllers, middleware, and background tasks

- **Project-defined classes:** None found in the main application source. The code is function-oriented.
- **Framework/library classes:** The source instantiates or composes `ChatMistralAI`, `ChatPromptTemplate`, `RecursiveCharacterTextSplitter`, `HuggingFaceEmbeddings`, `Document`, `Chroma`, and `yt_dlp.YoutubeDL`.
- **Controllers/services:** No formal controller/service classes. `app.py`'s button handler and `main.py:run_pipeline()` perform orchestration; the `core` modules provide service-like functions.
- **Middleware:** None. There is no web request middleware stack in the project; Streamlit handles its own web runtime.
- **Background tasks:** None. Processing and API calls run synchronously in the caller's execution flow. No task queue, worker, or scheduler appears.

## Interview discussion points

- Explain how audio chunking bounds input sizes and how sequential transcription preserves chunk order.
- Compare local Whisper with the remote Sarvam API path, including credentials, latency/network dependence, and temporary-piece cleanup.
- Walk through map-then-combine summarization and explain why its number of model calls depends on transcript length.
- Trace RAG from transcript split → embeddings → Chroma write → top-four similarity retrieval → context prompt → model response.
- Point out that Streamlit's visible chat history is not model conversation memory.
- Discuss operational edge cases visible in the implementation: synchronous long-running work, missing retries, local generated-file retention, repeated Chroma collection writes, and the unused broken `load_rag_chain()` helper.
