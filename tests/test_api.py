
from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient

from app import main, store
from app.main import app
from engine.state import MAP_H, MAP_W, Item, ItemOnFloor


@pytest.fixture(autouse=True)
def _clean_store():
    store.reset()
    yield
    store.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _new_game(client: TestClient, seed: int = 42) -> dict:
    r = client.post("/api/game", json={"seed": seed})
    assert r.status_code == 200
    return r.json()





def test_new_game_returns_playable_state(client: TestClient) -> None:
    body = _new_game(client)

    assert body["status"] == "playing"
    assert body["turn"] == 0
    assert body["floor"] == 1
    assert body["seed"] == 42
    assert len(body["tiles"]) == MAP_H
    assert all(len(row) == MAP_W for row in body["tiles"])
    assert body["player"]["hp"] > 0


def test_same_seed_same_dungeon(client: TestClient) -> None:
    a = _new_game(client, seed=7)
    b = _new_game(client, seed=7)

    assert a["game_id"] != b["game_id"]
    assert a["tiles"] == b["tiles"]


def test_new_game_without_seed_still_reports_one(client: TestClient) -> None:
    r = client.post("/api/game", json={})
    assert r.status_code == 200

    assert isinstance(r.json()["seed"], int)


def test_get_game_roundtrip(client: TestClient) -> None:
    created = _new_game(client)
    fetched = client.get(f"/api/game/{created['game_id']}")

    assert fetched.status_code == 200
    assert fetched.json() == created


def test_wait_advances_turn(client: TestClient) -> None:
    game = _new_game(client)
    r = client.post(f"/api/game/{game['game_id']}/action", json={"type": "wait"})

    assert r.status_code == 200

    assert r.json()["view"]["turn"] == game["turn"] + 1


def test_action_returns_view_and_events(client: TestClient) -> None:
    game = _new_game(client)
    r = client.post(f"/api/game/{game['game_id']}/action", json={"type": "wait"})

    body = r.json()
    assert set(body) == {"view", "events"}
    assert body["view"]["status"] == "playing"
    assert isinstance(body["events"], list)


def test_events_do_not_leak_invisible_enemies(client: TestClient) -> None:
    game = _new_game(client)
    gid = game["game_id"]
    events = client.post(f"/api/game/{gid}/action", json={"type": "wait"}).json()["events"]

    with store.session(gid) as found:
        assert found is not None
        state, _ = found
        visible_ids = {a.id for a in state.enemies if state.map.visible[a.y][a.x]}
    visible_ids.add("player")

    for e in events:
        actor = e.get("actor")
        assert (
            actor is None or actor in visible_ids or e.get("target") == "player"
        )





def test_new_game_exposes_inventory_shape(client: TestClient) -> None:
    body = _new_game(client)
    assert body["inventory"] == []
    assert set(body["equipped"]) == {"weapon", "armor"}
    assert body["equipped"]["weapon"] is None
    assert isinstance(body["floor_items"], list)


def test_pickup_through_http_adds_to_inventory(client: TestClient) -> None:
    game = _new_game(client)
    gid = game["game_id"]

    with store.session(gid) as found:
        assert found is not None
        state, _ = found
        p = state.player
        state.floor_items = [ItemOnFloor(id="i1", kind="potion", x=p.x, y=p.y)]

    r = client.post(f"/api/game/{gid}/action", json={"type": "pickup"})
    assert r.status_code == 200
    assert [it["kind"] for it in r.json()["view"]["inventory"]] == ["potion"]


def test_pickup_with_nothing_here_is_409(client: TestClient) -> None:
    game = _new_game(client)
    gid = game["game_id"]

    with store.session(gid) as found:
        assert found is not None
        found[0].floor_items = []

    r = client.post(f"/api/game/{gid}/action", json={"type": "pickup"})
    assert r.status_code == 409


def test_use_event_preserves_item_and_heal(client: TestClient) -> None:
    game = _new_game(client)
    gid = game["game_id"]

    with store.session(gid) as found:
        assert found is not None
        state, _ = found
        state.player.hp = state.player.max_hp - 5
        state.inventory = [Item(id="p1", kind="potion")]

    r = client.post(f"/api/game/{gid}/action", json={"type": "use", "item_id": "p1"})
    assert r.status_code == 200

    use_events = [e for e in r.json()["events"] if e["t"] == "use"]
    assert use_events
    assert use_events[0]["item"] == "potion"
    assert use_events[0]["heal"] == 5





def test_unknown_game_is_404(client: TestClient) -> None:
    assert client.get("/api/game/nope").status_code == 404
    r = client.post("/api/game/nope/action", json={"type": "wait"})
    assert r.status_code == 404


def test_schema_violation_is_422(client: TestClient) -> None:
    game = _new_game(client)
    gid = game["game_id"]


    assert client.post(f"/api/game/{gid}/action", json={"type": "fly"}).status_code == 422

    assert client.post(f"/api/game/{gid}/action", json={}).status_code == 422


def test_invalid_action_is_409_and_does_not_consume_turn(client: TestClient) -> None:
    game = _new_game(client)
    gid = game["game_id"]


    r = client.post(f"/api/game/{gid}/action", json={"type": "descend"})
    assert r.status_code == 409

    after = client.get(f"/api/game/{gid}").json()
    assert after["turn"] == game["turn"]


def test_bad_direction_is_409(client: TestClient) -> None:
    game = _new_game(client)
    r = client.post(
        f"/api/game/{game['game_id']}/action", json={"type": "move", "dir": "upward"}
    )

    assert r.status_code == 409


def test_finished_game_rejects_actions(client: TestClient) -> None:
    game = _new_game(client)
    gid = game["game_id"]

    with store.session(gid) as found:
        assert found is not None
        state, _ = found
        state.status = "dead"

    r = client.post(f"/api/game/{gid}/action", json={"type": "wait"})
    assert r.status_code == 409





def test_unexplored_tiles_are_not_sent(client: TestClient) -> None:
    body = _new_game(client)

    blank = sum(row.count(" ") for row in body["tiles"])
    assert blank > 0


    assert len(body["lit"]) == len(body["tiles"])
    assert all(len(a) == len(b) for a, b in zip(body["lit"], body["tiles"]))


def test_only_visible_enemies_are_sent(client: TestClient) -> None:
    body = _new_game(client)
    gid = body["game_id"]

    with store.session(gid) as found:
        assert found is not None
        state, _ = found
        total = len(state.enemies)
        visible = [e for e in state.enemies if state.map.visible[e.y][e.x]]

    assert len(body["actors"]) == len(visible)
    assert len(body["actors"]) <= total


    for actor in body["actors"]:
        assert body["lit"][actor["y"]][actor["x"]] == "1"



#




#





def _watch_overlap(monkeypatch: pytest.MonkeyPatch, hold: float = 0.02):
    real = main.turn.process_turn
    depth = 0
    peak = 0
    guard = threading.Lock()

    def watched(state, rng, action):  # noqa: ANN001, ANN202
        nonlocal depth, peak
        with guard:
            depth += 1
            peak = max(peak, depth)
        try:
            time.sleep(hold)
            return real(state, rng, action)
        finally:
            with guard:
                depth -= 1

    monkeypatch.setattr(main.turn, "process_turn", watched)
    return lambda: peak


def _hammer(fns: list) -> None:
    start = threading.Barrier(len(fns))

    def run(fn) -> None:  # noqa: ANN001
        start.wait()
        fn()

    threads = [threading.Thread(target=run, args=(fn,)) for fn in fns]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_same_game_is_never_processed_concurrently(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    gid = _new_game(client)["game_id"]
    peak = _watch_overlap(monkeypatch)

    _hammer(
        [
            lambda: client.post(f"/api/game/{gid}/action", json={"type": "wait"})
            for _ in range(8)
        ]
    )

    assert peak() == 1


def test_no_turn_is_lost_under_concurrency(client: TestClient) -> None:
    gid = _new_game(client)["game_id"]

    _hammer(
        [
            lambda: client.post(f"/api/game/{gid}/action", json={"type": "wait"})
            for _ in range(8)
        ]
    )

    assert client.get(f"/api/game/{gid}").json()["turn"] == 8


def test_different_games_do_run_concurrently(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    gids = [_new_game(client, seed=i)["game_id"] for i in range(8)]
    peak = _watch_overlap(monkeypatch)

    _hammer(
        [
            (lambda g=g: client.post(f"/api/game/{g}/action", json={"type": "wait"}))
            for g in gids
        ]
    )

    assert peak() > 1


def test_concurrency_does_not_break_seed_determinism(client: TestClient) -> None:

    def play(concurrent: bool) -> list[str]:
        gid = client.post("/api/game", json={"seed": 99}).json()["game_id"]
        post = lambda: client.post(  # noqa: E731
            f"/api/game/{gid}/action", json={"type": "wait"}
        )

        if concurrent:
            _hammer([post for _ in range(8)])
        else:
            for _ in range(8):
                post()

        return client.get(f"/api/game/{gid}").json()["tiles"]

    assert play(concurrent=False) == play(concurrent=True)





def test_sessions_are_capped(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(store, "MAX_SESSIONS", 5)

    for _ in range(12):
        client.post("/api/game", json={})

    assert store.count() <= 5


def test_oldest_session_is_evicted_first(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "MAX_SESSIONS", 3)

    first = _new_game(client)["game_id"]
    for _ in range(5):
        client.post("/api/game", json={})


    assert client.get(f"/api/game/{first}").status_code == 404


def test_finished_games_expire_sooner(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    alive = _new_game(client)["game_id"]
    done = _new_game(client)["game_id"]

    with store.session(done) as found:
        assert found is not None
        found[0].status = "dead"


    monkeypatch.setattr(store, "FINISHED_TTL_SECONDS", -1)

    client.post("/api/game", json={})

    assert client.get(f"/api/game/{done}").status_code == 404
    assert client.get(f"/api/game/{alive}").status_code == 200
