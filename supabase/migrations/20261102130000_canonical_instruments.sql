-- Seats and parts matched on one canonical instrument name (008, 010; CK 2026-11-02, E2E night item 1).
-- Written for the local stack; NOT applied to hosted (the orchestrator decides when to `db push`).
--
-- A group's seat says "Violin II"; a book's part carries what the edition prints ("Violino II", "Vln. 2", "2nd
-- Violins"). Until now the stand and the marks' policy matched the two by exact name, so the second violin saw no part
-- and none of the marks addressed to it (E2E night, PC3 and PC5). Both sides now carry the one English name the API's
-- normaliser gives (`api/app/librarian/instruments.py`, `canonical_instrument`): `parts.canonical` written at import
-- and cut, `members.part_canonical` written where a seat is set. The printed name stays `parts.name`, the seat as typed
-- stays `members.part`; the match is on the canonical names, and nothing about it shows during practice.
--
-- A seat reads a part when the canonical names are equal, or the part is a shared staff that names the seat ("Cello"
-- reads "Cello & Double Bass", the normaliser's form for "Violoncello e Contrabasso"). A row without its canonical
-- name (written before this migration, renamed by hand) falls back to its own name, so the exact match of before
-- still holds everywhere. After applying, fill the existing rows with
--   cd api && uv run python scripts/backfill_canonical_instruments.py --apply
-- (dry run without --apply). The SQL here never computes a canonical name itself: the normaliser lives in one place.

alter table public.parts   add column if not exists canonical text;
alter table public.members add column if not exists part_canonical text;

-- A part or seat renamed without its canonical name drops the stale one, and falls back to its own name until the
-- API writes the new one.
create or replace function public.drop_stale_canonical() returns trigger
language plpgsql set search_path = public as $$
begin
  if tg_table_name = 'parts' then
    if new.name is distinct from old.name and new.canonical is not distinct from old.canonical then
      new.canonical := null;
    end if;
  elsif new.part is distinct from old.part and new.part_canonical is not distinct from old.part_canonical then
    new.part_canonical := null;
  end if;
  return new;
end $$;

drop trigger if exists parts_canonical_stale on public.parts;
create trigger parts_canonical_stale before update of name on public.parts
  for each row execute function public.drop_stale_canonical();
drop trigger if exists members_canonical_stale on public.members;
create trigger members_canonical_stale before update of part on public.members
  for each row execute function public.drop_stale_canonical();

-- The caller's seat in group e, by its canonical name (else as typed).
create or replace function public.my_seat(e uuid) returns text
language sql stable security definer set search_path = public as $$
  select coalesce(part_canonical, part) from members where ensemble_id = e and user_id = auth.uid();
$$;

-- The canonical name of the part called p on book s (else p itself).
create or replace function public.part_canonical_of(s uuid, p text) returns text
language sql stable security definer set search_path = public as $$
  select coalesce((select canonical from parts where score_id = s and name = p limit 1), p);
$$;

-- Does a seat read a part? Same canonical name, or a shared staff (" & ") that names the seat.
create or replace function public.seat_reads(seat text, part text) returns boolean
language sql immutable set search_path = public as $$
  select seat is not null and part is not null and seat <> '' and (seat = part or seat = any(string_to_array(part, ' & ')));
$$;

-- Who sees a mark (20261028200000, unchanged but for the part clause): its author always; whoever leads its layer;
-- anyone who reads the layer when the mark is live and addressed to the layer's group, to a part their seat reads, or
-- to them.
create or replace function public.can_see_annotation(a public.annotations) returns boolean
language sql stable security definer set search_path = public as $$
  select a.author_id = auth.uid()
      or can_lead_layer(a.score_id, a.ensemble_id)
      or (a.status = 'live' and can_read_layer(a.score_id, a.ensemble_id) and (
            a.audience = 'ensemble'
         or (a.audience = 'part'   and (a.audience_part = my_part(mark_group(a.score_id, a.ensemble_id))
                                        or seat_reads(my_seat(mark_group(a.score_id, a.ensemble_id)),
                                                      part_canonical_of(a.score_id, a.audience_part))))
         or (a.audience = 'member' and a.audience_member_id = my_member_id(mark_group(a.score_id, a.ensemble_id)))
      ));
$$;
