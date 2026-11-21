# Security and Error Handling

This review describes protections present in the inspected source and separates them from risks or possible improvements. It is not a claim that absent protections are provided by the framework or deployment environment.

## Implemented protections and behavior

### Provider credentials and environment configuration

- API keys are read from environment variables: `MISTRAL_API_KEY` in `core/summarizer.py`, `core/extractor.py`, and `core/rag_engine.py`; `SARVAM_API_KEY` in `core/transcriber.py`.
- `app.py` and `main.py` call `load_dotenv()`. `test.py` loads `.env` before importing core modules.
- `.gitignore` contains `.env`, which helps prevent accidental commits of that local file.
- `core/transcriber.py:transcribe_chunk_sarvam()` checks for a missing Sarvam key and raises a clear `RuntimeError` before sending the request.

These measures keep credentials out of source literals, but the repository does not provide a production secret manager, key rotation, or comprehensive configuration validation.

### Some validation and cleanup

- `app.py` rejects blank/whitespace-only source input before running the pipeline.
- Streamlit offers `english` and `hinglish` as language choices.
- The Sarvam flow splits audio into short pieces before sending it, sets a 120-second request timeout, checks non-success HTTP responses, and removes each temporary piece file in a `finally` block.

## Missing protections and concrete risks

### Authentication and authorization

There is no user login, authentication middleware, authorization check, or role model in the source. Provider API keys authenticate this application to Mistral/Sarvam; they do not identify or authorize users of the Streamlit UI. Whether the deployed Streamlit process is protected must be determined from deployment configuration, which is absent here.

**Possible improvement:** Put the app behind an authenticated access layer if it will be exposed beyond a trusted local environment; keep user identity and authorization separate from provider credentials.

### Input validation and local file access

`app.py` takes a source as a text string. `utils/audio_processor.py:process_input()` treats any string beginning with `http://` or `https://` as a download URL and passes it to yt-dlp; every other string goes to Pydub as a local filesystem path. The code does not validate URL host, path existence, allowed file types, file size, or media duration at the entry point.

If this UI is exposed to untrusted users on a host with sensitive local files, accepting arbitrary local paths is a filesystem exposure risk. Passing arbitrary URLs to a downloader also warrants destination/host restrictions in a public deployment. The source does not establish whether such access is reachable in a particular deployment.

**Possible improvement:** Restrict inputs to explicitly allowed URL hosts and controlled upload/storage directories; enforce size/duration limits and validate media format before processing.

### Unsafe HTML rendering

`app.py` uses `st.markdown(..., unsafe_allow_html=True)` for both static UI markup and interpolated data. In particular, transcript, model-generated title/summary/extraction text, and chat message content are inserted into HTML strings and rendered with unsafe HTML enabled (for example, transcript around line 454 and chat history around lines 490–502). User questions and provider/model output can therefore contain markup interpreted by the browser. This is a concrete cross-site scripting risk if untrusted content is rendered as HTML.

**Possible improvement:** Render dynamic text using Streamlit's plain-text components or HTML-escape dynamic values before placing them inside HTML. Keep unsafe HTML for fixed, trusted styling markup only.

### Secret loading order for Sarvam

`core/transcriber.py` reads `SARVAM_API_KEY` into a module-level constant at import time. In `app.py` and `main.py`, core modules (including `core.transcriber`) are imported before `load_dotenv()` is called. Therefore, if the key exists only in `.env` and is not already exported in the process environment, `SARVAM_API_KEY` may remain `None` for that process, and the Hinglish path can fail the explicit key check. `test.py` loads dotenv before importing core modules, so its order differs.

Mistral keys are read when `get_llm()` is called, so that specific module-level capture does not apply there.

**Possible improvement:** Load configuration before importing modules that capture environment values, or read the key at function call time and validate centralized configuration.

### External data sharing and prompt handling

- Hinglish audio pieces are sent to Sarvam; transcript text is sent to Mistral for title, summary, extraction, and chat. The code does not include a consent or data-redaction layer.
- `core/rag_engine.py` tells Mistral to answer from retrieved transcript context, but that is a prompt instruction, not an enforced security boundary. There is no prompt-injection detection or output verification.

**Possible improvement:** Make data handling explicit to users, minimize/redact sensitive content where appropriate, and treat retrieved transcript/model output as untrusted data.

### Database and injection risks

There is no SQL database or SQL query construction in the application, so SQL injection is not applicable to the current implementation. Chroma is called through LangChain APIs, with transcript chunks and generated embeddings passed as values; the source does not concatenate user text into SQL.

No authentication scoping or session metadata is applied to the shared Chroma collection. Repeated analyses write to the same `meeting_transcript` collection without explicit cleanup or session filtering (`core/vector_store.py:build_vector_store()`). This may mix content across runs and is a data-isolation/privacy concern in a multi-user or shared deployment. No NoSQL injection pattern is apparent in the source, but the app lacks per-user collection isolation and lifecycle controls.

**Possible improvement:** Assign each analysis a stable identifier, filter retrieval by it, and define deletion/retention behavior. If Chroma is later accessed through user-controlled filters or a query language, validate those values and avoid constructing raw query expressions from unchecked input.

### CORS, transport, and rate limiting

No custom CORS configuration, TLS setup, rate limiting, request quotas, or abuse controls are present. There is also no custom inbound API route. Transport security and access protection depend on how Streamlit and external services are deployed; no deployment files are included to verify those settings.

**Possible improvement:** Configure HTTPS and network access controls at the deployment boundary, limit expensive analysis requests, and monitor provider quotas.

## Error handling and logging

### Implemented behavior

- The Streamlit analysis block wraps the pipeline in `try/except Exception`, displays the exception text, and returns any active step status to pending (`app.py`). It does not roll back files or Chroma data already written.
- The Sarvam client uses a 120-second timeout. For non-OK responses it prints status/body and calls `raise_for_status()` (`core/transcriber.py:_send_to_sarvam`).
- Temporary Sarvam request-piece files are removed in a `finally` block.
- `core/rag_engine.py:ask_question()` prints the question and answer. `main.py` prints the first 300 transcript characters; `test.py` prints up to 500 transcript characters and analysis output.

### Missing or limited behavior

- Most core modules do not catch errors, retry, or convert provider/library exceptions into typed application errors.
- The CLI has no top-level error handler, so exceptions generally end the run with a traceback.
- The Streamlit chat call to `ask_question()` occurs outside the analysis pipeline's `try/except`.
- Error text is shown directly in the UI; this can expose internal exception details to users.
- Logging uses `print()`, not structured logging with levels, redaction, or a controlled retention policy. Logged transcripts, questions, answers, or provider response bodies may contain sensitive content.
- No rollback is performed if a later analysis step fails after Chroma writes or media files are created.

**Possible improvement:** Use structured logging with secret/content redaction; return safe user-facing messages while retaining sanitized diagnostics; add timeouts/retries where appropriate, with bounded backoff and clear handling for non-idempotent operations; and define cleanup/rollback behavior for partial runs.

## Security checklist by requested topic

| Topic | Verified status |
|---|---|
| Authentication security | No user authentication implemented; provider keys only. |
| Authorization checks | None in application source. |
| Input validation | Blank source check in UI; API key check for Sarvam; no robust URL/path/file validation. |
| Password handling | No passwords or password storage. |
| Environment variables/secrets | `.env` loading and `.gitignore` entry exist; no secret manager. Sarvam key import-order issue is present in UI/CLI entry points. |
| CORS | No custom configuration found. |
| SQL/NoSQL injection | No SQL/ORM. No raw query construction found; shared Chroma data isolation is a concern. |
| Error handling | Broad catch only for Streamlit analysis; Sarvam raises HTTP errors; CLI/chat handling is limited. |
| Logging | `print()` statements; no structured logging or redaction. |
| Rate limiting | None found. |
| XSS/output rendering | Dynamic transcript/model/chat values are interpolated into `unsafe_allow_html=True` markup. |
| Background jobs | None; work is synchronous, with no queue or resource limits in code. |
