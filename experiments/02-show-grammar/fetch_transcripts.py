"""
Fetch YouTube transcripts for the rafmag show-grammar analysis.

Usage:
  # Add YouTube URLs to urls.txt (one per line), then:
  python fetch_transcripts.py

For each URL, writes transcripts/{videoId}.json containing either:
  { videoId, language, isGenerated, snippets: [{start, duration, text}, ...] }
or:
  { videoId, error }

Already-fetched successful videos are skipped.
If a cached file contains an `error`, it is retried automatically.
"""

import json
import re
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

ROOT = Path(__file__).parent
URLS_FILE = ROOT / "urls.txt"
OUT_DIR = ROOT / "transcripts"

VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|/live/|/shorts/)([\w-]{11})")

# Languages to try, in order. Tunisian/Maghrebi auto-captions are usually
# tagged plain "ar"; we keep "fr" and "en" as last-resort fallbacks.
PREFERRED_LANGS = ["ar", "ar-TN", "fr", "en"]


def extract_video_id(url: str) -> str | None:
    m = VIDEO_ID_RE.search(url)
    return m.group(1) if m else None


def _snippet_to_dict(s) -> dict:
    """Normalize a snippet from either v1.x (object) or v0.6.x (dict)."""
    if hasattr(s, "text"):
        return {"start": float(s.start), "duration": float(s.duration), "text": s.text}
    return {"start": float(s["start"]), "duration": float(s["duration"]), "text": s["text"]}


def _get_transcript_list(api: YouTubeTranscriptApi, video_id: str):
    """
    Return a transcript-list object across youtube-transcript-api variants.

    Supported:
    - v1.x: instance method `api.list(video_id)`
    - older: class/static method `YouTubeTranscriptApi.list_transcripts(video_id)`
    """
    if hasattr(api, "list"):
        return api.list(video_id)

    legacy_list = getattr(YouTubeTranscriptApi, "list_transcripts", None)
    if callable(legacy_list):
        return legacy_list(video_id)

    return None


def _fetch_direct_transcript(api: YouTubeTranscriptApi, video_id: str):
    """
    Last-resort path for very old/new API shapes that expose only direct fetch.
    Returns (language_code, is_generated, raw_snippets) or None.
    """
    for lang in PREFERRED_LANGS:
        if hasattr(api, "fetch"):
            fetched = api.fetch(video_id, languages=[lang])
            raw_snippets = fetched.snippets if hasattr(fetched, "snippets") else fetched
            return lang, True, raw_snippets

        legacy_get = getattr(YouTubeTranscriptApi, "get_transcript", None)
        if callable(legacy_get):
            raw_snippets = legacy_get(video_id, languages=[lang])
            return lang, True, raw_snippets

    return None


def fetch_one(video_id: str) -> dict:
    api = YouTubeTranscriptApi()
    try:
        transcript_list = _get_transcript_list(api, video_id)
    except (TranscriptsDisabled, VideoUnavailable) as e:
        return {"videoId": video_id, "error": type(e).__name__}
    except Exception as e:
        return {"videoId": video_id, "error": f"{type(e).__name__}: {e}"}

    if transcript_list is not None:
        chosen = None
        for finder_name in ("find_manually_created_transcript", "find_generated_transcript"):
            if chosen is not None:
                break
            finder = getattr(transcript_list, finder_name, None)
            if finder is None:
                continue
            for lang in PREFERRED_LANGS:
                try:
                    chosen = finder([lang])
                    break
                except NoTranscriptFound:
                    continue

        if chosen is None:
            return {"videoId": video_id, "error": "NoTranscriptFound"}

        fetched = chosen.fetch()
        # v1.x returns a FetchedTranscript with .snippets; v0.6.x returns a list of dicts.
        raw_snippets = fetched.snippets if hasattr(fetched, "snippets") else fetched

        return {
            "videoId": video_id,
            "language": chosen.language_code,
            "isGenerated": chosen.is_generated,
            "snippets": [_snippet_to_dict(s) for s in raw_snippets],
        }

    # Fallback for API variants that do not expose transcript-list APIs.
    try:
        direct = _fetch_direct_transcript(api, video_id)
    except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound) as e:
        return {"videoId": video_id, "error": type(e).__name__}
    except Exception as e:
        return {"videoId": video_id, "error": f"{type(e).__name__}: {e}"}

    if direct is None:
        return {"videoId": video_id, "error": "NoSupportedTranscriptApiMethod"}

    language, is_generated, raw_snippets = direct
    return {
        "videoId": video_id,
        "language": language,
        "isGenerated": is_generated,
        "snippets": [_snippet_to_dict(s) for s in raw_snippets],
    }


def main() -> int:
    if not URLS_FILE.exists():
        print(f"Missing {URLS_FILE}", file=sys.stderr)
        return 1

    urls = [
        line.strip()
        for line in URLS_FILE.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not urls:
        print(f"No URLs in {URLS_FILE.name}. Add one YouTube URL per line.", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(exist_ok=True)
    print(f"Found {len(urls)} URLs. Fetching transcripts...", file=sys.stderr)

    successes = 0
    failures = 0

    for i, url in enumerate(urls, 1):
        video_id = extract_video_id(url)
        if not video_id:
            print(f"[{i}/{len(urls)}] skip — cannot parse video id from: {url}", file=sys.stderr)
            failures += 1
            continue

        out_file = OUT_DIR / f"{video_id}.json"
        if out_file.exists():
            try:
                cached = json.loads(out_file.read_text())
            except Exception:
                cached = None

            if isinstance(cached, dict) and "error" in cached:
                print(
                    f"[{i}/{len(urls)}] {video_id}: cached error found, re-fetching...",
                    file=sys.stderr,
                )
            else:
                print(f"[{i}/{len(urls)}] {video_id}: already fetched", file=sys.stderr)
                successes += 1
                continue

        print(f"[{i}/{len(urls)}] {video_id}: fetching...", file=sys.stderr)
        try:
            data = fetch_one(video_id)
        except Exception as e:
            data = {"videoId": video_id, "error": f"{type(e).__name__}: {e}"}

        out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        if "error" in data:
            print(f"           -> error: {data['error']}", file=sys.stderr)
            failures += 1
        else:
            print(
                f"           -> {len(data['snippets'])} snippets, "
                f"lang={data['language']}, auto={data['isGenerated']}",
                file=sys.stderr,
            )
            successes += 1

    print(f"\nDone. Success: {successes}, failures: {failures}", file=sys.stderr)
    return 0 if successes > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
