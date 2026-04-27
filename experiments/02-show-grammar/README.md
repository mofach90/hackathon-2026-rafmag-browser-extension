# Experiment 02 — Show-grammar analysis

## Question

What are the actual linguistic and structural patterns that mark ad/promo breaks in `rafmag`, derived empirically from a sample of past episodes?

## Why

Run 1 of [experiment 01](../01-gemini-quality/) showed that Gemini 2.5 Flash, given a hand-written prompt about "common Tunisian break-marker phrases," fragmented one real break into three sub-breaks, false-positived on a guest columnist's recap, and truncated the end of the real break. The most plausible cause: the prompt was speculative — phrases I (the assistant) guessed the moderator might use, structural assumptions I made up.

This experiment replaces that speculation with **empirical evidence from 10 real episodes** by:

1. Fetching the YouTube auto-transcripts for 10 past `rafmag` episodes (transcripts are already available for older episodes — no Whisper needed at this stage).
2. Sending all 10 transcripts in one prompt to a strong model (**gemini-3.1-pro-preview**) and asking it to extract:
   - Every distinct phrase the moderator uses to enter a break
   - Every distinct phrase used to return from a break
   - Columnist / chroniqueur segment patterns (so we stop confusing them with breaks)
   - Structural regularities (typical break count, length, placement)
   - False-positive traps that look like break markers but aren't
3. Distilling the model's output into [`grammar.md`](./grammar.md) — a "show grammar" reference document.
4. Using `grammar.md` to rewrite the prompt in [`../01-gemini-quality/test.py`](../01-gemini-quality/test.py) for run 2.

## Caveats

- YouTube auto-captions on Tunisian Derja are noisy (~40–60% WER on dialectal Arabic benchmarks). The analysis works on imperfect data — patterns should still emerge if the moderator uses consistent phrases, but rare or subtle ones may be lost.
- The strong model is giving us its **opinion** of what marks a break, not ground truth. We still need at least one episode with a manually annotated break (we already have one: clip 1500–2100 of `kEjaNLGr4U0`, real break at 29:03–33:53) to measure whether the new prompt is actually better.

## Setup

```bash
cd experiments/02-show-grammar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# paste your Gemini API key (https://aistudio.google.com/apikey) into .env
```

## Run

### Step 1 — pick 10 episodes and put them in `urls.txt`

Edit [`urls.txt`](./urls.txt) with one YouTube URL per line. Recommended spread:

- Mix of guests / topics (so phrasing variety shows up).
- At least 1–2 episodes that include the columnist / chroniqueur recap segment (so the analysis catches that pattern explicitly).
- At least one short and one long episode (so structural regularities aren't biased to one length).

### Step 2 — fetch transcripts

```bash
python fetch_transcripts.py
```

Saves one `transcripts/{videoId}.json` per URL. Skips any that already exist. Logs which transcripts were unavailable / language used / auto vs manual.

### Step 3 — analyze

```bash
python analyze.py
```

Sends all fetched transcripts in one Gemini call, writes the result to [`grammar.md`](./grammar.md). Token usage prints to stderr.

## Result

See [`grammar.md`](./grammar.md) (populated by `analyze.py` from 10/10 successfully fetched transcripts). Headline findings:

- **4 break-entry phrases** — `فاصل ثم نواصل` (10/10 episodes), `الاخبار ثم نعود` (10/10), `ترتيحه صغيره/العاده بالموزيكا` (~8/10), `فاصل صغير` / `ما تبعدوش` (~9/10).
- **3 break-return phrases** — `مرحبا مرحبا رجعنا لكم في ساعتنا الثانيه` (10/10), `مرحبا بكم في الجزء الاخير من حلقتنا لليوم` (10/10), explicit time announcements (10/10).
- **2 columnist segments** that look like breaks but aren't — Zapping (Rami Fourati, ~3–5 min, near top of show) and Box News / بوكس نيوز (Jihan Sallini, ~5–10 min, start of second hour).
- **Episode skeleton**: Intro → Zapping → Break → Trend → Live Ads → Mega Break (~15–20 min station news + sports) → Second Hour → Box News → Break → Panel → Break → Quiz → Outro. Typically 4–6 breaks per episode.
- **3 false-positive traps**: live in-show sponsor reads (Ooredoo, Volkswagen giveaways), the mega break's professionally-read station bulletin (still a noisy break the listener wants skipped), Zapping replay montages that quote the moderator saying "فاصل".

## Conclusion

The grammar produced a usable, much more specific prompt than the speculative one from run 1. It was folded back into [`../01-gemini-quality/test.py`](../01-gemini-quality/test.py) under `PROMPT_TEMPLATE` + `SHOW_OUTPUT_CONTEXT` (with a parallel `BREAK_OUTPUT_CONTEXT` for the break-detection mode). Experiment 01 is the validation of whether the rewritten prompt actually fixes the run-1 failure modes — see its README for run results.
