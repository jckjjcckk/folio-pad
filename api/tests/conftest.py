"""The suite never reaches the OMR box: the engraving step (MuseScore over ssh) is switched off unless a test hands a
handler its own engraver (`engraver=FakeEngraver()` in test_engrave.py)."""
import os

import pytest


@pytest.fixture(autouse=True)
def _no_box(monkeypatch):
    if "ENGRAVE" not in os.environ:
        monkeypatch.setenv("ENGRAVE", "off")


@pytest.fixture(autouse=True)
def _no_printed_read(monkeypatch):
    """Page reading's printed-bar-number check (one more Spark call per page, `bar_numbers`) is off: the tests that
    script the label calls by index do not script it. `test_bar_numbers.py` turns it on."""
    from app.librarian import process_pages
    monkeypatch.setattr(process_pages, "READ_PRINTED", False)


@pytest.fixture(autouse=True)
def _no_chat_network(monkeypatch):
    """The chat-completions branch (effort minimal) never reaches Meta from a test: a test that wants it hands
    `llm._chat_transport` its own fake transport."""
    import httpx

    from app import llm

    def refuse(req):
        raise RuntimeError(f"a test reached the network: {req.url}")
    monkeypatch.setattr(llm, "_chat_transport", httpx.MockTransport(refuse))


@pytest.fixture(autouse=True)
def _no_realtime_network(monkeypatch):
    """The worker's Realtime wake (app/wake.py) never opens a socket from a test: a test hands `Wake` its own fake
    `connect`."""
    import websockets.asyncio.client as ws_client

    def refuse(*a, **kw):
        raise RuntimeError("a test reached the network: a websocket")
    monkeypatch.setattr(ws_client, "connect", refuse)
