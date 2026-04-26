# 05 — Constraints

> Goal of this doc: the limits we have to design within — technical, business, ethical, time. Locked in Round 4.

## Browser / platform

- **Firefox-only for the MVP.** The primary user runs Firefox; no resources are spent on Chrome/Edge until that ships.
- **Manifest V3.** Future-proof, matches Chromium if we ever expand, and Firefox's V3 support is now stable enough for a content-script + service-worker model. The slight extra friction (event-driven background vs persistent page) is accepted.
- **Cross-browser is a stretch goal**, not a constraint. Listed in [`04-scope.md`](./04-scope.md) under stretch.

## Permissions & privacy

The extension requests **only** what it needs:

| Permission | Why | Risk if granted |
|------------|-----|-----------------|
| Host: `https://*.youtube.com/*` | Read the page URL / `<video>` element to detect rafmag and seek past breaks. | Standard for any YouTube-aware extension. |
| `storage` | Local cache of fetched `showSegments` so a refresh / replay doesn't re-hit the Cloud Function. | Local-only; nothing leaves the browser. |
| `notifications` | Native OS notification when an episode isn't yet in the DB ("rafmag: this episode hasn't been processed yet"). | Visible to the user; no data sent. |

Not requested: `tabs` (we don't need cross-tab awareness), `webRequest` (we don't intercept network), `cookies`, history, bookmarks.

**Data sent to our backend:**

- YouTube **video ID** (necessary — that's the cache key).
- An **anonymous install ID** (random UUID generated on first run, stored in `storage`). Lets us count distinct installs without user identifiers. Disclosed in the AMO privacy policy.
- Request timestamp (added by the Cloud Function automatically).

No YouTube account info, no IP retention beyond Cloud Run defaults, no other telemetry.

## Performance

- **Seek-on-load latency target: < 2 seconds** from page load to the first `currentTime` seek. A second or two of intro/promo audio before the seek is acceptable — we don't pause the player to wait for the API; we just fetch and seek when ready.
- **Mid-playback skip latency: < 500ms.** When `currentTime` enters a gap between two `showSegments`, the seek should feel instant. Implementation-wise this means a single `timeupdate` listener with the segment list pre-loaded — no network call on the hot path.
- **No frame-by-frame work in the content script.** The extension is one fetch + one event listener; everything heavy lives server-side.

## Cost

**Parked for the MVP.** We use `gemini-3.1-pro-preview` per ADR 0001 even though full-episode runs hit ~873k input tokens (~$1–2/episode at public pricing). After some stable production usage we'll revisit and refactor (cheaper model, chunked clips, or Whisper-+-text-Gemini) if cost becomes a real concern.

This deferral is deliberate: the chunked-clip experiment on `yaeWOrjiDRM` will likely change the cost profile anyway, so optimizing now would be premature.

## Time / hackathon

**No hard deadline.** The hackathon date isn't locked, and even when it is, we treat it as a milestone rather than a guillotine. Better to ship a tight, working slice than rush a half-built pipeline. ADRs and experiments stay first-class — we don't cut corners on the discovery work to chase a demo date.

## Business / distribution

- **Public on AMO (addons.mozilla.org).** Listed publicly with auto-updates. This is the path that makes the extension easy for non-technical users to install — the primary user is the project author's mother, and a one-click "Add to Firefox" beats sideloading an `.xpi`.
- **Implications of going public:**
  - AMO review is required (privacy policy, source review for any minified code, permission justifications).
  - The privacy policy must disclose the install ID and the video-ID telemetry.
  - Updates are pushed by uploading new versions to AMO — review applies to each update too.
- **No monetization.** Free, no ads, no upsells. The extension exists to solve one person's listening problem; if it helps others too, good.

## What we are NOT constraining (yet)

- **Languages other than Tunisian Derja.** The whole pipeline is rafmag-specific — show grammar, prompt phrases, channel match. Generalizing is a different project.
- **Other Diwan FM shows.** Same reason: the empirical grammar is rafmag's, not the station's.
- **Mobile.** Firefox for Android supports a subset of extensions, but the primary user listens at home on a laptop.
