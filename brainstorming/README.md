# Brainstorming — `rafmag-browser-extension`

This folder is the living record of our shared understanding of the project, built up round by round before any implementation planning begins.

## TL;DR

A browser extension that **auto-skips the ad/promo breaks** in the YouTube live-archive recordings of the Tunisian radio show **`rafmag`**, so listeners (starting with the project author's mother) can play the show as **background audio** while doing other tasks at home — without having to walk back to the computer to manually skip past the loud upcoming-show promos every time the moderator goes on break.

**How it works** (in one breath): a backend feeds each episode's YouTube URL to **Gemini**, which returns the `{start, end}` timestamps of the **show-content** segments (everything between the breaks). Those ranges are stored in Firestore keyed by video ID and exposed via a small Cloud Function. The Firefox extension activates only on Diwan FM's `rafmag` videos, hits that endpoint, auto-seeks the player to the first show segment, and silently skips past every break. Heavy LLM work runs **once per episode**, not per viewer or per refresh.

**MVP for the hackathon**: extension + Firestore + read-endpoint + a one-shot backfill script that pre-populates the DB with the last month of episodes. The live auto-process pipeline (PubSubHubbub + polling) is deferred — see [`04-scope.md`](./04-scope.md).

## Sibling folders

- [`../adr/`](../adr/) — committed architecture decisions
- [`../experiments/`](../experiments/) — empirical tests that feed back into both this folder and `adr/`

## How to read this folder

Read the numbered files in order — they tell the project's story:

1. [`01-problem.md`](./01-problem.md) — what's broken in the world today
2. [`02-users.md`](./02-users.md) — who feels that pain
3. [`03-solution.md`](./03-solution.md) — what `rafmag` does about it
4. [`04-scope.md`](./04-scope.md) — what's in / out of the MVP
5. [`05-constraints.md`](./05-constraints.md) — what limits the design

Cross-cutting:

- [`glossary.md`](./glossary.md) — every domain term we've agreed on
- [`open-questions.md`](./open-questions.md) — things we haven't resolved yet

## Status

| Round | Focus | Status |
|-------|-------|--------|
| 1 | Problem & users | ✅ done |
| 2 | Solution & name | ✅ done — backend & data ADRs drafted in [`../adr/`](../adr/) |
| 3 | MVP scope | ✅ done — see [`04-scope.md`](./04-scope.md) |
| 4 | Constraints | ⏳ pending |
| 5 | Final review | ⏳ pending |
