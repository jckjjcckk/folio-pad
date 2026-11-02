"""Text and vision reasoning, Meta's Muse Spark only (hackathon rule: every model called at runtime is a Meta model).
Every call returns its cost so the caller can charge it.

Two Meta endpoints. Effort "minimal" goes to /v1/chat/completions (`chat`): Meta's Messages endpoint refuses it, and it
halves Spark's time on a page read (004-speed-eval) and a voice line (013-always-on). Every other effort goes to Meta's
Messages-compatible /v1/messages, through the `anthropic` Python SDK pointed at Meta's base URL (`_client`).

Two model tiers per profile (`profiles.model_tier`, `tiers.model_name`): "standard" (`META_MODEL`, e.g. muse-spark-1.3,
non-training) and "contributor" (the same name + "-contributor": cheaper, Meta may use the content to train future
models). The caller resolves the user's tier and passes the model; the charge records the model Meta reports.
"""
import asyncio
import json
import time
from dataclasses import dataclass, field
from decimal import Decimal

import httpx
from anthropic import AsyncAnthropic   # the SDK speaking Meta's Messages-compatible API (base URL is Meta's, see _client)

from .settings import settings
from .spend import Charge
from .tiers import TIERS, model_name, tier_of  # noqa: F401  (re-exported: callers say llm.model_name(tier))

# USD per 1M tokens, (input, output). Meta rates from dev.meta.ai pricing, verified 2026-10-27.
PRICES: dict[str, tuple[Decimal, Decimal]] = {
    "muse-spark-1.3": (Decimal("1.25"), Decimal("4.25")),
    "muse-spark-1.3-contributor": (Decimal("0.10"), Decimal("0.20")),
}
UNKNOWN_PRICE = (Decimal("5"), Decimal("25"))   # a model not listed is priced high, so spend is never undercounted


def price(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    p_in, p_out = PRICES.get(model, UNKNOWN_PRICE)
    return (p_in * input_tokens + p_out * output_tokens) / Decimal(1_000_000)


@dataclass(frozen=True)
class Completion:
    text: str
    charge: Charge
    api: str = "messages"            # "messages" | "chat"
    truncated: bool = False          # the reply stopped at the output budget
    seconds: float = 0.0
    first_token_s: float | None = None


CHAT_EFFORT = "minimal"
# One model call's ceiling, both endpoints (the SDK's default is 600 s). The longest Spark call measured is a 45 s page read;
# a Messages call that hung for 10 minutes stalled a convert in the speed pass (2026-10-30), so a stuck call is retried.
CALL_TIMEOUT_S = 180.0
CHAT_RETRY_S = 1.0
# Tests hand the chat branch a fake transport here (httpx.MockTransport); None is the network.
_chat_transport: httpx.AsyncBaseTransport | None = None


def uses_chat(effort: str) -> bool:
    return effort == CHAT_EFFORT


@dataclass
class ChatReply:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None = None
    cached_tokens: int = 0
    finish_reason: str | None = None
    seconds: float = 0.0
    first_token_s: float | None = None
    raw_usage: dict = field(default_factory=dict)


def chat_content(text: str, image_png_b64: str | None = None) -> str | list[dict]:
    if not image_png_b64:
        return text
    return [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_png_b64}"}}, {"type": "text", "text": text}]


async def chat(messages: list[dict], *, effort: str = CHAT_EFFORT, max_tokens: int = 4096, model: str | None = None,
               stream: bool = False, timeout: float = CALL_TIMEOUT_S) -> ChatReply:
    """One call on Meta's /v1/chat/completions, the request shape of the voice and page-read evals
    (`experiments/voice_stream/common.py`, `experiments/pageread_speed/common.py`): `reasoning_effort`,
    `max_completion_tokens` (Spark's reasoning counts against it, so at least 1024), usage as prompt/completion
    tokens. Streamed (SSE, usage in the last event) when `stream`. One retry on a transport error, 429 or 5xx."""
    model = model or settings.meta_model
    body: dict = {"model": model, "messages": messages, "reasoning_effort": effort,
                  "max_completion_tokens": max(max_tokens, 1024)}
    if stream:
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}
    url = settings.meta_api_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.meta_api_key}"}
    last: Exception | None = None
    for attempt in range(2):
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=_chat_transport) as c:
                if not stream:
                    r = await c.post(url, json=body, headers=headers)
                    if r.status_code != 200:
                        raise _ChatHTTP(r.status_code, r.text[:300])
                    d = r.json()
                    ch = (d.get("choices") or [{}])[0]
                    text = (ch.get("message") or {}).get("content") or ""
                    return _reply(text, d.get("model") or model, d.get("usage") or {}, ch.get("finish_reason"),
                                  time.monotonic() - t0, None)
                text, usage, finish, first = "", {}, None, None
                async with c.stream("POST", url, json=body, headers=headers) as r:
                    if r.status_code != 200:
                        raise _ChatHTTP(r.status_code, (await r.aread())[:300].decode("utf-8", "replace"))
                    got_model = model
                    async for line in r.aiter_lines():
                        if not line.startswith("data:") or line.strip() == "data: [DONE]":
                            continue
                        ev = json.loads(line[5:])
                        got_model = ev.get("model") or got_model
                        if ev.get("usage"):
                            usage = ev["usage"]
                        for chn in ev.get("choices") or []:
                            d = (chn.get("delta") or {}).get("content")
                            if d:
                                if first is None:
                                    first = time.monotonic() - t0
                                text += d
                            if chn.get("finish_reason"):
                                finish = chn["finish_reason"]
                return _reply(text, got_model, usage, finish, time.monotonic() - t0, first)
        except _ChatHTTP as e:
            last = e
            if not (e.status == 429 or e.status >= 500) or attempt:
                raise RuntimeError(f"chat completions HTTP {e.status}: {e.body!r}") from None
        except httpx.TransportError as e:
            last = e
            if attempt:
                raise
        await asyncio.sleep(CHAT_RETRY_S)
    raise RuntimeError(f"chat completions failed: {last}")


class _ChatHTTP(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(status)
        self.status, self.body = status, body


def _reply(text: str, model: str, u: dict, finish: str | None, secs: float, first: float | None) -> ChatReply:
    return ChatReply(text, model, int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0),
                     (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                     int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0), finish, secs, first, u)


def _client() -> AsyncAnthropic:
    """Meta's Messages-compatible endpoint through the `anthropic` SDK. The SDK appends /v1/messages itself;
    META_API_BASE_URL is written with its /v1 (as Meta documents it), so the /v1 is stripped here."""
    base = settings.meta_api_base_url.rstrip("/")
    base = base[:-3] if base.endswith("/v1") else base
    return AsyncAnthropic(api_key=settings.meta_api_key, base_url=base, max_retries=1, timeout=CALL_TIMEOUT_S)


def on_meta(client: object) -> bool:
    """True for a Messages client pointed at Meta's host (one `_client` made). `ask_model` sends effort "minimal" to
    chat completions only for such a client; a stand-in the tests inject (another base URL) keeps answering on Messages."""
    base = getattr(client, "base_url", None)
    try:
        return base is not None and httpx.URL(str(base)).host == httpx.URL(settings.meta_api_base_url).host
    except Exception:  # noqa: BLE001
        return False


async def complete(
    user_text: str, *, system: str | None = None, effort: str = "low", max_tokens: int = 4096,
    image_png_b64: str | None = None, model: str | None = None, stream: bool = False,
) -> Completion:
    """`model`: the Spark model for the user's tier (`model_name(tier)`); the standard model when not given.
    `effort="minimal"` goes to chat completions (`stream` applies there only); everything else is Messages."""
    model = model or model_name()
    if uses_chat(effort):
        msgs: list[dict] = [{"role": "system", "content": system}] if system else []
        msgs.append({"role": "user", "content": chat_content(user_text, image_png_b64)})
        r = await chat(msgs, effort=effort, max_tokens=max_tokens, model=model, stream=stream)
        cost = price(r.model, r.input_tokens, r.output_tokens)
        return Completion(r.text, Charge("meta", r.model, "spark", cost, r.input_tokens, r.output_tokens), "chat",
                          r.finish_reason == "length", r.seconds, r.first_token_s)
    t0 = time.monotonic()
    content: list[dict] = []
    if image_png_b64:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_png_b64}})
    content.append({"type": "text", "text": user_text})
    kwargs: dict = {
        "model": model, "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": content}],
    }
    if system:
        kwargs["system"] = system
    # Meta's /v1/messages takes output_config.effort (verified 2026-10-27: "low" cut Spark's reasoning from ~310 to
    # ~70 output tokens). Spark's reasoning counts against max_tokens, so give it room: a 64-token cap returned an
    # empty reply.
    kwargs["output_config"] = {"effort": effort}
    kwargs["max_tokens"] = max(max_tokens, 1024)
    res = await _client().messages.create(**kwargs)
    text = "".join(b.text for b in res.content if b.type == "text")
    usage = res.usage
    got = res.model or model
    cost = price(got, usage.input_tokens, usage.output_tokens)
    return Completion(text, Charge("meta", got, "spark", cost, usage.input_tokens, usage.output_tokens), "messages",
                      getattr(res, "stop_reason", None) == "max_tokens", time.monotonic() - t0)
