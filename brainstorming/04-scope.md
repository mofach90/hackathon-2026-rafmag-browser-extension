# 04 — Scope

> Goal of this doc: draw a hard line around the MVP. Everything outside the line is a "later", not a "no".

## MVP — must exist for v1 to be useful

**Plain-language definition (user's words):**
> A Firefox extension that, when I play a `rafmag` video, looks up the show-content timestamps in its database and seeks the player to those parts. If the episode isn't in the database yet, a small error notification — and the video plays normally.

### Components

1. **Firefox browser extension**
   - Activates only when the YouTube tab's channel = **Diwan FM** AND the video title contains a `rafmag` variant (`rafmag`, `راف ماك`, plus common spellings).
   - On video load: queries backend by `videoId`.
     - **Found** → auto-seeks the player to the start of the first show segment, then silently auto-seeks past every subsequent break (silent = no toast, no popup; mom is in another room).
     - **Not found** → shows a small on-page error notification ("This episode hasn't been processed yet"). Video plays normally from `00:00`.
   - On every other YouTube page (and every non-rafmag Diwan FM video): **completely silent**, no DB call.

2. **Backend read endpoint** — single Cloud Function Gen 2
   - `GET /episode/{videoId}` → Firestore lookup via Admin SDK → returns `{ showSegments: [...] }` or `404`.
   - Why a function and not direct Firestore-from-browser: keeps credentials server-side, gives one place to add rate limits, security checks, and CORS.

3. **Firestore** — single collection `episodes/{videoId}`
   - Stores **show-content ranges** (not break ranges). See [`adr/0002-data-storage.md`](../../adr/0002-data-storage.md) for the schema.
   - Backfilled manually before demo day; nothing writes to it at runtime in MVP.

4. **One-shot backfill script** — `scripts/backfill.py`
   - Lists the last ~month of `rafmag` episodes via YouTube Data API.
   - For each video: runs the same Gemini call we validated in [experiment 01](../experiments/01-gemini-quality/) (the `--output show` mode) and writes the result to Firestore via Admin SDK.
   - Run **once** locally before the demo. No infra, no scheduler, no webhook.

### What "demo day works" looks like

- Mom installs the extension in Firefox.
- She opens any of the last ~20 `rafmag` episodes on YouTube.
- Player jumps past the intro. She does her chores.
- Each break she would have skipped manually is now auto-skipped.
- If she opens an even-older episode that wasn't backfilled, she sees the small notification and plays it normally.

## Nice-to-have — only if there's time

- **Browser badge counter** (e.g. extension icon shows `3` after three breaks were skipped this episode). Cheap visual feedback that the extension is doing something.
- **"Total time saved" popup** when she clicks the extension icon (e.g. "rafmag: 14 min skipped this episode"). Pure feel-good metric.
- **Preferences popup**: a single "disable on this video" toggle for the rare false-positive case.

## Explicitly out of scope — punted from MVP

| What | Why it's out | Where it lives instead |
|------|--------------|------------------------|
| **Live backend pipeline** (PubSubHubbub subscription + `actualEndTime` polling + auto-process on new episodes) | DB stays manually backfilled before demo. The pipeline is documented as the eventual architecture. | [`adr/0001-backend-stack.md`](../../adr/0001-backend-stack.md) |
| **Manual override / feedback loop** ("this wasn't a break" / "you missed one" buttons) | We don't have real-world false-positive rates yet. Build this once we see how often detection actually misfires. | Open question 10 (deferred) |
| **Multi-channel / generic-podcast support** | Hardcoded to Diwan FM channel ID for now. Generalizing would force us to redo the show-grammar work for each new channel. | Stretch goals |
| **Whisper fallback path** | Experiments 01 + 02 validated the Gemini-direct path. Whisper stays documented as a fallback only. | [`adr/0001-backend-stack.md`](../../adr/0001-backend-stack.md) |
| **Chrome / Edge / Safari support** | Firefox first. Manifest V3 specifics for cross-browser are non-trivial. | Round 4 (constraints) |
| **User accounts, sync, watch history** | The extension is stateless; mom is the only user. No reason to build accounts. | — |

## Stretch goals — direction post-hackathon

- **Cron-based weekly auto-backfill**: one Cloud Scheduler entry calling the backfill function. First step toward the live pipeline without the webhook complexity.
- **Full live pipeline**: PubSubHubbub → polling → auto-process, as documented in ADR 0001.
- **Feedback loop**: small `report` button in the extension writes a flag back to Firestore; we use the data to refine the prompt or retrigger processing.
- **Cross-browser**: port to Chrome/Edge once the Firefox version stabilizes.
