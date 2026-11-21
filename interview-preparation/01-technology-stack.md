# Technology Stack

This inventory is based on the Python source files, `Requirements.txt`, and `.gitignore` present in the repository. The project has no `pyproject.toml`, lockfile, `package.json`, Dockerfile, deployment manifest, or environment template. `Requirements.txt` is the only dependency manifest, and it specifies minimum versions rather than a reproducible pinned environment.

## Language and application shape

### Python

- **What it is:** The programming language used to implement the application.
- **Why / problem solved:** Python hosts the media workflow, AI calls, retrieval pipeline, CLI, and Streamlit UI in one codebase.
- **Where:** `app.py`, `main.py`, `test.py`, `core/*.py`, and `utils/audio_processor.py`.
- **Interactions:** `app.py` and `main.py` call reusable functions from `utils` and `core`. Third-party Python libraries connect the code to media tools, local models, vector storage, and hosted APIs.
- **If removed/replaced:** All application code would need to be ported, and Python ecosystem integrations (Whisper, LangChain, Streamlit, and others) would need equivalents in the replacement language.

The repository uses Python modules and folders, but does not define a package build, installer, or formal test configuration.

## Frameworks and core libraries

### Streamlit

- **What it is:** A Python framework for building interactive web applications.
- **Why / problem solved:** Provides the browser-based interface without a separately implemented web frontend and API server.
- **Where:** `app.py` uses Streamlit widgets, columns, expanders, session state, spinners, and reruns.
- **Interactions:** The UI directly calls the same processing functions used by the CLI. `st.session_state` holds the current result and chat history for a Streamlit session.
- **If removed/replaced:** The graphical UI would need another frontend/server framework; the processing modules could remain and be called by it.

### LangChain (LCEL, core, and integrations)

- **What it is:** A Python framework for composing language-model prompts, model calls, transformations, retrieval, and output parsing into runnable chains. LCEL is its compositional expression style used here.
- **Why / problem solved:** Avoids writing separate glue code for each Mistral prompt and for passing retrieved transcript chunks into question-answering.
- **Where:** `core/summarizer.py`, `core/extractor.py`, and `core/rag_engine.py` use `ChatPromptTemplate`, `RunnablePassthrough`, `RunnableLambda`, and `StrOutputParser`. `core/vector_store.py` uses LangChain document, text-splitter, embedding, and Chroma adapters.
- **Interactions:** LangChain wraps the Mistral chat model and Chroma/Hugging Face components. In RAG, it pipes retrieved documents through a formatter, prompt, Mistral, and string parser.
- **If removed/replaced:** Prompts, model requests, splitting, retrieval, and chain composition would need to be written directly using vendor SDKs and database APIs. The application features are possible without LangChain, but more integration code would be needed.

### Mistral API and `langchain-mistralai`

- **What it is:** Mistral is a hosted language-model service; `langchain-mistralai` adapts its chat model to LangChain. The `mistralai` package is also listed as the official client.
- **Why / problem solved:** The model generates titles, summaries, action items, decisions, open questions, and grounded answers to transcript questions.
- **Where:** `core/summarizer.py`, `core/extractor.py`, and `core/rag_engine.py` create `ChatMistralAI` with model `mistral-small-latest`. They read `MISTRAL_API_KEY` from the environment.
- **Interactions:** LangChain prompts/chains send text to Mistral and parse its responses. RAG first adds transcript context retrieved from Chroma.
- **If removed/replaced:** Those generative features stop working until another model/provider is integrated; replacing Mistral requires adapting credentials, model configuration, and potentially LangChain's model adapter.

`mistralai` is declared in `Requirements.txt` but not directly imported by the project source; the source uses `langchain-mistralai`.

### Streamlit styling and Google Fonts

`app.py` defines custom CSS and references Syne and JetBrains Mono using a Google Fonts `@import`. This affects presentation only. Removing the CSS/font import leaves the application logic intact but changes the visual design; font loading depends on browser access to Google Fonts.

## Audio and speech technologies

### yt-dlp

- **What it is:** A media downloader and extractor.
- **Why / problem solved:** Obtains audio from a supplied YouTube URL.
- **Where:** `utils/audio_processor.py`, in `download_youtube_audio()`.
- **Interactions:** Configures FFmpeg extraction through yt-dlp's postprocessor and returns a WAV path for subsequent Pydub processing.
- **If removed/replaced:** URL input would need another downloader or would no longer work; local file handling could remain.

### Pydub and FFmpeg

- **What they are:** Pydub is a Python audio manipulation library; FFmpeg is an external media conversion tool.
- **Why / problem solved:** Convert local media into mono, 16 kHz WAV and split audio into ten-minute chunks. Pydub also loads WAV files for Sarvam's shorter pieces.
- **Where:** `utils/audio_processor.py` and `core/transcriber.py`.
- **Interactions:** Whisper receives chunk file paths. Sarvam receives temporary WAV files. Pydub relies on FFmpeg for formats FFmpeg supports; yt-dlp also invokes FFmpeg to extract WAV audio.
- **If removed/replaced:** The project needs another audio decoder/converter/chunker, and support for local files or compatible speech API input may break.

`ffmpeg-python` is listed in `Requirements.txt` but is not imported. The project uses Pydub/yt-dlp with the external FFmpeg executable, so the Python FFmpeg bindings themselves are not shown in use. Installing the binding alone does not install the FFmpeg executable.

### OpenAI Whisper, PyTorch, and Sarvam

- **What they are:** Whisper is a speech-recognition model run locally; PyTorch is its machine-learning runtime. Sarvam is an external speech API that transcribes/translates speech to text.
- **Why / problem solved:** Convert recorded speech into text. Whisper handles the English selection; Sarvam handles Hinglish and returns English text.
- **Where:** `core/transcriber.py`. Whisper model defaults to `small` (override `WHISPER_MODEL`). Sarvam endpoint is `https://api.sarvam.ai/speech-to-text-translate`; its model defaults to `saaras:v2.5` (override `SARVAM_STT_MODEL`). Hinglish requires `SARVAM_API_KEY`.
- **Interactions:** `transcribe_all()` processes the audio chunks produced by `utils/audio_processor.py`. Whisper loads once per Python process. Sarvam requests use `requests`, and each ten-minute chunk is divided into 25-second pieces before the API calls.
- **If removed/replaced:** Without Whisper and its runtime, local English transcription requires another recognizer. Without Sarvam credentials/service, the Hinglish route raises an error. Either can be replaced by another speech-to-text provider with compatible input/output handling.

Whisper inference is local after the model is available, while Sarvam and Mistral require network access. This means the application is not fully offline.

## Retrieval, embeddings, and database

### Chroma vector database

- **What it is:** A vector store that persists text chunks and their embeddings and can find chunks by semantic similarity.
- **Why / problem solved:** Finds transcript passages relevant to a user's question, even when the question does not use the same words as the transcript.
- **Where:** `core/vector_store.py` creates collection `meeting_transcript` in local directory `vector_db`, and `core/rag_engine.py` builds the retrieval chain.
- **Interactions:** Transcript chunks are embedded and written to Chroma. A retriever selects up to four similar chunks; LangChain passes their text and the question to Mistral.
- **If removed/replaced:** Chat would lose this semantic search path. It could be replaced by another vector database or by simpler keyword search, with changes to storage and retrieval code.

There is **no relational database or ORM** in this project. Chroma is the only database-like component visible in the source, and it is accessed through LangChain's Chroma integration rather than an ORM.

### Hugging Face Sentence Transformers embeddings

- **What they are:** Sentence Transformers converts text into numeric vectors; Hugging Face provides the model ecosystem and download infrastructure. The selected model is `all-MiniLM-L6-v2`.
- **Why / problem solved:** Gives Chroma vectors it can compare for semantic retrieval.
- **Where:** `core/vector_store.py` uses `HuggingFaceEmbeddings` with CPU device configuration.
- **Interactions:** The embedding model transforms transcript chunks and later user queries for Chroma similarity search. The model may need to be downloaded from Hugging Face on first use, depending on local cache.
- **If removed/replaced:** Vector creation and semantic retrieval need a different embedding model/provider, and existing vectors may need to be regenerated if embedding dimensions or model semantics differ.

The source imports `langchain_chroma` and `langchain_text_splitters`, but `Requirements.txt` does not explicitly list the corresponding standalone packages (`langchain-chroma` and `langchain-text-splitters`). They may be available in a particular environment through other installation choices, but the manifest alone does not guarantee these imports resolve. This is a setup gap to verify when creating a clean environment.

## External services and configuration

### Mistral and Sarvam APIs

These are the hosted AI services used for model tasks in application logic. Sarvam is called directly with an HTTP multipart request using `requests` in `core/transcriber.py`; Mistral is invoked through LangChain's `ChatMistralAI` adapter. Both require valid credentials for the related feature. There is no authentication system for application users: these API keys authenticate the application to providers, not users to this application.

### YouTube and Google Fonts

YouTube is an external media source reached through yt-dlp. Google Fonts is referenced by the UI's CSS. These are not application APIs used for user authentication or data storage.

### `python-dotenv` and `.env`

- **What it is:** A helper that loads environment variables from a local `.env` file.
- **Why / problem solved:** Keeps API credentials and model options out of hard-coded application logic.
- **Where:** `app.py` and `main.py` call `load_dotenv()` after importing core modules; `test.py` calls it before importing core modules. `.gitignore` excludes `.env`.
- **Interactions:** `core/summarizer.py`, `core/extractor.py`, `core/rag_engine.py`, and `core/transcriber.py` read settings with `os.getenv()`.
- **If removed/replaced:** Operators would need to export variables another way (for example, through the shell or deployment environment); missing keys would prevent the corresponding hosted API calls.

Recognized variables in source are `MISTRAL_API_KEY`, `SARVAM_API_KEY`, `WHISPER_MODEL`, and `SARVAM_STT_MODEL`. Note that `core/transcriber.py` reads `SARVAM_API_KEY` into a module constant during import; because `app.py` and `main.py` import it before `load_dotenv()`, a key present only in `.env` may not be available to Hinglish transcription in those entry points. `test.py` loads dotenv first. There is no checked-in `.env.example` or centralized validation/configuration layer.

## Declared packages not evidenced in source

The following are declared but have no direct imports or feature implementation in the inspected source: `deep-translator` (the Hinglish route uses Sarvam instead), `streamlit-extras`, `watchdog`, `reportlab`, `fpdf2`, `tiktoken`, `numpy`, `torchaudio`, `huggingface-hub`, and `mistralai` as a direct client. Some may be transitive dependencies or useful to underlying packages, but the source does not establish direct use. In particular, the manifest comments mention PDF/TXT export, but no export code is present.

`requests` is directly used for Sarvam. `time` and `os` are Python standard-library modules, so they are not third-party dependencies.

## Authentication, build, and deployment

- **Authentication libraries:** None. There is no login, user identity, session authentication, or authorization code. Streamlit session state is UI state, not proof of user identity.
- **Build tools:** No frontend bundler, package build configuration, or build pipeline is included. Python packages are listed in `Requirements.txt`; installation is not scripted.
- **Development tools:** No linter, formatter, type checker, test runner configuration, or CI workflow is included. `test.py` is an example script with a fixed YouTube URL, not an automated test suite.
- **Deployment infrastructure:** No Docker, cloud, serverless, orchestration, or deployment configuration is present. The intended UI runs as a Streamlit process (`streamlit run app.py`); the alternative is `python main.py`. A deployment would need Python dependencies, FFmpeg, credentials, network access to external APIs, and writable local storage for downloads and Chroma data.

## Execution flow across technologies

1. The user starts Streamlit via `app.py` or the CLI via `main.py`, and `python-dotenv` loads environment values.
2. The UI or CLI passes a URL/file path to `utils/audio_processor.py`. `yt-dlp` downloads URL audio and requests WAV extraction. For local input, Pydub/FFmpeg converts to mono 16 kHz WAV. Both paths then split the resulting WAV into chunks; the source does not apply the local conversion's channel/sample-rate normalization to the downloaded path explicitly.
3. `core/transcriber.py` routes English audio to local Whisper/PyTorch, or Hinglish audio to Sarvam through `requests`. The result is a transcript string.
4. `core/summarizer.py` splits the transcript and uses LangChain prompt chains with Mistral to produce a title and consolidated summary. `core/extractor.py` uses similar Mistral chains to produce action items, decisions, and open questions.
5. For question-answering, `core/vector_store.py` chunks the transcript, creates vectors with the Hugging Face sentence embedding model, and stores them in Chroma under `vector_db/`.
6. `core/rag_engine.py` retrieves the four most relevant chunks for a question and supplies those chunks as context to Mistral. The Streamlit UI shows the answer and keeps conversation display state in session state; the CLI prints answers in a loop.
