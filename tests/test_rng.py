
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
    assert Rng(20260716).derive("dungeon/items/v1", 1).randint(0, 10**9) == 875933610
