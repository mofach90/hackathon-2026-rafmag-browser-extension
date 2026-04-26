# Glossary

> Every domain-specific term we use in conversation gets defined here. This is the "common language" we agree on.

| Term | Definition | Added in |
|------|------------|----------|
| **rafmag** | A Tunisian radio show that is also live-streamed as video on YouTube. The browser extension is named after — and built around — this show. | Round 1 |
| **Live archive** | The unedited recording of a past live broadcast that YouTube keeps available on the channel under the "Live" section after the stream ends. This is what our user actually watches — not the live stream. | Round 1 |
| **Moderator break** | A stretch of the recording where the radio host steps away from the mic. Used by the radio to fill airtime. | Round 1 |
| **Ad break** | The content the radio plays during a moderator break — typically loud promos for upcoming shows. This is what the extension must auto-skip. | Round 1 |
| **Background listening** | The user's actual mode of consumption: the show is playing on a laptop in another room while the user does other tasks. They are *not* watching the screen. | Round 1 |
| **Transcript / transcription** | The text version of what's spoken in the video. Source of truth for break detection. Likely starts from YouTube's auto-generated captions. | Round 2 |
| **Break marker phrase** | A Tunisian-dialect phrase the moderator says to enter or leave a break (e.g. *"now we'll go for a break"*, *"we're back"*). The LLM's job is to find these in the transcript. | Round 2 |
| **Break range** | A `{start, end}` timestamp pair describing one ad/promo segment to skip in a given episode. | Round 2 |
| **Episode cache** | The backend database that stores break ranges keyed by YouTube video ID. Lets the heavy LLM work happen exactly once per episode. | Round 2 |
| **Auto-skip** | The extension's runtime behavior: when the YouTube player's `currentTime` enters a known break range, programmatically seek to the range's `end`. | Round 2 |
| **ASR** | Automatic Speech Recognition — converting audio to text. We do this server-side ourselves rather than relying on YouTube's auto-captions. | Round 2 |
| **Whisper** | OpenAI's open-source multilingual ASR model. The `large-v3` variant is our leading candidate for transcribing Tunisian-dialect audio. | Round 2 |
| **WER** | Word Error Rate — standard metric for ASR quality. Lower is better. Maghrebi/Tunisian Arabic typically lands at 35–55% WER even on tuned modern systems. | Round 2 |
| **Derja / dialectal Arabic** | Tunisian colloquial Arabic. Differs significantly from Modern Standard Arabic; heavy code-switching with French. Most generic Arabic ASR is tuned for MSA and degrades on derja. | Round 2 |
| **PubSubHubbub feed** | YouTube channel push-notification feed at `/feeds/videos.xml?channel_id=...`. Fires when a video/stream first becomes public. **Does not** reliably fire when a live stream ends → can't be used alone as the "archive ready" signal. | Round 2 |
| **`actualEndTime`** | Field on YouTube Data API's `videos.list` (`liveStreamingDetails.actualEndTime`). Set once a live stream has ended and the archive is ready. The reliable signal we poll for to know when to start processing. | Round 2 |
| **Gemini video understanding** | The Gemini API capability that accepts a YouTube URL via `file_data.file_uri` and reasons over the video directly (audio + frames). Returns timestamps in `HH:MM:SS` natively. Replaces our originally planned Whisper + LLM split for the MVP. | Round 2 |
| **Cloud Functions Gen 2** | Firebase / GCP's serverless function runtime, which is itself a Cloud Run service under the hood. Gives us source-deploy + auto build + HTTP/event triggers without writing a Dockerfile. Our chosen orchestrator runtime. | Round 2 |
| **ADR** | Architecture Decision Record — a short markdown doc that freezes *why* we picked a given approach. Lives in [`adr/`](../adr/), separate from brainstorming. Brainstorming explores; ADRs commit. | Round 2 |
| **Diwan FM** | The Tunisian radio station that produces and broadcasts `rafmag`. Its YouTube channel hosts the live archives the extension operates on. | Round 2 (experiment 01) |
| **Zapping** | A *different* show on Diwan FM. Mentioned because the radio's promo blocks reference upcoming shows like Zapping — useful for distinguishing rafmag content from inter-show promos. | Round 2 (experiment 01) |
| **Columnist / chroniqueur** | A guest co-host of `rafmag` who delivers their own recap segment of the previous show. Their voice differs from the main moderator's, which can mislead an LLM into thinking a break has started. NOT a break. | Round 2 (experiment 01) |
| **Sub-break splitting** | An LLM failure mode where one continuous ad block is returned as several short blocks with phantom "host returns" between them. | Round 2 (experiment 01) |
| **Late-end truncation** | An LLM failure mode where the model stops flagging promos before the real break ends, leaving the tail of the break unskipped. | Round 2 (experiment 01) |
| **Box News / بوكس نيوز** | A news-discussion sub-segment of `rafmag` (delivered by Jihan Sallini), played at the start of the second hour. It features news topics but transitions naturally into panel debate — so it counts as **show content**, not a break. | Round 2 (experiment 02) |
| **Mega break** | The long top-of-the-hour break (~15–20 min) that interrupts `rafmag` for the station's **8AM news bulletin** (موجز الأخبار) and **sports flash** (فلاش سبور). Even though it's professionally read content, it is part of the noisy break the listener wants to skip. | Round 2 (experiment 02) |
| **Second hour** | "ساعتنا الثانية" — the part of the show after the mega break, opened by the moderator with "مرحبا مرحبا رجعنا لكم في ساعتنا الثانيه". The transition is one of the most reliable break-return signals. | Round 2 (experiment 02) |
| **Quiz segment / final part** | The last sub-segment of every episode, opened with "مرحبا بكم في الجزء الاخير من حلقتنا لليوم" — a strong return-from-break signal. | Round 2 (experiment 02) |
| **Live sponsor read** | In-show advertising (e.g. Ooredoo, Volkswagen prize giveaways) read by the moderator/panel WHILE the show is live. Sounds promotional, but is show content — not a break. | Round 2 (experiment 02) |
| **Station bumper** | A short pre-recorded promo identifying the show ("تسمعوا الراف ماك من اثنين للجمعه...") played at break boundaries. Boundary-ambiguous — the detector has to decide whether to cut at the start or end of the bumper. | Round 2 (experiment 02) |
| **Manifest V3** | The current Chrome / cross-browser extension manifest format. Event-driven service worker instead of a persistent background page. Our chosen target — Firefox supports it, and matching it makes a future cross-browser port cheaper. | Round 4 |
| **AMO** | `addons.mozilla.org` — Mozilla's public extension store. Our chosen distribution channel. Every release goes through AMO review (permissions, privacy policy, source review for any minified code). | Round 4 |
| **Install ID** | A random UUID generated on the extension's first run and stored in `storage`. Sent with every Cloud Function request so we can count distinct installs. Not tied to any user identifier. | Round 4 |
