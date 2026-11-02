// The seat's part on the stand (010, CK 2026-11-02): matched on the canonical names the API stored, never normalised on
// the device. The printed name stays the part's; a row without its canonical name matches by its own name.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { seatPart, seatReads, splitIsSeats } from '../src/app/seat.ts'

const book = [
  { id: 'p1', name: 'Violino I', canonical: 'Violin I' },
  { id: 'p2', name: 'Violino II', canonical: 'Violin II' },
  { id: 'p3', name: 'Viola', canonical: 'Viola' },
  { id: 'p4', name: 'Violoncello e Contrabasso', canonical: 'Cello & Double Bass' },
]

test('a seat "Violin II" reads the printed "Violino II"', () => {
  assert.equal(seatPart(book, 'Violin II', 'Violin II')?.id, 'p2')
  assert.equal(seatPart(book, 'Violin II')?.id, 'p2')                 // a seat without its canonical name: as typed
  assert.equal(seatPart(book, '2nd Violins', 'Violin II')?.id, 'p2')  // a seat typed another way, its canonical stored
})

test('a seat reads a shared staff that names it', () => {
  assert.equal(seatPart(book, 'Cello', 'Cello')?.id, 'p4')
  assert.equal(seatPart(book, 'Double Bass', 'Double Bass')?.id, 'p4')
  assert.ok(seatReads('Flute I', 'Flute I & Flute II') && !seatReads('Flute III', 'Flute I & Flute II'))
})

test('the exact printed name wins, and no match is no part', () => {
  const two = [{ id: 'a', name: 'Violin II', canonical: 'Violin II' }, { id: 'b', name: 'Violino II', canonical: 'Violin II' }]
  assert.equal(seatPart(two, 'Violino II', 'Violin II')?.id, 'b')
  assert.equal(seatPart(book, 'Oboe', 'Oboe'), undefined)
  assert.equal(seatPart(book, '', null), undefined)
  assert.equal(seatPart(book, 'Violin I', 'Violin I')?.id, 'p1')       // never Violin II for the firsts
})

test('without canonical names (a stack before the migration) the match is exact, as before', () => {
  const old = [{ id: 'x', name: 'Violino II' }, { id: 'y', name: 'Cello' }]
  assert.equal(seatPart(old, 'Violin II', undefined), undefined)
  assert.equal(seatPart(old, 'Cello', undefined)?.id, 'y')
})

test('a player\'s strips: the split of the seat\'s part', () => {
  assert.ok(splitIsSeats(['Violino II'], book, 'Violin II', 'Violin II'))
  assert.ok(!splitIsSeats(['Violino I'], book, 'Violin II', 'Violin II'))
  assert.ok(splitIsSeats(['Violino I', 'Violino II'], book, 'Violin II', 'Violin II'))
})
