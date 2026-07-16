"""턴 시스템 v2 요구 — 속도 비율 (Phase 2).

이 파일은 docs/04_turn_system_pivot.md가 예고한 tests/test_turn.py다. 크리틱
Phase 2 사전 리뷰 권장 순서 2("v1이 새 속도 요구를 만족하지 못하는 테스트 작성 및
실패 확인")의 실물이다.

현재는 v1(즉시판정)이 살아 있으므로 **아래 요구는 만족될 수 없다.** 그 사실을
xfail(strict)로 못박는다:

- 지금(v1): 요구가 깨지므로 xfail → 스위트는 초록이다.
- v2(에너지 스케줄러) 도입 후: 실제로 speed 비율대로 행동이 생기면 이 테스트는
  XPASS로 뒤집혀 **실패로 보고된다** → 그때 marker를 떼고 정식 테스트로 승격하라는
  신호다. 그 뒤집힘이 전환이 실제로 일어났다는 증거이자 DQ1의 답이다.

즉 이 파일의 빨강→초록 전환과 tests/test_turn_v1.py의 초록→빨강 전환이 같은 커밋에서
맞물리는 것이 "턴 시스템 v2 전환"의 관측 가능한 정의다.
"""

from __future__ import annotations

import pytest

from engine import turn
from engine.state import make_enemy


def _count_enemy_actions(kinds: list[str], turns: int = 60) -> dict[str, int]:
    """적들을 시야 밖에 세워 두고 플레이어가 `turns`번 대기하며 적별 행동 수를 센다.

    시야(8) 밖의 적은 매 턴 idle → wait 이벤트 1건(actor=적 id)을 낸다. v1은 매
    입력마다 전원을 정확히 1회 행동시키므로, speed와 무관하게 모든 적이 정확히
    `turns`번 행동한 것으로 집계된다 — 바로 이 동률이 v2 요구를 위반한다.
    """
    state, rng = turn.new_game("ratio", 42)
    player = state.player

    enemies = [
        make_enemy(kind, i, player.x + 20, player.y + i)
        for i, kind in enumerate(kinds)
    ]
    state.actors = [player] + enemies

    counts = {e.id: 0 for e in enemies}
    for _ in range(turns):
        events = turn.process_turn(state, rng, {"type": "wait"})
        for ev in events:
            if ev["actor"] in counts:
                counts[ev["actor"]] += 1
    return counts


@pytest.mark.xfail(
    reason="v1 즉시판정은 speed 비율을 표현할 수 없다 — 에너지 스케줄러(v2) 전환의 근거. docs/04",
    strict=True,
)
def test_action_count_scales_with_speed() -> None:
    """요구: 장기적으로 적의 행동 횟수는 speed에 비례한다.

    Rat 150 : Goblin 100 : Golem 60 → 행동 횟수도 Rat > Goblin > Golem 이어야 한다.
    v1에서는 셋 다 동률(= turns)이라 이 단조성이 깨지고, 테스트는 실패한다.
    """
    counts = _count_enemy_actions(["rat", "goblin", "golem"])

    assert counts["rat#0"] > counts["goblin#1"] > counts["golem#2"]


@pytest.mark.xfail(
    reason="v1 즉시판정은 한 입력에 각 적을 정확히 1회만 행동시킨다 — v2 전환의 근거. docs/04",
    strict=True,
)
def test_fast_enemy_acts_more_than_once_between_inputs() -> None:
    """요구: Rat(150)은 플레이어 한 입력 사이에 1회를 초과해 행동할 수 있어야 한다.

    v1은 한 입력에 각 적을 정확히 1회만 행동시키므로 항상 1이다.
    """
    counts = _count_enemy_actions(["rat"], turns=1)

    assert counts["rat#0"] > 1
