// The microphone's audio session (013): WebKit refuses getUserMedia with an InvalidStateError, before the system's
// prompt, while `navigator.audioSession.type` is 'playback', which Play the parts sets. Run: npm test.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { describeError, holdAudioSessionForCapture } from '../src/lib/recorder.ts'

const host = (type: string) => ({ audioSession: { type } })

test('after Play the parts, a take sets play-and-record and gives playback back when it lets go', () => {
  const nav = host('playback')
  const letGo = holdAudioSessionForCapture(nav)
  assert.equal(nav.audioSession.type, 'play-and-record')
  letGo()
  assert.equal(nav.audioSession.type, 'playback')
  letGo() // twice is once
  assert.equal(nav.audioSession.type, 'playback')
})

test('a session already fit to record is left as it is', () => {
  for (const type of ['auto', 'play-and-record']) {
    const nav = host(type)
    const letGo = holdAudioSessionForCapture(nav)
    assert.equal(nav.audioSession.type, type)
    letGo()
    assert.equal(nav.audioSession.type, type)
  }
})

test('two takes overlapping (the second opens while the first is still letting go) keep the session until the last', () => {
  const nav = host('ambient')
  const a = holdAudioSessionForCapture(nav)
  const b = holdAudioSessionForCapture(nav)
  a()
  assert.equal(nav.audioSession.type, 'play-and-record')
  b()
  assert.equal(nav.audioSession.type, 'ambient')
})

test('the player setting its own type during a take is not undone, and the next take sets it again', () => {
  const nav = host('auto')
  const a = holdAudioSessionForCapture(nav)
  nav.audioSession.type = 'playback' // Play pressed mid-take
  const b = holdAudioSessionForCapture(nav)
  assert.equal(nav.audioSession.type, 'play-and-record')
  a(); b()
  assert.equal(nav.audioSession.type, 'playback')
  const c = holdAudioSessionForCapture(nav)
  nav.audioSession.type = 'transient'
  c()
  assert.equal(nav.audioSession.type, 'transient')
})

test('no audio session (Chrome, Firefox, node) is a no-op', () => {
  const letGo = holdAudioSessionForCapture({})
  letGo()
  holdAudioSessionForCapture(undefined)()
})

test('the small print names the exception', () => {
  const e = Object.assign(new Error('AudioSession category is not compatible with audio capture.'), { name: 'InvalidStateError' })
  assert.equal(describeError(e), 'InvalidStateError: AudioSession category is not compatible with audio capture.')
  assert.equal(describeError(Object.assign(new Error(''), { name: 'NotReadableError' })), 'NotReadableError')
  assert.equal(describeError(new TypeError('x'), 'audio graph:'), 'audio graph: TypeError: x')
  assert.equal(describeError('odd'), 'odd')
  assert.ok(describeError(new Error('y'.repeat(300))).length <= 120)
})
