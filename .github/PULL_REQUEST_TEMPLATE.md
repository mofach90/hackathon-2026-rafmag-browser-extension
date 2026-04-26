## Why

<!-- The motivation. What problem does this solve? Link the ADR / issue / open question if applicable. -->

## What changed

<!-- 1-3 bullets in plain English. The diff shows the exact code; this is the human summary. -->

-

## Type of change

<!-- Check all that apply; delete the rest. Mirrors Conventional Commit types. -->

- [ ] feat — user-visible new feature
- [ ] fix — user-visible bug fix
- [ ] docs — documentation only
- [ ] refactor — code change with no behavior change
- [ ] test — tests only
- [ ] chore — tooling / deps / config
- [ ] perf — performance improvement
- [ ] ci — CI/CD config
- [ ] build — build system / external deps
- [ ] BREAKING CHANGE — see migration notes below

## How to verify

<!--
Concrete steps a reviewer (or future you) can follow.
Different per affected component:

  - extension/: how to load it in Firefox, what to click, what to observe
  - backend/:   how to invoke the function locally, expected response
  - scripts/:   how to run with a test videoId, expected Firestore state
-->

## Screenshots / recordings

<!-- Required for extension UI changes. Delete this section if not applicable. -->

## Checklist

- [ ] Branch name follows Git Flow (`feature/...`, `bugfix/...`, `docs/...`, `chore/...`, `release/v*`, `hotfix/v*`)
- [ ] Commit messages follow Conventional Commits (`<type>(<scope>): <subject>`)
- [ ] Targeting `develop` (only `release/*` and `hotfix/*` target `main`)
- [ ] Tests added or updated where relevant
- [ ] Local lint + tests pass
- [ ] CONTRIBUTING.md / READMEs updated if conventions changed

## Migration notes

<!-- Only fill in for BREAKING CHANGE. What downstream code / config / data needs updating, in order. Otherwise delete this section. -->

## Linked

<!-- Closes #123 / Implements ADR-0004 / Refs brainstorming/04-scope.md -->
