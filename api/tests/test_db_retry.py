"""A Supabase call that dies on a dead keep-alive connection is sent once more (app/db.py, the 2026-11-03 500s:
`httpx.RemoteProtocolError: Server disconnected` after the stable box lost power). An httpx MockTransport stands in
for the network under the real supabase-py client, so the whole chain (postgrest / storage3 -> httpx) is exercised."""
import json

import httpx
import pytest

from app.db import _Client, _RetryOnce


def client_over(handler) -> _Client:
    c = _Client.create("http://supabase.test", "sb_secret_test")
    for session in (c.postgrest.session, c.storage.session):
        assert isinstance(session._transport, _RetryOnce)
        session._transport.inner = httpx.MockTransport(handler)
    return c


def flaky(error: type[httpx.TransportError], answer, failures: int = 1):
    """A network that fails the first `failures` requests with `error`, then answers."""
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        if len(sent) <= failures:
            raise error("Server disconnected", request=request)
        return answer(request)
    return handler, sent


def rows(request):
    return httpx.Response(200, json=[{"id": "b1", "title": "Dvořák 8"}])


def test_a_read_after_a_server_disconnect_is_sent_again_and_succeeds():
    handler, sent = flaky(httpx.RemoteProtocolError, rows)
    data = client_over(handler).table("books").select("*").eq("id", "b1").execute().data
    assert data == [{"id": "b1", "title": "Dvořák 8"}]
    assert [r.method for r in sent] == ["GET", "GET"]
    assert sent[0].url == sent[1].url


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadError])
def test_a_read_is_sent_again_after_a_connect_or_read_error(error):
    handler, sent = flaky(error, rows)
    assert client_over(handler).table("books").select("*").execute().data[0]["id"] == "b1"
    assert len(sent) == 2


def test_a_write_the_server_never_answered_is_sent_again_with_the_same_body():
    handler, sent = flaky(httpx.RemoteProtocolError, lambda r: httpx.Response(201, json=[json.loads(r.content)]))
    data = client_over(handler).table("books").insert({"id": "b2", "title": "Ma vlast"}).execute().data
    assert data == [{"id": "b2", "title": "Ma vlast"}]
    assert [r.method for r in sent] == ["POST", "POST"]
    assert sent[0].content == sent[1].content


def test_a_write_that_failed_reading_the_answer_is_not_sent_again():
    handler, sent = flaky(httpx.ReadError, rows)
    with pytest.raises(httpx.ReadError):
        client_over(handler).table("books").update({"title": "x"}).eq("id", "b1").execute()
    assert len(sent) == 1


def test_only_one_retry():
    handler, sent = flaky(httpx.RemoteProtocolError, rows, failures=5)
    with pytest.raises(httpx.RemoteProtocolError):
        client_over(handler).table("books").select("*").execute()
    assert len(sent) == 2


def test_a_storage_download_is_sent_again():
    handler, sent = flaky(httpx.RemoteProtocolError, lambda r: httpx.Response(200, content=b"%PDF-1.7"))
    assert client_over(handler).storage.from_("scores").download("b1/page-1.pdf") == b"%PDF-1.7"
    assert len(sent) == 2


def test_a_storage_upload_the_server_never_answered_is_sent_again():
    handler, sent = flaky(httpx.RemoteProtocolError, lambda r: httpx.Response(200, json={"Key": "scores/b1/p.pdf"}))
    client_over(handler).storage.from_("scores").upload("b1/p.pdf", b"%PDF-1.7", {"content-type": "application/pdf"})
    assert [r.method for r in sent] == ["POST", "POST"]
    assert b"%PDF-1.7" in sent[1].content and sent[0].content == sent[1].content
