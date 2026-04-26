"""
Gemini ad-break detection — quality test on one rafmag episode.

Usage:
  # Whole episode at low video resolution (default — fits ~4h of show in 1M tokens):
  python test.py "<youtube_url>"

  # Just a clip (recommended for the first run — much faster, much cheaper):
  python test.py "<youtube_url>" --start 1200 --end 1800

  # Bigger model (2M token context, costs more):
  python test.py "<youtube_url>" --model gemini-2.5-pro

The script sends the YouTube URL directly to Gemini's video-understanding API
and asks it to return a JSON list of ad/promo break ranges.

Setup is documented in README.md.
"""

import argparse
import json
import os
import re
import sys
import threading
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types


VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|/live/|/shorts/)([\w-]{11})")


BREAK_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "breaks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "startSec": {"type": "integer"},
                    "endSec": {"type": "integer"},
                    "type": {"type": "string", "enum": ["ad", "promo", "break"]},
                    "evidence": {"type": "string"},
                },
                "required": ["startSec", "endSec", "type", "evidence"],
                "propertyOrdering": ["startSec", "endSec", "type", "evidence"],
            },
        }
    },
    "required": ["breaks"],
    "propertyOrdering": ["breaks"],
}


SHOW_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "showSegments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "startSec": {"type": "integer"},
                    "endSec": {"type": "integer"},
                    "type": {"type": "string", "enum": ["show"]},
                    "evidence": {"type": "string"},
                },
                "required": ["startSec", "endSec", "type", "evidence"],
                "propertyOrdering": ["startSec", "endSec", "type", "evidence"],
            },
        }
    },
    "required": ["showSegments"],
    "propertyOrdering": ["showSegments"],
}


PROMPT_TEMPLATE = """\
You are analyzing a YouTube video that is the unedited live-archive recording
of a Tunisian radio show called "rafmag", broadcast on Diwan FM.

Your job is to separate RAFMAG SHOW CONTENT from NOISY RADIO BREAKS.

NOISY RADIO BREAKS are contiguous time ranges where the rafmag show content
stops and Diwan FM fills the airtime with automated radio material: promos
for other shows, station IDs, jingles, commercial ads, generic station news,
sports flashes, or pre-recorded bumpers.

Important definition: "show content" means the live rafmag studio/panel with
the main moderator and guests. Generic Diwan FM news/sports read by another
anchor is NOT rafmag show content for this task; it belongs inside the break.
Pre-show waiting content before rafmag begins is also NOT a break to report.

{segment_context}

# LEARNED RAFMAG SHOW GRAMMAR

Use these real patterns from past episodes. Transcript spelling can be noisy,
so match meaning and sound, not exact orthography.

Common break-entry phrases:
- "فاصل ثم نواصل" = a break, then we continue.
- "الاخبار ثم نعود" = the news, then we return.
- "ترتيحه صغيره بالموزيكا" / "ترتيحه العاده بالموزيكا" = a short/usual
  rest with music.
- "فاصل صغير" / "ما تبعدوش" = short break / do not go away.

Common break-return signals:
- "مرحبا مرحبا رجعنا لكم في ساعتنا الثانيه" = welcome back for the second
  hour.
- "مرحبا بكم في الجزء الاخير من حلقتنا لليوم" = welcome to the final part
  of today's episode.
- A time announcement followed by sustained rafmag discussion can also mark
  a return, but a time announcement alone is not enough.

Typical episode skeleton:
- Intro -> Zapping recap segment -> short break -> trend/main topic.
- Around the top of the hour, a long news/sports break may happen. This is
  one noisy break even if it contains professional news reading.
- Second-hour return -> Box News / discussion -> more breaks -> final quiz
  or final part -> outro.

# WHAT IS A BREAK

- A break STARTS when the main moderator hands off with one of the learned
  entry phrases or an equivalent phrase, AND rafmag show content stops.
- A valid break after the show starts must have rafmag show content before it.
  Do not mark the initial waiting room, pre-stream music, countdown, channel
  filler, or pre-show station audio as a break.
- Break material can include automated promos, jingles, station IDs, ads,
  generic Diwan FM news, sports flashes, music beds, or "you are listening
  to rafmag" bumpers.
- A break ENDS only when the actual show RESUMES — meaning the main moderator
  is back discussing the show's topic with their guests for at least ~30
  seconds of sustained content. NOT a brief station ID, NOT a jingle, NOT
  a "rafmag airs from 7 to 9:30" bumper, NOT another promo, and NOT generic
  Diwan FM news/sports.

# INTERNAL METHOD

Before producing JSON, do this internally:
1. Locate the first sustained rafmag studio/show segment. Ignore everything
   before it.
2. After show start, scan for every learned break-entry phrase or equivalent
   hand-off phrase.
3. For each candidate, inspect what follows. Keep it only if rafmag studio
   discussion stops and Diwan FM filler/news/sports/promos/ads take over.
4. Find the return point where sustained rafmag studio discussion resumes.
5. Merge adjacent filler blocks into one range.
6. Reject known traps: Zapping, Box News, columnist segments, live sponsor
   reads, giveaways, selected music, intro/outro.
7. For full long episodes, sanity-check that you did not return only the
   pre-show and one isolated break while missing later entry phrases.

# WHAT IS NOT A BREAK — CRITICAL, these are common false positives

1. **Co-host / columnist (chroniqueur) segments.** rafmag regularly features
   guest contributors who deliver their own recap or commentary segments
   (e.g. a recap of last week's show). Their voice differs from the main
   moderator's. The transition INTO and OUT OF their segment is NORMAL SHOW
   CONTENT, not a break — even if the main moderator says "we're back" /
   "hawa rj3na" right after the columnist finishes. A voice change alone
   is NEVER sufficient to mark a break; there must also be a sequence of
   non-rafmag filler such as promos, station IDs, news, sports, or ads.

2. **Zapping recap segment near the start.** The show often begins with a
   Zapping montage/recap introduced as yesterday's episode recap and closed
   with a phrase like "يلا شباب نتقابل غدوه في زابينغ". This is NORMAL SHOW
   CONTENT. Do not mark Zapping itself as a break.

3. **Live in-show sponsor reads and giveaways.** Brand mentions such as
   Ooredoo, Volkswagen, prizes, callers, and live ad reads are not breaks
   when the rafmag moderator/panel is actively talking and interacting. The
   promotional language alone is not enough.

4. **Box News / بوكس نيوز as a rafmag segment.** If it is introduced as Box
   News inside the second hour and then naturally returns to panel debate,
   treat it as show content, not a break.

5. **Music played as part of the show.** If the moderator chooses a song to
   play as content, that is NOT a break.

6. **Show intro / outro / opening theme jingles.** NOT breaks.

7. **Brief station IDs or stingers (under ~10 seconds) standing alone**,
   not surrounded by promo content. NOT a break.

# MERGE RULE — VERY IMPORTANT

Break material is often played BACK-TO-BACK, separated only by short jingles,
station IDs, news/sports headlines, music beds, or brief snippets of another
host's voice that may sound like the show resuming but are still automated
Diwan FM content.

You MUST merge ALL of the following into a SINGLE break range:
- Multiple consecutive promo spots.
- Jingles, stingers, station IDs, ads, news, sports, and bumpers between them.
- Brief (under ~30s) segments where it sounds like a host might be back, if
  they are followed by more promo content rather than sustained show talk.

Only END a break when there is SUSTAINED (>30 seconds) main-show content:
the main moderator and/or guests discussing the actual show topic.

# LENGTH EXPECTATION

Regular breaks are often about **3 to 6 minutes**. Some are much shorter
(around 1 to 2 minutes). The top-of-the-hour news/sports break can be much
longer, around **15 to 20 minutes**. Do not truncate a long break just because
it contains professional news/sports voices.

If you find multiple short (<90s) "breaks" clustered within a few minutes of
each other, you have probably fragmented one real break — merge them unless
sustained rafmag studio discussion clearly resumes between them.

# COMPLETENESS

Scan all the way to the end of the input. Do NOT stop flagging promo content
before the input ends. Be especially careful at the END of each break: the
true end is the moment SUSTAINED show content resumes, which is often
several minutes after the first promo started.

Most full archived episodes have about 4 to 7 noisy breaks. This is a sanity
check, not a hard rule. If you are analyzing a long full episode and find only
1 or 2 breaks, re-scan for the learned entry phrases before finalizing.

{output_context}
"""


BREAK_OUTPUT_CONTEXT = """\
# OUTPUT MODE: BREAKS TO SKIP

Return the noisy radio break ranges to skip.

JSON only, no prose, no markdown fences:

{
  "breaks": [
    {
      "startSec": 1234,
      "endSec": 1456,
      "type": "ad",
      "evidence": "Moderator says 'فاصل ثم نواصل' at MM:SS. Break contains station promos/news/sports. Rafmag studio discussion resumes at MM:SS."
    }
  ]
}

Rules:
- "startSec" and "endSec" are integers, in seconds, in the SAME TIMEBASE as
  the video segment you were given (clip-relative if a clip was specified;
  treat the start of the clip as 00:00).
- "type" is one of: "ad", "promo", "break".
- "evidence" is a short string explaining why the start and end boundaries
  are correct.
- Do not include any fields other than "startSec", "endSec", "type", and
  "evidence" inside each break.
- Sort the array by "startSec".
- An empty array {"breaks": []} is correct if no breaks exist in the input.
- Prefer FEWER, LONGER, CORRECT ranges over MANY SHORT, FRAGMENTED ones.
"""


SHOW_OUTPUT_CONTEXT = """\
# OUTPUT MODE: SHOW CONTENT TO KEEP

Return the rafmag show-content ranges to keep, not the noisy break ranges to
skip.

SHOW CONTENT includes:
- Rafmag studio/panel discussion with the main moderator and guests.
- Zapping recap segments.
- Box News when it is introduced as a rafmag segment.
- Columnist / chroniqueur segments.
- Live in-show sponsor reads, giveaways, callers, and selected music when the
  rafmag moderator or panel is actively carrying the show.
- Rafmag intro/outro once the actual show has started.

SHOW CONTENT excludes:
- Pre-show waiting audio before rafmag really begins.
- Noisy radio breaks: Diwan FM promos, station IDs, jingles, commercial ads,
  generic station news, sports flashes, and pre-recorded bumpers.

JSON only, no prose, no markdown fences:

{
  "showSegments": [
    {
      "startSec": 1234,
      "endSec": 1456,
      "type": "show",
      "evidence": "Rafmag studio discussion starts/resumes at MM:SS and continues until the moderator hands off to a break at MM:SS."
    }
  ]
}

Rules:
- "startSec" and "endSec" are integers, in seconds, in the SAME TIMEBASE as
  the video segment you were given (clip-relative if a clip was specified;
  treat the start of the clip as 00:00).
- "type" must be exactly "show".
- "evidence" is a short string explaining why this range is rafmag show
  content and why it ends.
- Do not include any fields other than "startSec", "endSec", "type", and
  "evidence" inside each show segment.
- Sort the array by "startSec".
- Do not include pre-show waiting content.
- If a clip starts inside real rafmag show content, the first show segment can
  start at 0.
- If a clip ends while real rafmag show content is still ongoing, the last
  show segment can end at the clip end.
- Prefer FEWER, LONGER, CORRECT show ranges split only by real noisy breaks.
"""


def build_prompt(start: int | None, end: int | None, output: str) -> str:
    if start is None and end is None:
        segment_context = """\
# FULL-VIDEO START GATING

You are analyzing the full YouTube archive, not a clipped segment. The first
minutes can contain pre-show waiting audio or station filler before rafmag
actually begins. Never report a break that starts at 0 in a full-video run.
Find the first sustained rafmag studio intro first, then only report noisy
breaks that happen after real rafmag show content has started.

Full rafmag archives normally contain multiple noisy radio breaks. Returning
an empty array for a full archive should be rare; only do that if you are
confident there are no moderator hand-offs, no station news/sports breaks, and
no Diwan FM promo/ad blocks after the rafmag show starts.
"""
    else:
        segment_context = """\
# CLIP BOUNDARY RULES

You are analyzing a clipped segment, so all output times must be relative to
the start of this clip. If the clip starts while already inside a noisy break
that began earlier after rafmag show content had started, report that break as
starting at 0. If the clip ends while still inside a noisy break and rafmag
show content has not resumed, report that break as ending at the clip end.
"""
    output_context = SHOW_OUTPUT_CONTEXT if output == "show" else BREAK_OUTPUT_CONTEXT
    return (
        PROMPT_TEMPLATE.replace("{segment_context}", segment_context)
        .replace("{output_context}", output_context)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Public YouTube URL of the rafmag episode")
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="Clip start in seconds (default: from beginning)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Clip end in seconds (default: to end)",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Gemini model id (default: gemini-2.5-flash; try gemini-2.5-pro if you need 2M context)",
    )
    parser.add_argument(
        "--output",
        choices=["breaks", "show"],
        default="breaks",
        help="Return noisy breaks to skip or show-content segments to keep (default: breaks)",
    )
    parser.add_argument(
        "--resolution",
        choices=["low", "medium", "high"],
        default="low",
        help="Video token-spend per frame (default: low — fine for a radio show)",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=8192,
        help="Maximum JSON output tokens (default: 8192)",
    )
    parser.add_argument(
        "--thinking-budget",
        type=int,
        default=1024,
        help="Gemini thinking token budget where supported (default: 1024)",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=20,
        help="Seconds between waiting-status messages on stderr (default: 20)",
    )
    parser.add_argument(
        "--duration",
        default=None,
        help="Video duration for --print-chunk-plan, as seconds or HH:MM:SS",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=1800,
        help="Chunk size for --print-chunk-plan (default: 1800)",
    )
    parser.add_argument(
        "--overlap-seconds",
        type=int,
        default=300,
        help="Chunk overlap for --print-chunk-plan (default: 300)",
    )
    parser.add_argument(
        "--print-chunk-plan",
        action="store_true",
        help="Print clip commands for an overlapping chunk run, then exit",
    )
    return parser.parse_args()


def build_video_part(url: str, start: int | None, end: int | None) -> types.Part:
    metadata = None
    if start is not None or end is not None:
        metadata = types.VideoMetadata(
            start_offset=f"{start}s" if start is not None else None,
            end_offset=f"{end}s" if end is not None else None,
        )
    return types.Part(
        file_data=types.FileData(file_uri=url),
        video_metadata=metadata,
    )


def describe_segment(start: int | None, end: int | None) -> str:
    if start is None and end is None:
        return "full video"
    return f"clip start={start if start is not None else 0}s end={end if end is not None else 'video end'}"


def parse_duration(value: str) -> int:
    if value.isdigit():
        return int(value)

    parts = value.split(":")
    if not 2 <= len(parts) <= 3:
        raise ValueError("duration must be seconds, MM:SS, or HH:MM:SS")

    try:
        numbers = [int(part) for part in parts]
    except ValueError as e:
        raise ValueError("duration must contain only integers") from e

    if len(numbers) == 2:
        minutes, seconds = numbers
        return minutes * 60 + seconds

    hours, minutes, seconds = numbers
    return hours * 3600 + minutes * 60 + seconds


def extract_video_id(url: str) -> str:
    match = VIDEO_ID_RE.search(url)
    return match.group(1) if match else "video"


def chunk_windows(duration_sec: int, chunk_sec: int, overlap_sec: int) -> list[tuple[int, int]]:
    if duration_sec <= 0:
        raise ValueError("duration must be greater than 0")
    if chunk_sec <= 0:
        raise ValueError("chunk-seconds must be greater than 0")
    if overlap_sec < 0:
        raise ValueError("overlap-seconds must be 0 or greater")
    if overlap_sec >= chunk_sec:
        raise ValueError("overlap-seconds must be smaller than chunk-seconds")

    windows: list[tuple[int, int]] = []
    step = chunk_sec - overlap_sec
    start = 0
    while start < duration_sec:
        end = min(start + chunk_sec, duration_sec)
        windows.append((start, end))
        if end == duration_sec:
            break
        start += step
    return windows


def print_chunk_plan(args: argparse.Namespace) -> int:
    if args.duration is None:
        print("--print-chunk-plan requires --duration", file=sys.stderr)
        return 1

    try:
        duration_sec = parse_duration(args.duration)
        windows = chunk_windows(duration_sec, args.chunk_seconds, args.overlap_seconds)
    except ValueError as e:
        print(f"Invalid chunk plan: {e}", file=sys.stderr)
        return 1

    video_id = extract_video_id(args.url)
    print(f"# {len(windows)} overlapping clip commands for {video_id}")
    print("# Run from experiments/01-gemini-quality")
    print("mkdir -p results")
    for index, (start, end) in enumerate(windows, 1):
        output = f"results/{video_id}-{index:02d}-{start}-{end}.json"
        output_arg = "" if args.output == "breaks" else f" --output {args.output}"
        print(
            f'python test.py "{args.url}" --model {args.model} '
            f"--start {start} --end {end}{output_arg} > {output}"
        )
    return 0


def run_with_heartbeat(label: str, interval: int, fn):
    print(label, file=sys.stderr, flush=True)
    if interval <= 0:
        return fn()

    done = threading.Event()
    started = time.monotonic()

    def report_waiting() -> None:
        while not done.wait(interval):
            elapsed = int(time.monotonic() - started)
            print(f"  still waiting for Gemini... {elapsed}s elapsed", file=sys.stderr, flush=True)

    reporter = threading.Thread(target=report_waiting, daemon=True)
    reporter.start()
    try:
        return fn()
    finally:
        done.set()
        reporter.join(timeout=1)
        elapsed = int(time.monotonic() - started)
        print(f"  Gemini call finished after {elapsed}s", file=sys.stderr, flush=True)


def output_key(output: str) -> str:
    return "showSegments" if output == "show" else "breaks"


def response_schema(output: str) -> dict:
    return SHOW_RESPONSE_SCHEMA if output == "show" else BREAK_RESPONSE_SCHEMA


def normalize_response(data: object, output: str) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    if not isinstance(data, dict):
        raise ValueError("Gemini response must be a JSON object.")

    key = output_key(output)
    raw_ranges = data.get(key)
    if not isinstance(raw_ranges, list):
        raise ValueError(f'Gemini response must contain a "{key}" array.')

    normalized = []
    valid_types = {"show"} if output == "show" else {"ad", "promo", "break"}
    default_type = "show" if output == "show" else "break"
    label = "show segment" if output == "show" else "break"

    for index, item in enumerate(raw_ranges, 1):
        if not isinstance(item, dict):
            warnings.append(f"Skipped {label} #{index}: not an object.")
            continue

        try:
            start_sec = int(item["startSec"])
            end_sec = int(item["endSec"])
        except (KeyError, TypeError, ValueError):
            warnings.append(f"Skipped {label} #{index}: missing or invalid startSec/endSec.")
            continue

        if end_sec <= start_sec:
            warnings.append(f"Skipped {label} #{index}: endSec <= startSec.")
            continue

        range_type = item.get("type", default_type)
        if range_type not in valid_types:
            warnings.append(
                f"Normalized {label} #{index}: invalid type {range_type!r} -> {default_type!r}."
            )
            range_type = default_type

        evidence = item.get("evidence", "")
        if not isinstance(evidence, str):
            evidence = str(evidence)

        normalized.append(
            {
                "startSec": start_sec,
                "endSec": end_sec,
                "type": range_type,
                "evidence": evidence,
            }
        )

    normalized.sort(key=lambda b: b["startSec"])
    return {key: normalized}, warnings


def extract_complete_json_objects(text: str, key: str) -> list[dict]:
    key_position = text.find(f'"{key}"')
    if key_position == -1:
        return []

    array_start = text.find("[", key_position)
    if array_start == -1:
        return []

    objects: list[dict] = []
    object_start: int | None = None
    depth = 0
    in_string = False
    escaped = False

    for index, char in enumerate(text[array_start + 1 :], array_start + 1):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            if depth == 0:
                object_start = index
            depth += 1
            continue

        if char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and object_start is not None:
                raw_object = text[object_start : index + 1]
                try:
                    parsed = json.loads(raw_object)
                except json.JSONDecodeError:
                    object_start = None
                    continue
                if isinstance(parsed, dict):
                    objects.append(parsed)
                object_start = None
            continue

        if char == "]" and depth == 0:
            break

    return objects


def parse_or_recover_response(text: str, output: str) -> tuple[dict, list[str]]:
    try:
        raw = json.loads(text)
        return normalize_response(raw, output)
    except json.JSONDecodeError as e:
        recovered = extract_complete_json_objects(text, output_key(output))
        if not recovered:
            raise ValueError(f"Could not parse Gemini JSON response: {e}") from e

        parsed, warnings = normalize_response({output_key(output): recovered}, output)
        warnings.insert(
            0,
            "Gemini returned truncated JSON. Recovered only complete range objects; "
            "later ranges may be missing.",
        )
        return parsed, warnings


def print_usage_metadata(response, parsed: dict | None, args: argparse.Namespace) -> None:
    if response.usage_metadata is None:
        return

    prompt_tokens = response.usage_metadata.prompt_token_count
    if (
        args.start is None
        and args.end is None
        and parsed is not None
        and not parsed[output_key(args.output)]
        and prompt_tokens is not None
        and prompt_tokens > 900_000
    ):
        print(
            "\nwarning: full-video run consumed >900k prompt tokens and returned no ranges. "
            "Treat this as unreliable; rerun with overlapping clips.",
            file=sys.stderr,
        )

    print(
        f"\n[tokens] prompt={prompt_tokens} "
        f"output={response.usage_metadata.candidates_token_count} "
        f"total={response.usage_metadata.total_token_count}",
        file=sys.stderr,
    )


def main() -> int:
    args = parse_args()

    if args.print_chunk_plan:
        return print_chunk_plan(args)

    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and paste your key.",
            file=sys.stderr,
        )
        return 1

    resolution_map = {
        "low": types.MediaResolution.MEDIA_RESOLUTION_LOW,
        "medium": types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,
        "high": types.MediaResolution.MEDIA_RESOLUTION_HIGH,
    }

    client = genai.Client(api_key=api_key)

    prompt = build_prompt(args.start, args.end, args.output)
    print(
        f"Preparing Gemini request: model={args.model}, "
        f"resolution={args.resolution}, output={args.output}, "
        f"segment={describe_segment(args.start, args.end)}",
        file=sys.stderr,
    )
    if args.start is None and args.end is None:
        print(
            "  full-video analysis is experimental; clips are more reliable for this task",
            file=sys.stderr,
        )

    try:
        response = run_with_heartbeat(
            "Calling Gemini video understanding API...",
            args.heartbeat_interval,
            lambda: client.models.generate_content(
                model=args.model,
                contents=types.Content(
                    parts=[
                        build_video_part(args.url, args.start, args.end),
                        types.Part(text=prompt),
                    ]
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema(args.output),
                    media_resolution=resolution_map[args.resolution],
                    max_output_tokens=args.max_output_tokens,
                    temperature=0,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=args.thinking_budget,
                    ),
                ),
            ),
        )
    except errors.APIError as e:
        print(f"Gemini API error: {e}", file=sys.stderr)
        return 1

    text = response.text or ""
    try:
        parsed, warnings = parse_or_recover_response(text, args.output)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print("\nRaw response:", file=sys.stderr)
        print(text, file=sys.stderr)
        print_usage_metadata(response, None, args)
        return 1

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    print_usage_metadata(response, parsed, args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
