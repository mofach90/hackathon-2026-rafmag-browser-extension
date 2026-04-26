# ADR 0003 — Tech stack and repo structure

- **Status**: Accepted
- **Date**: 2026-04-26
- **Deciders**: Mohamed (project owner)

## Context

ADRs 0001 (backend stack) and 0002 (data storage) committed to *what* runs (Cloud Functions Gen 2 + Firestore + Gemini). This ADR commits to the *language and tooling* across the three buildable components — the backend, the backfill script, and the browser extension — and to the layout that holds them in one repo.

Constraints driving the decision:

- **One person, junior dev.** Every tool added is a tool to learn, configure, and maintain.
- **Existing code is Python.** `experiments/01-gemini-quality/test.py` already encodes the validated Gemini prompt and the `--output show` parser. The MVP backfill script (per [`brainstorming/04-scope.md`](../brainstorming/04-scope.md)) reuses that code.
- **Firefox MV3 + cross-browser as a stretch goal.** Per [`brainstorming/05-constraints.md`](../brainstorming/05-constraints.md). The extension toolchain should not lock us out of a future Chrome port.
- **Senior-team feel without over-engineering.** Modern tooling where it pays for itself daily; defer monorepo workspace complexity until a second consumer actually exists.

## Decision

| Component | Language | Build / package tool | Notes |
|-----------|----------|----------------------|-------|
| Browser extension | **TypeScript** | **WXT** + **pnpm** | Firefox MV3 first, Chrome via WXT's cross-browser flag later. |
| Cloud Functions backend | **Python** | **uv** (`pyproject.toml` + `uv.lock`); export to `requirements.txt` for deploy | Deploys via `gcloud functions deploy --runtime=python312`. |
| One-shot scripts (`backfill.py` etc.) | **Python** | **uv** (same project or sibling, TBD when second script exists) | Reuses the `test.py` Gemini call directly. |
| Shared Python code | *deferred* | — | Not introduced until a second Python consumer (the eventual pipeline Cloud Function) actually exists. |

### Repo layout

```
.
├── extension/           # WXT + TypeScript
├── backend/             # Cloud Functions (Python) — episode_read for MVP
├── scripts/             # backfill.py + future one-shots (Python)
├── adr/                 # this folder
├── brainstorming/       # discovery docs
├── experiments/         # empirical validation
├── .github/             # CI workflows, PR + issue templates
├── CONTRIBUTING.md      # how-we-work index
├── README.md            # project elevator pitch
└── .gitignore
```

`extension/`, `backend/`, and `scripts/` each carry their own `README.md` (local "how to run / how to test"), their own dependency manifest, and their own test setup.

## Alternatives considered

### Backend in Node.js + TypeScript

Would unify the repo on one language and enable a shared `types/` package for the extension ↔ backend JSON contract. Rejected because (a) we'd rewrite the validated Gemini prompt + parser already living in Python, (b) the JSON contract is two fields (`startSec`, `endSec`) — type sharing is low-value at this scale, (c) `google-genai` Python SDK is Google's reference implementation and every doc page leads with Python.

### Backend in Go

Best cold-start latency, strict typing, smallest binary. Rejected because cold start is irrelevant to our < 2s seek-on-load budget, and learning Go would extend the project for no functional gain.

### Plasmo or Vite-with-manual-MV3 for the extension

Plasmo is React-heavy and Chrome-biased; overkill for a one-page popup + content script. Vite with hand-rolled MV3 setup is doable but loses WXT's auto-reload, manifest typing, and one-flag cross-browser builds. WXT covers our scope with the smallest framework surface.

### Single Python project at root (`pyproject.toml` at top, all Python under `src/rafmag/`)

The most "Python-canonical" monorepo shape. Rejected for two reasons: (a) Cloud Functions Gen 2 deploys from a self-contained source directory — a single root project requires a copy/vendor step at deploy time, which is friction we don't need at MVP scope, (b) it conflates the CLI and the server, two things that evolve at different rates.

### Flat monorepo with `shared/` from day one

Considered. Rejected for MVP because there is currently exactly one Python consumer of the Gemini call (`backfill.py`). The Rule of Three applies — wait for a second consumer (the eventual pipeline function) before extracting a shared package. Refactor cost when the trigger arrives is low.

### `requirements.txt` only (no `pyproject.toml`)

Simpler, ships with pip, Cloud Functions reads it natively. Rejected because `pyproject.toml` + a lock file is now the modern Python baseline, and `uv` makes the modern stack faster than the legacy one. Defaulting to legacy when the modern tool is strictly better would be a missed signal of seniority.

### npm or yarn for the extension

npm ships with Node and has zero install cost. yarn is the legacy 2017–2020 default. Rejected in favor of pnpm because (a) pnpm's strict mode catches phantom-dep bugs that npm allows, (b) workspace support is materially better if we ever introduce a shared TS package, (c) install speed and disk usage in CI matter even at one-package scale.

## Consequences

### Good

- **Zero rewrite of validated code.** The Python Gemini call from experiment 01 ports straight into `scripts/backfill.py` and (later) the pipeline Cloud Function.
- **Modern, fast dev loop.** uv installs in seconds; WXT auto-reloads the extension on save; pnpm's disk cache makes the second `pnpm install` near-instant.
- **Cross-browser is one flag.** WXT's build target switch leaves the extension code unchanged.
- **Clear component boundaries.** Three top-level folders, three independent dependency files, three READMEs. A new contributor finds the right place in seconds.

### Bad

- **Two languages in one repo.** Switching contexts between TS and Python carries a small daily cost. Tooling can't unify (different linters, different formatters, different CI matrix). Acceptable cost for a senior-typical layout.
- **No shared code yet → some duplication is possible.** The read endpoint will likely import the Firestore client; if/when a pipeline function lands and wants the Gemini call too, we extract `shared/`. We accept this as a deferred refactor.
- **uv is < 5 years old.** Faster ecosystem move means faster API churn risk. Mitigated by exporting to `requirements.txt` for deploy — the Cloud Function never sees uv directly.
- **WXT is a relatively young framework** (v1.0 in 2024). If it goes unmaintained, the extension code is portable but the build config is rewritten. Contained risk.

### Neutral

- A future shared TS types package between extension and backend is *possible* but unlikely to be worth it: the JSON contract is small. We're not closing the door, just not opening it preemptively.

## When we'd revisit this

- **Second Python consumer of the Gemini call appears** (the eventual pipeline Cloud Function). **Action:** introduce `shared/` Python package, publish via `uv build`, add a `cp -r shared/ backend/<func>/` step to the deploy script.
- **Cold-start latency becomes a UX problem on the read endpoint** (above the 2s seek-on-load budget). **Action:** evaluate Cloud Run min-instances, or rewrite the read function in Go. ADR likely amended, not superseded.
- **Cross-browser port begins.** **Action:** flip WXT's target flag, validate manifest differences, no ADR change expected.
- **WXT or uv goes unmaintained.** **Action:** new ADR documenting the migration; extension/backend code mostly portable, only build config changes.
