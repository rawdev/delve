"""턴 시스템 — v1: 즉시판정 (lockstep).

    플레이어 입력 1회 = 모든 액터가 각각 1회 행동.

## 이 결정은 "지금은" 옳다

현 조건: 적이 Goblin 1종, **속도 개념 없음.** 이 조건에서 에너지 시스템(액터마다
게이지를 굴리고 스케줄러 루프를 돌리는 것)은 명백한 과설계다 — 복잡도를 지불하고
얻는 것이 0이다.

## 그리고 이 결정은 깨질 것이다

Phase 2에서 적 3종에 속도를 준다: Rat 150 / Goblin 100 / Golem 60.
아래 `for enemy in state.enemies: act_once(enemy)` 구조로는 **"Rat이 1.5번 행동한다"를
표현할 방법이 없다.** 보스의 "HP 50% 이하 각성"도 마찬가지다.

그때 에너지 스케줄러로 전환한다 → docs/04_turn_system_pivot.md

**적에 speed를 넣는 순간 이 파일을 재검토해야 한다.** 그게 사전 설계된 유일한
통과 지점이며, 지금 미리 앞당기면 전환이 일어나지 않아 DQ1이 죽는다
(docs/09_risks_checklist.md R4). tests/test_dungeon.py의 `test_only_goblins_in_phase1`이
가드로 걸려 있다.
"""

from __future__ import annotations

from engine import actions, ai, dungeon, fov
from engine.rng import Rng
from engine.state import MAX_FLOOR, GameState


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


def process_turn(
    state: GameState, rng: Rng, action: dict
) -> list[dict]:
    """플레이어 행동 1회 → 모든 적 1회 행동. v1 즉시판정.

    행동이 성립하지 않으면 actions.InvalidAction이 올라가고 **턴은 소비되지 않는다.**
    """
    if state.status != "playing":
        raise actions.InvalidAction("게임이 끝났다")

    events = _apply_player(state, rng, action)

    # 층을 내려갔으면 이번 턴에 적은 행동하지 않는다 (새 층의 적은 아직 못 봤다).
    if any(e["t"] == "descend" for e in events):
        state.turn += 1
        return events

    if state.status == "playing":
        events += _apply_enemies(state)

    state.turn += 1
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


def _apply_enemies(state: GameState) -> list[dict]:
    """★ v1의 핵심 — 모든 적이 정확히 1회 행동한다.

    속도가 다른 적을 여기에 끼워넣을 자리가 없다. 그게 이 구조의 한계이자,
    Phase 2 전환의 이유가 된다.
    """
    events: list[dict] = []

    for enemy in state.enemies:
        if state.status != "playing":
            break

        dx, dy = ai.decide(state, enemy)
        try:
            events += actions.move_or_attack(state, enemy, dx, dy)
        except actions.InvalidAction:
            events += actions.wait(state, enemy)  # 막혔으면 대기

    return events


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

    state.log.append(f"{state.floor}층으로 내려왔다.")
    fov.compute(state.map, player.x, player.y)
    return [{"t": "floor", "floor": state.floor}]
