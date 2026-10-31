/** Push-to-talk capture for voice notes (013). The microphone's raw samples, resampled here to 16 kHz mono and written
 *  as a 16-bit PCM WAV with a plain 44-byte header: the one shape Muse Voice Transcribe takes (the extensible header
 *  `afconvert` writes is refused, docs/features/013). Never MediaRecorder: on the iPad it records AAC in an m4a.
 *
 *  The microphone is open only between `startRecording` and `stop`/`cancel`; both stop the track, so the system's
 *  recording light goes out with the button. */

export const VOICE_RATE = 16000
/** A note is a sentence, not a rehearsal: the take stops itself here. */
export const MAX_SECONDS = 120

export type MicProblem = 'denied' | 'unavailable' | 'failed'
export class MicError extends Error {
  problem: MicProblem
  /** What the engine said, for the small print under the line and the console: the exception's name and message
   *  ("InvalidStateError: AudioSession category is not compatible with audio capture."), so a report from the iPad
   *  says which failure it was. Empty when there was no exception. */
  code: string
  constructor(problem: MicProblem, message: string, code = '') {
    super(message)
    this.problem = problem
    this.code = code
  }
}

/** An exception as one short line: its name, then its message when it has one, at most 120 characters. */
export function describeError(e: unknown, where?: string): string {
  const err = e as { name?: unknown; message?: unknown } | null
  const name = typeof err?.name === 'string' && err.name ? err.name : typeof e === 'string' ? e : 'Error'
  const msg = typeof err?.message === 'string' ? err.message.trim() : ''
  const line = (where ? `${where} ` : '') + (msg && msg !== name ? `${name}: ${msg}` : name)
  return line.length > 120 ? `${line.slice(0, 119)}…` : line
}

/** The part of `navigator` the audio session lives on (WebKit, Safari 16.4 and the iPad's WKWebView). */
export interface AudioSessionHost { audioSession?: { type: string } }

const CAPTURE_TYPES = new Set(['auto', 'play-and-record'])
let holds = 0
let restoreTo: string | null = null

/**
 * Make the page's audio session one that may record, for as long as a take holds it; the returned function lets go.
 *
 * WebKit refuses getUserMedia outright while `navigator.audioSession.type` is anything but 'auto' or 'play-and-record':
 * an InvalidStateError ("AudioSession category is not compatible with audio capture.", WebCore MediaDevices.cpp), raised
 * before the permission request, so the system's microphone prompt never shows. Play the parts sets 'playback' (sound
 * with the silent switch on) and the type stays for the life of the page, so one Play anywhere in the app used to
 * close the microphone until the app was quit. The type is set synchronously, before the first await, so it holds
 * when getUserMedia checks it. The last take to let go puts back the type it found, unless something else (the
 * player) has set its own type meanwhile.
 */
export function holdAudioSessionForCapture(host: AudioSessionHost | undefined = typeof navigator === 'undefined' ? undefined : navigator as AudioSessionHost): () => void {
  const session = host?.audioSession
  if (!session) return () => undefined
  try {
    // Checked on every take, not only the first: the player may have set its type while an earlier take was open.
    const type = session.type
    if (holds === 0) restoreTo = null
    if (!CAPTURE_TYPES.has(type)) {
      restoreTo = type
      session.type = 'play-and-record'
    }
  } catch {
    return () => undefined
  }
  holds++
  let held = true
  return () => {
    if (!held) return
    held = false
    holds = Math.max(0, holds - 1)
    if (holds > 0 || restoreTo == null) return
    const back = restoreTo
    restoreTo = null
    try { if (session.type === 'play-and-record') session.type = back } catch { /* gone with the page */ }
  }
}

export interface Recording { wav: Blob; seconds: number }

export interface Recorder {
  /** Seconds captured so far. */
  elapsed: () => number
  /** Stop, let the microphone go and return the take. */
  stop: () => Promise<Recording>
  /** Stop and let the microphone go; nothing is kept. */
  cancel: () => void
}

interface Options {
  /** The voice level, 0..1 (RMS in dBFS, -60 = 0, -10 = 1), fast attack and slow release like a meter; ~20 times a second. */
  onLevel?: (level: number) => void
  /** The take reached `MAX_SECONDS` and stopped capturing; the caller ends it with `stop`. */
  onLimit?: () => void
}

/** Collects the input in blocks of ~2048 frames and posts them to the page. */
const WORKLET = `
class Tap extends AudioWorkletProcessor {
  constructor() { super(); this.buf = new Float32Array(2048); this.n = 0 }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0]
    if (ch) for (let i = 0; i < ch.length; i++) {
      this.buf[this.n++] = ch[i]
      if (this.n === this.buf.length) { this.port.postMessage(this.buf); this.buf = new Float32Array(2048); this.n = 0 }
    }
    return true
  }
}
registerProcessor('folio-tap', Tap)
`

type Ctx = typeof AudioContext
const AudioCtx: Ctx | undefined = typeof window === 'undefined' ? undefined
  : window.AudioContext ?? (window as unknown as { webkitAudioContext?: Ctx }).webkitAudioContext

/**
 * Open the microphone and start capturing. Call it straight from the pointer-down handler: the audio session is set
 * for capture and the audio context made before the first await, inside the touch, which is what lets the iPad start
 * them; getUserMedia is called in the same turn. A failure is a MicError whose `code` names the exception.
 */
export async function startRecording(opts: Options = {}): Promise<Recorder> {
  if (!AudioCtx || !navigator.mediaDevices?.getUserMedia) {
    throw note(new MicError('unavailable', 'This device has no microphone Folio can use.', !AudioCtx ? 'no AudioContext' : 'no mediaDevices.getUserMedia'))
  }
  // Before anything else and before any await: getUserMedia below checks the session type synchronously.
  const letGo = holdAudioSessionForCapture()
  let ctx: AudioContext
  try {
    ctx = new AudioCtx()
  } catch (e) {
    letGo()
    throw fail('audio context', e)
  }
  void ctx.resume().catch(() => undefined)

  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: false },
    })
  } catch (e) {
    void ctx.close().catch(() => undefined)
    letGo()
    const name = (e as DOMException)?.name
    const code = describeError(e)
    if (name === 'NotAllowedError' || name === 'SecurityError') throw note(new MicError('denied', 'Folio is not allowed to use the microphone.', code))
    if (name === 'NotFoundError' || name === 'OverconstrainedError') throw note(new MicError('unavailable', 'No microphone was found.', code))
    throw note(new MicError('failed', 'The microphone could not be opened.', code))
  }

  const rate = ctx.sampleRate
  const limit = Math.round(MAX_SECONDS * rate)
  const blocks: Float32Array[] = []
  let frames = 0
  let level = 0
  let open = true

  const take = (block: Float32Array) => {
    if (!open || frames >= limit) return
    const room = limit - frames
    const b = block.length > room ? block.subarray(0, room) : block
    blocks.push(b)
    frames += b.length
    let sum = 0
    for (let i = 0; i < b.length; i++) sum += b[i] * b[i]
    const db = 20 * Math.log10(Math.sqrt(sum / (b.length || 1)) + 1e-9)
    const target = Math.min(1, Math.max(0, (db + 60) / 50))
    level += (target - level) * (target > level ? 0.35 : 0.06)
    opts.onLevel?.(level)
    if (frames >= limit) opts.onLimit?.()
  }

  let source: MediaStreamAudioSourceNode | null = null
  let node: AudioNode | null = null
  const release = () => {
    if (!open) return
    open = false
    try { source?.disconnect(); node?.disconnect() } catch { /* already gone */ }
    stream.getTracks().forEach(t => t.stop())
    void ctx.close().catch(() => undefined)
    letGo()
  }

  // From here on the microphone is open: anything that goes wrong lets it go before saying so.
  try {
    source = ctx.createMediaStreamSource(stream)
    // A silent sink keeps the graph pulling on every engine without playing the voice back.
    const mute = ctx.createGain()
    mute.gain.value = 0
    mute.connect(ctx.destination)
    let url: string | null = null
    try {
      if (!ctx.audioWorklet) throw new Error('no worklet')
      url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }))
      await ctx.audioWorklet.addModule(url)
      const w = new AudioWorkletNode(ctx, 'folio-tap', { numberOfInputs: 1, numberOfOutputs: 1, channelCount: 1, channelCountMode: 'explicit' })
      w.port.onmessage = e => take(e.data as Float32Array)
      node = w
    } catch {
      // Older engines: the deprecated ScriptProcessor does the same job on the main thread.
      const sp = ctx.createScriptProcessor(2048, 1, 1)
      sp.onaudioprocess = e => take(new Float32Array(e.inputBuffer.getChannelData(0)))
      node = sp
    } finally {
      if (url) URL.revokeObjectURL(url)
    }
    source.connect(node)
    node.connect(mute)
    // The context was made inside the touch; once the stream is live, ask again in case the engine held it suspended.
    if (ctx.state !== 'running') await ctx.resume().catch(() => undefined)
  } catch (e) {
    release()
    throw fail('audio graph', e)
  }
  // A context that will not run records silence: say so now rather than send an empty take.
  if ((ctx.state as string) !== 'running') {
    release()
    throw note(new MicError('failed', 'The microphone did not start.', `audio context ${ctx.state}`))
  }

  return {
    elapsed: () => frames / rate,
    cancel: release,
    stop: async () => {
      release()
      const all = new Float32Array(frames)
      let at = 0
      for (const b of blocks) { all.set(b, at); at += b.length }
      const pcm = resample(all, rate, VOICE_RATE)
      return { wav: encodeWav(pcm, VOICE_RATE), seconds: frames / rate }
    },
  }
}

/** The failure in the console as well (Safari's Web Inspector on the iPad), where the whole exception can be read. */
function note(err: MicError): MicError {
  console.warn('[voice] microphone:', err.problem, err.code || '(no exception)')
  return err
}
const fail = (where: string, e: unknown) => note(new MicError('failed', 'The microphone could not be opened.', describeError(e, `${where}:`)))

/** Band-limited resampling (a Hann-windowed sinc, eight zero crossings of the low-pass each side), so a 48 kHz voice
 *  comes down to 16 kHz without folding its hiss into the speech band. The kernel is tabulated once per call at
 *  `PHASES` fractional offsets, so a two-minute take is multiply-adds only (no sin/cos per tap): about a tenth of a
 *  second on an iPad rather than a frozen second or two. */
const PHASES = 256
export function resample(x: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return x
  const r = from / to
  const n = Math.floor(x.length / r)
  const out = new Float32Array(n)
  const fc = Math.min(1, to / from) * 0.94 // the cutoff, as a fraction of the source's Nyquist
  const half = Math.ceil(8 / fc)
  const taps = 2 * half
  // table[p * taps + j]: the weight of x[c - half + 1 + j] when the output falls p / PHASES past sample c.
  const table = new Float32Array((PHASES + 1) * taps)
  for (let p = 0; p <= PHASES; p++) {
    for (let j = 0; j < taps; j++) {
      const d = p / PHASES + half - 1 - j
      const a = Math.PI * fc * d
      table[p * taps + j] = Math.abs(d) >= half ? 0 : (d === 0 ? 1 : Math.sin(a) / a) * (0.5 + 0.5 * Math.cos((Math.PI * d) / half))
    }
  }
  for (let i = 0; i < n; i++) {
    const t = i * r
    const c = Math.floor(t)
    const row = Math.round((t - c) * PHASES) * taps
    const k0 = c - half + 1
    const j0 = Math.max(0, -k0), j1 = Math.min(taps - 1, x.length - 1 - k0)
    let acc = 0, wsum = 0
    for (let j = j0; j <= j1; j++) {
      const h = table[row + j]
      acc += x[k0 + j] * h
      wsum += h
    }
    out[i] = wsum ? acc / wsum : 0
  }
  return out
}

/** Mono 16-bit PCM in a RIFF/WAVE file with the plain 44-byte header (format 1, no extensible chunk, no FLLR). */
export function encodeWav(pcm: Float32Array, rate: number): Blob {
  const buf = new ArrayBuffer(44 + pcm.length * 2)
  const v = new DataView(buf)
  const str = (at: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(at + i, s.charCodeAt(i)) }
  str(0, 'RIFF'); v.setUint32(4, 36 + pcm.length * 2, true); str(8, 'WAVE')
  str(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true)
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true)
  str(36, 'data'); v.setUint32(40, pcm.length * 2, true)
  for (let i = 0; i < pcm.length; i++) {
    const s = Math.max(-1, Math.min(1, pcm[i]))
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return new Blob([buf], { type: 'audio/wav' })
}
