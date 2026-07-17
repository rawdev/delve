"""전역 시드 — 파생 스트림 계약 (설계 evt_5c9d0278).

밸런스 A/B가 통제 실험이 되려면 파생이 다음을 만족해야 한다:
- 같은 (seed, namespace, floor) → 항상 같은 스트림
- namespace나 floor가 다르면 다른 스트림
- **부모가 얼마나 소비됐든 결과가 같고, 부모를 소비하지도 않는다**
- 실행/프로세스가 달라도 같은 값 (hash()를 쓰면 여기서 깨진다)
"""

from __future__ import annotations

from engine.rng import Rng

NS = "dungeon/items/v1"


def _draws(rng: Rng, n: int = 5) -> list[int]:
    return [rng.randint(0, 10**6) for _ in range(n)]


def test_same_inputs_give_same_stream() -> None:
    assert _draws(Rng(42).derive(NS, 1)) == _draws(Rng(42).derive(NS, 1))


def test_different_namespace_gives_different_stream() -> None:
    assert _draws(Rng(42).derive("dungeon/items/v1", 1)) != _draws(
        Rng(42).derive("dungeon/enemies/v1", 1)
    )


def test_different_floor_gives_different_stream() -> None:
    assert _draws(Rng(42).derive(NS, 1)) != _draws(Rng(42).derive(NS, 2))


def test_different_seed_gives_different_stream() -> None:
    assert _draws(Rng(42).derive(NS, 1)) != _draws(Rng(43).derive(NS, 1))


def test_derive_ignores_parent_consumption() -> None:
    """★ 격리의 핵심 — 부모가 얼마나 소비됐든 파생 결과는 같다.

    이게 없으면 앞선 스트림의 소비량 변화(예: 적 1마리 제거)가 뒤의 스트림을 흔든다.
    """
    fresh = Rng(42)
    consumed = Rng(42)
    for _ in range(37):
        consumed.randint(0, 100)

    assert _draws(fresh.derive(NS, 3)) == _draws(consumed.derive(NS, 3))


def test_derive_does_not_consume_parent() -> None:
    parent = Rng(42)
    before = parent.get_state()

    parent.derive(NS, 1)
    parent.derive("other/v1", 2)

    assert parent.get_state() == before


def test_derive_is_stable_across_runs() -> None:
    """알려진 값 고정 — 프로세스마다 salt가 바뀌는 hash()로 회귀하면 여기서 깨진다."""
    assert Rng(20260716).derive("dungeon/items/v1", 1).randint(0, 10**9) == 875933610
