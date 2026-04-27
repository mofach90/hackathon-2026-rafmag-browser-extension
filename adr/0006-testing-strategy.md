# ADR 0006 — Testing strategy (pyramid, frameworks, coverage)

- **Status**: Accepted
- **Date**: 2026-04-26
- **Deciders**: Mohamed (project owner)

## Context

The repo has three components with very different testable surfaces:

- `extension/` — DOM manipulation, time math, message passing; runs in a real browser.
- `backend/` — Cloud Functions handlers around Firestore + Gemini API.
- `scripts/` — One-shot Python CLIs that mutate Firestore.

A blanket "follow the test pyramid uniformly" rule fits none of them well: it would over-invest in extension e2e (genuinely painful) and under-invest in backend integration (where the Firestore/Gemini contract is the most failure-prone surface). Senior teams pick the pyramid *shape* per component.

Constraints:

- **One contributor today (Mohamed), one user (his mother).** The strategy must not collapse under the daily cost it imposes.
- **Stretch goal: enterprise-pattern muscle memory** ([feedback memory](../README.md): canonical rigorous patterns over minimum-viable shortcuts).
- **CI gates land in Round E.** This round picks the strategy, frameworks, and coverage threshold; Round E wires the actual GitHub Actions workflows.

## Decision

### Test pyramid shape — per-component pragmatic

The pyramid is a lens, not a law. Per-component shape:

| Component | Unit | Integration | E2E |
|-----------|------|-------------|-----|
| `extension/` | **Heavy** — pure logic: timing math, URL parsing, segment merging, message envelope shape. | Light — content-script DOM behavior with `happy-dom`. | Real Firefox via Playwright (see below). |
| `backend/` | Medium — handler logic, prompt building, response parsing. | **Heavy** — Firestore client + handler flow against the Firebase Emulator Suite; Gemini calls against recorded fixtures. | Sparse — single deploy-and-hit smoke check per release branch. |
| `scripts/` | Medium — pure logic. | **Heavy** — full script run against the Firebase Emulator with fake input fixtures. | N/A — the script *is* the e2e. |

### Frameworks

| Layer | Tool | Notes |
|-------|------|-------|
| TS unit + component | **Vitest** | Vite-based (WXT runs on Vite — same toolchain), Jest-compatible API, fast. Default for new TS projects in 2024+. |
| TS DOM-needing tests | **Vitest + happy-dom** | Lighter than jsdom, sufficient for content-script-style DOM checks. |
| TS extension e2e | **Playwright** with Firefox extension loading | See "Extension e2e" below. |
| Python unit + integration | **pytest** + `pytest-asyncio` | Universal Python default. `pytest-asyncio` for our async Gemini/Firestore call paths. |
| Firestore in tests | **Firebase Emulator Suite** | Free, fast, official, same API surface as prod Firestore. Spun up per test session. |
| Gemini API in tests | **Recorded fixtures** | `vcrpy` (HTTP cassettes) or hand-rolled JSON fixtures. Real API calls in tests = cost + flake; record once, replay forever. Refresh fixtures on prompt changes. |
| Backend e2e | Single deployed-function smoke test on `release/*` branches | Manual `curl` or scripted check; pre-AMO release gate. |

### Extension e2e — Playwright with Firefox extension loading

Playwright drives a real Firefox build with the WXT-built `.zip` loaded via `--load-extension` (or web-ext's runner harness, depending on what works smoothly with Playwright). Targets:

- **Scope**: 1–3 happy-path scenarios. The auto-seek-to-first-show-segment flow is the single most important regression to catch.
- **Frequency**: every PR to `develop` (Round E) and every `release/*` branch.
- **Flake budget**: up to 2 retries per test allowed in CI; if a test flakes >5% over a week, quarantine it and triage.
- **Cost**: Firefox binary in CI (~1 min cold pull, cached otherwise); e2e wall-clock will dominate CI time. Acceptable in exchange for the regression-catching value.
- **Out of scope for now**: cross-OS testing (Linux runners only); cross-Firefox-version testing (current stable only); performance benchmarking.

### Coverage stance — hard ≥80% line coverage gate in CI

Each project (`extension/`, `backend/`, `scripts/`) ships its own coverage threshold; CI fails any PR that drops below 80% line coverage at the project level.

**Exclusion philosophy** (to keep the gate honest, not theatrical):

- Allowed exclusions: pure entry-point glue (`entrypoints/background.ts` boot code, `__main__` blocks), defensive `assert`s, type-only stubs.
- **Not** allowed: business logic, error handling on the happy path, prompt construction, response parsing, segment math, Firestore read/write paths.
- Exclusions live in tool config (`vitest.config.ts` `coverage.exclude`, `pyproject.toml` `tool.coverage.run.omit`), not as scattered comments. Every exclusion entry needs a one-line "why."

Coverage tooling:

- TS: Vitest's built-in `--coverage` (V8 provider).
- Python: `pytest-cov` → `coverage.py`.
- CI reporting: Codecov PR comment OR GitHub Actions step summary (Round E picks).

## Alternatives considered

### Pyramid shape: classic uniform pyramid for all components

Identical heavy-unit / modest-integration / sparse-e2e shape across all three. **Rejected** — over-invests in extension e2e (cost is real) and under-invests in backend integration (where the actual contract risk lives). The pyramid is a heuristic; senior teams shape it per service.

### Pyramid shape: minimum-viable hackathon mode

Test only the money paths (segment skipping). **Rejected** for conflicting with the enterprise-practice stretch goal — picking this would deny the muscle memory we're explicitly building.

### Extension e2e: deferred / manual smoke checklist (recommended)

5-minute manual Firefox checklist before each AMO submission, no CI automation. **Rejected** in favor of Playwright. Trade-off accepted: more CI complexity now in exchange for automated regression catch and the practice value of running real-browser e2e in CI.

### Extension e2e: Puppeteer

Chromium-only. **Rejected** — we ship a Firefox extension. WXT can produce Chromium builds too, but the production target is Firefox.

### Coverage: soft target with reporting, no gate (recommended)

~70% aspirational, reported per PR but not blocking. **Rejected** in favor of the hard 80% gate. Trade-off accepted: occasional PR blocks on hard-to-test code (mitigated by the exclusion philosophy above) in exchange for the discipline a hard gate enforces.

### Coverage: no target at all

"Tests prove behavior; coverage is vanity." **Rejected** — loses the early-warning signal when test investment rots. Mature teams keep at least the metric visible.

### Frameworks: Jest for TypeScript

Older, slower, but more deployed. **Rejected** — Vitest matches the WXT/Vite toolchain (one bundler across dev + test), is Jest-API-compatible (so we lose nothing), and is the modern default for new projects.

### Frameworks: unittest for Python

Stdlib, no dep. **Rejected** — pytest's fixture model, parametrization, and plugin ecosystem (`pytest-asyncio`, `pytest-cov`, `pytest-mock`) is what every Python team reaches for.

### Real Gemini API in tests instead of fixtures

**Rejected** — real-API tests cost money per run, are flaky on rate-limit / transient errors, and slow. The right place to validate Gemini contract changes is a separate, manually-triggered "fixture refresh" job, not the per-PR test run.

## Consequences

### Good

- **Failure modes are tested where they live.** Backend integration is heavy (Firestore + Gemini contract), extension unit is heavy (segment math), e2e is thin and focused (auto-seek happy path).
- **CI catches regressions automatically.** Playwright e2e on every PR means the auto-seek flow can't silently break.
- **Coverage gate enforces discipline.** Hard 80% means new untested code can't slip in unnoticed; the exclusion philosophy keeps it from becoming theater.
- **Same toolchain across dev + test on TS side.** WXT/Vite + Vitest = one bundler, one config language, one set of plugins.
- **Recorded Gemini fixtures = deterministic, free CI.** No API spend per test run; tests don't break when Gemini has a bad day.
- **Enterprise practice.** Daily reps on Playwright, Firebase emulator, coverage-gated CI — the patterns shipping at large product teams.

### Bad

- **Playwright Firefox-extension setup has friction.** Playwright's first-class extension support is stronger on Chromium than Firefox; expect some workarounds (web-ext runner integration, manual `.zip` build step, browser-binary caching). Documented in `extension/README.md` once written.
- **CI wall-clock will be dominated by e2e.** Mitigated by parallelizing with backend tests; e2e budget capped at 1–3 scenarios.
- **Flake risk on real Firefox + real Vite dev server.** Up to 2 retries per test allowed; flake-rate >5% over a week triggers triage.
- **Hard coverage gate will sometimes block legitimate PRs.** When it does, the fix is either (a) write the missing test, or (b) add a justified exclusion. Not (c) drop the threshold.
- **Recorded fixtures rot.** When the Gemini prompt or response shape changes, fixtures must be re-recorded. Mitigated by making fixture refresh a single documented script.

### Neutral

- **Each component owns its own test setup.** `extension/`, `backend/`, `scripts/` each ship their own test config and `README.md` instructions. Round A's flat-monorepo, no-`shared/`-yet decision is consistent with this.
- **Backend e2e is sparse.** A single smoke check per release. The bulk of backend confidence comes from heavy integration with the Firebase Emulator.

## When we'd revisit this

- **Playwright Firefox e2e flake-rate exceeds 5% over a sustained week.** **Action:** quarantine the flaky tests, evaluate moving e2e off CI (back to manual smoke checklist) or simplifying scenarios. New ADR amendment if strategy changes shape.
- **The 80% coverage gate becomes a frequent PR blocker for legitimate reasons** (you find yourself adding exclusions weekly, or skipping tests because hitting 80% on a particular file is genuinely impossible). **Action:** drop to 70% with reporting, or split the threshold per project (e.g., 90% backend, 70% extension). Document in this ADR's amendment.
- **Gemini fixture refresh becomes a bottleneck.** **Action:** move to a smarter recording layer (a Gemini gateway that records-replays automatically) or add a scheduled CI job that re-records on a cadence.
- **CI minutes start hurting.** **Action:** move e2e to a nightly job or to release-branch-only; keep unit + integration on every PR.
- **A second contributor joins.** **Action:** no test-strategy change; extend the per-component README instructions for parallel test runs.
