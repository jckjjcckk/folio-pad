# Folio API

FastAPI backend. Owns every call to the Meta Model API, OMR, and music21 processing, and holds all secrets.

```bash
cp .env.example .env   # fill in keys
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Docs at http://localhost:8000/docs once running.

## Layout

- `app/auth.py`: `CurrentUser` dependency. Verifies the Supabase session token (JWKS for hosted projects, Supabase Auth for the local stack's HS256 tokens), then loads the `profiles` row. No row = not on the list = 403.
- `app/spend.py`: `BudgetedUser` refuses with 402 when the user's budget or the shared cap is spent; `charge()` records a model call through the `charge_usage` function, which takes one row lock so concurrent calls cannot overspend.
- `app/llm.py`: `complete()` for text and vision reasoning, Meta's Muse Spark only: effort `minimal` on Meta's chat completions, every other effort on Meta's Messages-compatible endpoint (through the `anthropic` Python SDK pointed at Meta's base URL); returns the text and a `Charge` with the cost.
- `app/tiers.py`: the per-profile model tier (`profiles.model_tier`): `standard` uses `META_MODEL` (non-training), `contributor` uses `META_MODEL` + `-contributor` (cheaper; Meta may use the content to train future models). Voice Transcribe has no contributor variant and keeps its one name.
- `app/routes/me.py`: `GET /me`, the account (with its `model_tier`), its memberships and what it may still spend; `PATCH /me` sets the caller's own `model_tier`.
- `app/routes/llm.py`: `POST /llm/probe`, the smallest model call, to prove the chain end to end.

## Database

Schema and policies live in `../supabase/migrations/`. Locally:

```bash
supabase start                 # Docker; applies the migrations
uv run scripts/smoke_local.py  # creates the five demo users locally and checks RLS, storage, jobs, spend, /me, 401/403/402
```

Hosted: `supabase link --project-ref <ref>` once (asks for the database password), then `supabase db push`.
