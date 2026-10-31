/** The audio clock Play the parts runs on (014), and what to do when it stands still. No Tone and no app imports here,
 *  so the node tests load it as it is.
 *
 *  Tone's transport counts time on the AudioContext's `currentTime`. WebKit can leave a context saying 'running' while
 *  its clock no longer moves: the audio output under it stopped (in the simulator, a CoreAudio device change ended in
 *  "IO started (err -66665)" and every context in the app stood at the same second from then on). Nothing throws and no
 *  'statechange' fires, so a Play scheduled the count-in, drew its first beat and waited for a start time that never
 *  came, on every book, until the app was quit. The player now checks that the clock moves after it starts, restarts
 *  the context, then makes a new one, and says so when neither brings the sound back. */

/** How long a just-started clock may stand still before the player tries to bring it back (a resumed context can take a
 *  few hundred ms on an iPad before its first quantum). */
export const START_WITHIN_MS = 1200
/** How long a playing clock may stand still before the player says the sound stopped. */
export const STALL_MS = 1500

/** The clock stood still and no way back worked; the panel shows the message. */
export class AudioStalled extends Error {
  constructor(message = 'The sound stopped on this device and did not come back. Close Folio, open it again and tap Play.') {
    super(message)
    this.name = 'AudioStalled'
  }
}

export const STOPPED_WHILE_PLAYING = 'The sound stopped on this device. Tap Play to start it again.'

const wait = (ms: number) => new Promise<void>(r => setTimeout(r, ms))

/** Whether the audio clock `read` (seconds) moves forward within `within` ms. A cancelled wait (a Stop, another Play)
 *  counts as moved: whoever cancelled it has taken over. */
export async function clockMoves(read: () => number, within: number, cancelled: () => boolean = () => false, step = 40): Promise<boolean> {
  const t0 = read()
  const end = Date.now() + within
  for (;;) {
    await wait(step)
    if (cancelled()) return true
    if (read() > t0) return true
    if (Date.now() >= end) return false
  }
}

/** `p`, or nothing after `ms`: a promise from a wedged audio output (a resume, a suspend) may never settle. A rejection
 *  still rejects. */
export function settled<T>(p: Promise<T>, ms: number): Promise<T | undefined> {
  p.catch(() => undefined)   // a late rejection, after the wait won, is nobody's to handle
  return Promise.race([p, wait(ms).then(() => undefined)])
}

/** Starts a pass, then brings a still clock back: each way back runs only while the clock has not moved, and is given
 *  `limit` ms. Returns the number of ways back it took (0 when the clock moved at once), or -1 when none worked. */
export async function startWithRevival(opts: {
  /** Schedule the pass on the context there is now. */
  start: () => void | Promise<void>
  /** Resolves true once the clock moves (`clockMoves`). */
  moves: () => Promise<boolean>
  /** Ways back, cheapest first: restart the context, then replace it. */
  revive: (() => Promise<void>)[]
  limit: number
  cancelled: () => boolean
}): Promise<number> {
  await opts.start()
  for (let i = 0; ; i++) {
    if (await opts.moves()) return i
    if (opts.cancelled()) return i
    if (i === opts.revive.length) return -1
    try {
      await settled(opts.revive[i](), opts.limit)
    } catch { /* this way back failed; the next one may not */ }
    if (opts.cancelled()) return i + 1
    await opts.start()
  }
}

/** Watches a playing clock against the wall clock: stalled when the audio time has not moved for longer than `limit` ms.
 *  A hidden page that draws no frames is not a stall: the first reading after it compares values, not rates. */
export class ClockWatch {
  private t = Number.NaN
  private at = 0
  private limit: number
  constructor(limit = STALL_MS) {
    this.limit = limit
  }
  reset() {
    this.t = Number.NaN
  }
  stalled(audioSeconds: number, wallMs: number): boolean {
    if (audioSeconds !== this.t) {
      this.t = audioSeconds
      this.at = wallMs
      return false
    }
    return wallMs - this.at > this.limit
  }
}

/** The audio session type a Play asks for, or null to leave it. 'playback' sounds with the silent switch on; a voice
 *  take holds 'play-and-record' for the microphone (WebKit refuses getUserMedia under 'playback', recorder.ts) and puts
 *  back what it found afterwards, so the player never takes the session from a take. */
export function sessionForPlay(type: string | undefined): string | null {
  if (type == null || type === 'playback' || type === 'play-and-record') return null
  return 'playback'
}
