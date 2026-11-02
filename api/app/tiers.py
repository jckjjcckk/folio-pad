"""Meta's two model tiers, chosen per profile (`profiles.model_tier`, migration 20261101090000).

"standard": `META_MODEL` (e.g. muse-spark-1.3, $1.25/$4.25 per M tokens), content not used for training.
"contributor": the same name + "-contributor" (e.g. muse-spark-1.3-contributor, $0.10/$0.20); Meta may use the
content to train future models. Voice Transcribe has no contributor variant (model list checked 2026-11-01), so it
stays on its one name whatever the tier.

No imports from the rest of the app but settings, so auth, llm and the handlers can all use it.
"""
from .settings import settings

TIERS = ("standard", "contributor")
DEFAULT_TIER = "standard"
CONTRIBUTOR_SUFFIX = "-contributor"


def tier_of(value: object) -> str:
    """A profile's `model_tier`, read safely: anything but "contributor" (absent column, null, a typo) is standard."""
    return "contributor" if value == "contributor" else DEFAULT_TIER


def model_name(tier: str | None = None) -> str:
    """The Spark model for a tier: `META_MODEL` for standard, the same name + "-contributor" for contributor."""
    base = settings.meta_model
    if tier_of(tier) == "contributor" and not base.endswith(CONTRIBUTOR_SUFFIX):
        return base + CONTRIBUTOR_SUFFIX
    return base
