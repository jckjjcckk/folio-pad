"""Groups (feature 001) against the LOCAL Supabase stack: join codes and the create / join / leave / delete RPCs, and
since 2026-11-02 the API's join (`POST /ensembles/join`, with its guess limit) and delete-with-files
(`DELETE /ensembles/{id}`), run in-process with the API's database client pointed at the local stack.

Follows `scripts/smoke_local.py`: keys from `supabase status`, never `api/.env`, so this cannot touch the hosted
project. Three throwaway accounts (groups-a/b/c@muse.test, fresh password each run) are made with the service-role
client, which also sets up and checks rows; the RPCs are called as those people through the anon key, as the
browser calls them. Skipped when the stack is down or migration 20261028150000 is not applied.
"""
from __future__ import annotations

import json
import secrets
import subprocess
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth import User, current_user
from app.main import app
from app.routes import ensembles as ens

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "pytest groups"


def local_stack() -> dict | None:
    try:
        out = subprocess.run(["supabase", "status", "-o", "json"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        status = json.loads(out.stdout)
    except Exception:  # noqa: BLE001
        return None
    url = status.get("API_URL", "")
    if not any(h in url for h in ("127.0.0.1", "localhost")):
        return None
    try:
        httpx.get(f"{url}/rest/v1/", headers={"apikey": status["PUBLISHABLE_KEY"]}, timeout=3)
    except Exception:  # noqa: BLE001
        return None
    return status


STATUS = local_stack()
pytestmark = pytest.mark.skipif(STATUS is None, reason="local Supabase stack is not running (`supabase start`)")


@pytest.fixture(scope="module")
def stack():
    url, anon, secret = STATUS["API_URL"], STATUS["PUBLISHABLE_KEY"], STATUS["SECRET_KEY"]
    svc = httpx.Client(base_url=url, headers={"apikey": secret, "Authorization": f"Bearer {secret}"}, timeout=20)
    probe = svc.get("/rest/v1/ensembles", params={"select": "join_code", "limit": 1})
    if probe.status_code != 200:
        pytest.skip("migration 20261028150000 is not applied locally (`supabase migration up --local`)")
    password = secrets.token_urlsafe(12)
    existing = {u["email"]: u["id"] for u in svc.get("/auth/v1/admin/users", params={"per_page": 1000}).json()["users"]}
    ids, people = {}, {}
    for name in ("a", "b", "c"):
        email = f"groups-{name}@muse.test"
        if email in existing:
            ids[name] = existing[email]
            svc.put(f"/auth/v1/admin/users/{ids[name]}", json={"password": password}).raise_for_status()
        else:
            r = svc.post("/auth/v1/admin/users", json={"email": email, "password": password, "email_confirm": True})
            r.raise_for_status()
            ids[name] = r.json()["id"]
        r = httpx.post(f"{url}/auth/v1/token?grant_type=password", headers={"apikey": anon}, json={"email": email, "password": password})
        r.raise_for_status()
        people[name] = httpx.Client(base_url=url, headers={"apikey": anon, "Authorization": f"Bearer {r.json()['access_token']}"}, timeout=20)
    people["anon"] = httpx.Client(base_url=url, headers={"apikey": anon}, timeout=20)

    def cleanup():
        svc.delete("/rest/v1/ensembles", params={"name": f"like.{PREFIX}*"})
    cleanup()
    yield svc, people, ids
    cleanup()


@pytest.fixture
def api(stack, monkeypatch):
    """`api(who, method, path, ...)`: the API's group routes as one of the people, against the LOCAL stack only (the
    route's database client, settings and the signed-in user are all replaced; nothing reads api/.env)."""
    from supabase import create_client
    svc, people, ids = stack
    local = create_client(STATUS["API_URL"], STATUS["SECRET_KEY"])
    monkeypatch.setattr(ens, "db", lambda: local)
    monkeypatch.setattr(ens, "settings", SimpleNamespace(supabase_url=STATUS["API_URL"], supabase_secret_key=STATUS["SECRET_KEY"]))
    ens.user_limiter.reset()
    ens.ip_limiter.reset()
    who: dict[str, str] = {}
    app.dependency_overrides[current_user] = lambda: User(ids[who["name"]], None, None, Decimal("5"), Decimal("0"))
    client = TestClient(app)

    def call(name: str, method: str, path: str, **kw) -> httpx.Response:
        who["name"] = name
        return client.request(method, path, headers={"Authorization": people[name].headers["Authorization"]}, **kw)
    yield call
    app.dependency_overrides.clear()
    ens.user_limiter.reset()
    ens.ip_limiter.reset()


def join(api, name: str, code: str) -> httpx.Response:
    return api(name, "POST", "/ensembles/join", json={"code": code})


def api_refused(r: httpx.Response, hint: str) -> str:
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["hint"] == hint, r.text
    return r.json()["detail"]["message"]


def rpc(client: httpx.Client, fn: str, **args) -> httpx.Response:
    return client.post(f"/rest/v1/rpc/{fn}", json=args)


def members(svc: httpx.Client, ensemble: str) -> dict[str, str]:
    rows = svc.get("/rest/v1/members", params={"select": "user_id,role", "ensemble_id": f"eq.{ensemble}"}).json()
    return {r["user_id"]: r["role"] for r in rows}


def refused(r: httpx.Response, hint: str) -> str:
    assert r.status_code == 400, r.text
    body = r.json()
    assert body["hint"] == hint, body
    return body["message"]


def test_create_join_leave_delete(stack, api):
    svc, p, ids = stack
    # create: the caller becomes admin; the code is 8 digits and the admin can read it
    r = rpc(p["a"], "create_ensemble", name=f"  {PREFIX} quartet ")
    assert r.status_code == 200, r.text
    e = r.json()
    eid, code = e["id"], e["join_code"]
    assert e["name"] == f"{PREFIX} quartet" and len(code) == 8 and code.isdigit() and e["created_by"] == ids["a"]
    assert members(svc, eid) == {ids["a"]: "admin"}
    assert p["a"].get("/rest/v1/ensembles", params={"select": "join_code", "id": f"eq.{eid}"}).json() == [{"join_code": code}]
    assert p["c"].get("/rest/v1/ensembles", params={"select": "join_code", "id": f"eq.{eid}"}).json() == []      # a stranger sees nothing

    # join (through the API since 20261102120000): player, idempotent, spaces and a dash forgiven; a member reads the code
    r = join(api, "b", f"{code[:4]} {code[4:]}")
    assert r.status_code == 200 and r.json() == {"ensemble_id": eid}
    assert join(api, "b", f"{code[:4]}-{code[4:]}").json() == {"ensemble_id": eid}
    assert members(svc, eid) == {ids["a"]: "admin", ids["b"]: "player"}
    assert p["b"].get("/rest/v1/ensembles", params={"select": "join_code", "id": f"eq.{eid}"}).json() == [{"join_code": code}]
    assert join(api, "a", code).json() == {"ensemble_id": eid} and members(svc, eid)[ids["a"]] == "admin"   # an admin stays admin
    unknown = "00000000" if code != "00000000" else "00000001"
    assert api_refused(join(api, "c", unknown), "unknown_code") == f"No group has the code {unknown}. Check the digits with the group's admin."
    assert api_refused(join(api, "c", "1234"), "bad_code") == "A join code is 8 digits."
    assert ids["c"] not in members(svc, eid)
    # the direct path is closed: a signed-in person cannot call join_ensemble around the limit
    assert rpc(p["c"], "join_ensemble", code=code).status_code in (401, 403, 404)
    assert ids["c"] not in members(svc, eid)

    # leave: the last admin cannot, by the RPC or by deleting or demoting their own row directly
    assert refused(rpc(p["a"], "leave_ensemble", ensemble=eid), "last_admin").startswith("You are this group's only admin")
    r = p["a"].delete("/rest/v1/members", params={"ensemble_id": f"eq.{eid}", "user_id": f"eq.{ids['a']}"})
    assert r.status_code == 400 and r.json()["hint"] == "last_admin"
    r = p["a"].patch("/rest/v1/members", params={"ensemble_id": f"eq.{eid}", "user_id": f"eq.{ids['a']}"}, json={"role": "player"})
    assert r.status_code == 400 and r.json()["hint"] == "last_admin"
    assert members(svc, eid)[ids["a"]] == "admin"
    assert rpc(p["b"], "leave_ensemble", ensemble=eid).status_code in (200, 204)
    assert members(svc, eid) == {ids["a"]: "admin"}
    assert refused(rpc(p["b"], "leave_ensemble", ensemble=eid), "not_member") == "You are not in this group."
    # with a second admin, the first may leave
    join(api, "b", code)
    assert p["a"].patch("/rest/v1/members", params={"ensemble_id": f"eq.{eid}", "user_id": f"eq.{ids['b']}"}, json={"role": "admin"}).status_code in (200, 204)
    assert rpc(p["a"], "leave_ensemble", ensemble=eid).status_code in (200, 204)
    assert members(svc, eid) == {ids["b"]: "admin"}

    # delete: admin only; cascades through members and scores
    join(api, "c", code)
    score = svc.post("/rest/v1/scores", headers={"Prefer": "return=representation"},
                     json={"ensemble_id": eid, "title": f"{PREFIX} score", "created_by": ids["b"]}).json()[0]
    assert refused(rpc(p["c"], "delete_ensemble", ensemble=eid), "not_admin") == "Only an admin can delete this group."
    assert refused(rpc(p["a"], "delete_ensemble", ensemble=eid), "not_admin") == "Only an admin can delete this group."
    assert rpc(p["b"], "delete_ensemble", ensemble=eid).status_code in (200, 204)
    assert svc.get("/rest/v1/ensembles", params={"id": f"eq.{eid}"}).json() == []
    assert members(svc, eid) == {}
    assert svc.get("/rest/v1/scores", params={"id": f"eq.{score['id']}"}).json() == []
    assert refused(rpc(p["b"], "delete_ensemble", ensemble=eid), "not_found") == "This group no longer exists."


def test_names_signed_out_and_the_code_column(stack):
    svc, p, ids = stack
    assert refused(rpc(p["a"], "create_ensemble", name="   "), "bad_name") == "Give the group a name of up to 80 characters."
    assert refused(rpc(p["a"], "create_ensemble", name="x" * 81), "bad_name")
    assert rpc(p["anon"], "create_ensemble", name=f"{PREFIX} anon").status_code in (401, 403)      # execute revoked from anon
    assert rpc(p["anon"], "join_ensemble", code="12345678").status_code in (401, 403)
    # a direct insert (the old path, still allowed by ensembles_insert) gets a code from the column default
    r = p["a"].post("/rest/v1/ensembles", headers={"Prefer": "return=representation"}, json={"name": f"{PREFIX} direct", "created_by": ids["a"]})
    assert r.status_code == 201, r.text
    assert len(r.json()[0]["join_code"]) == 8 and r.json()[0]["join_code"].isdigit()
    # the check constraint and uniqueness
    r = svc.post("/rest/v1/ensembles", json={"name": f"{PREFIX} bad", "created_by": ids["a"], "join_code": "12ab5678"})
    assert r.status_code == 400 and "ensembles_join_code_check" in r.text
    r = svc.post("/rest/v1/ensembles", json={"name": f"{PREFIX} dup", "created_by": ids["a"], "join_code": r_code(svc)})
    assert r.status_code == 409 and "ensembles_join_code_key" in r.text
    # every ensemble has a well-formed code, the ones that existed before the migration included
    codes = [row["join_code"] for row in svc.get("/rest/v1/ensembles", params={"select": "join_code"}).json()]
    assert codes and all(len(c) == 8 and c.isdigit() for c in codes) and len(codes) == len(set(codes))


def r_code(svc: httpx.Client) -> str:
    return svc.get("/rest/v1/ensembles", params={"select": "join_code", "limit": 1}).json()[0]["join_code"]


def test_codes_are_spread_out(stack):
    svc, p, _ = stack
    codes = [rpc(p["c"], "create_ensemble", name=f"{PREFIX} spread {i}").json()["join_code"] for i in range(12)]
    assert len(set(codes)) == 12 and len({c[0] for c in codes}) > 3      # leading zeros kept, no fixed prefix


def test_join_guess_limit_on_the_local_stack(stack, api):
    svc, p, ids = stack
    e = rpc(p["a"], "create_ensemble", name=f"{PREFIX} limit").json()
    wrong = "00000000" if e["join_code"] != "00000000" else "00000001"
    for _ in range(10):
        assert join(api, "c", wrong).status_code == 400
    r = join(api, "c", e["join_code"])
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 500
    assert ids["c"] not in members(svc, e["id"])
    assert join(api, "b", e["join_code"]).status_code == 200          # another account is not held up


def test_delete_through_the_api_removes_the_groups_files(stack, api):
    """A group's own book's files go with the group; a personal book shared with it by reference keeps its files."""
    svc, p, ids = stack
    e = rpc(p["a"], "create_ensemble", name=f"{PREFIX} files").json()
    eid = e["id"]
    group_book = svc.post("/rest/v1/scores", headers={"Prefer": "return=representation"},
                          json={"ensemble_id": eid, "title": f"{PREFIX} group book", "created_by": ids["a"]}).json()[0]["id"]
    own_book = svc.post("/rest/v1/scores", headers={"Prefer": "return=representation"},
                        json={"owner_user_id": ids["a"], "title": f"{PREFIX} own book", "created_by": ids["a"]}).json()[0]["id"]
    for key in (f"{group_book}/source.pdf", f"{group_book}/pages/1.png", f"{own_book}/source.pdf"):
        r = svc.post(f"/storage/v1/object/scores/{key}", content=b"%PDF-1.4 test", headers={"Content-Type": "application/pdf", "x-upsert": "true"})
        assert r.status_code == 200, r.text
    assert rpc(p["a"], "share_score", score=own_book, ensemble=eid).status_code == 200

    def keys(prefix: str) -> set[str]:
        out = set()
        for it in svc.post("/storage/v1/object/list/scores", json={"prefix": prefix, "limit": 100}).json():
            if it.get("id") is None:
                out |= keys(f"{prefix}/{it['name']}")
            else:
                out.add(f"{prefix}/{it['name']}")
        return out
    try:
        assert join(api, "b", e["join_code"]).status_code == 200
        assert api("b", "DELETE", f"/ensembles/{eid}").json()["detail"]["hint"] == "not_admin"
        dry = api("a", "DELETE", f"/ensembles/{eid}", params={"dry_run": "true"}).json()
        assert set(dry["objects"]) == {f"{group_book}/source.pdf", f"{group_book}/pages/1.png"} and dry["shared_books_kept"] == 1
        assert keys(group_book) == set(dry["objects"])                  # the dry run removed nothing
        done = api("a", "DELETE", f"/ensembles/{eid}")
        assert done.status_code == 200, done.text
        assert done.json()["removed"] == 2 and done.json()["failed"] == []
        assert svc.get("/rest/v1/ensembles", params={"id": f"eq.{eid}"}).json() == []
        assert svc.get("/rest/v1/scores", params={"id": f"eq.{group_book}"}).json() == []
        assert keys(group_book) == set()
        assert keys(own_book) == {f"{own_book}/source.pdf"}            # shared by reference: the owner's file stays
        assert svc.get("/rest/v1/scores", params={"id": f"eq.{own_book}"}).json() != []
    finally:
        svc.delete("/rest/v1/scores", params={"id": f"eq.{own_book}"})
        svc.request("DELETE", "/storage/v1/object/scores", json={"prefixes": [f"{own_book}/source.pdf", f"{group_book}/source.pdf", f"{group_book}/pages/1.png"]})
