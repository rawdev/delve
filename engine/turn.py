"""턴 시스템 — v2: 에너지 스케줄러 (정수).

    플레이어 입력 1회 → 플레이어가 자기 턴을 소비 → 플레이어가 다시 행동 가능해질
    때까지 내부 시간을 진행하며, 그 사이 적들은 각자의 speed에 비례해 행동한다.

## v1(즉시판정)에서 왜 전환했나

v1은 "1입력 = 전원 정확히 1행동"이었다. 적 3종에 속도를 주자(Rat 150 / Goblin 100 /
Golem 60) v1으로는 "Rat이 1.5배 행동한다"를 표현할 수 없었다 — tests/test_turn.py가
그 파열을 증명했다(60>60). 대안 A(적별 카운터 hack)는 적 비율은 맞췄으나 플레이어를
가속할 자리가 없어 비대칭이었다. 대안 B(float 우선순위 큐)는 직렬화·재현에서 부동소수점
오차가 결정론을 깬다. 정수 에너지(대안 C)만이 결정론과 플레이어 대칭을 동시에 만족한다.
→ docs/04_turn_system_pivot.md §3

## 실행 순서 (크리틱 Phase 2 사전 리뷰 발견 1)

docs/04 §3의 최초 의사코드는 actors[0]인 플레이어가 임계치에 도달하면 적 처리 전에
반환할 수 있어, Rat의 추가 행동이 정확히 표현되지 않을 수 있었다. 그래서 순서를
바로잡아 채택했다:

1. 새 게임에서 플레이어 energy=100 (바로 행동 가능).
2. 유효한 플레이어 행동을 적용하고 energy를 ENERGY_THRESHOLD만큼 차감.
3. player.energy가 다시 임계치 이상이 될 때까지 내부 시간을 진행한다.
4. 각 내부 tick에 살아 있는 모든 액터가 speed만큼 energy를 얻는다.
5. 적은 actors의 고정 순서로 energy>=임계치인 동안 행동하고 임계치만큼 차감한다.
6. 플레이어가 다시 행동 가능하면 응답을 반환한다(입력 대기).
7. 잔여 energy는 다음 입력까지 보존된다.

turn 카운터는 **플레이어가 소비한 행동 수**로 유지한다(발견 2) — 내부 tick으로
증가시키지 않는다. 재현 표기(seed/floor/turn)의 의미를 v1과 동일하게 보존한다.

모든 무작위성은 여전히 engine/rng.py를 거친다. 전투에는 무작위가 없고 스케줄러는
정수만 쓰므로, 같은 시드·같은 입력이면 events 순서까지 동일하다.
"""

from __future__ import annotations

from engine import actions, ai, dungeon, fov
from engine.rng import Rng
from engine.state import ENERGY_THRESHOLD, MAX_FLOOR, GameState


def new_game(game_id: str, seed: int | None = None) -> tuple[GameState, Rng]:
    rng = Rng(seed)
    game_map, actors = dungeon.generate(1, rng)

    state = GameState(
        game_id=game_id,
        seed=rng.seed,
        turn=0,
        floor=1,
        map=game_map,
        actors=actors,
    )
    state.log.append("당신은 던전에 발을 들였다. (1층)")
    fov.compute(state.map, state.player.x, state.player.y)
    return state, rng


def process_turn(state: GameState, rng: Rng, action: dict) -> list[dict]:
    """플레이어 행동 1회 → 플레이어가 다시 행동 가능해질 때까지 내부 시간 진행.

    행동이 성립하지 않으면 actions.InvalidAction이 올라가고 **에너지도 turn도
    소비되지 않는다** (v1과 동일한 계약 — 벽에 부딪혀도 손해가 없다).
    """
    if state.status != "playing":
        raise actions.InvalidAction("게임이 끝났다")

    events = _apply_player(state, rng, action)

    # turn = 플레이어가 소비한 행동 수 (발견 2). 내부 tick으로는 증가시키지 않는다.
    state.turn += 1

    # 층을 내려갔으면 새 층이 에너지 경제를 리셋한다(_next_floor). 이번 입력엔 적이
    # 행동하지 않는다 (새 층의 적은 아직 못 봤다).
    if any(e["t"] in ("floor", "win") for e in events):
        return events

    state.player.energy -= ENERGY_THRESHOLD  # 플레이어가 자기 턴을 소비

    if state.status == "playing":
        events += _advance_until_player_ready(state)
        fov.compute(state.map, state.player.x, state.player.y)

    return events


def _apply_player(state: GameState, rng: Rng, action: dict) -> list[dict]:
    kind = action.get("type")

    if kind == "move":
        direction = action.get("dir")
        if direction not in actions.DIRECTIONS:
            raise actions.InvalidAction(f"모르는 방향: {direction}")
        dx, dy = actions.DIRECTIONS[direction]
        return actions.move_or_attack(state, state.player, dx, dy)

    if kind == "wait":
        return actions.wait(state, state.player)

    if kind == "descend":
        events = actions.descend(state)
        return events + _next_floor(state, rng)

    raise actions.InvalidAction(f"모르는 행동: {kind}")


def _advance_until_player_ready(state: GameState) -> list[dict]:
    """★ v2의 핵심 — 플레이어가 다시 행동 가능해질 때까지 내부 시간을 진행한다.

    매 tick마다 살아 있는 모든 액터가 speed만큼 energy를 얻는다. 그 tick에 적은
    actors의 고정 순서로 energy>=임계치인 동안 반복 행동한다 — Rat(150)은 한 입력
    사이 2번 행동할 수 있고, Golem(60)은 여러 입력에 한 번꼴로만 행동한다. 이 비대칭이
    v1이 표현하지 못하던 바로 그것이다.

    결정론: 리스트 순서가 고정이고 정수만 쓰므로 같은 상태 → 같은 events 순서.
    """
    events: list[dict] = []

    while state.player.energy < ENERGY_THRESHOLD:
        for actor in state.actors:
            if actor.alive:
                actor.energy += actor.speed

        for enemy in state.enemies:  # 고정 순서, 살아 있는 적만
            while enemy.energy >= ENERGY_THRESHOLD:
                if state.status != "playing":  # 플레이어가 죽었으면 즉시 중단
                    return events
                events += _enemy_act(state, enemy)
                enemy.energy -= ENERGY_THRESHOLD

        if state.status != "playing":
            return events

    return events


def _enemy_act(state: GameState, enemy) -> list[dict]:
    dx, dy = ai.decide(state, enemy)
    try:
        return actions.move_or_attack(state, enemy, dx, dy)
    except actions.InvalidAction:
        return actions.wait(state, enemy)  # 막혔으면 대기 (에너지는 소비된다)


def _next_floor(state: GameState, rng: Rng) -> list[dict]:
    if state.floor >= MAX_FLOOR:
        state.status = "won"
        state.log.append("당신은 던전을 빠져나왔다. 승리!")
        return [{"t": "win"}]

    state.floor += 1
    player = state.player

    game_map, actors = dungeon.generate(state.floor, rng)
    new_player_pos = actors[0]
    player.x, player.y = new_player_pos.x, new_player_pos.y

    state.map = game_map
    state.actors = [player] + actors[1:]  # 플레이어는 HP/레벨을 유지한 채 데려간다

    # 새 층은 에너지 경제를 리셋한다: 플레이어는 바로 행동 가능, 새 적은 0에서 시작.
    # (계단을 내려간 그 입력이 이번 층 첫 행동을 소비하지 않도록.)
    player.energy = ENERGY_THRESHOLD

    state.log.append(f"{state.floor}층으로 내려왔다.")
    fov.compute(state.map, player.x, player.y)
    return [{"t": "floor", "floor": state.floor}]
