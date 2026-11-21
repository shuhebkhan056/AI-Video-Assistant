# Project-Specific SDE Interview Question Bank

Answers are written to be spoken in roughly 20–40 seconds. “Why it matters” gives a beginner-friendly framing; “Project evidence” points to the implementation; and “Follow-up” suggests the next question an interviewer may ask.

## Basic questions (20)

### 1. Basic project introduction

#### B1. What does your project do?
- **Why it matters:** This is the short opening summary of the project.
- **Interview-ready answer:** “AI Video Assistant takes a YouTube URL or local media path, turns its audio into a transcript, generates a title and meeting notes, and lets me ask questions about the transcript using retrieval-augmented generation.”
- **Project evidence:** `app.py`; pipeline in `main.py:run_pipeline()`; media in `utils/audio_processor.py`.
- **Likely follow-up:** What problem does it solve?

#### B2. What problem does it solve, and who benefits?
- **Why it matters:** Interviewers want the user need, not only a feature list.
- **Interview-ready answer:** “It reduces the time needed to review long recordings by providing a searchable transcript, summary, action items, decisions, open questions, and question answering. It is useful to someone reviewing a meeting or long video.”
- **Project evidence:** Output fields assembled in `main.py:run_pipeline()` and rendered in `app.py`.
- **Likely follow-up:** Which features are actually implemented end to end?

#### B3. What are the main features?
- **Why it matters:** It shows you can explain the product scope clearly.
- **Interview-ready answer:** “It accepts URL or local media, converts and chunks audio, transcribes English locally with Whisper or Hinglish through Sarvam, generates title/summary/extractions with Mistral, and supports transcript Q&A with Chroma retrieval.”
- **Project evidence:** `utils/audio_processor.py`, `core/transcriber.py`, `core/summarizer.py`, `core/extractor.py`, `core/vector_store.py`, `core/rag_engine.py`.
- **Likely follow-up:** Which is the most technically interesting feature?

#### B4. What language and application framework does it use?
- **Why it matters:** This establishes the main implementation choices.
- **Interview-ready answer:** “The project is implemented in Python. Its graphical UI is built with Streamlit, and it also has a command-line entry point. Processing is organized into Python modules rather than a separate backend service.”
- **Project evidence:** `app.py`, `main.py`, `core/`, `utils/`.
- **Likely follow-up:** Why Streamlit for this kind of app?

#### B5. What are the application entry points?
- **Why it matters:** Entry points show how a user starts and reaches the logic.
- **Interview-ready answer:** “The browser UI starts through Streamlit using `app.py`. The CLI starts with `python main.py`; it calls `run_pipeline()` and then offers a terminal chat loop. `test.py` is a hard-coded example script, not a test suite.”
- **Project evidence:** `app.py`; `main.py` main guard; `test.py`.
- **Likely follow-up:** Do both user-facing entry points share processing logic?

#### B6. How does the UI communicate with the processing code?
- **Why it matters:** It clarifies whether the app has a separate REST backend.
- **Interview-ready answer:** “The Streamlit script directly calls Python functions such as `process_input()` and `transcribe_all()`. There is no custom REST API between a separately built frontend and backend.”
- **Project evidence:** Analyze handler in `app.py`; no route definitions in source.
- **Likely follow-up:** What would change if you split frontend and backend?

### 2. Project architecture

#### B7. How would you describe the overall architecture?
- **Why it matters:** It tests your ability to summarize module relationships.
- **Interview-ready answer:** “It is a single-process, modular Python application. Streamlit and CLI are two entry points; both orchestrate audio preparation, transcription, text generation, and RAG through shared modules.”
- **Project evidence:** `app.py`, `main.py`, `utils/audio_processor.py`, `core/*.py`.
- **Likely follow-up:** What are the main layers?

#### B8. What does the `utils` folder do compared with `core`?
- **Why it matters:** It checks whether you understand separation of responsibilities.
- **Interview-ready answer:** “`utils/audio_processor.py` handles media-specific work such as download, conversion, and chunking. The `core` modules handle transcription, summarization, extraction, embeddings, storage, and question answering.”
- **Project evidence:** `utils/audio_processor.py`; `core/transcriber.py`, `core/summarizer.py`, `core/extractor.py`, `core/vector_store.py`, `core/rag_engine.py`.
- **Likely follow-up:** Where does orchestration happen?

### 3. Technology stack

#### B9. Which external AI services and local models are used?
- **Why it matters:** The project combines remote and local computation.
- **Interview-ready answer:** “English transcription uses a local Whisper model backed by PyTorch. Hinglish audio is sent to Sarvam for transcription and translation. Mistral generates titles, summaries, extracted notes, and RAG answers.”
- **Project evidence:** `core/transcriber.py`, `core/summarizer.py`, `core/extractor.py`, `core/rag_engine.py`.
- **Likely follow-up:** What happens if Sarvam is unavailable?

### 4. Frontend questions

#### B10. How does the Streamlit UI keep results visible after interactions?
- **Why it matters:** Streamlit reruns its script when widgets are used.
- **Interview-ready answer:** “It stores the current result, chat history, completion flag, and pipeline step states in `st.session_state`. After a successful analysis or chat turn, `st.rerun()` redraws the page using that state.”
- **Project evidence:** Session initialization and result/chat logic in `app.py`.
- **Likely follow-up:** Is this durable storage or user authentication?

### 5. Backend questions

#### B11. Where is the project’s business logic?
- **Why it matters:** Interviewers distinguish UI code from domain processing.
- **Interview-ready answer:** “Most processing logic is in `core/`, while media conversion is in `utils/audio_processor.py`. The entry points coordinate those functions. There is no separate backend service class or REST controller layer.”
- **Project evidence:** `core/*.py`, `utils/audio_processor.py`, `app.py`, `main.py`.
- **Likely follow-up:** How would you test those functions independently?

### 6. Database questions

#### B12. What database does the application use?
- **Why it matters:** “Database” can mean more than a relational store.
- **Interview-ready answer:** “It uses Chroma as a local persistent vector store for transcript chunks. There is no SQL database or ORM in the code.”
- **Project evidence:** `core/vector_store.py`, collection `meeting_transcript`, directory `vector_db/`.
- **Likely follow-up:** What does it store in each record?

### 7. API and HTTP questions

#### B13. Does the project expose an API?
- **Why it matters:** A web UI does not automatically mean a custom REST API exists.
- **Interview-ready answer:** “There are no project-defined HTTP routes. Streamlit manages its own UI transport, and the app makes an outbound Sarvam HTTP request. Mistral is called through LangChain’s integration.”
- **Project evidence:** `core/transcriber.py:_send_to_sarvam()`; `app.py`; no FastAPI/Flask route code.
- **Likely follow-up:** What fields go to Sarvam?

### 8. Authentication and security

#### B14. How are API credentials handled?
- **Why it matters:** AI service keys should not be hard-coded in source.
- **Interview-ready answer:** “The code reads Mistral and Sarvam keys from environment variables, and `.gitignore` excludes `.env`. These keys authenticate the application to providers; the app has no end-user login.”
- **Project evidence:** `.gitignore`, `load_dotenv()` in entry points, `os.getenv()` calls in `core/`.
- **Likely follow-up:** Is `.env` loading order correct for every key?

### 9. Important functions and code logic

#### B15. What does `process_input()` return?
- **Why it matters:** It is the bridge between user input and speech recognition.
- **Interview-ready answer:** “It detects URL versus local path, downloads or converts the media to WAV, splits it into ten-minute chunks, and returns a list of chunk file paths.”
- **Project evidence:** `utils/audio_processor.py:process_input()`, `download_youtube_audio()`, `convert_to_wav()`, `chunk_audio()`.
- **Likely follow-up:** How is the WAV normalized?

#### B16. How does transcription choose between Whisper and Sarvam?
- **Why it matters:** This is a concrete branch in the application’s business logic.
- **Interview-ready answer:** “`transcribe_chunk()` lowercases the language string. If it equals `hinglish`, it uses Sarvam; every other value uses Whisper. `transcribe_all()` applies that choice to each chunk and joins the text.”
- **Project evidence:** `core/transcriber.py:transcribe_chunk()` and `transcribe_all()`.
- **Likely follow-up:** What could happen if an unsupported language value is passed?

### 10. Design patterns and OOP

#### B17. Does the project use object-oriented design heavily?
- **Why it matters:** Candidates should describe the code they have, not force patterns onto it.
- **Interview-ready answer:** “No. The project is mainly function-oriented. It uses library classes such as `ChatMistralAI`, `Document`, and `Chroma`, but defines no application classes or class hierarchy.”
- **Project evidence:** `core/` and `utils/` function definitions.
- **Likely follow-up:** What would be a reason to introduce classes?

### 13. Error handling

#### B18. How are analysis errors shown in the UI?
- **Why it matters:** It shows you understand failure boundaries.
- **Interview-ready answer:** “The Streamlit Analyze handler wraps the pipeline in a broad `try/except Exception`, sets any active step back to pending, and displays the exception text. The CLI has no equivalent top-level handler.”
- **Project evidence:** Analyze block in `app.py`; `main.py` main guard.
- **Likely follow-up:** What errors can happen after a database write?

### 14. Debugging and challenges

#### B19. What is one incomplete path you found?
- **Why it matters:** Honest code review is part of engineering interviews.
- **Interview-ready answer:** “`load_rag_chain()` appears intended to reopen persisted Chroma data, but calls `get_retriever()` without the required vector-store argument. The main app avoids it and builds the chain from the current transcript.”
- **Project evidence:** `core/rag_engine.py:load_rag_chain()` versus `build_rag_chain()`.
- **Likely follow-up:** How would you fix and test that path?

### 16. System design extensions

#### B20. How would you make this usable by several people at once?
- **Why it matters:** It connects current design to a realistic next stage.
- **Interview-ready answer:** “I would first add authentication and per-user/session isolation for transcripts and Chroma records. For long work, I would move analysis into background jobs and persist job status and results. Those pieces are not present today.”
- **Project evidence:** Single-process flow in `app.py`/`main.py`; one Chroma collection in `core/vector_store.py`.
- **Likely follow-up:** What identifier would you use to isolate each analysis?

## Intermediate questions (20)

### 2. Project architecture

#### I1. Walk through the complete request flow for an analysis.
- **Why it matters:** This checks whether you can trace control and data across modules.
- **Interview-ready answer:** “The UI or CLI passes a source to `process_input()`. Its chunk paths go to `transcribe_all()`. The transcript feeds title and summary generation, three extraction calls, then `build_rag_chain()` indexes it and returns a runnable chain. The entry point stores or prints the resulting outputs.”
- **Project evidence:** `app.py` Analyze block; `main.py:run_pipeline()`.
- **Likely follow-up:** Which steps call Mistral, and how many requests can summary require?

#### I2. Why have two entry points if they use the same modules?
- **Why it matters:** It tests understanding of reuse and separation.
- **Interview-ready answer:** “The Streamlit entry point provides an interactive UI and visible step states. The CLI is a simpler terminal flow. Both reuse the same processing functions, avoiding separate implementations of media and AI logic.”
- **Project evidence:** `app.py`, `main.py` imports and calls.
- **Likely follow-up:** Are they perfectly behavior-equivalent?

#### I3. What happens if the pipeline fails halfway through?
- **Why it matters:** Pipelines can leave partial side effects.
- **Interview-ready answer:** “In Streamlit, the exception is displayed, but generated files or a Chroma write from earlier steps are not rolled back. In the CLI, exceptions propagate. There is no job record or transaction spanning these steps.”
- **Project evidence:** `app.py` exception handler; `core/vector_store.py:build_vector_store()`.
- **Likely follow-up:** What cleanup or idempotency would you add?

### 3. Technology stack

#### I4. Why is LangChain used here?
- **Why it matters:** It tests whether a framework choice is connected to code behavior.
- **Interview-ready answer:** “LangChain composes prompts, model calls, output parsing, retrievers, and transformations into runnable chains. The project uses that composition in summarization, extraction, and RAG rather than making all provider requests and context plumbing manually.”
- **Project evidence:** `core/summarizer.py`, `core/extractor.py`, `core/rag_engine.py`.
- **Likely follow-up:** What is one trade-off of this abstraction?

#### I5. Which declared packages are not visibly used?
- **Why it matters:** Dependency hygiene is a practical engineering skill.
- **Interview-ready answer:** “The requirements list includes packages like `deep-translator`, PDF libraries, `streamlit-extras`, and `watchdog`, but the inspected source does not use them directly. Hinglish translation uses Sarvam. Also, source imports `langchain_chroma` and `langchain_text_splitters`, while the manifest does not explicitly list their standalone packages.”
- **Project evidence:** `Requirements.txt`; imports in `core/vector_store.py` and `core/summarizer.py`.
- **Likely follow-up:** How would you make installs reproducible?

### 4. Frontend questions

#### I6. How does chat history work, and is it sent to the model?
- **Why it matters:** UI history and conversational model memory are different concepts.
- **Interview-ready answer:** “`app.py` appends user and assistant messages to `st.session_state.chat_history` for display. `ask_question()` passes only the current question to the RAG chain; previous turns are not included in the model prompt.”
- **Project evidence:** `app.py` chat handler; `core/rag_engine.py:ask_question()`.
- **Likely follow-up:** How could you add context-aware follow-up turns?

#### I7. What are the limitations of the current Streamlit state approach?
- **Why it matters:** It clarifies what survives reruns versus restarts.
- **Interview-ready answer:** “Session state preserves values across Streamlit reruns for that session, but it is not durable application storage. There is no account model or persistent chat history, and results can disappear when the session/process ends.”
- **Project evidence:** `app.py` session state initialization and result storage.
- **Likely follow-up:** Where would durable results live in a production design?

### 5. Backend questions

#### I8. How does the summarization algorithm handle long transcripts?
- **Why it matters:** It asks about an important algorithmic choice.
- **Interview-ready answer:** “`split_transcript()` uses 3,000-character chunks with 200-character overlap. `summarize()` asks Mistral to summarize each chunk, joins those partial summaries, and makes a final combine call. It is sequential map-then-combine processing.”
- **Project evidence:** `core/summarizer.py:split_transcript()` and `summarize()`.
- **Likely follow-up:** What trade-offs come from overlap and sequential calls?

#### I9. How does `transcribe_chunk_sarvam()` handle service limits?
- **Why it matters:** It shows reasoning about provider constraints and data preparation.
- **Interview-ready answer:** “It reads each WAV chunk with Pydub, slices it into 25-second pieces, sends each piece individually, appends returned transcript text, and deletes the temporary piece in `finally`. The source comment says 25 seconds leaves a margin under Sarvam’s 30-second limit.”
- **Project evidence:** `core/transcriber.py:transcribe_chunk_sarvam()` and `_send_to_sarvam()`.
- **Likely follow-up:** What happens if the third piece fails?

#### I10. How is Whisper model loading optimized?
- **Why it matters:** Model startup can be expensive.
- **Interview-ready answer:** “`load_model()` stores the loaded Whisper model in module-global `_model` and only loads it when the value is `None`. Later chunks reuse the same model for that process.”
- **Project evidence:** `core/transcriber.py:load_model()`.
- **Likely follow-up:** What are the limitations of module-level caching?

### 6. Database questions

#### I11. Describe the logical Chroma record and indexing flow.
- **Why it matters:** It tests practical data modeling even without SQL.
- **Interview-ready answer:** “The transcript is split into 500-character chunks with 50-character overlap. Each LangChain `Document` contains chunk text and `chunk_index`; embeddings are generated with `all-MiniLM-L6-v2` and written to Chroma collection `meeting_transcript` under `vector_db/`.”
- **Project evidence:** `core/vector_store.py:build_vector_store()`.
- **Likely follow-up:** Is there a transcript ID or explicit record ID?

#### I12. What could go wrong when running analysis repeatedly?
- **Why it matters:** Persistence and lifecycle behavior matter to correctness.
- **Interview-ready answer:** “The code uses the same collection name and directory every time and does not explicitly clear old documents or attach a transcript/session ID. Repeated analyses may leave chunks from older recordings, so a question could retrieve unrelated context.”
- **Project evidence:** `core/vector_store.py:COLLECTION_NAME`, `CHROMA_DIR`, `build_vector_store()`.
- **Likely follow-up:** How would you isolate and clean collections?

### 7. API and HTTP questions

#### I13. Explain the Sarvam API request.
- **Why it matters:** It checks concrete HTTP integration details.
- **Interview-ready answer:** “`_send_to_sarvam()` sends a multipart POST to `/speech-to-text-translate`, includes the `api-subscription-key` header, WAV `file`, `model`, and `with_diarization=false` fields, and uses a 120-second timeout. It reads the JSON `transcript` field.”
- **Project evidence:** `core/transcriber.py:_send_to_sarvam()`.
- **Likely follow-up:** How are non-2xx responses handled?

#### I14. Does the application validate URLs or uploaded files robustly?
- **Why it matters:** Validation affects reliability and security.
- **Interview-ready answer:** “Not robustly. `process_input()` checks only whether the string starts with HTTP or HTTPS. It does not verify the host or local path before passing it to yt-dlp or Pydub. The UI accepts a path string, not a file upload.”
- **Project evidence:** `utils/audio_processor.py:process_input()`; `app.py` input widget.
- **Likely follow-up:** What restrictions would you add before exposing it publicly?

### 8. Authentication and security

#### I15. Identify a concrete security risk in the UI.
- **Why it matters:** Interviews often test ability to review output handling.
- **Interview-ready answer:** “`app.py` interpolates transcript, model output, and chat text into HTML strings rendered with `unsafe_allow_html=True`. Untrusted markup could be interpreted by the browser. I would render dynamic content as text or HTML-escape it.”
- **Project evidence:** Transcript rendering and chat HTML in `app.py`.
- **Likely follow-up:** Which values are user-controlled versus model-generated?

#### I16. Is there a user authentication mechanism?
- **Why it matters:** API credentials are often confused with user login.
- **Interview-ready answer:** “No. The API keys authenticate the app to Sarvam and Mistral. There is no user login, authorization layer, JWT, or access control in the project source.”
- **Project evidence:** `core/transcriber.py`, `core/*` LLM factories; no auth middleware/routes.
- **Likely follow-up:** How would you add multi-user access safely?

### 9. Important functions and code logic

#### I17. Explain the LCEL structure of the RAG chain.
- **Why it matters:** It evaluates whether you can reason through a composed pipeline.
- **Interview-ready answer:** “The input question is passed to two branches: one invokes the retriever and formats documents as context; the other passes the question through. The prompt combines both, Mistral generates an answer, and `StrOutputParser` returns a string.”
- **Project evidence:** `core/rag_engine.py:build_rag_chain()`.
- **Likely follow-up:** What does the `k=4` retriever setting control?

#### I18. How are action items and decisions extracted?
- **Why it matters:** It checks the difference between prompt-based extraction and deterministic parsing.
- **Interview-ready answer:** “Each public extractor supplies a task-specific prompt to `build_chain()`. The chain maps the transcript into the prompt, invokes Mistral, and parses the response as plain text. There is no JSON schema or validation of owners/dates.”
- **Project evidence:** `core/extractor.py:build_chain()` and extraction functions.
- **Likely follow-up:** How could you guarantee a stable response shape?

### 10. Design patterns and OOP

#### I19. What design patterns or architectural styles are visible?
- **Why it matters:** Use accurate pattern vocabulary.
- **Interview-ready answer:** “There is modular separation by responsibility, sequential pipeline orchestration, a strategy-like language branch for Whisper versus Sarvam, and LangChain chain composition. There is no formal strategy class, MVC framework, or dependency injection container.”
- **Project evidence:** `core/transcriber.py:transcribe_chunk()`; entry point flows; LangChain LCEL use.
- **Likely follow-up:** How would a formal strategy interface help if providers grew?

### 11. Performance and optimization

#### I20. Where are the main performance costs likely to be?
- **Why it matters:** It tests whether you can identify work from the code path.
- **Interview-ready answer:** “Likely costs include local Whisper inference, sequential Sarvam requests, repeated Mistral calls for each summary chunk and extraction task, and CPU embedding of all transcript chunks. The code does not measure these costs or execute calls concurrently.”
- **Project evidence:** `core/transcriber.py`, `core/summarizer.py`, `core/extractor.py`, `core/vector_store.py`.
- **Likely follow-up:** What would you profile first?

## Advanced questions (15)

### 11. Performance and optimization

#### A1. How would you reduce end-to-end latency without changing output semantics unnecessarily?
- **Why it matters:** It tests optimization grounded in the current call graph.
- **Interview-ready answer:** “I would measure stage timings first. The current chunk transcription and summary calls are sequential, and extraction tasks are independent after transcription, so controlled concurrency could reduce wall time. I would add provider rate-limit handling, bounded concurrency, and preserve transcript chunk order before enabling it.”
- **Project evidence:** Loops in `transcribe_all()` and `summarize()`; three independent extractor calls in `app.py`/`main.py`.
- **Likely follow-up:** How would you prevent rate-limit spikes or memory pressure?

#### A2. How would you optimize embedding and retrieval at larger transcript sizes?
- **Why it matters:** It asks how the prototype would evolve under larger workloads.
- **Interview-ready answer:** “I would profile embedding time, batch where supported, reuse embeddings for unchanged content, and use per-recording IDs with filtered retrieval. I would tune chunk size and retrieval count based on evaluation. Current code embeds the full transcript on each chain build using CPU and requests four results.”
- **Project evidence:** `core/vector_store.py:build_vector_store()`, `get_embeddings()`, `get_retriever()`.
- **Likely follow-up:** How would you evaluate retrieval quality rather than guess `k`?

### 12. Scalability

#### A3. What prevents the current app from scaling horizontally?
- **Why it matters:** Scaling requires understanding current state and persistence boundaries.
- **Interview-ready answer:** “The pipeline runs synchronously in one process, Whisper is cached in process memory, Streamlit state is session-local, and Chroma uses a local directory. Multiple instances would not automatically share results or vector data. A production design would externalize state and move work to workers.”
- **Project evidence:** `core/transcriber.py:_model`; `app.py:st.session_state`; `core/vector_store.py:CHROMA_DIR`.
- **Likely follow-up:** Which components would you externalize first?

#### A4. Design a background job flow for long videos.
- **Why it matters:** Long media makes synchronous request handling costly.
- **Interview-ready answer:** “I would accept the source, create a job ID, enqueue processing, and return the ID. A worker would run the existing stages and persist progress/results; the UI would poll or subscribe for status. Today, the pipeline executes inline and has no queue or durable job record.”
- **Project evidence:** Inline sequence in `app.py` and `main.py:run_pipeline()`.
- **Likely follow-up:** How would retries avoid duplicating Chroma chunks?

### 16. System design extensions

#### A5. How would you redesign Chroma storage for multiple recordings and users?
- **Why it matters:** Current fixed collection design has isolation implications.
- **Interview-ready answer:** “I would add a recording/session identifier to every chunk and filter retrieval by that identifier, plus define a retention and deletion policy. For stronger isolation, I could use separate collections or tenants. The current code writes chunks without a transcript ID into one collection.”
- **Project evidence:** `core/vector_store.py:build_vector_store()` metadata currently contains only `chunk_index`.
- **Likely follow-up:** How would you migrate existing vectors and handle users’ delete requests?

#### A6. How would you make analysis idempotent?
- **Why it matters:** Retried jobs should not duplicate persistent side effects.
- **Interview-ready answer:** “I would derive a stable analysis ID from the input/job and use stable chunk IDs or replace a scoped collection before re-indexing. I would record stage completion and make writes repeatable. Current `build_vector_store()` supplies no IDs and does not clear old records.”
- **Project evidence:** `core/vector_store.py:build_vector_store()`.
- **Likely follow-up:** What if a recording has changed but its source URL is the same?

#### A7. What changes are needed to provide a real API backend?
- **Why it matters:** It tests how to turn an interactive prototype into a service.
- **Interview-ready answer:** “I would add explicit HTTP routes for creating an analysis and asking questions, validate request schemas, authenticate users, return a job/result identifier, and isolate data by user/analysis. The existing modules can be reused behind handlers, but the current app defines no project REST endpoints.”
- **Project evidence:** `app.py` directly calls modules; `main.py` uses terminal I/O.
- **Likely follow-up:** Would analysis be synchronous or asynchronous, and why?

### 17. Difficult interviewer follow-ups

#### A8. The RAG prompt says “based ONLY” on transcript context. Does that guarantee grounded answers?
- **Why it matters:** Prompt instructions are not hard enforcement.
- **Interview-ready answer:** “No. It guides model behavior but does not mathematically guarantee grounding. The application retrieves up to four chunks and sends them with the question; it does not check citations, validate claims, or reject unsupported answers after generation.”
- **Project evidence:** System prompt and chain in `core/rag_engine.py:build_rag_chain()`.
- **Likely follow-up:** What evaluation or verification layer would you add?

#### A9. Does the current chat maintain conversational memory?
- **Why it matters:** A chat UI can display history without providing model memory.
- **Interview-ready answer:** “No. `chat_history` is used to render prior turns. `ask_question()` invokes the chain with the current question only, and the RAG chain retrieves transcript chunks. Follow-up references like ‘what about the second one?’ may lack context.”
- **Project evidence:** `app.py` chat history rendering; `core/rag_engine.py:ask_question()` and chain input.
- **Likely follow-up:** How would you preserve context while keeping answers transcript-grounded?

#### A10. Is `load_rag_chain()` usable for restart persistence today?
- **Why it matters:** It tests ability to distinguish intent from functioning code.
- **Interview-ready answer:** “Not as written. It loads a Chroma adapter, but calls `get_retriever()` without passing the required vector store, so it raises a `TypeError`. The normal entry points call `build_rag_chain(transcript)` instead.”
- **Project evidence:** `core/rag_engine.py:load_rag_chain()`; signature in `core/vector_store.py:get_retriever()`.
- **Likely follow-up:** What else would be needed to load the correct transcript safely?

#### A11. What is the `.env` loading-order issue?
- **Why it matters:** Configuration bugs can appear only in one workflow.
- **Interview-ready answer:** “`core/transcriber.py` reads `SARVAM_API_KEY` at module import. In `app.py` and `main.py`, core imports occur before `load_dotenv()`, so a key stored only in `.env` may be captured as `None`. `test.py` loads dotenv before core imports. I would load configuration first or defer reading the key.”
- **Project evidence:** Import order in `app.py`, `main.py`, `test.py`; module-level constant in `core/transcriber.py`.
- **Likely follow-up:** Why does the Mistral key behave differently?

#### A12. What data could leak through the current UI rendering or logs?
- **Why it matters:** Content often includes sensitive meeting information.
- **Interview-ready answer:** “Transcript and generated content are interpolated into `unsafe_allow_html=True` markup, which risks interpreting untrusted markup. CLI and module `print()` calls can also output transcript excerpts, questions, answers, or provider response bodies. I would escape dynamic HTML and redact or structure logs.”
- **Project evidence:** `app.py` transcript/chat rendering; `main.py` transcript excerpt; `core/rag_engine.py:ask_question()`; `core/transcriber.py` error logging.
- **Likely follow-up:** Which content should be considered untrusted?

#### A13. How would you handle provider retries correctly?
- **Why it matters:** Retrying blindly can increase cost or duplicate side effects.
- **Interview-ready answer:** “For read-like model requests, I would use bounded exponential backoff for transient timeouts or rate limits, with a maximum attempt count and telemetry. I would not retry validation/authentication failures. For vector writes, I would first make chunk IDs stable so retries are idempotent. Current code has no retry policy.”
- **Project evidence:** Direct `requests.post()` and chain `.invoke()` calls; no retry configuration in `core/`.
- **Likely follow-up:** How would you distinguish transient from permanent errors?

#### A14. What are the trade-offs in using local Whisper and hosted APIs together?
- **Why it matters:** It touches privacy, cost, latency, and reliability.
- **Interview-ready answer:** “Whisper keeps English transcription local after model setup, but consumes local compute and can be slow. Sarvam handles the Hinglish route remotely, which adds network/API dependency and sends audio externally. Mistral is also remote for text generation. The hybrid approach uses different strengths but means the app is not fully offline.”
- **Project evidence:** `core/transcriber.py`; Mistral integrations in `core/summarizer.py`, `core/extractor.py`, `core/rag_engine.py`.
- **Likely follow-up:** How would you offer a privacy-preserving mode?

#### A15. If asked to explain one algorithm from scratch, which would you choose?
- **Why it matters:** Interviewers often ask candidates to reconstruct a concrete part of their project.
- **Interview-ready answer:** “I would explain the RAG path: split a transcript into overlapping chunks, embed each chunk, store vectors, embed/search a question for the top similar chunks, join those passages as context, then send context plus question to an LLM. This project implements that with Chroma, Hugging Face embeddings, LangChain, and Mistral.”
- **Project evidence:** `core/vector_store.py:build_vector_store()` and `get_retriever()`; `core/rag_engine.py:build_rag_chain()` and `ask_question()`.
- **Likely follow-up:** What are the failure modes of chunking and nearest-neighbor retrieval?

## Quick project facts to memorize

- **UI entry point:** `app.py`; **CLI entry point:** `main.py`.
- **Main orchestration:** Streamlit Analyze block and `main.py:run_pipeline()`.
- **Media preparation:** `utils/audio_processor.py:process_input()`.
- **Transcription routing:** `core/transcriber.py:transcribe_chunk()`.
- **Long summary:** `core/summarizer.py:summarize()` uses 3,000-character chunks, 200 overlap, map then combine.
- **Meeting extraction:** `core/extractor.py` uses three Mistral prompt chains.
- **Vector store:** Chroma collection `meeting_transcript`, directory `vector_db/`; metadata includes `chunk_index`; retriever requests `k=4`.
- **External APIs:** Sarvam direct HTTP multipart request; Mistral through LangChain.
- **Important absences:** No custom REST routes, user auth, ORM, SQL database, background queue, custom middleware, retries, or formal test suite.
- **Notable issues:** Broken `load_rag_chain()` retriever call; fixed shared Chroma collection without app-level cleanup/session IDs; Sarvam key import-order concern in `app.py`/`main.py`; dynamic data rendered using `unsafe_allow_html=True`.
