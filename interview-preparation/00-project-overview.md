# Project Overview: AI Video Assistant

## What the project does

This Python application turns a YouTube video or local audio/video file into meeting-style notes. It extracts audio, transcribes speech, creates a title and summary, identifies action items, decisions, and unresolved questions, and lets the user ask questions about the transcript.

## Problem it solves and why it is useful

Long recordings are slow to review. The application converts their spoken content into a searchable transcript and compact notes, then supports follow-up questions grounded in that transcript. This can help someone review a meeting or video without replaying the entire recording.

## Main features

- **YouTube and local-file input:** `utils/audio_processor.py` downloads YouTube audio or converts a local media file to WAV, then splits it into ten-minute chunks.
- **English and Hinglish transcription:** `core/transcriber.py` routes English to a locally run OpenAI Whisper model. Hinglish uses Sarvam's speech-to-text-and-translation API to produce English text; each chunk is further split into 25-second pieces for that API.
- **Title and summary generation:** `core/summarizer.py` asks Mistral for a short title and summarizes transcript segments before combining them into bullet points.
- **Meeting information extraction:** `core/extractor.py` asks Mistral for action items (including owner and deadline when stated), key decisions, and open questions.
- **Transcript question-answering:** `core/vector_store.py` splits and embeds transcript text into a local Chroma vector store. `core/rag_engine.py` retrieves the four most similar chunks and asks Mistral to answer using that context.
- **Streamlit interface:** `app.py` presents input, processing status, results, and an in-session chat interface. Chat history can be cleared.
- **Command-line workflow:** `main.py` runs the processing pipeline from a terminal and then offers an interactive question-answer loop.

## Technology stack

- **Language:** Python (the requirements recommend Python 3.10 or newer).
- **UI:** Streamlit, with custom CSS defined in `app.py`.
- **Audio/video handling:** `yt-dlp`, `pydub`, and FFmpeg (the FFmpeg executable is required separately for media operations).
- **Speech recognition:** OpenAI Whisper and PyTorch locally for English; Sarvam's hosted API for Hinglish transcription and translation.
- **LLM and orchestration:** Mistral's `mistral-small-latest` through LangChain's Mistral integration, prompts, output parsers, and runnable chains.
- **Retrieval and embeddings:** Chroma as a local vector database and Hugging Face Sentence Transformers using `all-MiniLM-L6-v2` embeddings on CPU.
- **Configuration and HTTP:** `python-dotenv` loads `.env`; `requests` sends Sarvam requests.
- **Other listed dependencies:** `Requirements.txt` also lists `deep-translator`, PDF libraries (`reportlab`, `fpdf2`), `streamlit-extras`, `watchdog`, `numpy`, `tiktoken`, and other LangChain/Hugging Face packages. There is no corresponding translation helper, export feature, or direct use of several of these in the inspected Python source. No relational database or separate backend server is present.

## High-level folder structure

```text
.
├── app.py                         # Streamlit application and UI workflow
├── main.py                        # CLI pipeline and chat entry point
├── test.py                        # Example end-to-end script using a hard-coded YouTube URL
├── Requirements.txt               # Python dependencies
├── core/
│   ├── transcriber.py             # Whisper/Sarvam transcription
│   ├── summarizer.py              # Mistral title and summary generation
│   ├── extractor.py               # Action items, decisions, and questions
│   ├── vector_store.py            # Transcript chunking, embeddings, Chroma storage
│   └── rag_engine.py              # Retrieval-augmented question answering
└── utils/
    └── audio_processor.py         # Download, conversion, and audio chunking
```

At runtime, additional files/directories may be created: `downloades/` for downloaded media and chunks, and `vector_db/` for Chroma persistence. The misspelling `downloades` is the literal directory name in the source. `__pycache__` directories are Python-generated files and are not part of the application design.

## Important files and responsibilities

- [`app.py`](../app.py): Main graphical entry point. Loads environment variables, defines the Streamlit layout and state, executes each pipeline stage, displays outputs, and handles transcript Q&A.
- [`main.py`](../main.py): Alternative command-line entry point. `run_pipeline(source, language)` coordinates audio processing, transcription, title/summary generation, extraction, and RAG chain creation.
- [`utils/audio_processor.py`](../utils/audio_processor.py): Distinguishes URL input from local file paths; downloads/converts media and writes audio chunks.
- [`core/transcriber.py`](../core/transcriber.py): Loads and reuses a Whisper model for English, or sends short WAV pieces to Sarvam for Hinglish.
- [`core/summarizer.py`](../core/summarizer.py): Implements transcript splitting, map-and-combine summarization, and title generation using Mistral.
- [`core/extractor.py`](../core/extractor.py): Builds Mistral prompt chains for the three meeting-note extraction tasks.
- [`core/vector_store.py`](../core/vector_store.py): Defines the embedding model, chunking settings, Chroma collection, persistence path, and similarity retriever.
- [`core/rag_engine.py`](../core/rag_engine.py): Builds the retrieval-and-answer chain and exposes `ask_question`.
- [`test.py`](../test.py): A runnable example script with a fixed YouTube URL; it prints the transcript excerpt, title, summary, and extracted notes. Despite its name, it contains no test assertions or test framework setup.
- [`Requirements.txt`](../Requirements.txt): Declares Python package requirements. `.gitignore` currently ignores `.env`.

## How the application starts

The Streamlit UI can be started from the project root with:

```bash
streamlit run app.py
```

The CLI can be started with:

```bash
python main.py
```

It prompts for a YouTube URL or local file path, then for `english` or `hinglish`. The example script can be run with `python test.py`, but its source URL is hard-coded. These startup commands are based on the entry-point code and dependency list; no README or deployment configuration is included in the inspected project files.

The app expects `MISTRAL_API_KEY` for Mistral and `SARVAM_API_KEY` for Hinglish transcription, plus optional `WHISPER_MODEL` (default `small`) and `SARVAM_STT_MODEL` (default `saaras:v2.5`). Although `app.py` and `main.py` call `load_dotenv()`, both import `core.transcriber` first; that module captures `SARVAM_API_KEY` at import time. If the key exists only in `.env`, the Hinglish route may therefore see it as missing. `test.py` loads dotenv before importing core modules.

## Overall working

```text
YouTube URL or local media file
              │
              ▼
 audio_processor.py: download/convert to WAV, split into 10-minute chunks
              │
              ▼
 transcriber.py: Whisper (English) or Sarvam (Hinglish → English text)
              │
              ├──► summarizer.py: title + combined summary (Mistral)
              ├──► extractor.py: action items, decisions, open questions (Mistral)
              └──► vector_store.py: chunk + embed transcript in local Chroma
                                      │
                                      ▼
                         rag_engine.py: retrieve relevant chunks,
                         pass context and question to Mistral
              │
              ▼
         app.py displays notes and chat, or main.py prints notes and runs CLI chat
```

The graphical and command-line paths both orchestrate the same processing modules. In the Streamlit app, the generated RAG chain and chat history live in Streamlit session state for that session; the transcript vectors are persisted under `vector_db/`.

## Implemented versus incomplete or unverified

The main UI and CLI call `build_rag_chain(transcript)`, which creates the vector store for the current transcript. `core/rag_engine.py` also defines `load_rag_chain()`, apparently for loading a previously persisted store, but that helper calls `get_retriever()` without the required vector-store argument, so that path is incomplete as written and is not used by the main entry points.

PDF/TXT export packages are listed in `Requirements.txt`, but no export implementation appears in the inspected source. Likewise, no separate account system, upload API, server-side job queue, or relational database is implemented. The listed `deep-translator` dependency does not match the actual Hinglish flow, which uses Sarvam's translate API.
