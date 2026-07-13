"""전역 시드 — 게임의 모든 무작위성이 여기를 거친다.

불변식 3 (docs/03_architecture.md §2):
    engine 안에서 `random` 전역 모듈을 직접 호출하지 않는다.

이걸 어기면 시드 결정론이 조용히 깨진다. 그러면 버그 재현이 안 되고, 재현이 안 되면
근본 원인을 못 찾고, 근본 원인이 없으면 버그 이벤트를 규약대로 저장할 수 없다.
"""

from __future__ import annotations

import random
from typing import Any, Sequence, TypeVar

T = TypeVar("T")

MAX_SEED = 2**31 - 1


class Rng:
    """시드 RNG. `random.Random` 인스턴스를 감싼다.

    세이브/로드에는 `seed`와 `state`를 **둘 다** 넣어야 한다. 시드만으로는 복원되지
    않는다 — 시드는 시작점일 뿐이고, RNG는 이미 N번 소비된 상태이기 때문이다.
    """

    def __init__(self, seed: int | None = None) -> None:
        if seed is None:
            seed = random.SystemRandom().randrange(MAX_SEED)
        self.seed = int(seed)
        self._r = random.Random(self.seed)

    def randint(self, a: int, b: int) -> int:
        """a <= n <= b."""
        return self._r.randint(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        return self._r.choice(seq)

    def shuffle(self, seq: list[Any]) -> None:
        self._r.shuffle(seq)

    def chance(self, p: float) -> bool:
        """확률 p로 True."""
        return self._r.random() < p

    # 직렬화 — 세이브 포맷이 의존한다 (Phase 4)

    def get_state(self) -> tuple:
        return self._r.getstate()

    def set_state(self, state: tuple) -> None:
        self._r.setstate(state)
