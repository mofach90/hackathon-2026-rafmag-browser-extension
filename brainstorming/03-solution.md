# 03 — Solution

> Goal of this doc: how `rafmag` answers the problem. The shape of the idea — not the implementation.

## What "rafmag" means

`rafmag` is the name of the **Tunisian radio show** the extension is built for. The show is broadcast live on radio and simultaneously live-streamed (with video) on YouTube. After each broadcast, YouTube keeps the unedited recording on the channel under the "Live" section — and that's the artifact the extension operates on.

The extension takes the show's name to make its purpose unmistakable: it is *the* `rafmag` companion.

## The one-sentence pitch

> A browser extension that automatically skips the loud upcoming-show promo breaks in `rafmag`'s YouTube live archives, so listeners can play the show as background audio without interruption.

## How it works (from the user's point of view)

1. The user opens a `rafmag` past-broadcast video on YouTube as they would normally.
2. The extension recognizes it's a `rafmag` episode.
3. The user presses play, walks away, does whatever they were doing.
4. When an ad break starts, the extension **silently seeks the video past the break** to where the moderator returns.
5. The user never has to come back to the laptop to skip anything. The show plays as if it had been edited.

## How it works (under the hood)

Detection is **Gemini-driven, video-native, and cached**:

1. **Gemini ingests the YouTube URL directly.** Gemini's video-understanding API accepts a `file_data.file_uri` pointing at a public YouTube watch URL — no audio extraction, no separate transcription step required. The model can return timestamps in `HH:MM:SS` format directly.
2. **The prompt is grammar-grounded.** We use the prompt living in [`experiments/01-gemini-quality/test.py`](../experiments/01-gemini-quality/test.py) (`--output show` mode), which was distilled from the empirical analysis of 10 real episodes in [experiment 02](../experiments/02-show-grammar/grammar.md). It returns the **show-content ranges** (the parts to keep), not the break ranges to skip.
3. **Cache the result.** Store the show-content ranges in **Firestore**, keyed by the YouTube video ID, under `episodes/{videoId}.showSegments`. The Gemini call runs **exactly once per episode**, never per viewer or per refresh. See [ADR 0002](../adr/0002-data-storage.md).
4. **Extension consumes the cache through a small read endpoint.** When a `rafmag` episode loads in the user's browser, the extension calls a Cloud Function `GET /episode/{videoId}` that reads the document with the Admin SDK. Credentials never leave the server. The extension uses the returned `showSegments` to auto-seek the YouTube `<video>` element to the first segment and silently skip every gap.

```
   ┌─────────────────────────────────────────────────────────┐
   │  ONE-TIME, PER EPISODE (server side)                    │
   │                                                          │
   │  YouTube URL ──► Gemini (video understanding)           │
   │              prompt: grammar-grounded, --output show    │
   │              ──► { showSegments: [{startSec,endSec}, …]}│
   │                                                          │
   │              ──► Firestore (episodes/{videoId})         │
   └─────────────────────────────────────────────────────────┘
                           │
                           ▼  (GET /episode/{videoId})
   ┌─────────────────────────────────────────────────────────┐
   │  EVERY VIEWER, EVERY PLAYBACK (browser side)            │
   │                                                          │
   │  Extension on YouTube page ──► Cloud Function read       │
   │      ──► auto-seek to first showSegment, then silently  │
   │          skip every gap between segments                │
   └─────────────────────────────────────────────────────────┘
```

> **MVP note**: for the hackathon, the Gemini call is invoked by a one-shot local backfill script (run once before demo day to populate the last ~month of episodes) — *not* by an event-driven pipeline. The eventual trigger flow described below is documented in [ADR 0001](../adr/0001-backend-stack.md) but isn't built yet. See [`04-scope.md`](./04-scope.md).

### Quality risk and fallback

Gemini's published quality on **Tunisian Derja** is its weakest Arabic variant — the Frontiers in AI 2025 cross-dialectal study flagged Tunisian as the hardest case across major LLMs. Crucially, our task is *not* verbatim transcription — it's **boundary detection** ("did the host just announce a break?"). Coarse-grained tasks tolerate noisy transcription far better than fine-grained ones. So:

- **MVP path**: just use Gemini direct. Validate quality on 2–3 real episodes.
- **Fallback**: if Gemini misses too many breaks, swap in Whisper `large-v3` as the transcription step (via a hosted API like Groq) and call Gemini on the resulting transcript instead. The orchestrator stays the same; only the inner step changes.

## When does processing happen? (the trigger model)

- YouTube's **PubSubHubbub feed** (`/feeds/videos.xml?channel_id=...`) fires when a stream goes live — but does **not** reliably fire when a stream ends and becomes a watchable archive.
- The reliable signal is YouTube Data API's `videos.list → liveStreamingDetails.actualEndTime`. Once that field is set, the archive is ready.
- We don't depend on YouTube's auto-captions any more (Gemini handles the audio itself), so the old "wait hours for captions" worry goes away.

```
  PubSubHubbub feed fires (stream scheduled / live)
              │
              ▼
  Backend records the videoId, polls YouTube Data API
  every N minutes for liveStreamingDetails.actualEndTime
              │
              ▼  (actualEndTime is set ⇒ archive ready)
  Call Gemini with the YouTube URL ──► write ranges to Firestore
```

## Why a browser extension (and not something else)

- The user already watches on YouTube in the browser — meeting them where they are means **zero behavior change** for the listener.
- A native app or a re-uploaded edited video would mean: a separate place to go, a separate UI, possible copyright issues with re-hosting the radio's content.
- The extension is invisible in the happy path: it just makes YouTube behave the way the listener already wished it did.

## Value proposition

- **For the listener**: an uninterrupted background-audio experience. The show plays through, the loud promos disappear.
- **For the cost model**: each episode is processed exactly once, no matter how many times or how many listeners watch it.
- **For the hackathon**: a tight, well-bounded MVP — one show, one platform (YouTube), one browser to start (Firefox).
