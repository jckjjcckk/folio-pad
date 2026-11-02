-- Join codes get a guess limit (001, docs/backlog.md, 2026-11-02).
--
-- An 8-digit code is all it takes to join a group, and `join_ensemble` could be called from the browser as often as
-- Supabase's own rate limits allow. Joining now goes through the API (`POST /ensembles/join`, api/app/routes/
-- ensembles.py), which counts wrong codes per account (10 in 10 minutes) and per address (30 in 10 minutes) and
-- answers 429 with Retry-After at the limit. The API joins with the service role, following join_ensemble's steps and
-- sentences. This migration closes the direct path, so the limit cannot be stepped round: signed-in people may no
-- longer execute `join_ensemble`. The function stays for the service role and the dashboard.
--
-- Apply only after the API that serves `POST /ensembles/join` is running (yoga) and the web app that calls it is
-- deployed: until then the browser still joins through this RPC. The web app falls back to the RPC only when the API
-- answers 404 (an API without the route).

revoke execute on function public.join_ensemble(text) from authenticated;
