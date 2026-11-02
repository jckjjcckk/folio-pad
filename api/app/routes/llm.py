from fastapi import APIRouter
from pydantic import BaseModel

from ..llm import complete
from ..spend import BudgetedUser, charge

router = APIRouter()


class Probe(BaseModel):
    text: str = "Reply with the single word: ok"


@router.post("/llm/probe")
async def probe(body: Probe, user: BudgetedUser) -> dict:
    """The smallest possible model call, to prove the chain: token → profile → budget → tier → Spark → charge."""
    c = await complete(body.text, effort="low", max_tokens=64, model=user.model)
    totals = charge(user, c.charge)
    return {"provider": "meta", "model": c.charge.model, "model_tier": user.model_tier, "text": c.text,
            "cost_usd": float(c.charge.cost_usd), "totals": totals}
