"""Groups through the API (001, 2026-11-02): the join-code guess limit and deleting a group with its files. Fakes only:
no network, no Supabase."""
from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from app.auth import User, current_user
from app.main import app
from app.routes import ensembles as ens
from app.routes.ensembles import AttemptLimiter, group_files, list_folder, remove_objects


# ---------------------------------------------------------------- fakes

class Q:
    def __init__(self, db: "DB", table: str):
        self.db, self.table, self.filters, self.op, self.row, self.kw = db, table, [], "select", None, {}

    def select(self, *_a, **_k): return self
    def eq(self, k, v): self.filters.append((k, v)); return self
    def limit(self, _n): return self
    def upsert(self, row, **kw): self.op, self.row, self.kw = "upsert", row, kw; return self

    def execute(self):
        rows = self.db.rows.setdefault(self.table, [])
        if self.op == "upsert":
            keys = self.kw["on_conflict"].split(",")
            same = [r for r in rows if all(r[k] == self.row[k] for k in keys)]
            if same and self.kw.get("ignore_duplicates"):
                return type("R", (), {"data": []})
            for r in same:
                rows.remove(r)
            rows.append(dict(self.row))
            return type("R", (), {"data": [self.row]})
        return type("R", (), {"data": [r for r in rows if all(r.get(k) == v for k, v in self.filters)]})


class Bucket:
    def __init__(self, store: "Storage"):
        self.store = store

    def list(self, prefix, opts):
        """One level under `prefix`, folders without an id, as Storage answers; paged by limit/offset."""
        seen: dict[str, dict] = {}
        for key in sorted(self.store.keys):
            if not key.startswith(prefix + "/"):
                continue
            head, _, rest = key[len(prefix) + 1:].partition("/")
            seen.setdefault(head, {"name": head, "id": None} if rest else {"name": head, "id": str(uuid.uuid4())})
        items = sorted(seen.values(), key=lambda i: i["name"])
        self.store.list_calls += 1
        return items[opts["offset"]:opts["offset"] + opts["limit"]]

    def remove(self, paths):
        if self.store.fail_on and any(self.store.fail_on in p for p in paths):
            raise RuntimeError("storage said no")
        self.store.removed_calls.append(list(paths))
        self.store.keys -= set(paths)
        return [{"name": p} for p in paths]


class Storage:
    def __init__(self, keys):
        self.keys, self.removed_calls, self.list_calls, self.fail_on = set(keys), [], 0, None

    def from_(self, bucket):
        assert bucket == "scores"
        return Bucket(self)


class DB:
    def __init__(self, storage: Storage | None = None):
        self.rows: dict[str, list[dict]] = {}
        self.storage = storage or Storage([])

    def table(self, name):
        return Q(self, name)


G, OTHER = "g0000000-0000-0000-0000-000000000001", "g0000000-0000-0000-0000-000000000002"
B1, B2, MINE, ELSE = "b1", "b2", "personal-shared", "other-group-book"
CODE = "12345678"


def world() -> DB:
    st = Storage([
        f"{B1}/source.pdf", f"{B1}/pages/1.png", f"{B1}/pages/2.png", f"{B1}/parts/piano/p001-s1.png",
        f"{B2}/source.musicxml", f"{B2}/engraved/ipad/1.svg",
        f"{MINE}/source.pdf", f"{MINE}/pages/1.png",          # a personal book shared with G by reference: stays
        f"{ELSE}/source.pdf",                                  # another group's book: stays
        f"{B1}x/source.pdf",                                   # a key that only starts like B1's folder: stays
    ])
    db = DB(st)
    db.rows["ensembles"] = [{"id": G, "join_code": CODE}, {"id": OTHER, "join_code": "87654321"}]
    db.rows["members"] = [{"ensemble_id": G, "user_id": "admin", "role": "admin"}, {"ensemble_id": G, "user_id": "player", "role": "player"}]
    db.rows["scores"] = [{"id": B1, "title": "Op. 18", "ensemble_id": G}, {"id": B2, "title": "Goldberg", "ensemble_id": G},
                         {"id": MINE, "title": "Mine", "ensemble_id": None}, {"id": ELSE, "title": "Else", "ensemble_id": OTHER},
                         {"id": f"{B1}x", "title": "Lookalike", "ensemble_id": OTHER}]
    db.rows["score_shares"] = [{"score_id": MINE, "ensemble_id": G}]
    return db


@pytest.fixture
def api(monkeypatch):
    db = world()
    monkeypatch.setattr(ens, "db", lambda: db)
    ens.user_limiter.reset()
    ens.ip_limiter.reset()
    who = {"id": "stranger"}
    app.dependency_overrides[current_user] = lambda: User(who["id"], None, None, Decimal("5"), Decimal("0"))
    client = TestClient(app, headers={"Authorization": "Bearer t"})

    def as_(user_id: str) -> TestClient:
        who["id"] = user_id
        return client
    yield db, as_
    app.dependency_overrides.clear()
    ens.user_limiter.reset()
    ens.ip_limiter.reset()


# ---------------------------------------------------------------- the limiter

def test_limiter_slides_and_counts_only_hits():
    now = [1000.0]
    lim = AttemptLimiter(limit=3, window=600, clock=lambda: now[0])
    for _ in range(3):
        assert lim.retry_after(["k"]) == 0
        lim.hit(["k"])
        now[0] += 10
    assert 570 < lim.retry_after(["k"]) <= 581        # the first hit (t=1000) leaves at t=1600; now is 1030
    assert lim.retry_after(["other"]) == 0
    now[0] = 1600.5
    assert lim.retry_after(["k"]) == 0                 # the oldest left the window: one more try
    lim.hit(["k"])
    assert lim.retry_after(["k"]) > 0


# ---------------------------------------------------------------- join

def test_join_as_player_idempotent_forgiving(api):
    db, as_ = api
    r = as_("stranger").post("/ensembles/join", json={"code": "1234 5678"})
    assert r.status_code == 200 and r.json() == {"ensemble_id": G}
    assert as_("stranger").post("/ensembles/join", json={"code": "1234-5678"}).json() == {"ensemble_id": G}
    rows = [m for m in db.rows["members"] if m["user_id"] == "stranger"]
    assert rows == [{"ensemble_id": G, "user_id": "stranger", "role": "player"}]
    assert as_("admin").post("/ensembles/join", json={"code": CODE}).status_code == 200
    assert [m["role"] for m in db.rows["members"] if m["user_id"] == "admin"] == ["admin"]     # an admin stays admin


def test_join_refusals_carry_the_rpc_sentences(api):
    _, as_ = api
    r = as_("stranger").post("/ensembles/join", json={"code": "1234"})
    assert r.status_code == 400 and r.json()["detail"] == {"message": "A join code is 8 digits.", "hint": "bad_code"}
    r = as_("stranger").post("/ensembles/join", json={"code": "00000000"})
    assert r.status_code == 400 and r.json()["detail"]["hint"] == "unknown_code"
    assert r.json()["detail"]["message"] == "No group has the code 00000000. Check the digits with the group's admin."


def test_ten_wrong_codes_lock_the_account(api):
    db, as_ = api
    c = as_("stranger")
    for i in range(10):
        assert c.post("/ensembles/join", json={"code": f"0000000{i}"}).status_code == 400
    r = c.post("/ensembles/join", json={"code": CODE})                      # even the right code waits now
    assert r.status_code == 429 and r.json()["detail"]["hint"] == "too_many_attempts"
    assert 590 <= int(r.headers["Retry-After"]) <= 601
    assert "Wait 10 minutes" in r.json()["detail"]["message"]
    assert not [m for m in db.rows["members"] if m["user_id"] == "stranger"]
    # another account on another address is not held up
    assert as_("player2").post("/ensembles/join", json={"code": CODE}, headers={"cf-connecting-ip": "203.0.113.9"}).status_code == 200


def test_right_codes_never_count(api):
    _, as_ = api
    for _ in range(25):
        assert as_("stranger").post("/ensembles/join", json={"code": CODE}).status_code == 200


def test_thirty_wrong_codes_lock_the_address(api):
    _, as_ = api
    ip = {"cf-connecting-ip": "198.51.100.7"}
    for n in range(30):                                    # three accounts, ten misses each, one address
        r = as_(f"guesser{n // 10}").post("/ensembles/join", json={"code": f"{n:08d}"}, headers=ip)
        assert r.status_code in (400, 429)
    r = as_("newcomer").post("/ensembles/join", json={"code": CODE}, headers=ip)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) > 0
    assert as_("newcomer").post("/ensembles/join", json={"code": CODE}, headers={"cf-connecting-ip": "198.51.100.8"}).status_code == 200


def test_client_ip_prefers_cloudflare_then_first_forwarded_hop():
    from starlette.requests import Request

    def req(headers):
        return Request({"type": "http", "headers": [(k.encode(), v.encode()) for k, v in headers.items()], "client": ("10.0.0.5", 1)})
    assert ens.client_ip(req({"cf-connecting-ip": "1.2.3.4", "x-forwarded-for": "5.6.7.8"})) == "1.2.3.4"
    assert ens.client_ip(req({"x-forwarded-for": "5.6.7.8, 10.0.0.1"})) == "5.6.7.8"
    assert ens.client_ip(req({})) == "10.0.0.5"


# ---------------------------------------------------------------- delete with the files

GROUP_FILES = {f"{B1}/source.pdf", f"{B1}/pages/1.png", f"{B1}/pages/2.png", f"{B1}/parts/piano/p001-s1.png",
               f"{B2}/source.musicxml", f"{B2}/engraved/ipad/1.svg"}


def test_group_files_lists_only_the_groups_own_books():
    db = world()
    plan = group_files(db, G)
    assert set(plan["objects"]) == GROUP_FILES and len(plan["objects"]) == 6
    assert [b["id"] for b in plan["books"]] == [B1, B2] and plan["shared_books_kept"] == 1


def test_list_folder_pages_past_a_thousand():
    st = Storage([f"s/pages/{i:04d}.png" for i in range(2300)] + ["s/source.pdf"])
    keys = list_folder(st, "s")
    assert len(keys) == 2301 and len(set(keys)) == 2301


def test_remove_objects_chunks_and_reports_failures():
    st = Storage([f"s/{i}" for i in range(250)])
    st.fail_on = "s/1"            # a chunk holding a key that starts "s/1" fails: the first two of three
    removed, failed = remove_objects(st, sorted(st.keys, key=lambda k: int(k[2:])), chunk=100)
    assert [len(c) for c in st.removed_calls] == [50] and removed == 50 and len(failed) == 200


def test_dry_run_deletes_nothing(api, monkeypatch):
    db, as_ = api
    monkeypatch.setattr(ens, "rpc_as_user", lambda *a: pytest.fail("a dry run never calls the RPC"))
    before = set(db.storage.keys)
    r = as_("admin").delete(f"/ensembles/{G}", params={"dry_run": "true"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is True and set(body["objects"]) == GROUP_FILES and body["shared_books_kept"] == 1
    assert "removed" not in body and db.storage.keys == before


def test_delete_removes_the_group_files_and_keeps_shared_books(api, monkeypatch):
    db, as_ = api
    calls = []

    def rpc(token, name, args):
        calls.append((token, name, args))
        db.rows["ensembles"] = [e for e in db.rows["ensembles"] if e["id"] != args["ensemble"]]
        return httpx.Response(204)
    monkeypatch.setattr(ens, "rpc_as_user", rpc)
    r = as_("admin").delete(f"/ensembles/{G}")
    assert r.status_code == 200, r.text
    assert calls == [("t", "delete_ensemble", {"ensemble": G})]           # as the caller, with their token
    assert r.json()["removed"] == 6 and r.json()["failed"] == []
    assert db.storage.keys == {f"{MINE}/source.pdf", f"{MINE}/pages/1.png", f"{ELSE}/source.pdf", f"{B1}x/source.pdf"}


def test_delete_refusals_touch_no_file(api, monkeypatch):
    db, as_ = api
    before = set(db.storage.keys)
    assert as_("player").delete(f"/ensembles/{G}").json()["detail"]["hint"] == "not_admin"
    assert as_("player").delete(f"/ensembles/{G}", params={"dry_run": "true"}).status_code == 403
    assert as_("stranger").delete(f"/ensembles/{G}").status_code == 403
    assert as_("admin").delete("/ensembles/nope").status_code == 404
    # the RPC has the last word: a refusal there leaves every file
    monkeypatch.setattr(ens, "rpc_as_user", lambda *a: httpx.Response(
        400, json={"message": "Only an admin can delete this group.", "hint": "not_admin"}, headers={"content-type": "application/json"}))
    r = as_("admin").delete(f"/ensembles/{G}")
    assert r.status_code == 403 and r.json()["detail"]["message"] == "Only an admin can delete this group."
    assert db.storage.keys == before
