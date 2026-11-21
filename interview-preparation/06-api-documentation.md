# API and Route Documentation

## Scope: what this project actually exposes

The inspected source defines **no application-owned HTTP API routes**. There are no FastAPI/Flask route decorators, controller endpoints, or custom request/response handlers. The browser interface is a Streamlit application in `app.py`; Streamlit manages its web transport and reruns the Python script when a user interacts with widgets. The repository does not define or document Streamlit's internal transport as a project API.

The project makes one direct HTTP API request in its own source: Sarvam speech-to-text-and-translate from `core/transcriber.py`. It also calls Mistral through the LangChain `ChatMistralAI` integration, but source code does not specify the provider's HTTP endpoint, method, or wire request schema. Those details belong to the SDK/integration and cannot be documented as actual project-defined routes here.

## Implemented outbound API: Sarvam speech-to-text-and-translate

| Item | Actual implementation |
|---|---|
| HTTP method | `POST` via `requests.post()` |
| Endpoint | `https://api.sarvam.ai/speech-to-text-translate` |
| Purpose | Transcribe and translate short Hinglish audio pieces into English text. |
| Caller / handler | `core/transcriber.py:_send_to_sarvam(piece_path)`; invoked by `transcribe_chunk_sarvam()` and routed by `transcribe_chunk()`. |
| Authentication | Sarvam subscription key in the `api-subscription-key` header. The code reads `SARVAM_API_KEY` from environment at module import. It is provider authentication, not end-user authentication. |
| Content type | Multipart form data. `requests` constructs the multipart request because `files` and `data` are passed. |
| Timeout | 120 seconds per piece request. |

### Request fields

The source passes:

- **File part `file`:** The short WAV file, with its basename and MIME type `audio/wav`.
- **Form field `model`:** `SARVAM_MODEL`, default `saaras:v2.5` and overrideable by `SARVAM_STT_MODEL`.
- **Form field `with_diarization`:** Literal string `false`.
- **Header `api-subscription-key`:** Value of `SARVAM_API_KEY`.

A conceptual `curl` example for the request shape is:

```bash
curl --request POST \
  'https://api.sarvam.ai/speech-to-text-translate' \
  --header 'api-subscription-key: <SARVAM_API_KEY>' \
  --form 'file=@piece.wav;type=audio/wav' \
  --form 'model=saaras:v2.5' \
  --form 'with_diarization=false'
```

This is an illustration of the fields built by `_send_to_sarvam()`, not a request issued by the application as a command.

### Validation and processing before the request

The endpoint is reached only via `transcribe_chunk_sarvam(chunk_path)`:

1. It checks that `SARVAM_API_KEY` is truthy. If absent, it raises `RuntimeError` before sending a request.
2. It opens the supplied chunk as WAV with `AudioSegment.from_wav()`.
3. It divides that chunk into pieces no longer than 25 seconds. This stays below the 30-second limit noted in the source comment.
4. Each piece is exported to a temporary WAV path and passed to `_send_to_sarvam()`.
5. `_send_to_sarvam()` sends the file and fields above. The code does not separately validate audio content, duration, or model name at the HTTP call site; duration is bounded by the preceding slicing step.
6. A `finally` block removes each generated short piece after its request attempt.

The main `process_input()` flow produces ten-minute WAV chunks, but the Sarvam route then splits them into 25-second pieces. These are separate chunking stages for separate reasons.

### Response consumed by the project

On a successful HTTP response, `_send_to_sarvam()` parses JSON and returns:

```python
response.json().get("transcript", "")
```

Thus, the only response field explicitly consumed by project code is `transcript`, expected to be text. The application does not validate a full response schema. If that key is absent, it treats the result as an empty string. The exact full provider response schema is not defined in this repository.

The text is appended to `full_text` in `transcribe_chunk_sarvam()`. `transcribe_all()` then joins each chunk's text into one transcript string for summarization and extraction.

### Errors

- Missing key: explicit `RuntimeError("SARVAM_API_KEY is not set in environment / .env")` from `transcribe_chunk_sarvam()`.
- Non-success response: logs the status and response body, then calls `response.raise_for_status()`. `requests` raises an HTTP error; this source does not map it to a custom response payload.
- Network/timeout error: `requests` exceptions propagate. The request timeout is 120 seconds.
- Invalid/unreadable audio: Pydub/file errors propagate before or during piece creation.
- Missing `transcript` response key: no exception; returns empty text via `.get()` default.
- Cleanup: temporary request-piece WAV files are removed in `finally`, including when `_send_to_sarvam()` fails. Original ten-minute chunks remain.

There is no application API client receiving these errors and converting them to a standardized JSON error response. In the Streamlit analysis flow, the outer `try/except` displays the exception text in the UI. In the CLI, exceptions generally terminate the run.

## Mistral calls (SDK-managed outbound requests, not project routes)

The project creates `ChatMistralAI` instances and invokes LangChain chains from:

- `core/summarizer.py:get_llm()`, used by `generate_title()` and `summarize()`.
- `core/extractor.py:get_llm()`, used by `build_chain()` and the three extraction functions.
- `core/rag_engine.py:get_llm()`, used by the RAG chain.

The configured model is `mistral-small-latest`; credentials come from `MISTRAL_API_KEY`. Prompts and text inputs are passed to LangChain, which invokes the SDK integration. The repository does not call `requests` directly for Mistral and contains no literal Mistral URL, HTTP method, headers, or wire body schema. Therefore no concrete HTTP endpoint or body example can be accurately given from this codebase. Mistral/API errors are not caught inside these modules; they propagate to the caller.

Chroma retrieval is local database access through LangChain and is not an HTTP API route. YouTube media acquisition uses yt-dlp; this repository does not define a YouTube HTTP API request. The Google Fonts `@import` in `app.py` is a browser CSS resource request, not an application API.

## Routing, frontend/backend communication, and middleware

### Routing

- **Custom application routes:** None.
- **Streamlit UI:** `app.py` defines widgets and top-level script logic, not URL route handlers. Streamlit hosts the app and handles widget interactions; `app.py` responds by re-executing its code and reading/writing `st.session_state`.
- **CLI:** `main.py` uses `input()` and `print()`; it has no HTTP routing.
- **External Sarvam route:** The only literal application-level API endpoint is the fixed URL in `core/transcriber.py`.

### Frontend/backend communication

There is no separately implemented frontend/backend API boundary. Streamlit UI code and backend processing functions run within the same Python application. The button handler calls `process_input()`, `transcribe_all()`, summarization, extraction, and RAG functions directly; it does not serialize a request to a project REST endpoint. In the CLI path, orchestration and processing also happen through in-process function calls.

### Middleware

No custom middleware is implemented. There is no authentication middleware, request logging middleware, CORS configuration, rate limiter, or exception middleware in the project source. Streamlit and third-party libraries provide their own runtime behavior, but custom middleware is not present.

### Authentication and authorization

- There is no user login, user identity, role, or authorization logic.
- `MISTRAL_API_KEY` and `SARVAM_API_KEY` authenticate the application to external AI providers only.
- The local Streamlit UI has no project-level access-control checks in the inspected code.

### Request validation

- The UI checks that the input source is not blank before beginning analysis.
- `process_input()` only distinguishes strings beginning with `http://` or `https://` from local paths; it does not validate URL host or file existence before delegating.
- The language selector offers `english` and `hinglish` in Streamlit. In code, only case-insensitive `hinglish` selects Sarvam; any other value selects Whisper.
- Sarvam flow checks for a configured API key and slices audio before transmission. It does not implement a separate schema-validation layer for provider responses.
- No API request validation framework or typed request model exists.

### Error delivery

Because there are no project-defined HTTP endpoints, the code has no API response status/body contract. Analysis errors in Streamlit are caught by the Analyze handler and shown with `st.error`-style UI feedback (the code uses the error slot associated with the progress placeholder). Chat request errors are outside that analysis `try/except`. CLI errors propagate and may terminate the process. Sarvam HTTP errors are raised by `requests` rather than translated into application-defined HTTP responses.

## APIs and routes not implemented

The following should not be presented as existing endpoints or features:

- REST endpoints for upload, analysis, chat, authentication, or export.
- A custom backend API consumed by the Streamlit UI.
- A project-owned Mistral HTTP route or documented wire schema.
- CRUD routes for Chroma/database records.
- Middleware-based authentication, authorization, or validation.

These capabilities could be added later, but are not present in the inspected source.
