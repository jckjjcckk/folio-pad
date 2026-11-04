"""One Supabase client with the secret key. It bypasses RLS: every write it makes is the API's responsibility.

The client lives for the whole process (`lru_cache`), and so do the two connection pools under it: PostgREST's and
Storage's, each an httpx client over HTTP/2 with httpx's default pool limits (an idle connection is dropped after
5 s, `keepalive_expiry`). Nothing in supabase-py, postgrest or storage3 retries a request that dies on the wire
(postgrest retries only a 503 or 520 answer to a GET), so a connection the far end has already closed, as after the
stable box lost power on 2026-11-03, surfaced as a 500 (`httpx.RemoteProtocolError: Server disconnected`) although
the same request succeeded when sent again. `_RetryOnce` sends such a request once more: the pool has discarded the
dead connection by then, so the second attempt goes out on a live or fresh one.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import httpx
from supabase import Client

from .settings import settings

log = logging.getLogger("folio.db")

# A read can be sent again whatever went wrong on the wire.
READS = frozenset({"GET", "HEAD", "OPTIONS"})
READ_RETRY = (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadError)
# A write is sent again only when no answer came back at all: the connection never opened (ConnectError), or the
# server closed it before any response (RemoteProtocolError, "Server disconnected"). A ReadError on a write may
# come after the server acted on it, so it is not retried.
WRITE_RETRY = (httpx.RemoteProtocolError, httpx.ConnectError)


class _RetryOnce(httpx.BaseTransport):
    """Wraps a client's transport: a request that fails before any response is sent once more. The transport returns
    as soon as the status line and headers arrive, so an error raised here never follows a response."""

    def __init__(self, inner: httpx.BaseTransport):
        self.inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return self.inner.handle_request(request)
        except READ_RETRY as e:
            if not isinstance(e, READ_RETRY if request.method in READS else WRITE_RETRY):
                raise
            log.warning("supabase %s %s: %s: %s; sending it once more", request.method, request.url.path,
                        type(e).__name__, e)
            try:
                return self.inner.handle_request(request)
            except httpx.StreamConsumed:
                raise e from None  # a streamed body cannot be sent twice; report the first failure

    def close(self) -> None:
        self.inner.close()


def _harden(session: httpx.Client) -> None:
    """Puts `_RetryOnce` around every transport the httpx client routes through (its own, and any proxy mounts)."""
    if not isinstance(session._transport, _RetryOnce):
        session._transport = _RetryOnce(session._transport)
    for pattern, transport in list(session._mounts.items()):
        if transport is not None and not isinstance(transport, _RetryOnce):
            session._mounts[pattern] = _RetryOnce(transport)


class _Client(Client):
    """supabase-py builds its PostgREST and Storage clients lazily, and builds them again after an auth event, so the
    retry is put on each one as it is handed out."""

    @property
    def postgrest(self):
        pg = super().postgrest
        _harden(pg.session)
        return pg

    @property
    def storage(self):
        st = super().storage
        _harden(st.session)
        return st


@lru_cache(maxsize=1)
def db() -> Client:
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set in api/.env")
    return _Client.create(settings.supabase_url, settings.supabase_secret_key)
