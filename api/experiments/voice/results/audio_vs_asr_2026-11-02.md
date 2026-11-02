# Audio straight to Spark vs the production chain (2026-11-02)

Question (CK): Muse Spark takes audio input (`input_audio`). Is muse-spark-1.2 on the audio better than the shipped chain
(Muse Voice Transcribe → muse-spark-1.3 on the transcript)?

Script: `api/experiments/voice/audio_vs_asr.py`. Raw replies are in `out/audio_vs_asr/` (ignored). Scores are in
`results/audio_vs_asr_r1.json` and `_r2.json`, the generated tables in `results/audio_vs_asr_tables.md`, and every paid
call in `spend.jsonl` (kinds `ava:*` and `judge:ava_*`).

## Setup

- **Clips:** the 40 recordings, `fixtures/voice/audio/wav/*.wav`: 30 script lines plus retakes v01c–v10c, which share
  their lines' labels. All are plain 16 kHz mono PCM, normalised by the app's `pcm_wav`, 3.2–12.8 s long, 275 s in all.
- **Pipelines:**
  - **A:** `muse-spark-1.2`, with the WAV as an `input_audio` part.
  - **B:** `muse-spark-1.3`, with the same WAV and prompt as A.
  - **C:** production. `meta_transcribe` (muse-voice-transcribe-1.0, DIARIZATION, the app's `Score.keywords()` for
    this book, glossary included), then `muse-spark-1.3` on the transcript.
- **Every Spark call** is the product's call: `/v1/chat/completions`, `reasoning_effort: "minimal"`
  (`transcribe_voice.VOICE_EFFORT`), streamed, `max_completion_tokens: 8192`. It uses the system prompt and user
  prompt from `voice_prompt.build_prompt`, with the facts the app would pass for this quartet-plus-choir book: groups
  from `derive_groups`, landmarks `[]`.
- **A/B prompt:** the same prompt, except that the "Transcript of what the conductor said" block is replaced by "What
  the conductor said is the attached audio recording". The quote rule and schema ask for the words "as said" instead
  of a verbatim transcript span, and the mishearing rule is reworded for a recording. Every other rule and all eight
  worked examples are unchanged.
- **Scoring:** `voice_eval.score_line` against script.csv, the same metric as voice_eval.
  - A line counts as right when all 5 fields are right: position, bar_from, bar_to, audience (part or addressee) and
    kind. A non-instruction line counts as right when no mark is produced.
  - `checked_marks` applies as in the app. A and B have no transcript, so their quote check runs against the
    model's own quote.
  - The eval's judge2 scored the stand text separately (shown in the tables, not counted in "lines ok").
- **Runs:** run 1 put all three pipelines on all 40 clips, interleaved in shuffled order, 4 calls at a time. The
  result was close (32 / 32 / 33), so run 2 repeated all three; B came along because it costs $0.17.
- **Errors:** none in either run (0 HTTP errors, 0 retries, every `finish_reason` was `stop`). Spark 1.3 accepted
  audio without complaint.

### The `input_audio` request shape (dev.meta.ai/docs/video-understanding#audio; no separate audio page exists)

Audio understanding is available on Chat Completions and on the Responses API, but not on Messages. The accepted
types are `audio/wav` and `audio/mpeg`, uploaded or sent inline as base64. Meta's example, verbatim:

```json
{"type": "input_audio", "input_audio": {"data": audio_b64, "format": "wav"}}
```

What this script sent to `POST https://api.meta.ai/v1/chat/completions`:

```json
{"model": "muse-spark-1.2",
 "messages": [{"role": "system", "content": "<voice_prompt.SYSTEM>"},
              {"role": "user", "content": [
                  {"type": "text", "text": "<build_prompt user text, transcript block swapped for the recording>"},
                  {"type": "input_audio", "input_audio": {"data": "<base64 of the PCM WAV>", "format": "wav"}}]}],
 "reasoning_effort": "minimal", "max_completion_tokens": 8192,
 "stream": true, "stream_options": {"include_usage": true}}
```

Meta's caveats on that page:
- "Audio understanding in Muse Spark 1.3 is currently not fully supported", and response quality "may be degraded";
  the page's examples use 1.2.
- Set the output budget to at least 4000, because reasoning shares it.
- Stream, or lower the effort, for long clips.

### Price

- **Spark Standard** is $1.25 in, $0.15 cached in and $4.25 out per M tokens, the same for 1.2 and 1.3.
- **Audio** has no price of its own on dev.meta.ai/docs/pricing-rate-limits. It is counted in `prompt_tokens`, and
  usage gives no `audio_tokens` field. A fit of input tokens against clip length is exact at **12.5 tokens per
  second** of audio (2074 + 12.5 × seconds in both runs, both models): $0.056 per hour of audio at the input rate,
  below Voice Transcribe's $0.18 per hour.
- **Voice Transcribe** is $0.18 per hour, metered in whole seconds.
- **Cost per call:**
  - The tables price every token at list, with no cache discount.
  - In practice about 2,000 of the ~2,150 prompt tokens came back as `cached_tokens`. The cached-rate cost per
    clip is about $0.0024 (A), $0.0022 (B) and $0.0022 (C).

## Results per run

"Lines ok" means right on all 5 fields, or rightly no mark. "Unseen 30" leaves out the 8 lines whose own words are
worked examples in the production prompt (v02, v08, v14, v18, v21, v22, v25, v30) and the retakes v02c and v08c.
Latency is the wall time per clip: for C, Voice Transcribe plus Spark. Production streams, so TTFT is the first
content token, plus the ASR time for C.

| run | pipeline | lines ok /40 | 30 lines | 10 retakes | unseen 30 | rightly refused | stand text (judge) /35 | median s | p95 s | median TTFT s | median in / out / reasoning tok | $/clip (list) | $ total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r1 | A 1.2 audio | 32 | 25 | 7 | 22 | 5/5 | 28 | 1.87 | 3.46 | 1.80 | 2154 / 412 / 340 | 0.00470 | 0.188 |
| r1 | B 1.3 audio | 32 | 25 | 7 | 22 | 5/5 | 28 | 3.79 | 5.61 | 3.50 | 2154 / 392 / 311 | 0.00448 | 0.179 |
| r1 | C production | **33** | 26 | 7 | 23 | 5/5 | 30 | 4.41 | 6.69 | 3.98 | 2070 / 297 / 205 | 0.00429 | 0.172 |
| r2 | A 1.2 audio | 31 | 24 | 7 | 21 | 5/5 | 30 | 1.72 | 3.24 | 1.58 | 2154 / 374 / 334 | 0.00457 | 0.183 |
| r2 | B 1.3 audio | **33** | 26 | 7 | 23 | 5/5 | 32 | 3.33 | 5.54 | 3.05 | 2154 / 334 / 282 | 0.00436 | 0.174 |
| r2 | C production | **33** | 26 | 7 | 23 | 5/5 | 31 | 4.29 | 10.83 | 3.88 | 2068 / 288 / 199 | 0.00429 | 0.172 |

Pooled over both runs (80 calls per pipeline):

| pipeline | lines ok /80 | 30 lines /60 | retakes /20 | unseen /60 | rightly refused | stand text /70 | 5 fields and text /70 | median s | p95 s | median TTFT s | p95 TTFT s | $/clip list | $/clip with cache |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A 1.2 audio | 63 | 49 | 14 | 43 | 10/10 | 58 | 44 | **1.77** | **3.42** | **1.63** | **3.34** | 0.0046 | 0.0024 |
| B 1.3 audio | 65 | 51 | 14 | 45 | 10/10 | 60 | 50 | 3.56 | 5.61 | 3.27 | 5.34 | 0.0044 | 0.0022 |
| C production | **66** | **52** | 14 | **46** | 10/10 | **61** | 49 | 4.31 | 10.76 | 3.91 | 10.16 | 0.0043 | 0.0022 |

Notes on the numbers:
- **C's latency:** median 1.34 s of Voice Transcribe plus 2.93 s of Spark 1.3.
- **C's p95:** set by three slow Spark calls in run 2 (v15 10.8 s, v23 11.1 s, v11 15.8 s). Run 1's C p95 was 6.7 s.
- **Spark alone, median:** 1.2 on audio 1.76 s, 1.3 on audio 3.55 s, 1.3 on text 2.93 s.
- **Streaming:** the JSON comes after the reasoning, so the first token arrives only about 0.1 s before the end.
  Streaming buys almost nothing here.

## Failures

**Six lines fail in every pipeline and both runs (the shared floor).** The best any pipeline can score against this
answer key is about 34/40. In 4 of the 6, the recording does not say what the key says:

| line | key | what all three heard and did |
|---|---|---|
| v04c | Alto | The take ends "No, sorry, I mean sopranos". Every run marked Soprano, which is correct under the prompt's last-version-wins rule. **The key is wrong; label v04c Soprano.** |
| v11 | member:Lin | No "Lin" in the take, in either the ASR or the audio models ("C sharp in bar 15 is flat…"). Everyone marked ensemble. The name is clipped or was not said. |
| v16 | Violin I + Violin II | The take starts "and second from 96…"; "Firsts" is clipped. Everyone marked Violin II only. |
| v28 | Cello | The take starts "Bar three, that's four beats…"; "Cello" is clipped. Everyone marked ensemble. |
| v10c | kind dynamic | "the opposite, hold it back" is marked as `text` every time. A judgement call: the key could accept text. |
| v07c | Viola only | The take says "first violin you are late at 71… okay, violas, the entry is on the and of two". The models give two marks (Violin I late plus the Viola entry), or for B r1 none. Arguably two marks is a fair reading. |

**Failures beyond the floor:**

- **A (1.2 audio):**
  - r1 v23: `mark` and the four voice parts for "whole choir… last page" (key: global, ensemble).
  - r1 v26: two single-bar marks, f at 55 and p subito at 56, where the key has one 55–56 range. The content is
    right; only the scoring shape differs.
  - r2 v15: **inverted the exclusion.** "Everyone except the cello" became pizz. for Cello only.
  - r2 v27: **answered with a worked example.** "Fermata on the last chord" came back as "cresc. 112–116, range
    112–116", which is the prompt's v08 example, word for word.
  - r2 v29: Soprano missed, so ensemble.
- **B (1.3 audio):**
  - r1 v09: `{"none": true}`, **a dropped instruction** ("Tenors and basses, bar twenty…").
  - r1 v07c: `{"none": true}`, a dropped instruction.
  - r1 v23: the four voice parts, as A.
  - r2 v17: `{"none": true}`, a dropped instruction ("Bar 203, basses, low E").

  That is three false negatives in 80 calls, against none for A or C. It fits Meta's 1.3 audio caveat.
- **C (production):**
  - r1 v07c: the Viola mark came back `global` with no bars.
  - r1 v23: the four voice parts, as A.
  - r2 v27: **the ASR misheard** "Right, Inès Fermenta on the last chord", so the mark went to member:Inès. The audio
    models got v27 right in 3 of 4 calls.

On v23, every pipeline in run 1 listed the four voice parts and every pipeline in run 2 marked ensemble. The prompt's
rule that "a group the speaker names is every part listed in it" makes both readings defensible. The key could accept
both.

## Spend

| item | $ |
|---|---|
| A propose (80 calls + 1 probe) | 0.3744 |
| B propose (80) | 0.3533 |
| C Voice Transcribe (80 × ~7 s) | 0.0276 |
| C propose (80) | 0.3157 |
| judge2 on the stand text (6 × ~35) | 0.5274 |
| **total this experiment** | **$1.60** at list (less with cache) |

The voice ledger (`spend.jsonl`) now totals $4.62, against its $20 budget.

## Recommendation

Keep production (C). Over two runs, 1.2-on-audio (A) does not beat it on accuracy: 63/80 against 66/80, and 43/60
against 46/60 on the unseen lines. That gap is within run-to-run noise (A moved 32 → 31, B 32 → 33). The six-line
shared floor is mostly the recordings and the key, not the models.

A's real advantage is speed:
- 1.8 s median end-to-end against 4.3 s.
- 3.4 s p95 against 6.7–10.8 s.
- No second service to wait on.
- At equal cost: about $0.0024 per clip with cache. Audio is 12.5 input tokens per second, cheaper than Voice
  Transcribe.

But A's misses in run 2 are the dangerous kind. It inverted "everyone except the cello" and answered an unrelated
line with a worked example's "cresc. 112–116". The audio path also loses two of production's safeguards:
- the verbatim-quote guard: there is no transcript to check a quote against, so the quote is the model's own claim;
- the transcript the admin sees in the tray.

B (1.3 on audio) is slower than A and drops instructions outright (3 of 70), as Meta warns.

If speed becomes the priority, the next step is not a switch. It is a larger A-vs-C test: more voices, more runs, a
fixed answer key (v04c to Soprano, and either re-record v11, v16 and v28 or relabel them), plus a hold-out version of
the prompt so the worked examples cannot be copied.
