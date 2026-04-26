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

### Run 2 — gemini-3.1-pro-preview, low resolution, full episode, `--output show`

After [experiment 02](../02-show-grammar/) produced [`grammar.md`](../02-show-grammar/grammar.md), the prompt in `test.py` was rewritten with the empirical break-entry / break-return phrases and the "WHAT IS NOT A BREAK" trap list. Re-ran on the same video as run 1, this time on the full episode and asking for show-content ranges instead of break ranges.

- URL: `https://www.youtube.com/watch?v=kEjaNLGr4U0`
- Command: `python test.py "<url>" --model gemini-3.1-pro-preview --output show --max-output-tokens 16000`
- Tokens: prompt = 873,280 / output = 911 / total ≈ 883,877. **~87% of the 1M-token context** for a single full-episode call at low resolution.
- Wall-clock: 254s.

**What Gemini returned:** 11 `showSegments` covering 18:27 onward.

**What we have ground truth for** (from run 1, same video): the real ad break is at absolute **29:03 – 33:53**. Gemini's `showSegments` imply the break gap is **28:38 – 33:29**.

| Edge      | Gemini | Reality | Off-by                                              |
|-----------|--------|---------|-----------------------------------------------------|
| Break start | 28:38 | 29:03  | **25s early** — extension would skip 25s of show    |
| Break end   | 33:29 | 33:53  | **24s early** — extension would resume into 24s of break audio |

That's outside the ±15s decision rule.

**Red flag — periodic fabrication.** From segment 2 onward the output becomes implausibly regular: every show segment is 385–387s, every gap is exactly 137s or 291s, and the `evidence` strings repeat verbatim across alternating segments. Real radio doesn't run on a metronome — the grammar work showed the show has one ~15–20 min mega break, not a fixed cadence. The most plausible explanation: at 87% of the token budget on a 2h+ video, the model loses fidelity past a certain point and pattern-completes a synthetic schedule rather than continuing to attend to the audio. Where ground truth exists (the early portion of the video) the segmentation is roughly right but boundary-loose; where ground truth doesn't exist (the later portion) the output looks fabricated.

**Implications:**

- The grammar-grounded prompt did remove the run-1 columnist false positive in the area we have ground truth for. That's a real improvement.
- Boundary precision is still off (~25s vs ±15s target).
- **Full-episode at low resolution is not a viable invocation strategy** for this video length. A chunked-clip strategy (already implemented in `test.py` via `--chunk-seconds` / `--overlap-seconds`) is the next thing to try.

**User decision (Round 3):** treat this as good enough to **proceed with MVP scope decisions** (so brainstorming could move forward) — not as a final validation of the Gemini path. ADR 0001 stays **Proposed**. A clean validation run on a manually annotated episode (`yaeWOrjiDRM`, with 7 ground-truth break ranges) is the next test that should flip the ADR to **Accepted** or trigger the Whisper fallback.

## Conclusion

**Status: inconclusive — the language and grammar layers work, the boundary layer is still ±25s and full-episode runs degrade past ~80% of the token budget.** Open next moves:

- **Chunked-clip strategy on `yaeWOrjiDRM`** — feed 30-min windows with 5-min overlap, merge ranges, score against the manually annotated 7 break ranges.
- **`gemini-2.5-pro` or `gemini-3.1-pro-preview` on a single short clip with tight ground truth** — establish a per-clip accuracy floor before scaling up.
- **Fall back to the Whisper plan** if chunked clips can't get inside ±15s — `audio → Whisper transcript → Gemini on full transcript`. Boundary reasoning over text is more controllable than over multi-hour low-res video.

Decision deferred until a chunked-clip run on `yaeWOrjiDRM` is scored.
