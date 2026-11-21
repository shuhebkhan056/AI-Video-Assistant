# AI Video Assistant

AI Video Assistant turns a YouTube video or local audio/video file into a transcript, meeting summary, action items, decisions, open questions, and a transcript Q&A chat.

## Run locally

Python 3.11 and FFmpeg are recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Add a Gemini API key to `.env` as `GEMINI_API_KEY`. `SARVAM_API_KEY` is optional and is only needed for the Hinglish transcription option. Whisper downloads its selected model the first time it runs; `WHISPER_MODEL=base` is the default.

For local-file analysis, enter a path visible to the machine running Streamlit. When hosted, use a YouTube URL; a path on your own computer is not available to the hosted server.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create an app from the repository's `main` branch and set the main file to `app.py`.
3. In the app's **Settings → Secrets**, add:

   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   GEMINI_MODEL = "gemini-3.5-flash-lite"
   WHISPER_MODEL = "base"
   # Optional, for Hinglish transcription:
   # SARVAM_API_KEY = "your-sarvam-api-key"
   # SARVAM_STT_MODEL = "saaras:v2.5"
   ```

The app reads cloud secrets from Streamlit and local values from `.env`. Never commit `.env` or `secrets.toml`. Hosted instances have limited CPU and temporary storage; Whisper transcription can take a while, and generated audio/vector data is not durable across restarts.
