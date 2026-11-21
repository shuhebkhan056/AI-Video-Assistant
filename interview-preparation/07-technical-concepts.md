# Technical Concepts in the Project

This guide distinguishes concepts present in the code from common backend topics that are not implemented here. The application is a synchronous Python/Streamlit project with local processing and calls to external
Analyze the important engineering concepts implemented in this project.

Create:

interview-preparation/07-technical-concepts.md

Cover relevant concepts actually used in the codebase, such as:

- Authentication and authorization.
- JWT and sessions.
- Middleware.
- Asynchronous programming.
- Promises and async/await.
- Database indexing.
- Caching.
- Pagination.
- File uploads.
- API integration.
- Background processing.
- State management.
- Dependency injection.
- Design patterns.
- Other important project-specific concepts.

For each concept:
1. Explain it in simple language.
2. Explain why it is needed.
3. Show where it is implemented.
4. Explain how it works internally in this project.
5. Give a practical example from the source code.
6. Mention potential interview questions.

Create:

interview-preparation/08-security-and-error-handling.md

Cover:
- Authentication security.
- Authorization checks.
- Input validation.
- Password handling, if applicable.
- Environment variables and secrets.
- CORS configuration.
- SQL/NoSQL injection risks.
- Error handling.
- Logging.
- Rate limiting, if implemented.
- Other relevant security concerns.

IMPORTANT:
Do not claim a security mechanism exists unless verified in source code.

Separate implemented protections from missing protections and suggested improvements.

Do not modify source code.
 AI services.

## 1. Authentication and authorization

- **Simple meaning:** Authentication answers “who are you?”; authorization answers “what are you allowed to do?”
- **Why needed:** These control access in multi-user applications.
- **Where/how here:** No user authentication or authorization exists in `app.py`, `main.py`, or the processing modules. `MISTRAL_API_KEY` and `SARVAM_API_KEY` authenticate the application to AI providers, not a user to this app.
- **Example:** `core/transcriber.py` sends `SARVAM_API_KEY` in the provider header.
- **Interview questions:** What is the difference between authentication and authorization? Would provider API keys count as user authentication? No: they identify the calling app/account to the provider.

## 2. JWT and sessions

- **Simple meaning:** JWT is a signed token often used to carry identity claims; a session is server-side state associated with a user/browser interaction.
- **Why needed:** Both can support authenticated multi-user applications.
- **Where/how here:** No JWT library or token handling is present. Streamlit's `st.session_state` in `app.py` stores transient UI state (`result`, `chat_history`, pipeline status) for a Streamlit session; this is not authentication and contains no user identity check.
- **Example:** The app appends user/assistant display messages to `st.session_state.chat_history`, and clears that list when the user starts another analysis or clicks Clear Chat.
- **Interview questions:** Is Streamlit session state an authenticated session? No. What data is stored there? Results and UI interaction state.

## 3. Middleware

- **Simple meaning:** Middleware is code that runs around requests, commonly for authentication, logging, or error conversion.
- **Where/how here:** No custom middleware or custom HTTP request stack exists. Streamlit manages its own web runtime, but the source does not add middleware.
- **Interview questions:** Where would you enforce authentication or request logging in a REST service? In middleware or a framework dependency layer; this project has neither.

## 4. Synchronous versus asynchronous work

- **Simple meaning:** Synchronous work waits for each operation to finish before continuing. Asynchronous work can suspend while waiting for I/O and let other work proceed.
- **Where/how here:** The application is synchronous. `app.py` and `main.py` call functions directly; `requests.post()` in `core/transcriber.py` waits for Sarvam. LangChain `.invoke()` waits for model calls. There are no Python `async def`, `await`, threads, queues, or background workers in application source.
- **Why relevant:** Long downloads, local transcription, embedding, and hosted model calls can keep an interaction waiting.
- **Example:** `transcribe_all()` loops over chunks and finishes one `transcribe_chunk()` call before starting the next.
- **Interview questions:** What is the impact of sequential I/O? How might you add concurrency safely? Which model/API calls are suitable for asynchronous execution, and how would you handle rate limits and ordering?

## 5. Caching

- **Simple meaning:** Keep an expensive result in memory so it does not need to be recreated for every use.
- **Where/how here:** `core/transcriber.py:load_model()` uses module global `_model`; it calls `whisper.load_model()` only when `_model is None`, then reuses that model for later chunks in the process.
- **Why needed:** Model loading is costly; caching avoids reloading once per audio chunk.
- **Limitations:** This is process-local model reuse, not a general cache for transcript, LLM, or embedding results. It resets when the process restarts and has no eviction/invalidation logic.
- **Interview questions:** What is the cache key? There is no explicit key; the module loads the configured model once. What happens if the configured model changes during process lifetime? The already cached object remains.

## 6. Database indexing and retrieval

- **Simple meaning:** A vector index supports finding text with similar meaning, even if wording differs.
- **Where/how here:** `core/vector_store.py:build_vector_store()` splits transcript into chunks, embeds each with `all-MiniLM-L6-v2`, and writes to Chroma. `get_retriever()` requests similarity search with `k=4`; `core/rag_engine.py` uses retrieved chunks in the answer prompt.
- **Why needed:** Finds relevant transcript context for questions without placing the entire transcript in each prompt.
- **Limitations:** No custom index configuration, metadata filtering, pagination, or explicit cleanup exists.
- **Interview questions:** What does `k=4` mean? Up to four similar chunks are requested. How would you isolate multiple recordings? Add stable recording IDs and filter by them.

## 7. File handling and uploads

- **Simple meaning:** File handling reads, transforms, and writes content on disk. A web upload usually transfers file bytes to a server.
- **Where/how here:** The UI accepts a path or URL in a text field, not an uploaded file widget. `utils/audio_processor.py` downloads from URL or opens a local path with Pydub, normalizes audio, and writes WAV chunks. Sarvam processing creates short temporary WAV pieces and removes those pieces after each request.
- **Why needed:** Speech recognizers expect audio, not arbitrary input video formats.
- **Interview questions:** Is this a browser file upload? No, it asks for a path string. Where are intermediate files kept? Downloaded files under `downloades/`, converted/chunked files near the media path, and temporary Sarvam pieces alongside chunk paths.

## 8. API integration

- **Simple meaning:** A program sends a request to another service and processes its response.
- **Where/how here:** `_send_to_sarvam()` in `core/transcriber.py` sends multipart audio with `requests.post()` and reads JSON `transcript`. Mistral is used through `ChatMistralAI` and LangChain chains in `core/summarizer.py`, `core/extractor.py`, and `core/rag_engine.py`.
- **Why needed:** Speech translation and generative language-model tasks are provided by external services.
- **Example:** Sarvam request uses `api-subscription-key`, model form field, audio file, and a 120-second timeout.
- **Limitations:** No retry/backoff logic is implemented; a failing call propagates an exception.
- **Interview questions:** How are timeouts and errors handled? How would you add retries without duplicating side effects? How should secrets be configured in production?

## 9. State management

- **Simple meaning:** State management stores values needed across UI interactions.
- **Where/how here:** `app.py` stores `result`, `chat_history`, `pipeline_done`, and `pipeline_steps` in `st.session_state`; Streamlit reruns the script and these values allow results to remain visible. `main.py` keeps values in local variables for the life of its process.
- **Example:** Starting a new analysis clears the old result and chat history; successful output stores the transcript, notes, and RAG chain in `result`.
- **Limitations:** This is not durable storage; state is not saved as a user/account record and can be lost when the session/process ends.
- **Interview questions:** What is the difference between UI state and persistence? Why is chat history not automatically model memory? The chain receives only the current question.

## 10. Dependency injection and modular design

- **Simple meaning:** Dependency injection passes a dependency into a component instead of having it construct the dependency internally.
- **Where/how here:** There is no DI container. Some functions receive values directly, such as `get_retriever(vector_store, k=4)` or `ask_question(rag_chain, question)`. However, model factories like `get_llm()` construct their own Mistral wrapper and read environment variables internally.
- **Why relevant:** Direct parameters make some components easier to reuse; internally constructed model clients couple code to Mistral configuration.
- **Interview questions:** Which function has an injected dependency? `ask_question()` receives a chain; how could you make LLM provider/model configuration more testable?

## 11. Design patterns and pipelines

- **Pipeline:** The entry points run source → audio chunks → transcript → generated notes → vector index. Implemented in `app.py` and `main.py:run_pipeline()`.
- **Strategy-like branch:** `transcribe_chunk()` chooses Whisper or Sarvam based on language. It is a conditional, not a formal strategy class hierarchy.
- **Map then combine:** `summarize()` summarizes transcript pieces and then combines partial summaries.
- **Chain composition:** LangChain's LCEL pipes prompt, model, retrieval, formatting, and output parsing in `core/summarizer.py`, `core/extractor.py`, and `core/rag_engine.py`.
- **Interview questions:** What are the tradeoffs of an in-process pipeline? Why chunk long inputs? What changes would be needed to move long-running steps into a queue?

## 12. Pagination and background processing

- **Pagination:** Not implemented. The transcript and chat history are rendered as current session content; there are no page/offset/cursor parameters.
- **Background processing:** Not implemented. No worker or queue exists; work is performed inline and sequentially.
- **Interview questions:** How would you process a long video without blocking a request? A job queue plus persistent job status is one approach; that architecture is not present here.

## 13. Other project-specific concepts

- **Chunking:** Audio is chunked into ten-minute WAVs; Sarvam pieces are 25 seconds; summaries use 3,000-character chunks with overlap; RAG indexing uses 500-character chunks with overlap. Chunking bounds processing input and supports retrieval.
- **Prompt-based extraction:** `core/extractor.py` asks an LLM to format action items, decisions, and questions. The output is plain text, not validated structured data.
- **Session-scoped chat display versus retrieval:** UI history is displayed from `chat_history`, but the RAG prompt is called with only the current question plus retrieved transcript context. There is no prior-turn memory.

## Not used in this project

No project-level auth/JWT, middleware, async/await, promises (JavaScript concept), pagination, ORM, relational indexes, browser file upload flow, background queue, or formal dependency injection framework appears in the inspected code.
