# Final SDE Interview Revision: AI Video Assistant

A compact review of the implementation. Treat the project as it exists in source: a single-process Python application with Streamlit and CLI entry points, local media/vector storage, and hosted AI calls.

## 1. Project introduction in 30 seconds

“AI Video Assistant turns a YouTube video or local audio/video file into meeting-style notes. It converts and chunks audio, transcribes English locally with Whisper or Hinglish through Sarvam, then uses Mistral to generate a title, summary, action items, decisions, and open questions. For follow-up questions, it embeds transcript chunks into local Chroma and retrieves relevant passages for a Mistral answer. It has a Streamlit UI and a CLI, both built on shared Python modules.”

## 2. Project introduction in 2 minutes

“Long recordings take time to review, so I built an assistant that extracts useful notes and supports questions about the recording. A user can provide a YouTube URL or local media path. `utils/audio_processor.py` downloads or converts the media to WAV and creates ten-minute chunks. `core/transcriber.py` routes English through a locally loaded Whisper model and Hinglish through Sarvam, where each chunk is split into 25-second requests.

The transcript is passed to separate LangChain/Mistral chains. `core/summarizer.py` generates a short title and uses a map-then-combine strategy for summaries. `core/extractor.py` asks for action items, decisions, and unresolved questions. For transcript chat, `core/vector_store.py` creates overlapping chunks, embeds them with `all-MiniLM-L6-v2`, and stores them in a local Chroma collection. `core/rag_engine.py` retrieves up to four similar chunks and sends them with the question to Mistral.

The Streamlit UI in `app.py` shows progress, results, and chat; `main.py` offers the same pipeline in a terminal. The project is modular but runs synchronously in one process. It has no custom REST API, user login, relational database, or background queue. The main areas I would improve before production are data isolation/cleanup in Chroma, robust input and HTML handling, retry and error policies, and persistent job processing.”

## 3. Main features

- URL or local media input; WAV conversion and ten-minute audio chunks.
- English transcription with local Whisper; Hinglish transcription/translation with Sarvam.
- Mistral title, chunked summary, action items, key decisions, and open questions.
- Transcript Q&A using Sentence Transformers embeddings, Chroma similarity retrieval (`k=4`), and Mistral.
- Streamlit UI with session-based result/chat display; CLI alternative.

## 4. Stack and why it is used

| Technology | Role in this codebase |
|---|---|
| Python | One language for UI, orchestration, media utilities, and AI integrations. |
| Streamlit | UI and per-session display state in `app.py`; it calls Python functions directly. |
| yt-dlp, Pydub, FFmpeg | Download, decode/convert, normalize, and chunk media. FFmpeg executable is external. |
| Whisper + PyTorch | Local English speech transcription; model reused in process. |
| Sarvam + `requests` | Hosted Hinglish speech-to-text/translation, called with short multipart WAV pieces. |
| LangChain / LCEL | Compose prompts, models, retrievers, transformations, and string parsing. |
| Mistral (`mistral-small-latest`) | Text generation for title, summary, extraction, and RAG answers. |
| Hugging Face Sentence Transformers | CPU embeddings via `all-MiniLM-L6-v2`. |
| Chroma | Local persistent vector store for semantic transcript retrieval. |
| `python-dotenv` | Load environment variables; `.env` is ignored by `.gitignore`. |

`Requirements.txt` contains packages not evidenced in direct source use (including PDF libraries and `deep-translator`). Source also imports `langchain_chroma` and `langchain_text_splitters`, whose standalone package names are not explicitly listed in that requirements file.

## 5. Architecture overview

**Single process, modular functions.** The entry points orchestrate and directly call modules; there is no separate backend API service.

```text
app.py (Streamlit) ─┐
                    ├─> process_input -> transcribe_all -> title/summary/extraction
main.py (CLI) ──────┘                                      -> build RAG chain
                                                                  ↓
                                            question -> Chroma retrieve -> Mistral
```

- `utils/audio_processor.py`: download/convert/chunk media.
- `core/transcriber.py`: Whisper/Sarvam selection and transcript assembly.
- `core/summarizer.py`, `core/extractor.py`: model-based notes.
- `core/vector_store.py`, `core/rag_engine.py`: vector indexing and QA.
- Streamlit uses `st.session_state`; vector data is local under `vector_db/`.

## 6. Most important workflows

1. **Analysis:** source → `process_input()` → `transcribe_all()` → title/summary/extractions → `build_rag_chain()` → display/print.
2. **Media:** URL uses yt-dlp/FFmpeg; local path uses Pydub/FFmpeg; audio becomes WAV chunks of ten minutes.
3. **Transcription:** English → cached local Whisper model; Hinglish → Pydub slices into 25-second WAV files → Sarvam → joined transcript.
4. **Summary:** split at 3,000 characters with 200 overlap → summarize each chunk sequentially → combine partial summaries.
5. **RAG:** split at 500 characters with 50 overlap → embed → write Chroma → retrieve top four chunks per question → prompt Mistral.
6. **Chat:** `ask_question()` receives the current question and chain. UI chat history is displayed from session state but is not passed into the model as prior-turn memory.

## 7. Most important classes and functions

The project defines no application classes. Important library classes include `ChatMistralAI`, `Chroma`, `Document`, and `HuggingFaceEmbeddings`.

- `main.py:run_pipeline(source, language)`: CLI orchestration; returns notes plus the RAG chain.
- `utils/audio_processor.py:process_input()`: URL/path branching and media pipeline.
- `utils/audio_processor.py:download_youtube_audio()`, `convert_to_wav()`, `chunk_audio()`: acquisition and file transforms.
- `core/transcriber.py:transcribe_all()`, `transcribe_chunk()`: sequential processing and engine selection.
- `core/transcriber.py:load_model()`: lazy module-level Whisper model reuse.
- `core/transcriber.py:transcribe_chunk_sarvam()`, `_send_to_sarvam()`: 25-second slicing and API request.
- `core/summarizer.py:summarize()`, `generate_title()`: map/combine summary and title prompt.
- `core/extractor.py:build_chain()` and three extraction functions: task-specific Mistral prompts.
- `core/vector_store.py:build_vector_store()`, `get_retriever()`: chunk, embed, persist, retrieve.
- `core/rag_engine.py:build_rag_chain()`, `ask_question()`: retrieval-grounded response.
- `app.py` Analyze handler: UI orchestration and broad pipeline error boundary.

## 8. Database relationships

There is no relational database, ORM, SQL schema, or foreign key. Chroma stores logical vector records in collection `meeting_transcript` under `vector_db/`. Each record receives chunk text (`Document.page_content`), `chunk_index` metadata, and an embedding. The app supplies no transcript ID or explicit record ID. Conceptually: one transcript is split into many chunks; each chunk becomes one embedded record; the collection contains many records. `get_retriever()` requests up to four similar records.

No explicit update, delete, collection reset, or transaction is implemented. Repeated analyses use the same collection without app-level cleanup or per-session filtering, so old content may remain and mix with new content.

## 9. Important APIs

- **Sarvam:** `POST https://api.sarvam.ai/speech-to-text-translate`, implemented by `core/transcriber.py:_send_to_sarvam()`. Sends multipart WAV `file`, `model`, `with_diarization=false`, and `api-subscription-key`; timeout 120 seconds. Source consumes JSON `transcript`.
- **Mistral:** Called through LangChain `ChatMistralAI`; code uses model `mistral-small-latest` and `MISTRAL_API_KEY`. The repository does not define its raw HTTP endpoint/schema.
- **Inbound project API:** None. Streamlit UI calls Python functions directly; no custom HTTP routes.

## 10. Most challenging technical implementation

A strong example to explain is transcript RAG: chunking balances model context and retrieval granularity; embeddings convert text into vectors; Chroma selects semantically similar passages; LangChain passes passages plus the current question into a prompt; Mistral generates an answer. Explain that the “answer only from context” rule is a prompt instruction, not a guarantee validated by code.

A second example is adapting long recordings to provider limits: ten-minute audio chunks are further split into 25-second Sarvam pieces, sent one at a time, concatenated, and temporary pieces are removed in `finally`.

## 11. Performance considerations

- Processing is synchronous and mostly sequential; long media blocks interaction.
- Whisper inference and CPU embedding can be expensive.
- Summary makes one Mistral call per transcript chunk plus a combine call; title and three extractors add further calls.
- Sarvam is called once per 25-second piece; there is no retry/backoff or concurrency control.
- Chroma re-embeds transcripts on each build; no cache, deduplication, or cleanup is present.
- UI and CLI do not report per-stage timings or resource metrics.

## 12. Security considerations

- No user authentication/authorization, rate limiting, custom CORS, or access-control layer is implemented.
- API keys use environment variables and `.env` is ignored, but `core/transcriber.py` captures `SARVAM_API_KEY` at import time. `app.py`/`main.py` import core before `load_dotenv()`, which can make `.env`-only Sarvam configuration unavailable; `test.py` loads dotenv first.
- UI accepts a path string or URL without robust host/path/file validation.
- Dynamic transcript/model/chat text is interpolated into `unsafe_allow_html=True` markup in `app.py`; render dynamic values as text or escape them.
- Audio is sent to Sarvam for Hinglish; transcript text is sent to Mistral. There is no redaction/consent layer in source.
- Print statements may expose transcript excerpts, questions, answers, and provider response bodies.

## 13. Current limitations

- One process, synchronous execution; no worker queue or durable job status.
- No custom REST API, user accounts, relational store, or persistent chat history.
- Chroma has one fixed collection and no app-level session isolation, cleanup, delete, or explicit IDs.
- `load_rag_chain()` is broken: it calls `get_retriever()` without the required vector-store argument; normal entry points instead call `build_rag_chain(transcript)`.
- No retries, structured logging, metrics, or formal test suite (`test.py` is an example script).
- PDF/TXT export libraries are listed but export code is absent.
- Dependency manifest is not pinned and has some source/manifest package gaps.

## 14. Future improvements

1. Fix configuration loading order and centralize validated settings.
2. Escape/render user and model text safely; validate URLs, file paths, types, size, and duration.
3. Give each analysis a stable ID, filter Chroma by it, and implement update/delete/retention.
4. Add tests around chunking, routing, error cases, and RAG behavior; repair and test `load_rag_chain()`.
5. Add structured, redacted logs; safe UI errors; bounded retries/timeouts and stage metrics.
6. Move long analyses to background workers with job status and durable result storage if multi-user scale is needed.
7. Pin dependencies and reconcile `Requirements.txt` with actual imports.
8. Add authentication/network protections before public deployment.

## 15. Top 25 probable questions with short answers

1. **What does the project do?** Turns recordings into transcripts, notes, and transcript-grounded Q&A.
2. **How does input become audio chunks?** `process_input()` uses yt-dlp for URLs or Pydub conversion for local paths, then writes ten-minute WAV chunks.
3. **How is speech recognition selected?** `transcribe_chunk()` sends case-insensitive `hinglish` to Sarvam; other values go to Whisper.
4. **Why chunk the audio?** To process long media in bounded pieces; Sarvam further requires pieces shorter than its stated limit.
5. **How does Whisper reuse its model?** `load_model()` lazily stores it in module-global `_model` for the process.
6. **How does the summary work?** Mistral summarizes 3,000-character chunks with 200 overlap, then combines the partial summaries.
7. **How are action items extracted?** A task-specific LangChain prompt invokes Mistral and returns plain text.
8. **What is RAG in this project?** Embed transcript chunks, retrieve similar passages for a question, and send those passages with the question to Mistral.
9. **What does Chroma persist?** Chunk text, metadata, and embeddings in `vector_db/`, collection `meeting_transcript`.
10. **What does `k=4` mean?** The retriever requests up to four similar transcript chunks.
11. **Is there a relational database?** No; Chroma is the only database-like component, with no ORM or SQL schema.
12. **Does the project expose REST endpoints?** No; Streamlit calls Python modules in-process.
13. **How does the Sarvam request work?** Multipart POST with WAV, model, diarization flag, API-key header, and 120-second timeout.
14. **How are Mistral calls made?** Via LangChain `ChatMistralAI` with `mistral-small-latest`.
15. **Does chat history go to the LLM?** No; it is displayed from Streamlit state, while the chain receives only the current question and retrieved context.
16. **What is stored in Streamlit state?** Current result/RAG chain, chat display history, pipeline status and completion flag.
17. **How are errors handled?** Streamlit catches analysis exceptions broadly; core functions and CLI mostly propagate them; chat is outside that pipeline catch.
18. **What is an important incomplete path?** `load_rag_chain()` omits the required vector-store argument when calling `get_retriever()`.
19. **How could repeated analyses affect Chroma?** Same collection is reused without explicit clear or session metadata, risking stale/mixed chunks.
20. **What is one security issue?** Dynamic content is interpolated into HTML rendered with `unsafe_allow_html=True`.
21. **How are API keys managed?** Environment variables and dotenv; `.env` is in `.gitignore`, but Sarvam key import timing is problematic in UI/CLI.
22. **Is the app asynchronous?** No; calls and chunk loops run synchronously.
23. **What is the main latency cost?** Local Whisper, sequential Sarvam calls, multiple Mistral requests, and CPU embedding.
24. **How would you scale it?** Add per-analysis IDs/isolation, durable storage, background workers, job status, and controlled concurrency.
25. **What would you improve first?** Fix config ordering, safe rendering/input validation, and Chroma isolation/cleanup; then add tests and observability.

## Important files to revisit

- `app.py` — Analyze flow, Streamlit state, dynamic HTML, chat.
- `main.py` — `run_pipeline()` and CLI loop.
- `utils/audio_processor.py` — URL/local branching, WAV conversion, chunking.
- `core/transcriber.py` — Whisper caching, Sarvam request and 25-second slicing.
- `core/summarizer.py` — map/combine logic and title truncation.
- `core/extractor.py` — prompt chain and plain-text extraction.
- `core/vector_store.py` — chunk metadata, embedding, collection persistence, retriever.
- `core/rag_engine.py` — RAG chain, `ask_question()`, incomplete `load_rag_chain()`.
- `Requirements.txt`, `.gitignore` — dependencies and local secret-file exclusion.

## Checklist before the interview

- [ ] Explain the end-to-end flow without mixing up audio chunks and transcript chunks.
- [ ] State which work is local (Whisper, embeddings, Chroma) and which is remote (Sarvam, Mistral).
- [ ] Explain map-then-combine summarization and top-four RAG retrieval.
- [ ] Clarify that the UI has no custom backend API and no user authentication.
- [ ] Explain Chroma's logical record fields and missing session/recording ID.
- [ ] Know that chat display history is not model memory.
- [ ] Describe pipeline error handling and what is not rolled back.
- [ ] Be ready to discuss the broken `load_rag_chain()` path and Sarvam environment import order.
- [ ] Mention unsafe dynamic HTML rendering as a security issue and suggest escaping/plain-text rendering.
- [ ] Avoid claiming export, tests, background workers, ORM, or deployment features that are not implemented.

## Five difficult follow-up questions

1. **How would you stop one user's RAG search from returning another recording's chunks?** Add analysis/user identifiers to metadata and enforce filters or separate collections, plus deletion and retention rules.
2. **If Sarvam fails after several pieces, how would you retry without duplicate transcript text?** Track each piece's result by stable index, retry only transient failures with bounded backoff, and concatenate once in index order.
3. **How would you prove the RAG answer is supported by the retrieved transcript?** Evaluate retrieval and answer grounding, attach source chunk references, and add a verification/abstention step; the current prompt alone does not guarantee grounding.
4. **How would you safely make this asynchronous and multi-user?** Add authenticated request/job creation, a queue and workers, durable job/result state, per-user data isolation, and bounded provider concurrency.
5. **What would you fix before exposing the current UI publicly?** Safe rendering, strict source/file validation, authentication/access controls, secret loading, resource/rate limits, and per-analysis storage isolation.
