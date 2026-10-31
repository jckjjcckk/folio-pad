// Play the parts across books when the audio clock stops (`player.ts`, `audioClock.ts`). Run: npm test.
//
// CK's iPad: Op. 18 played, then PC3, then every book showed the count-in's first beat and never moved on. In the
// simulator the same state was a context that said 'running' while its currentTime stood still (a CoreAudio device
// change had left the output stopped), so the transport never reached its start time. These tests drive the real
// PartsPlayer on a stand-in Tone whose clock can be stopped the same way.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { registerHooks } from 'node:module'
import { ClockWatch, clockMoves, sessionForPlay, startWithRevival, STOPPED_WHILE_PLAYING } from '../src/app/audioClock.ts'

// player.ts is written for Vite: extensionless imports and the app's Supabase client. Load it as it is, with those two
// resolved here (the client is never called: the tests hand the player its book).
registerHooks({
  resolve(specifier, context, next) {
    if (specifier === '../lib/supabase') return { url: 'data:text/javascript,export const supabase = {}', shortCircuit: true }
    if (/^\.\.?\//.test(specifier) && !/\.\w+$/.test(specifier) && context.parentURL?.includes('/src/app/')) return next(`${specifier}.ts`, context)
    return next(specifier, context)
  },
})
const { PartsPlayer } = await import('../src/app/player.ts')
type Player = InstanceType<typeof PartsPlayer>

// ---------------------------------------------------------------- the stand-in: a context, its transport, the nodes

const device = { newContextsFrozen: false, restartHeals: false }

class FakeContext {
  state = 'suspended'
  private acc = 0
  private since = 0
  private frozenAt: number | null = null
  transport: FakeTransport
  rawContext = {
    suspend: async () => { this.pause(); if (device.restartHeals) this.frozenAt = null },
    resume: async () => { this.run() },
  }
  constructor() {
    this.transport = new FakeTransport(this)
    if (device.newContextsFrozen) this.frozenAt = 0
  }
  get currentTime() {
    if (this.frozenAt != null) return this.frozenAt
    return this.state === 'running' ? this.acc + (performance.now() - this.since) / 1000 : this.acc
  }
  run() { if (this.state === 'suspended') { this.since = performance.now(); this.state = 'running' } }
  pause() { if (this.state === 'running') { this.acc = this.currentTime; this.state = 'suspended' } }
  /** The output under the context stops: still 'running', the clock stands at this second. */
  freeze() { this.frozenAt = this.currentTime }
  immediate() { return this.currentTime }
  now() { return this.currentTime + 0.1 }
  decodeAudioData = async () => ({ duration: 1 })
  dispose() { this.state = 'closed' }
}

class FakeTransport {
  PPQ = 192
  loop = false
  loopStart: unknown = 0
  loopEnd: unknown = 0
  private startAt: number | null = null
  private ctx: FakeContext
  bpm = { value: 120, setValueAtTime: (v: number) => { this.bpm.value = v }, getValueAtTime: () => this.bpm.value }
  constructor(ctx: FakeContext) { this.ctx = ctx }
  set position(_: unknown) { /* ticks restart at the next start */ }
  get state() { return this.startAt != null && this.ctx.now() >= this.startAt ? 'started' : 'stopped' }
  get ticks() { return this.getTicksAtTime(this.ctx.now()) }
  getTicksAtTime(t: number) { return this.startAt != null && t >= this.startAt ? ((t - this.startAt) * this.bpm.value / 60) * this.PPQ : 0 }
  schedule() { return 0 }
  cancel() {}
  start(at: number) { this.startAt = at }
  stop() { this.startAt = null }
}

class Node_ {
  gain = { value: 0, rampTo: () => {} }
  loaded = true
  connect() { return this }
  toDestination() { return this }
  releaseAll() {}
  triggerAttackRelease() {}
  dispose() {}
}

let ctx = new FakeContext()
const Tone = {
  getContext: () => ctx,
  setContext: (c: FakeContext) => { ctx = c },
  Context: FakeContext,
  getTransport: () => ctx.transport,
  start: () => ctx.rawContext.resume(),
  immediate: () => ctx.immediate(),
  now: () => ctx.now(),
  Gain: Node_, Synth: Node_, Sampler: Node_,
  Frequency: () => ({ toNote: () => 'C4' }),
}

// The page around the player: the samples arrive (status 0 with bytes, as in the iPad shell), frames are timers.
Object.assign(globalThis, {
  window: globalThis,
  location: { href: 'capacitor://localhost/' },
  fetch: async () => new Response(new Uint8Array(64), { status: 200 }),
  requestAnimationFrame: (fn: () => void) => setTimeout(fn, 16) as unknown as number,
  cancelAnimationFrame: (id: number) => clearTimeout(id),
})

// Two short books in 3/4 at a quick printed tempo, so a count-in and a few bars pass in well under a second.
function book(part: string) {
  const bars = Array.from({ length: 8 }, (_, i) => ({ bar: i + 1, at: i * 3, quarters: 3 }))
  return {
    map: {
      version: 1, ppq: 480, parts: [part], quarters: 24, bars,
      tempos: [{ bar: 1, at: 0, qpm: 720, bpm: 720, beat: 'quarter', text: null, marked: true }],
      meters: [{ bar: 1, at: 0, meter: '3/4', beats: 3, beat_quarters: 1 }],
    },
    tracks: [{ name: part, notes: bars.map(b => ({ q: b.at, dur: 1, midi: 69, vel: 0.7 })) }],
  }
}
const OPTS = { tone: async () => Tone as never, startWithin: 150, stallAfter: 250 }
const FROM_BAR_1 = { from: 1, to: null, loop: false, countIn: true }

function positions(p: Player) {
  const seen: { status: string; bar: number | null; countBeat: number }[] = []
  p.subscribe(x => seen.push({ status: x.status, bar: x.bar, countBeat: x.countBeat }))
  return seen
}

async function until(ok: () => boolean, ms = 2000) {
  const end = Date.now() + ms
  while (!ok()) {
    if (Date.now() > end) return false
    await new Promise(r => setTimeout(r, 10))
  }
  return true
}
const reachedBar = (seen: ReturnType<typeof positions>, bar: number) => () => seen.some(s => s.status === 'playing' && (s.bar ?? 0) >= bar)

function fresh() {
  device.newContextsFrozen = false
  device.restartHeals = false
  ctx = new FakeContext()
}

// ---------------------------------------------------------------- the engine across books

test('book A plays, stops; book B then plays past its count-in on the same transport', async () => {
  fresh()
  const a = new PartsPlayer(book('Violin I') as never, OPTS)
  a.setPace(1)
  const seenA = positions(a)
  await a.play(FROM_BAR_1)
  assert.ok(await until(reachedBar(seenA, 3)), 'book A moved past its count-in')
  a.stop()
  a.dispose()

  const b = new PartsPlayer(book('Cello') as never, OPTS)
  b.setPace(1)
  const seenB = positions(b)
  await b.play(FROM_BAR_1)
  assert.ok(await until(reachedBar(seenB, 3)), 'book B moved past its count-in')
  assert.ok(seenB.some(s => s.status === 'counting' && s.countBeat === 1), 'B counted in first')
  b.dispose()
})

test('the clock stopped under the context after book A: book B replaces the context and plays', async () => {
  fresh()
  const a = new PartsPlayer(book('Violin I') as never, OPTS)
  a.setPace(1)
  await a.play(FROM_BAR_1)
  a.stop()
  a.dispose()
  const stale = ctx
  stale.freeze()   // 'running', currentTime standing still: what every book met on the iPad

  const b = new PartsPlayer(book('Cello') as never, OPTS)
  b.setPace(1)
  const seenB = positions(b)
  await b.play(FROM_BAR_1)
  assert.ok(await until(reachedBar(seenB, 3)), 'book B plays instead of holding count-in beat 1')
  assert.notEqual(ctx, stale, 'a new context')
  assert.equal(stale.state, 'closed', 'the stale one closed')
  b.dispose()
})

test('a restart of the same context is tried first, and kept when it brings the clock back', async () => {
  fresh()
  device.restartHeals = true
  const p = new PartsPlayer(book('Viola') as never, OPTS)
  p.setPace(1)
  const seen = positions(p)
  await p.play(FROM_BAR_1)
  p.stop()
  const same = ctx
  same.freeze()
  await p.play(FROM_BAR_1)
  assert.ok(await until(reachedBar(seen, 3)))
  assert.equal(ctx, same, 'no new context needed')
  p.dispose()
})

test('when no way back moves the clock, Play says so and the player is idle, not counting', async () => {
  fresh()
  const p = new PartsPlayer(book('Viola') as never, OPTS)
  const seen = positions(p)
  ctx.freeze()
  device.newContextsFrozen = true
  await assert.rejects(p.play(FROM_BAR_1), (e: Error) => e.name === 'AudioStalled' && /Close Folio, open it again/.test(e.message))
  assert.equal(seen.at(-1)?.status, 'idle')
  p.dispose()
})

test('a clock that stops while playing stops the player and reports it', async () => {
  fresh()
  const p = new PartsPlayer(book('Violin II') as never, OPTS)
  p.setPace(1)
  const seen = positions(p)
  const faults: string[] = []
  p.onFault(e => faults.push(e.message))
  await p.play(FROM_BAR_1)
  assert.ok(await until(reachedBar(seen, 2)))
  ctx.freeze()
  assert.ok(await until(() => faults.length > 0), 'the stop was noticed')
  assert.deepEqual(faults, [STOPPED_WHILE_PLAYING])
  assert.equal(seen.at(-1)?.status, 'idle')
  p.dispose()
})

test('a Stop during the clock check cancels the play quietly', async () => {
  fresh()
  const p = new PartsPlayer(book('Viola') as never, OPTS)
  ctx.freeze()
  device.newContextsFrozen = true
  const playing = p.play(FROM_BAR_1)
  await new Promise(r => setTimeout(r, 60))
  p.stop()
  await playing   // resolves: the Stop took over
  p.dispose()
})

// ---------------------------------------------------------------- the clock rules on their own

test('clockMoves: true once the clock passes its first reading, false when it stands still', async () => {
  let t = 5
  const moving = setInterval(() => { t += 0.01 }, 5)
  assert.equal(await clockMoves(() => t, 200), true)
  clearInterval(moving)
  assert.equal(await clockMoves(() => 7, 80), false)
  assert.equal(await clockMoves(() => 7, 80, () => true), true, 'a cancelled wait is not a stall')
})

test('startWithRevival: ways back in order, each only while the clock is still', async () => {
  const done: string[] = []
  let healedBy: string | null = 'replace'
  const took = await startWithRevival({
    start: () => { done.push('start') },
    moves: async () => done.at(-2) === healedBy,
    revive: [async () => { done.push('restart') }, async () => { done.push('replace') }],
    limit: 50,
    cancelled: () => false,
  })
  assert.equal(took, 2)
  assert.deepEqual(done, ['start', 'restart', 'start', 'replace', 'start'])

  healedBy = null
  done.length = 0
  const none = await startWithRevival({ start: () => { done.push('start') }, moves: async () => false, revive: [async () => { throw new Error('x') }], limit: 50, cancelled: () => false })
  assert.equal(none, -1, 'a failing way back is passed over')
  const hung = await startWithRevival({ start: () => {}, moves: async () => false, revive: [() => new Promise<void>(() => {})], limit: 30, cancelled: () => false })
  assert.equal(hung, -1, 'a way back that never answers is given its limit')
})

test('ClockWatch: still past the limit is a stall; a long gap between moving readings is not', () => {
  const w = new ClockWatch(1500)
  assert.equal(w.stalled(10, 0), false)
  assert.equal(w.stalled(10, 1000), false)
  assert.equal(w.stalled(10, 1600), true)
  w.reset()
  assert.equal(w.stalled(10, 2000), false)
  assert.equal(w.stalled(12, 9000), false, 'a hidden page: no frames for 7 s, the clock moved')
})

test('a Play asks for the playback session, never over a voice take', () => {
  assert.equal(sessionForPlay('auto'), 'playback')
  assert.equal(sessionForPlay('ambient'), 'playback')
  assert.equal(sessionForPlay('playback'), null)
  assert.equal(sessionForPlay('play-and-record'), null, 'the microphone holds the session')
  assert.equal(sessionForPlay(undefined), null, 'no audioSession here')
})
