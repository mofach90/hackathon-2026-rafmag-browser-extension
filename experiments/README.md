# Experiments

Self-contained, runnable tests we use to **de-risk decisions before committing code**. Each experiment lives in its own numbered folder with its own README, scripts, and recorded results.

## Why a separate folder

- `brainstorming/` is for ideas in flux.
- `adr/` is for committed decisions.
- `experiments/` is for **empirical checks** that feed back into both.

If an ADR depends on an empirical assumption (e.g. *"Gemini can detect ad breaks in Tunisian dialect"*), the experiment that validates that assumption lives here, and the ADR links to it.

## How to add a new one

1. New folder: `00NN-short-kebab-title/`.
2. Inside it: a `README.md` (test plan + result), the script(s), and a `requirements.txt` or equivalent.
3. Add a row to the index below once the experiment has a result.

## Index

| #    | Title                                                           | Status      |
|------|-----------------------------------------------------------------|-------------|
| 0001 | [Gemini ad-break detection quality](./01-gemini-quality/)      | 🔄 run 1 done (run 2 prompt rewritten with grammar; ready to execute) |
| 0002 | [Show-grammar analysis](./02-show-grammar/)                    | ✅ done — see [`grammar.md`](./02-show-grammar/grammar.md). 10/10 transcripts usable. |
