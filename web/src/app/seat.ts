/** Which of a book's parts a seat reads (010, CK 2026-11-02). A group's seat says "Violin II"; a book's part carries the
 *  name the edition prints ("Violino II", "Vln. 2", "2nd Violins"). The API gives both one canonical English name when
 *  it writes them (`api/app/librarian/instruments.py`: `parts.canonical` at import and cut, `members.part_canonical`
 *  where the seat is set); the device never normalises a name itself, it only compares the stored ones. A row without
 *  its canonical name (a stack before migration 20261102130000) is matched by its own name, as before.
 *  The policy on marks addressed to a part makes the same comparison (`seat_reads` in that migration). */

export interface SeatablePart { id: string; name: string; canonical?: string | null }

/** A seat reads a part when the canonical names are the same, or the part is a shared staff (" & ") naming the seat:
 *  "Cello" reads "Cello & Double Bass", "Flute I" reads "Flute I & Flute II". */
export function seatReads(seat: string | null | undefined, part: string | null | undefined): boolean {
  if (!seat || !part) return false
  return seat === part || part.split(' & ').includes(seat)
}

/** The part on the seat's stand: the part printed with the seat's own name first, then the one with the seat's
 *  canonical name, then a shared staff that names it. Undefined when the book has none. */
export function seatPart<P extends SeatablePart>(parts: P[], seat: string | null | undefined, seatCanonical?: string | null): P | undefined {
  if (!seat) return undefined
  const mine = seatCanonical || seat
  const canon = (p: P) => p.canonical || p.name
  return parts.find(p => p.name === seat) ?? parts.find(p => canon(p) === mine) ?? parts.find(p => seatReads(mine, canon(p)))
}

/** Whether a split's instruments (printed names, as the book's parts carry them) are the seat's part. */
export function splitIsSeats<P extends SeatablePart>(instruments: string[], parts: P[], seat: string | null | undefined, seatCanonical?: string | null): boolean {
  const own = seatPart(parts.filter(p => instruments.includes(p.name)), seat, seatCanonical)
  if (own) return true
  const mine = seatCanonical || seat
  return !!mine && instruments.some(n => n === seat || seatReads(mine, n))
}
