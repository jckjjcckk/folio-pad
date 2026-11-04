"""DELETE /scores/{score_id}: one book and its files, with Storage and the tables faked (nothing reaches Supabase)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.auth import User, current_user
from app.main import app
from app.routes import scores as scores_routes


# ---------------------------------------------------------------- fakes

class Q:
    def __init__(self, db: "DB", table: str):
        self.db, self.table, self.filters, self.op = db, table, [], "select"

    def select(self, *_a, **_k): return self
    def eq(self, k, v): self.filters.append((k, lambda r, k=k, v=v: r.get(k) == v)); return self
    def in_(self, k, vs): self.filters.append((k, lambda r, k=k, vs=vs: r.get(k) in vs)); return self
    def limit(self, _n): return self
    def delete(self): self.op = "delete"; return self

    def execute(self):
        rows = self.db.rows.setdefault(self.table, [])
        hit = [r for r in rows if all(f(r) for _, f in self.filters)]
        if self.op == "delete":
            self.db.deleted.append((self.table, [r["id"] for r in hit]))
            self.db.rows[self.table] = [r for r in rows if r not in hit]
        return type("R", (), {"data": hit})


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
        return items[opts["offset"]:opts["offset"] + opts["limit"]]

    def remove(self, paths):
        if self.store.fail_on and any(self.store.fail_on in p for p in paths):
            raise RuntimeError("storage said no")
        self.store.removed_calls.append(list(paths))
        self.store.keys -= set(paths)
        return [{"name": p} for p in paths]


class Storage:
    def __init__(self, keys):
        self.keys, self.removed_calls, self.fail_on = set(keys), [], None

    def from_(self, bucket):
        assert bucket == "scores"
        return Bucket(self)


class DB:
    def __init__(self, storage: Storage):
        self.rows: dict[str, list[dict]] = {}
        self.deleted: list[tuple[str, list[str]]] = []
        self.storage = storage

    def table(self, name):
        return Q(self, name)


G = "g0000000-0000-0000-0000-000000000001"
MINE, GROUPS, OTHER = "s-mine", "s-group", "s-other"
MINE_FILES = {f"{MINE}/source.pdf", f"{MINE}/pages/1.png", f"{MINE}/pages/2.png", f"{MINE}/digital/score.musicxml",
              f"{MINE}/parts/violin-i/p001-s1.png", f"{MINE}/voice/u1.wav", f"{MINE}/playback/score.mid"}


def world() -> DB:
    st = Storage(MINE_FILES | {f"{GROUPS}/source.pdf", f"{GROUPS}/pages/1.png", f"{OTHER}/source.pdf",
                               f"{MINE}x/source.pdf"})   # a key that only starts like MINE's folder: stays
    db = DB(st)
    db.rows["scores"] = [{"id": MINE, "title": "Op. 18", "owner_user_id": "owner", "ensemble_id": None},
                         {"id": GROUPS, "title": "Goldberg", "owner_user_id": "owner", "ensemble_id": G},
                         {"id": OTHER, "title": "Else", "owner_user_id": "someone", "ensemble_id": None},
                         {"id": f"{MINE}x", "title": "Lookalike", "owner_user_id": "someone", "ensemble_id": None}]
    db.rows["members"] = [{"ensemble_id": G, "user_id": "admin", "role": "admin"},
                          {"ensemble_id": G, "user_id": "player", "role": "player"}]
    db.rows["jobs"] = []
    return db


@pytest.fixture
def api(monkeypatch):
    db = world()
    monkeypatch.setattr(scores_routes, "db", lambda: db)
    who = {"id": "stranger"}
    app.dependency_overrides[current_user] = lambda: User(who["id"], None, None, Decimal("5"), Decimal("0"))
    client = TestClient(app, headers={"Authorization": "Bearer t"})

    def as_(user_id: str) -> TestClient:
        who["id"] = user_id
        return client
    yield db, as_
    app.dependency_overrides.clear()


# ---------------------------------------------------------------- tests

def test_owner_deletes_the_book_and_every_file_under_its_folder(api):
    db, as_ = api
    r = as_("owner").delete(f"/scores/{MINE}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["objects"]) == MINE_FILES and body["removed"] == len(MINE_FILES) and body["failed"] == []
    assert db.deleted == [("scores", [MINE])]
    assert not any(k.startswith(f"{MINE}/") for k in db.storage.keys)
    assert {f"{MINE}x/source.pdf", f"{GROUPS}/source.pdf", f"{OTHER}/source.pdf"} <= db.storage.keys


def test_group_admin_may_delete_a_group_book_a_player_may_not(api):
    db, as_ = api
    r = as_("player").delete(f"/scores/{GROUPS}")
    assert r.status_code == 403 and r.json()["detail"]["hint"] == "not_owner"
    assert db.deleted == [] and db.storage.removed_calls == []
    r = as_("admin").delete(f"/scores/{GROUPS}")
    assert r.status_code == 200, r.text
    assert db.deleted == [("scores", [GROUPS])] and f"{GROUPS}/source.pdf" not in db.storage.keys


def test_refusals_touch_no_row_and_no_file(api):
    db, as_ = api
    r = as_("stranger").delete(f"/scores/{MINE}")
    assert r.status_code == 403
    r = as_("owner").delete("/scores/nope")
    assert r.status_code == 404 and r.json()["detail"]["hint"] == "not_found"   # a hint: the web tells it from a missing route
    assert db.deleted == [] and db.storage.removed_calls == []


@pytest.mark.parametrize("job", [
    {"id": "j1", "kind": "omr_convert", "status": "running", "score_id": MINE, "payload": {}},
    {"id": "j2", "kind": "transcribe_voice", "status": "queued", "score_id": None, "payload": {"score_id": MINE}},
])
def test_a_running_or_queued_job_holds_the_delete(api, job):
    db, as_ = api
    db.rows["jobs"] = [job]
    r = as_("owner").delete(f"/scores/{MINE}")
    assert r.status_code == 409
    d = r.json()["detail"]
    assert d["hint"] == "job_live" and d["job_id"] == job["id"] and d["kind"] == job["kind"]
    assert db.deleted == [] and db.storage.removed_calls == []


def test_a_parked_question_or_another_books_job_does_not_hold_it(api):
    db, as_ = api
    db.rows["jobs"] = [{"id": "p", "kind": "process_pages", "status": "done", "score_id": MINE, "payload": {},
                        "result": {"question": "Which staves?"}},
                       {"id": "o", "kind": "part_cut", "status": "running", "score_id": OTHER, "payload": {}}]
    assert as_("owner").delete(f"/scores/{MINE}").status_code == 200


def test_dry_run_lists_and_deletes_nothing(api):
    db, as_ = api
    r = as_("owner").delete(f"/scores/{MINE}?dry_run=true")
    assert r.status_code == 200 and r.json()["dry_run"] is True and set(r.json()["objects"]) == MINE_FILES
    assert db.deleted == [] and db.storage.removed_calls == [] and MINE_FILES <= db.storage.keys


def test_a_failed_chunk_is_reported_after_the_row_is_gone(api):
    db, as_ = api
    db.storage.fail_on = "voice"
    r = as_("owner").delete(f"/scores/{MINE}")
    assert r.status_code == 200
    assert r.json()["failed"] == sorted(MINE_FILES) and r.json()["removed"] == 0   # one chunk of seven
    assert db.deleted == [("scores", [MINE])]
