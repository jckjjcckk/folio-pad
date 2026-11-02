// DEBUG: remove before release. The debug take recorder streams the microphone's blocks into a WAV; these prove its
// bytes are the bytes the voice-note path makes for the same samples: encodeWav(resample(all, rate, 16000), 16000).
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { encodeWav, resample, VOICE_RATE } from '../src/lib/recorder.ts'
import { StreamingWav, readWavHeader, takeName } from '../src/lib/debugTake.ts'

/** A deterministic take: voice-like tones, noise and a few clipped spikes, in float32 like the worklet's blocks. */
function take(frames: number, seed: number): Float32Array {
  let s = seed >>> 0
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32) * 2 - 1
  const x = new Float32Array(frames)
  for (let i = 0; i < frames; i++) x[i] = 0.4 * Math.sin(i * 0.031) + 0.2 * Math.sin(i * 0.47) + 0.15 * rnd() + (i % 9973 === 0 ? 1.7 : 0)
  return x
}

/** Feed it in blocks the way the worklet posts them (2048 frames), or in ragged sizes. */
function stream(x: Float32Array, rate: number, sizes: () => number): Promise<Uint8Array> {
  const w = new StreamingWav(rate)
  for (let at = 0; at < x.length;) { const n = Math.min(sizes(), x.length - at); w.push(x.subarray(at, at + n)); at += n }
  return w.finish().wav.arrayBuffer().then(b => new Uint8Array(b))
}

const production = async (x: Float32Array, rate: number) => new Uint8Array(await encodeWav(resample(x, rate, VOICE_RATE), VOICE_RATE).arrayBuffer())

for (const rate of [48000, 44100, 24000, 16000]) {
  test(`at ${rate} Hz the streamed take is byte for byte the voice-note WAV`, async () => {
    // 75 s: past the 10 s output chunks and the input buffer's compaction point many times over.
    const x = take(rate * 75 + 1234, rate)
    const want = await production(x, rate)
    assert.deepEqual(await stream(x, rate, () => 2048), want)
    let k = 7
    assert.deepEqual(await stream(x, rate, () => (k = (k * 31 + 17) % 5000) + 1), want)
  })
}

test('a take shorter than the filter, and an empty one, still match', async () => {
  for (const frames of [0, 1, 5, 40, 100]) {
    const x = take(frames, frames + 3)
    assert.deepEqual(await stream(x, 48000, () => 2048), await production(x, 48000))
  }
})

test('the header reads back as 16 kHz mono 16-bit PCM in a plain 44-byte RIFF/WAVE', async () => {
  const w = new StreamingWav(48000)
  w.push(take(48000 * 3, 1))
  const f = w.finish()
  const h = await readWavHeader(f.wav)
  assert.equal(h.format, 1); assert.equal(h.channels, 1); assert.equal(h.sampleRate, 16000); assert.equal(h.bits, 16)
  assert.equal(h.blockAlign, 2); assert.equal(h.byteRate, 32000)
  assert.equal(h.dataBytes, 16000 * 3 * 2); assert.equal(h.fileBytes, 44 + 16000 * 3 * 2)
  assert.equal(f.samples, 48000); assert.equal(f.seconds, 3)
})

test('the file name is take-YYYYMMDD-HHMMSS.wav', () => {
  assert.equal(takeName(new Date(2026, 10, 1, 9, 5, 7)), 'take-20261101-090507.wav')
})
