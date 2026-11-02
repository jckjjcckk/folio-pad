// DEBUG: remove before release.
/** A debug take recorder for CK: one long rehearsal take, captured by the voice-note chain itself (`startRecording` in
 *  recorder.ts: the same audio session hold, getUserMedia constraints, AudioContext, worklet and fallback), written as
 *  the same 16 kHz mono 16-bit PCM WAV the app sends to Voice Transcribe, but uncapped and whole (not endpointed, not
 *  chunked). The blocks stream into `StreamingWav` (lib/debugTake.ts), whose bytes equal recorder.ts's
 *  `encodeWav(resample(...))` for the same samples (tests/debugTake.test.ts). Then the share sheet (Save to Files,
 *  AirDrop), or a download.
 *
 *  The take lives in module state, not in the menu, so closing the account menu or opening a book does not end it;
 *  the dock (`DebugTakeDock`, mounted once in App.tsx) shows the timer, Stop, and afterwards the file's facts as read
 *  back from its own header. */
import { useEffect, useState, useSyncExternalStore } from 'react'
import { describeError, startRecording, VOICE_RATE, type Recorder } from '../lib/recorder'
import { StreamingWav, readWavHeader, takeName, type WavFacts } from '../lib/debugTake'
import { deliverFile, isNative } from '../lib/native'
import './debug.css'

interface Done { wav: Blob; name: string; url: string; seconds: number; captureRate: number; facts: WavFacts | null }
interface State {
  phase: 'idle' | 'starting' | 'recording' | 'done' | 'error'
  name: string
  done: Done | null
  error: string | null
  note: string | null
}

let state: State = { phase: 'idle', name: '', done: null, error: null, note: null }
const subs = new Set<() => void>()
const set = (p: Partial<State>) => { state = { ...state, ...p }; subs.forEach(f => f()) }
const subscribe = (f: () => void) => { subs.add(f); return () => { subs.delete(f) } }
const useTake = () => useSyncExternalStore(subscribe, () => state)

let rec: Recorder | null = null
let writer: StreamingWav | null = null
let wake: { release: () => Promise<void> } | null = null
/** Bumped by every start and stop, so a microphone that opens after Stop is let go at once. */
let gen = 0

function keepAwake(on: boolean) {
  if (!on) { void wake?.release().catch(() => undefined); wake = null; return }
  const wl = (navigator as Navigator & { wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> } }).wakeLock
  wl?.request('screen').then(w => { if (state.phase === 'recording' || state.phase === 'starting') wake = w; else void w.release() }, () => undefined)
}

/** Call straight from the tap, like the voice button: startRecording sets the audio session and makes the context inside the touch. */
function start() {
  if (state.phase === 'starting' || state.phase === 'recording') return
  if (state.done) URL.revokeObjectURL(state.done.url)
  const g = ++gen
  writer = null
  rec = null
  set({ phase: 'starting', name: takeName(new Date()), done: null, error: null, note: null })
  startRecording({
    maxSeconds: Infinity,
    keepBlocks: false,
    onBlock: (b, rate) => { if (g === gen) (writer ??= new StreamingWav(rate)).push(b) },
  }).then(
    r => { if (g !== gen) { r.cancel(); return } rec = r; set({ phase: 'recording' }) },
    e => { if (g === gen) { keepAwake(false); set({ phase: 'error', error: describeError(e) + ((e as { code?: string }).code ? ` (${(e as { code?: string }).code})` : '') }) } },
  )
  keepAwake(true)
}

/** Stop: let the microphone go exactly as the voice note's `stop` does (release first, so blocks still in flight are
 *  dropped the same way), close the WAV, and offer it to the share sheet while the tap still counts as a gesture. */
function stop() {
  if (state.phase === 'starting') { gen++; keepAwake(false); set({ phase: 'idle' }); return }
  if (state.phase !== 'recording' || !rec) return
  gen++
  rec.cancel()
  rec = null
  keepAwake(false)
  const f = (writer ?? new StreamingWav(VOICE_RATE)).finish()
  writer = null
  const done: Done = { wav: f.wav, name: state.name, url: URL.createObjectURL(f.wav), seconds: f.samples / VOICE_RATE, captureRate: f.captureRate, facts: null }
  set({ phase: 'done', done })
  void readWavHeader(f.wav).then(facts => { if (state.done === done) set({ done: { ...done, facts } }) })
  void share()
}

async function share() {
  const d = state.done
  if (!d) return
  const file = new File([d.wav], d.name, { type: 'audio/wav' })
  const nav = navigator as Navigator & { canShare?: (data: ShareData) => boolean }
  if (typeof nav.share === 'function' && nav.canShare?.({ files: [file] })) {
    try {
      await nav.share({ files: [file], title: d.name })
      set({ note: 'Shared.' })
      return
    } catch (e) {
      if ((e as DOMException)?.name === 'AbortError') { set({ note: 'Share sheet closed. Tap Share to open it again.' }); return }
      set({ note: `navigator.share failed: ${describeError(e)}` })
      if (!isNative) return
    }
  }
  if (isNative) {
    try { await deliverFile(d.wav, d.name); set({ note: 'Handed to the share sheet (Capacitor).' }) } catch (e) { set({ note: `Share failed: ${describeError(e)}` }) }
    return
  }
  set({ note: 'No share sheet here: use the download link.' })
}

function dismiss() {
  if (state.phase === 'recording' || state.phase === 'starting') return
  if (state.done) URL.revokeObjectURL(state.done.url)
  set({ phase: 'idle', done: null, error: null, note: null })
}

const clock = (s: number) => {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60)
  return `${h ? `${h}:${String(m).padStart(2, '0')}` : m}:${String(sec).padStart(2, '0')}`
}
const mb = (b: number) => `${(b / 1e6).toFixed(2)} MB`

function useElapsed(on: boolean) {
  const [s, setS] = useState(0)
  useEffect(() => {
    if (!on) return
    const id = window.setInterval(() => setS(rec?.elapsed() ?? 0), 250)
    return () => window.clearInterval(id)
  }, [on])
  return on ? s : 0
}

/** The menu entry, in the account popover (Display.tsx). */
export function DebugRecordButton() {
  const t = useTake()
  const live = t.phase === 'recording' || t.phase === 'starting'
  const s = useElapsed(t.phase === 'recording')
  return (
    <div className="acct-sec" data-debug="voice-take">
      <span className="r3-label">Debug</span>
      <button type="button" data-debug="voice-take" className={`r3-btn is-line dbg-rec${live ? ' is-live' : ''}`} aria-pressed={live}
        onClick={() => (live ? stop() : start())}>
        {t.phase === 'starting' ? 'Debug: opening microphone… (tap to cancel)' : t.phase === 'recording' ? `Debug: stop take · ${clock(s)}` : 'Debug: record take'}
      </button>
    </div>
  )
}

/** The take's timer and, afterwards, its file: mounted once at the app's root so it outlives the menu. */
export function DebugTakeDock() {
  const t = useTake()
  const s = useElapsed(t.phase === 'recording')
  if (t.phase === 'idle') return null
  const d = t.done
  const f = d?.facts
  return (
    <div className="dbg-dock" data-debug="voice-take" role="status" aria-live="polite">
      {(t.phase === 'starting' || t.phase === 'recording') && (
        <div className="dbg-row">
          <span className="dbg-dot" aria-hidden="true" />
          <span className="dbg-time num">{t.phase === 'starting' ? 'Opening…' : clock(s)}</span>
          <span className="dbg-sub">{t.name} · ~{mb(44 + Math.floor(s * VOICE_RATE) * 2)}</span>
          <button type="button" className="r3-btn is-danger dbg-btn" onClick={stop}>Stop</button>
        </div>
      )}
      {t.phase === 'error' && (
        <div className="dbg-row">
          <span className="dbg-sub">Debug take failed: {t.error}</span>
          <button type="button" className="r3-btn is-line dbg-btn" onClick={dismiss}>Close</button>
        </div>
      )}
      {t.phase === 'done' && d && (
        <>
          <div className="dbg-row">
            <b className="dbg-name">{d.name}</b>
            <button type="button" className="r3-btn is-solid dbg-btn" onClick={() => void share()}>Share</button>
            <a className="r3-btn is-line dbg-btn" href={d.url} download={d.name}>Download</a>
            <button type="button" className="r3-btn is-quiet dbg-btn" onClick={dismiss}>Close</button>
          </div>
          <dl className="dbg-facts">
            <dt>Duration</dt><dd className="num">{clock(d.seconds)} ({d.seconds.toFixed(3)} s)</dd>
            <dt>Sample rate</dt><dd className="num">{f ? `${f.sampleRate} Hz` : '…'} (captured at {d.captureRate} Hz)</dd>
            <dt>Channels</dt><dd className="num">{f ? f.channels : '…'}</dd>
            <dt>Encoding</dt><dd>{f ? `${f.bits}-bit PCM (format ${f.format}), block ${f.blockAlign}, ${f.byteRate} B/s` : '…'}</dd>
            <dt>Container</dt><dd>{f ? f.container : '…'}</dd>
            <dt>Size</dt><dd className="num">{f ? `${f.fileBytes.toLocaleString()} bytes (${mb(f.fileBytes)}), data ${f.dataBytes.toLocaleString()}` : `${d.wav.size.toLocaleString()} bytes`}</dd>
          </dl>
          {t.note && <p className="dbg-sub">{t.note}</p>}
        </>
      )}
    </div>
  )
}
