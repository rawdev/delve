"""HTTP 경계 계약 테스트.

`engine/` 테스트(test_dungeon / test_turn)를 **대체하지 않는다.** 저쪽은 게임 규칙을
HTTP 없이 순수 Python으로 검증하고, 여기는 `app/`이 그 규칙을 올바르게 노출하는지만
본다. 두 층이 겹치면 엔진 리팩터링 때 API 테스트가 같이 깨져서 경계가 무의미해진다.

여기서 지키는 계약:
- 생성 → 조회 → 행동 흐름
- 404 (없는 게임) / 409 (성립하지 않는 행동) / 422 (스키마 위반)
- 끝난 게임은 더 이상 행동을 받지 않는다
- **미탐색 타일과 안 보이는 적은 응답에 실리지 않는다** — 클라이언트에게 던전을
  통째로 보내면 FOV가 서버 권위라는 주장이 거짓이 된다
- **같은 game_id 동시 요청이 직렬화된다** — 잠금이 없으면 turn과 Rng 소비가 겹친다
"""

from __future__ import annotations

import threading
import time

import pytest
from fastapi.testclient import TestClient

from app import main, store
from app.main import app
from engine.state import MAP_H, MAP_W, ItemOnFloor


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


# --- 기본 흐름 -------------------------------------------------------------


def test_new_game_returns_playable_state(client: TestClient) -> None:
    body = _new_game(client)

    assert body["status"] == "playing"
    assert body["turn"] == 0
    assert body["floor"] == 1
    assert body["seed"] == 42  # 시드는 항상 실린다 — 버그 재현의 전제
    assert len(body["tiles"]) == MAP_H
    assert all(len(row) == MAP_W for row in body["tiles"])
    assert body["player"]["hp"] > 0


def test_same_seed_same_dungeon(client: TestClient) -> None:
    """HTTP를 거쳐도 시드 결정론이 유지된다."""
    a = _new_game(client, seed=7)
    b = _new_game(client, seed=7)

    assert a["game_id"] != b["game_id"]  # 게임은 다르다
    assert a["tiles"] == b["tiles"]  # 던전은 같다


def test_new_game_without_seed_still_reports_one(client: TestClient) -> None:
    r = client.post("/api/game", json={})
    assert r.status_code == 200
    # 시드를 안 줘도 서버가 정한 시드를 돌려준다 — 없으면 그 게임의 버그는 재현 불가다.
    assert isinstance(r.json()["seed"], int)


def test_get_game_roundtrip(client: TestClient) -> None:
    created = _new_game(client)
    fetched = client.get(f"/api/game/{created['game_id']}")

    assert fetched.status_code == 200
    assert fetched.json() == created  # 조회는 상태를 바꾸지 않는다


def test_wait_advances_turn(client: TestClient) -> None:
    game = _new_game(client)
    r = client.post(f"/api/game/{game['game_id']}/action", json={"type": "wait"})

    assert r.status_code == 200
    # v2: action 응답은 {view, events}. turn은 view 안에 있다.
    assert r.json()["view"]["turn"] == game["turn"] + 1


def test_action_returns_view_and_events(client: TestClient) -> None:
    """v2 계약: 최종 상태(view) + 그 사이 순서대로 일어난 일(events)."""
    game = _new_game(client)
    r = client.post(f"/api/game/{game['game_id']}/action", json={"type": "wait"})

    body = r.json()
    assert set(body) == {"view", "events"}
    assert body["view"]["status"] == "playing"
    assert isinstance(body["events"], list)


def test_events_do_not_leak_invisible_enemies(client: TestClient) -> None:
    """events[]도 FOV를 존중한다 — 안 보이는 적의 이동/대기는 실리지 않는다.

    이게 새면 GameView가 적을 숨기는 의미가 사라진다 (서버 권위 FOV).
    """
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
        ), f"안 보이는 적의 이벤트가 노출됐다: {e}"


# --- 인벤토리 -------------------------------------------------------------


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
        found[0].floor_items = []  # 시작칸엔 아이템이 없다 — 확실히 비운다

    r = client.post(f"/api/game/{gid}/action", json={"type": "pickup"})
    assert r.status_code == 409


# --- 오류 계약 -------------------------------------------------------------


def test_unknown_game_is_404(client: TestClient) -> None:
    assert client.get("/api/game/nope").status_code == 404
    r = client.post("/api/game/nope/action", json={"type": "wait"})
    assert r.status_code == 404


def test_schema_violation_is_422(client: TestClient) -> None:
    game = _new_game(client)
    gid = game["game_id"]

    # 없는 행동 타입 — pydantic Literal이 막는다
    assert client.post(f"/api/game/{gid}/action", json={"type": "fly"}).status_code == 422
    # type 자체가 없다
    assert client.post(f"/api/game/{gid}/action", json={}).status_code == 422


def test_invalid_action_is_409_and_does_not_consume_turn(client: TestClient) -> None:
    """성립하지 않는 행동은 턴을 소비하지 않는다 (engine/actions.py의 계약)."""
    game = _new_game(client)
    gid = game["game_id"]

    # 계단 위가 아닌 곳에서 descend — 스키마는 맞지만 규칙이 거부한다
    r = client.post(f"/api/game/{gid}/action", json={"type": "descend"})
    assert r.status_code == 409

    after = client.get(f"/api/game/{gid}").json()
    assert after["turn"] == game["turn"]  # 턴이 안 늘었다


def test_bad_direction_is_409(client: TestClient) -> None:
    game = _new_game(client)
    r = client.post(
        f"/api/game/{game['game_id']}/action", json={"type": "move", "dir": "upward"}
    )
    # 방향은 자유 문자열이라 스키마를 통과하고, 엔진이 거부한다
    assert r.status_code == 409


def test_finished_game_rejects_actions(client: TestClient) -> None:
    """끝난 게임은 더 이상 행동을 받지 않는다 (turn.process_turn의 계약)."""
    game = _new_game(client)
    gid = game["game_id"]

    with store.session(gid) as found:
        assert found is not None
        state, _ = found
        state.status = "dead"  # 사망까지 실제로 플레이하는 대신 상태를 직접 세운다

    r = client.post(f"/api/game/{gid}/action", json={"type": "wait"})
    assert r.status_code == 409


# --- 정보 은닉 (서버 권위 FOV) ---------------------------------------------


def test_unexplored_tiles_are_not_sent(client: TestClient) -> None:
    """미탐색 칸은 공백으로 나간다 — 던전 전체를 보내면 FOV가 무의미해진다."""
    body = _new_game(client)

    blank = sum(row.count(" ") for row in body["tiles"])
    assert blank > 0, "시작 시점에 미탐색 칸이 하나도 없다면 맵 전체를 보낸 것이다"

    # lit 격자는 tiles와 같은 모양이어야 한다
    assert len(body["lit"]) == len(body["tiles"])
    assert all(len(a) == len(b) for a, b in zip(body["lit"], body["tiles"]))


def test_only_visible_enemies_are_sent(client: TestClient) -> None:
    """안 보이는 적은 응답에 없다."""
    body = _new_game(client)
    gid = body["game_id"]

    with store.session(gid) as found:
        assert found is not None
        state, _ = found
        total = len(state.enemies)
        visible = [e for e in state.enemies if state.map.visible[e.y][e.x]]

    assert len(body["actors"]) == len(visible)
    assert len(body["actors"]) <= total

    # 응답에 실린 적은 전부 실제로 보이는 칸에 있다
    for actor in body["actors"]:
        assert body["lit"][actor["y"]][actor["x"]] == "1"


# --- 동시성 ---------------------------------------------------------------
#
# ⚠️ 여기서 한 번 속았다. 처음에는 "같은 게임을 20개 스레드로 때리고 최종 turn == 20인가"로
# 썼는데, **Lock을 지워도 통과했다.** TestClient는 실제로 병렬 실행하지만(sync 핸들러가
# 스레드풀로 간다), `state.turn += 1`의 경합 창이 GIL 아래에서 몇 바이트코드뿐이라
# 우연히 안 터진 것이다. 경쟁 조건은 **실재하는데 테스트가 못 잡는** 상태였다.
#
# 그런 테스트는 방어선이 아니라 방어선이 있다는 착각이다. 그래서 결과(turn 수)를 보지 않고
# **겹침 자체를 관측**하도록 바꿨다: 같은 게임을 두 요청이 동시에 처리 중인 순간이
# 한 번이라도 있었는가. 이건 Lock을 지우면 반드시 실패한다.


def _watch_overlap(monkeypatch: pytest.MonkeyPatch, hold: float = 0.02):
    """`turn.process_turn`을 감싸 '동시에 몇 개가 안에 있었나'를 센다.

    프로덕션 코드는 건드리지 않는다 — 테스트가 보는 이름만 바꾼다.
    """
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
            time.sleep(hold)  # 겹칠 수 있으면 반드시 겹치도록 창을 넓힌다
            return real(state, rng, action)
        finally:
            with guard:
                depth -= 1

    monkeypatch.setattr(main.turn, "process_turn", watched)
    return lambda: peak


def _hammer(fns: list) -> None:
    """모든 스레드를 같은 순간에 출발시킨다."""
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
    """★ 같은 게임을 두 요청이 동시에 처리하지 않는다.

    이게 깨지면 `state.turn`과 **`Rng` 소비가 겹친다.** 결정론이 깨지면 버그 재현이
    안 되고, 재현이 안 되면 버그 이벤트를 규약대로 저장할 수 없다 (BQ1·BQ2).
    """
    gid = _new_game(client)["game_id"]
    peak = _watch_overlap(monkeypatch)

    _hammer(
        [
            lambda: client.post(f"/api/game/{gid}/action", json={"type": "wait"})
            for _ in range(8)
        ]
    )

    assert peak() == 1, f"같은 게임을 동시에 {peak()}개 요청이 처리했다 — 직렬화 실패"


def test_no_turn_is_lost_under_concurrency(client: TestClient) -> None:
    """8번 요청했으면 8턴이 지나 있어야 한다. (위 테스트의 결과 쪽 확인)"""
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
    """게임별 Lock이지 전역 Lock이 아니다.

    전역 Lock으로 막으면 이 테스트가 실패한다 — 그건 동시성 문제를 "고친" 게 아니라
    서버를 한 줄로 세운 것이다. 서로 다른 게임은 **겹쳐서 처리되어야 정상**이다.
    """
    gids = [_new_game(client, seed=i)["game_id"] for i in range(8)]
    peak = _watch_overlap(monkeypatch)

    _hammer(
        [
            (lambda g=g: client.post(f"/api/game/{g}/action", json={"type": "wait"}))
            for g in gids
        ]
    )

    assert peak() > 1, "서로 다른 게임이 직렬화됐다 — Lock이 전역으로 걸렸다"


def test_concurrency_does_not_break_seed_determinism(client: TestClient) -> None:
    """동시 요청을 겪은 게임도 순차 진행과 같은 상태에 도달한다.

    `Rng`가 두 요청에 나뉘어 소비되면 같은 시드·같은 입력이 다른 던전을 만든다.
    """

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


# --- 세션 수명 / 용량 -------------------------------------------------------


def test_sessions_are_capped(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """무한히 쌓이지 않는다. 로그인이 없으므로 누구나 게임을 만들 수 있다."""
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

    # 가장 오래된 게임은 밀려났다 — 404가 정상이다 (서버 재시작과 같은 계약)
    assert client.get(f"/api/game/{first}").status_code == 404


def test_finished_games_expire_sooner(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """끝난 게임(dead/won)은 진행 중인 게임보다 빨리 버려진다."""
    alive = _new_game(client)["game_id"]
    done = _new_game(client)["game_id"]

    with store.session(done) as found:
        assert found is not None
        found[0].status = "dead"

    # 끝난 게임의 TTL만 지난 시점을 흉내낸다
    monkeypatch.setattr(store, "FINISHED_TTL_SECONDS", -1)

    client.post("/api/game", json={})  # put()이 청소를 유발한다

    assert client.get(f"/api/game/{done}").status_code == 404
    assert client.get(f"/api/game/{alive}").status_code == 200
