# 02 — Users

> Goal of this doc: a clear picture of who we're building for. Not "everyone" — specific people in specific moments.

## Primary user

**The user's mother** (the original, archetypal user — "if it works for her, it works").

Profile:
- Loves the `rafmag` radio show.
- Watches/listens to the **post-live archived recording** on YouTube — *not* the live broadcast.
- Plays it on a **desktop or laptop computer**, not phone, not TV.
- Uses the show as **background audio** while doing household tasks (tidying up, etc.) — she is *not* sitting in front of the screen.
- Not a power user. The fix has to "just work" — no settings, no fiddling.

## Secondary users

- Anyone else who consumes `rafmag` archives the same way: as passive background listening from a laptop while doing something else.
- Plausibly: other Tunisian-radio-on-YouTube fans with the same archive-watching habit.

## The painful moment we intercept

> *The listener is in the kitchen / hallway / another room. The show is playing from a YouTube tab. Suddenly the audio shifts — the moderator has gone on break, and a loud promo for upcoming shows starts blaring. The listener has to drop what they're doing, walk back to the computer, click the timeline, guess how far to skip, miss part of the show, and resume.*

The extension should make sure that moment **never happens** — the skip happens automatically, before the listener even notices.

## Non-users (explicitly out of scope)

- People watching the **live** broadcast as it airs (they can't skip ahead anyway).
- Mobile-only viewers (we're building a browser extension; mobile YouTube apps are out of reach).
- Listeners who actively *want* to hear the upcoming-show promos.
