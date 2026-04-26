# ADR 0001 — Backend stack

- **Status**: Proposed
- **Date**: 2026-04-26
- **Deciders**: Mohamed (project owner)

## Context

The project needs a server-side pipeline that runs **once per `rafmag` episode** and produces a list of ad-break `{start, end}` ranges to be cached in a database for the browser extension to consume.

The pipeline's responsibilities, in order:

1. Detect that a new `rafmag` live stream has gone up (via YouTube's PubSubHubbub feed for the channel).
2. Wait until the live stream's archive is ready (poll YouTube Data API for `liveStreamingDetails.actualEndTime`).
3. Send the public YouTube URL to a model that can identify ad-break ranges in the video.
4. Persist the result.

Constraints driving the decision:

- **Hackathon timeline.** Time-to-first-working-pipeline matters more than long-term polish.
- **Junior dev (one person)** building, deploying, and operating it. Lower operational complexity > theoretical flexibility.
- **Cadence**: ~1 execution per new episode (daily at most). Each run lasts a few minutes. Idle the rest of the time.
- **Single-ecosystem benefit**: the chosen LLM is **Gemini**, which lives in Google Cloud. Staying in the same ecosystem cuts auth, billing, and console overhead.
- **Cost ceiling**: should be ~$0 at hackathon scale.

## MVP vs eventual architecture

This ADR describes the **eventual** pipeline. For the **hackathon MVP** (per [`brainstorming/04-scope.md`](../brainstorming/04-scope.md)) only a subset is built:

| Component | MVP | Eventual |
|-----------|-----|----------|
| Gemini call (the Gemini-direct-YouTube part of the pipeline) | ✅ via one-shot Python script (`scripts/backfill.py`) | ✅ same call, triggered by the pipeline |
| Firestore | ✅ | ✅ |
| `GET /episode/{videoId}` Cloud Function (extension's read endpoint) | ✅ | ✅ |
| PubSubHubbub subscription | ❌ deferred | ✅ |
| `actualEndTime` polling via Cloud Scheduler | ❌ deferred | ✅ |
| Auto-process Cloud Function | ❌ deferred | ✅ |

The MVP pre-populates the DB by running the backfill script once before demo day. The "stack" decision below applies to both — the eventual pipeline reuses the MVP's Gemini call and Firestore unchanged; it only adds the trigger plumbing on top.

## Decision

Build the backend on **Google Cloud, Firebase-flavored**, with this stack:

- **Compute**: **Cloud Functions Gen 2** (Node.js or Python — TBD by language preference, not by capability). Triggered by HTTP (Cloud Scheduler hits it for the `actualEndTime` polling cycle, and a webhook endpoint receives PubSubHubbub notifications).
- **Model**: **Gemini API** with the **video-understanding** capability. We pass the public YouTube URL via `file_data.file_uri` and prompt Gemini directly for `{start, end, type}` ranges in JSON. This collapses what would otherwise be two steps (transcribe with Whisper, then analyze with an LLM) into one model call.
  - Model variant: start with **Gemini 2.5 Flash** for cost/latency; promote to **2.5 Pro** if Tunisian-dialect quality is insufficient on real episodes.
- **Scheduler**: **Cloud Scheduler** to run the `actualEndTime` poller every N minutes for any episode currently in the "waiting for archive" state.
- **YouTube channel feed**: **PubSubHubbub** subscription pointing at a Cloud Functions HTTP endpoint to learn about new streams.
- **Secrets**: **Secret Manager** for the Gemini API key and the YouTube Data API key.
- **Observability**: default **Cloud Logging** + **Cloud Monitoring** (no external APM at hackathon scale).

## Alternatives considered

### Cloud Run (instead of Cloud Functions Gen 2)

Cloud Run is the more "general" runtime, and Cloud Functions Gen 2 is in fact a Cloud Run service under the hood. The differences that matter for us:

- Functions Gen 2 ships with a **source-to-container build pipeline** out of the box; Cloud Run requires writing a Dockerfile.
- Functions Gen 2 has **first-class trigger wiring** for Cloud Scheduler, Pub/Sub, Firestore, HTTPS; Cloud Run requires more manual Eventarc / Pub/Sub plumbing.
- Pricing and runtime semantics are otherwise identical.

For a one-person hackathon project with no exotic system dependencies, Cloud Functions Gen 2 is the strictly simpler choice. **Rejected** because it gives us nothing Functions Gen 2 doesn't, at the cost of more setup.

### Self-hosted Whisper on a GPU VM

Originally considered to transcribe audio ourselves. **Rejected** because Gemini's video-understanding API ingests YouTube URLs directly and returns timestamps — there is no need for a separate transcription step. Self-hosting a GPU model would also mean managing GPU quotas, cold starts, and a much higher always-on cost.

### Whisper via a hosted API (e.g. Groq) + separate LLM call

This was the previous leading candidate before the Gemini direct-YouTube path was confirmed. **Rejected for MVP**, **kept as a fallback**: if a real episode shows Gemini misjudging Tunisian-dialect break markers, swap the inner step for *Whisper API → Gemini on transcript*. The orchestrator (Cloud Functions Gen 2) and the storage (Firestore) stay unchanged.

### A different cloud (AWS, Cloudflare Workers, Vercel)

Cloudflare Workers and Vercel are excellent serverless platforms, but Gemini, Firestore, and YouTube Data API are all Google products — staying in GCP means one auth model, one billing line, one console. **Rejected**: ecosystem alignment is the deciding factor.

## Consequences

### Good

- **One ecosystem, one billing line, one console.** Critical for solo operations.
- **No Dockerfile, no GPU**: Cloud Functions Gen 2 deploys from source; no container expertise needed.
- **Gemini collapses two steps into one**: no separate ASR service to operate, monitor, or pay for.
- **Stays effectively free** at hackathon scale (Cloud Functions free tier covers our request volume; Gemini free tier covers our daily input).
- **Lock-in is mild**: the orchestrator is a few hundred lines of code; if we ever leave GCP, the migration is a weekend.

### Bad

- **Tunisian Derja is Gemini's weakest Arabic variant.** If quality is poor on real episodes, we'll need the Whisper-fallback escape hatch. This adds risk to the MVP — we don't know it works until we test it on a real recording.
- **YouTube URL ingestion is public-only**: if the radio ever sets a video to unlisted/private, Gemini cannot ingest it. We'd be forced into the audio-download path that day.
- **Cloud Functions Gen 2 cold starts** (~hundreds of ms) — irrelevant for our daily-cadence workload but worth knowing.

### Neutral

- We'll be writing a small amount of Cloud-Functions-specific glue (trigger config, secret access). It's portable enough that a future move to plain Cloud Run is straightforward.

## When we'd revisit this

- **Quality**: if Gemini's break-detection accuracy is below a usable threshold on 2–3 real episodes. **Action**: keep the orchestrator, swap the inner step to Whisper API → Gemini on transcript.
- **Audience growth**: if the user base ever exceeds the Firestore / Cloud Functions free tier in a way that makes cost meaningful. **Action**: re-evaluate cost; this ADR likely still stands, just with cost-controls added.
- **Job duration**: if any single processing run pushes past the **60-minute** Cloud Functions HTTP timeout. **Action**: split into Cloud Run Jobs, or break the work into smaller scheduled steps. Today this is nowhere near possible.
- **Strategic**: if the project ever expands beyond a single radio channel, the polling architecture may need to change. New ADR.
