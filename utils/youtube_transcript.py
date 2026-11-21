import os
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


def transcribe_youtube_with_gemini(url: str, language: str = "english") -> str | None:
    """Ask Gemini to read a public YouTube video directly, avoiding server-side downloads.

    Gemini's YouTube URL input is a preview feature and only supports public videos.
    Return None on any API/availability error so the caller can use captions or audio
    download as fallbacks.
    """
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key or not _video_id_from_url(url):
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_VIDEO_MODEL") or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        if language.lower() == "hinglish":
            prompt = (
                "Transcribe all spoken dialogue in this video as faithfully and completely as possible. "
                "Translate Hindi speech into clear English while retaining speech already in English. "
                "Do not summarize, omit sections, add commentary, or describe visuals. Return only the transcript."
            )
        else:
            prompt = (
                "Transcribe all spoken dialogue in this video in English as faithfully and completely as possible. "
                "Do not summarize, omit sections, add commentary, or describe visuals. Return only the transcript."
            )

        response = client.models.generate_content(
            model=model,
            contents=types.Content(
                parts=[
                    types.Part(file_data=types.FileData(file_uri=url)),
                    types.Part(text=prompt),
                ]
            ),
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=8192),
        )
        transcript = (response.text or "").strip()
        if transcript:
            return transcript
        print("Gemini returned an empty YouTube transcript; trying captions/audio fallback.")
    except Exception as error:
        # Hosted IPs can still be refused, and this preview may be unavailable for
        # private, unlisted, region-restricted, or otherwise unsupported videos.
        print(f"Gemini YouTube transcription unavailable; trying captions/audio fallback: {error}")
    return None


def _video_id_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":", 1)[0]

    if host == "youtu.be" or host.endswith(".youtu.be"):
        return parsed.path.strip("/").split("/", 1)[0] or None

    is_youtube_host = (
        host == "youtube.com"
        or host.endswith(".youtube.com")
        or host == "youtube-nocookie.com"
        or host.endswith(".youtube-nocookie.com")
    )
    if is_youtube_host:
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if video_id:
            return video_id
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"}:
            return parts[1]

    return None


def fetch_youtube_captions(url: str, language: str = "english") -> str | None:
    """Return available captions as plain text, or None when unavailable."""
    video_id = _video_id_from_url(url)
    if not video_id:
        return None

    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=["en"])
    except Exception as english_error:
        if language.lower() != "hinglish":
            print(f"YouTube captions unavailable; falling back to audio: {english_error}")
            return None

        try:
            transcript_list = api.list(video_id)
            transcript = transcript_list.find_transcript(["hi", "en"])
            if transcript.language_code.split("-")[0] != "en":
                if not transcript.is_translatable:
                    return None
                transcript = transcript.translate("en")
            fetched = transcript.fetch()
        except Exception as caption_error:
            print(f"YouTube captions unavailable; falling back to audio: {caption_error}")
            return None

    text = " ".join(snippet.text for snippet in fetched.snippets).strip()
    return text or None
