from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


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
