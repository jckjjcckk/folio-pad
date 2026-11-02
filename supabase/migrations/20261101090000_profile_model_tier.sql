-- Per-profile Meta model tier (2026-11-01).
--   'standard'    : META_MODEL (e.g. muse-spark-1.3). Meta does not use the content to train its models.
--   'contributor' : META_MODEL || '-contributor' (e.g. muse-spark-1.3-contributor). Cheaper; Meta may use the content
--                   to train future models.
-- The default keeps the published promise ("non-training tier"): nobody is moved to contributor without choosing it.
-- The API reads it per job with the service role (app/librarian JobContext.model_tier) and treats an absent column or
-- any other value as 'standard', so the API runs before and after this migration.

alter table public.profiles
  add column if not exists model_tier text not null default 'standard'
  check (model_tier in ('standard', 'contributor'));

-- Until now profiles had no update policy: budget and spend are written by the dashboard and the service role only.
-- The API's PATCH /me sets model_tier with the service role. This also lets the browser change its own tier directly,
-- and nothing else: the table-wide UPDATE grant is replaced by a grant on model_tier alone, so a user can never touch
-- budget_usd, spent_usd, email or display_name through PostgREST.
revoke update on public.profiles from anon, authenticated;
grant update (model_tier) on public.profiles to authenticated;

drop policy if exists profiles_update_own_tier on public.profiles;
create policy profiles_update_own_tier on public.profiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid());
