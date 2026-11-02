// DEBUG: remove before release.
/** The debug take recorder's encoder: the microphone's blocks, as `startRecording` captures them, streamed into the
 *  very bytes `recorder.ts` would produce for the same take (`encodeWav(resample(all, rate, VOICE_RATE), VOICE_RATE)`):
 *  16 kHz, mono, 16-bit PCM, the plain 44-byte RIFF/WAVE header. Streaming keeps a long rehearsal take small in memory
 *  (16-bit output at 16 kHz, ~115 MB an hour, instead of every 48 kHz float sample twice over). The windowed-sinc
 *  arithmetic below is a copy of `resample` in recorder.ts, done in the same order on the same float32 inputs, so
 *  every output sample is identical; tests/debugTake.test.ts proves the bytes equal on random takes. */
import { VOICE_RATE } from './recorder.ts'

const PHASES = 256
/** Output samples per stored chunk (10 s at 16 kHz). */
const CHUNK = VOICE_RATE * 10

export interface TakeFile { wav: Blob; seconds: number; samples: number; captureRate: number }

export class StreamingWav {
  private readonly from: number
  private readonly to = VOICE_RATE
  private readonly r: number
  private readonly half: number
  private readonly taps: number
  private readonly table: Float32Array | null
  /** Input samples not yet consumed; `buf[0]` is absolute input index `base`, `len` of them are filled. */
  private buf = new Float32Array(1 << 16)
  private base = 0
  private len = 0
  /** Input samples received so far. */
  private received = 0
  /** Next output index. */
  private i = 0
  private chunks: ArrayBuffer[] = []
  private cur = new DataView(new ArrayBuffer(CHUNK * 2))
  private curN = 0

  constructor(from: number) {
    this.from = from
    this.r = from / this.to
    const fc = Math.min(1, this.to / from) * 0.94
    this.half = Math.ceil(8 / fc)
    this.taps = 2 * this.half
    if (from === this.to) { this.table = null; return }
    const { half, taps } = this
    const table = new Float32Array((PHASES + 1) * taps)
    for (let p = 0; p <= PHASES; p++) {
      for (let j = 0; j < taps; j++) {
        const d = p / PHASES + half - 1 - j
        const a = Math.PI * fc * d
        table[p * taps + j] = Math.abs(d) >= half ? 0 : (d === 0 ? 1 : Math.sin(a) / a) * (0.5 + 0.5 * Math.cos((Math.PI * d) / half))
      }
    }
    this.table = table
  }

  /** Output samples written so far. */
  get samples(): number { return this.chunks.length * CHUNK + this.curN }

  push(block: Float32Array): void {
    if (this.base + this.len !== this.received) throw new Error('debugTake: buffer out of step')
    this.append(block)
    this.received += block.length
    this.drain(false)
  }

  /** The whole take as one WAV. The recorder is spent afterwards. */
  finish(): TakeFile {
    this.drain(true)
    const n = this.samples
    if (this.curN) this.chunks.push(this.cur.buffer.slice(0, this.curN * 2) as ArrayBuffer)
    this.curN = 0
    const head = new DataView(new ArrayBuffer(44))
    const str = (at: number, s: string) => { for (let k = 0; k < s.length; k++) head.setUint8(at + k, s.charCodeAt(k)) }
    // The same header fields, in the same order, as encodeWav in recorder.ts.
    str(0, 'RIFF'); head.setUint32(4, 36 + n * 2, true); str(8, 'WAVE')
    str(12, 'fmt '); head.setUint32(16, 16, true); head.setUint16(20, 1, true); head.setUint16(22, 1, true)
    head.setUint32(24, this.to, true); head.setUint32(28, this.to * 2, true); head.setUint16(32, 2, true); head.setUint16(34, 16, true)
    str(36, 'data'); head.setUint32(40, n * 2, true)
    const wav = new Blob([head.buffer as ArrayBuffer, ...this.chunks], { type: 'audio/wav' })
    this.chunks = []
    return { wav, seconds: this.received / this.from, samples: n, captureRate: this.from }
  }

  private append(block: Float32Array) {
    if (this.len + block.length > this.buf.length) {
      const next = new Float32Array(Math.max(this.buf.length * 2, this.len + block.length))
      next.set(this.buf.subarray(0, this.len))
      this.buf = next
    }
    this.buf.set(block, this.len)
    this.len += block.length
  }

  /** encodeWav's conversion of one float32 output sample. */
  private emit(v: number) {
    const s = Math.max(-1, Math.min(1, v))
    this.cur.setInt16(this.curN * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    if (++this.curN === CHUNK) {
      this.chunks.push(this.cur.buffer as ArrayBuffer)
      this.cur = new DataView(new ArrayBuffer(CHUNK * 2))
      this.curN = 0
    }
  }

  private drain(final: boolean) {
    const total = this.received
    // resample's n for a take of this length; outputs are only ever final once their every tap has arrived.
    const n = Math.floor(total / this.r)
    if (!this.table) {
      // from === to: resample returns the input itself and encodeWav quantises it.
      for (; this.i < total; this.i++) this.emit(this.buf[this.i - this.base])
      this.drop(this.i)
      return
    }
    const { r, half, taps, table, buf } = this
    for (; this.i < n; this.i++) {
      const t = this.i * r
      const c = Math.floor(t)
      const k0 = c - half + 1
      if (!final && k0 + taps > total) break
      const row = Math.round((t - c) * PHASES) * taps
      const j0 = Math.max(0, -k0), j1 = Math.min(taps - 1, total - 1 - k0)
      let acc = 0, wsum = 0
      const off = k0 - this.base
      for (let j = j0; j <= j1; j++) {
        const h = table[row + j]
        acc += buf[off + j] * h
        wsum += h
      }
      // resample stores into a Float32Array, so the value is rounded to float32 before encodeWav reads it.
      this.emit(Math.fround(wsum ? acc / wsum : 0))
    }
    this.drop(Math.floor(this.i * r) - half + 1)
  }

  /** Forget input below absolute index `keep` (the next output's first tap). */
  private drop(keep: number) {
    const k = Math.min(Math.max(0, keep - this.base), this.len)
    if (k < 1 << 15) return
    this.buf.copyWithin(0, k, this.len)
    this.len -= k
    this.base += k
  }
}

/** `take-YYYYMMDD-HHMMSS.wav`, local time. */
export function takeName(at: Date): string {
  const p = (n: number) => String(n).padStart(2, '0')
  return `take-${at.getFullYear()}${p(at.getMonth() + 1)}${p(at.getDate())}-${p(at.getHours())}${p(at.getMinutes())}${p(at.getSeconds())}.wav`
}

export interface WavFacts { container: string; format: number; channels: number; sampleRate: number; byteRate: number; blockAlign: number; bits: number; dataBytes: number; fileBytes: number }

/** Read the header back out of the finished file, so the screen shows what is in the bytes, not what was meant. */
export async function readWavHeader(wav: Blob): Promise<WavFacts> {
  const v = new DataView(await wav.slice(0, 44).arrayBuffer())
  const str = (at: number, n: number) => String.fromCharCode(...Array.from({ length: n }, (_, k) => v.getUint8(at + k)))
  return {
    container: `${str(0, 4)}/${str(8, 4)} ${str(12, 4).trim()}+${str(36, 4)} (${v.getUint32(16, true) + 28}-byte header)`,
    format: v.getUint16(20, true), channels: v.getUint16(22, true), sampleRate: v.getUint32(24, true),
    byteRate: v.getUint32(28, true), blockAlign: v.getUint16(32, true), bits: v.getUint16(34, true),
    dataBytes: v.getUint32(40, true), fileBytes: wav.size,
  }
}
