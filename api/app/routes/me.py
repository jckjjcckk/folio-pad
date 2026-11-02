from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth import CurrentUser, load_user
from ..db import db
from ..spend import shared_spend
from ..tiers import model_name

router = APIRouter()


def account(user) -> dict:
    """The account, its libraries (own + each ensemble with role and seat), and what it may still spend."""
    rows = db().table("members").select("id,role,part,ensemble_id,ensembles(id,name)").eq("user_id", user.id).execute().data
    shared = shared_spend()
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "model_tier": user.model_tier,
        "model": model_name(user.model_tier),
        "memberships": [
            {"member_id": m["id"], "ensemble_id": m["ensemble_id"], "ensemble_name": (m.get("ensembles") or {}).get("name"), "role": m["role"], "part": m["part"]}
            for m in rows
        ],
        "budget": {
            "budget_usd": float(user.budget_usd), "spent_usd": float(user.spent_usd),
            "shared_cap_usd": float(shared.shared_cap), "shared_spent_usd": float(shared.shared_spent),
            "can_call_models": not user.over_budget and not shared.exhausted,
        },
    }


@router.get("/me")
def me(user: CurrentUser) -> dict:
    """The account, its libraries (own + each ensemble with role and seat), and what it may still spend."""
    return account(user)


class MeBody(BaseModel):
    """What a user may change on their own profile here: the Meta model tier their books and takes are read with.
    "standard": not used to train Meta models. "contributor": cheaper; Meta may use the content to train future models."""
    model_tier: Literal["standard", "contributor"]


@router.patch("/me")
def update_me(body: MeBody, user: CurrentUser) -> dict:
    """Set the caller's own model tier; the next model call of each of their jobs uses it. 503 when the database
    has no `profiles.model_tier` yet (migration 20261101090000 not applied)."""
    try:
        db().table("profiles").update({"model_tier": body.model_tier}).eq("id", user.id).execute()
    except Exception as e:  # noqa: BLE001  (PostgREST answers 400 for an unknown column)
        if "model_tier" in str(e):
            raise HTTPException(503, "Choosing a model tier is not available on this server yet") from e
        raise
    return account(load_user(user.id))
