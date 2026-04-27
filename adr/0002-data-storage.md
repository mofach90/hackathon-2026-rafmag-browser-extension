# ADR 0002 — Data storage

- **Status**: Proposed
- **Date**: 2026-04-26
- **Deciders**: Mohamed (project owner)

## Context

The system needs to store, per processed `rafmag` episode, the cached list of **show-content time ranges** (the parts the listener wants to keep — everything between the breaks) so that:

- the **backend** writes once after Gemini analysis completes, and
- the **browser extension** reads many times (every viewer, every playback) by YouTube video ID.

The data is tiny, immutable per episode (we don't update an episode's ranges except to mark a re-process), and accessed by a single primary key (the video ID).

> **Note on the show-vs-break shape**: this ADR originally described break ranges. It was flipped to **show-content ranges** in Round 3 (see [`brainstorming/04-scope.md`](../brainstorming/04-scope.md)). Reasons: (a) the extension's auto-seek logic is simpler with keep-ranges (find the segment containing `currentTime`; if past its end, jump to the next segment's start), and (b) the validated Gemini prompt's `--output show` mode already returns this shape natively.

Constraints:

- **Read pattern is `videoId → showSegments`** — single-document lookups, no joins, no analytics.
- **Write pattern is rare** — once per new episode (daily-ish), or all at once during hackathon backfill.
- **Reads go through a small backend endpoint** rather than directly from the browser, so credentials stay server-side and we have one place to add rate limits / security checks.
- **Cost ceiling**: ~$0 at hackathon scale.
- **Stack alignment**: ADR 0001 commits to Cloud Functions Gen 2 + Gemini in Google Cloud. Storage should not introduce a second ecosystem.

## Decision

Use **Firestore** (Native mode) as the only persistence layer, with a single collection:

### Schema

Collection: `episodes`. Document ID: the YouTube video ID.

```
episodes/{videoId}
  videoId:        string                       // redundant with doc id; convenient for queries
  channelId:      string                       // Diwan FM channel ID
  title:          string                       // for debugging / admin views
  publishedAt:    timestamp
  durationSec:    number
  status:         "pending"
                | "waiting_for_archive"
                | "processing"
                | "ready"
                | "failed"
  showSegments:   [{ startSec: number,
                     endSec:   number,
                     evidence: string }]       // evidence kept for debugging; extension ignores it
  model:          string                       // e.g. "gemini-3.1-pro-preview"
  processedAt:    timestamp | null
  error:          string | null
  schemaVersion:  number                       // start at 1
```

`startSec` / `endSec` are stored as **seconds (number)** rather than `HH:MM:SS` strings — the YouTube `<video>` element's `currentTime` is also in seconds, so this is the format the extension needs anyway.

### Access pattern

- **Backend writes (one-shot backfill script for MVP, Cloud Functions Gen 2 later)**: writes/updates documents using the **Firebase Admin SDK** (privileged).
- **Browser extension reads**: hit a small `GET /episode/{videoId}` Cloud Function. The function does the Firestore lookup with the Admin SDK and returns `{ showSegments: [...] }` or `404`. The extension never holds Firestore credentials.

### Security rules (intent)

```
match /episodes/{videoId} {
  allow read:  if false;        // direct browser reads disabled — extension goes through the Cloud Function
  allow write: if false;        // writes only via Admin SDK
}
```

## Alternatives considered

### Cloud SQL (Postgres)

Postgres is more "real" — strong typing, real joins, mature tooling. **Rejected** because we have a single key-value access pattern and zero relational needs. Cloud SQL also has a non-zero idle cost (instance always-on), which breaks the "$0 at hackathon scale" goal.

### SQLite + Litestream / a file in the function's filesystem

Cloud Functions instances are ephemeral and concurrent — there is no shared writable filesystem we can count on. **Rejected**: doesn't fit serverless.

### A simple KV store (Redis, Cloudflare KV, etc.)

Could work, but introduces a second ecosystem outside GCP and gives us nothing Firestore doesn't. **Rejected** for ecosystem alignment.

### Realtime Database (Firebase RTDB)

Firebase's older NoSQL store. Firestore is its strict successor: better querying, better scaling, better security rules. **Rejected**: no reason to pick the predecessor.

## Consequences

### Good

- **Single seam between extension and storage**: the read endpoint is the only thing the extension talks to. Adds rate limiting, abuse protection, CORS, and analytics in one place — without touching the extension.
- **Free at our scale**: Firestore free tier (50K reads / 20K writes per day) is far above what hackathon traffic will produce. The Cloud Function read endpoint is also free at this volume.
- **Simple schema = simple migrations**: `schemaVersion` future-proofs the doc shape; we'll likely never need it.
- **Native integration with Cloud Functions Gen 2** via the Firebase Admin SDK.
- **Document model fits**: one episode = one document = one read.

### Bad

- **Two hops instead of one** for every extension read (browser → function → Firestore). Adds ~50–150ms over a direct Firestore SDK read. Acceptable for our use case (one read per video load, not per second).
- **One more thing to deploy and monitor**: the read function is a separate Cloud Functions deployment. Trade-off accepted in exchange for the credential isolation and central control point.
- **Vendor lock-in via Firestore-specific APIs** in the backend (Admin SDK). If we ever leave Firestore, the read function gets rewritten — but the extension doesn't, which is the more expensive thing to change.
- **No ad-hoc analytical queries**. If we later want "give me all episodes with > 5 ad breaks," that's awkward in Firestore. (Not on the roadmap; flagging only.)
- **NoSQL eventual consistency** is technically a thing, though for a single-document read after a single-document write, it's not observable in practice.

### Neutral

- The entire data model lives in one collection. If complexity grows (e.g. user feedback, episode metadata from another source), we'll add collections; the existing one doesn't change.

## When we'd revisit this

- **Multi-write contention** on a single episode (e.g. multiple processors racing). Today impossible — only one writer. **Action**: add transactional writes; ADR likely still stands.
- **Quota pressure**: if we ever cross the Firestore free tier and cost becomes meaningful. **Action**: shave reads with extension-side caching (e.g. cache for the lifetime of the YouTube tab) before changing storage.
- **Querying needs change** (analytics, search). **Action**: introduce BigQuery as a downstream sink; keep Firestore as the operational store. New ADR.
- **Strategic**: if the project leaves GCP entirely. **Action**: this ADR gets superseded along with ADR 0001.
