# Experiment 01 — Gemini ad-break detection quality

## Question

Can **Gemini 2.5 Flash**, given a public `rafmag` YouTube URL, reliably identify the **ad/promo break ranges** in the video using only the moderator's Tunisian-dialect cues and audio shifts?

This is the **single biggest unknown** in [ADR 0001](../../adr/0001-backend-stack.md) — if Gemini can do this well enough, the whole pipeline collapses to one API call. If it can't, we need the Whisper fallback.

## Hypothesis

Gemini's documented weakness on Tunisian Derja is for **verbatim transcription**. Our task is **boundary detection**, which is much coarser — we just need to know that *somewhere around minute 23* the moderator handed off to a promo block. So we expect Gemini to perform usably here even if its raw transcription would be poor.

## Ground truth (filled by user)

YouTube URL: `<paste here>`

Episode duration: `<HH:MM:SS>`

Known ad-break ranges (best-effort — fill what you remember from listening):

| # | startSec | endSec | What's playing during the break |
|---|----------|--------|---------------------------------|
| 1 |          |        |                                 |
| 2 |          |        |                                 |
| 3 |          |        |                                 |

Notes about the episode (anything unusual — guest interview, special format, etc.):

> _(fill in)_

## Setup

```bash
cd experiments/01-gemini-quality
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# open .env and paste your Gemini API key (get one at https://aistudio.google.com/apikey)
```

## Run

The script defaults to **low video resolution** (we don't need frame detail for a radio show — the audio is what matters), which fits roughly **4 hours** of content into Gemini 2.5 Flash's 1M-token context. If your episode is even longer, use the clip flags or switch to `gemini-2.5-pro` (2M context).

```bash
# Whole episode, low res (the default — usually what you want):
python test.py "https://www.youtube.com/watch?v=kEjaNLGr4U0" > result.json

# Just a 10-min clip you suspect contains a break (fastest, cheapest sanity check):
python test.py "https://www.youtube.com/watch?v=kEjaNLGr4U0" --start 1200 --end 1800 > result.json

# Return the rafmag show-content ranges to keep instead of the break ranges to skip:
python test.py "https://www.youtube.com/watch?v=kEjaNLGr4U0" --start 1200 --end 1800 --output show > show-result.json

# Bigger model for longer episodes or harder cases:
python test.py "https://www.youtube.com/watch?v=kEjaNLGr4U0" --model gemini-2.5-pro > result.json
```

Token usage for the run is printed to stderr, so it doesn't end up in `result.json`.

> **Tip for the first run**: do the clip version. Pick a 5–10 min window where you *know* a break occurs. If Gemini finds it there, expand to the full episode.

## Evaluation

After running, fill in the table below by comparing `result.json` to the ground-truth ranges above.

| Ground-truth break # | Detected by Gemini? | Gemini's startSec | Gemini's endSec | Off-by (sec) | Notes |
|----------------------|---------------------|-------------------|-----------------|--------------|-------|
| 1                    |                     |                   |                 |              |       |
| 2                    |                     |                   |                 |              |       |
| 3                    |                     |                   |                 |              |       |

False positives (Gemini flagged a range that isn't actually a break):

| Gemini's startSec | Gemini's endSec | What's actually there | Notes |
|-------------------|-----------------|------------------------|-------|
|                   |                 |                        |       |

## Decision rule

- **Accept** (Gemini path is good enough for MVP): every real break detected with start within ±15s; ≤1 false positive on the test episode; no false positive longer than ~30s.
- **Reject and fall back to Whisper**: any real break missed; multiple false positives; or ranges drifting >30s off.
- **Inconclusive**: re-run on a second episode with different format/length before deciding.

## Result

### Run 1 — gemini-2.5-flash, low resolution, clip 1500–2100s

- URL: `https://www.youtube.com/watch?v=kEjaNLGr4U0`
- Command: `python test.py "<url>" --start 1500 --end 2100`
- Timestamps in Gemini's output are **clip-relative** (i.e. `00:00` in the output = `25:00` in the original video).

**Ground truth for this clip:** one real ad break, absolute 29:03–33:53, which is **clip-relative 04:03–08:53** (~4:50 long). Before the break, a guest columnist does a recap segment of the previous show — *legitimate show content*, with a voice that differs from the main moderator's.

**What Gemini returned:**

| Gemini break (clip) | Gemini break (absolute) | Reality                                                                |
|---------------------|--------------------------|------------------------------------------------------------------------|
| 02:53 – 03:52       | 27:53 – 28:52           | End of the columnist's recap. **False positive — legit show content.** |
| 04:09 – 04:52       | 29:09 – 29:52           | Inside the real ad break ✅                                             |
| 05:07 – 05:52       | 30:07 – 30:52           | Inside the real ad break ✅                                             |
| 06:10 – 06:52       | 31:10 – 31:52           | Inside the real ad break ✅                                             |
| (none)              | 32:00 – 33:53           | Still inside the real ad break. **Truncation — ~2 min missed.**        |

**Three failure modes observed:**

1. **Sub-break splitting.** A single ~5-min ad block was returned as three ~45s blocks with phantom "moderator returns" between them. Auto-skip would still mostly work but the listener hears ~15s of promo audio between each skip.
2. **Columnist false positive.** Gemini interpreted the voice shift between the main moderator and a guest columnist (and the "we're back" phrase that follows the columnist's segment) as an ad break. Acting on this would skip real show content.
3. **Late-end truncation.** Gemini stopped flagging promos ~2 minutes before the real break ended. The tail of the break would play through.

**One clear win:**

- Language quality is good — Gemini quoted specific Derja phrases (`يلا شباب نتقابلو غدوة في الزابينغ`, `ما تبعدوش`) and structured output as requested. The original concern about Tunisian-dialect performance does not appear to be the bottleneck for this task.

## Conclusion

**Status: inconclusive — the language layer works, the boundary layer needs more iteration.** Possible next moves:

- **Prompt refinement** — explicitly instruct Gemini that (a) consecutive promos with brief jingles between them are *one* break, (b) voice shifts to a co-host / columnist are NOT breaks, (c) breaks can run several minutes and should be reported as a single contiguous range.
- **Run on the full episode**, not a 10-minute clip — more context might help Gemini distinguish recurring co-host segments from ad breaks.
- **Try `gemini-2.5-pro`** — same input, larger model.
- **Fall back to the Whisper plan** — `audio → Whisper transcript → Gemini on full transcript`. Boundary reasoning over text might be more controllable than over a 10-minute video chunk.

Decision deferred until at least one of the above is tried.
