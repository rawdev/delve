
from __future__ import annotations

import hashlib
import random
from typing import Any, Sequence, TypeVar

T = TypeVar("T")

MAX_SEED = 2**31 - 1


class Rng:

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
        return self._r.random() < p

    def derive(self, namespace: str, floor: int) -> "Rng":
        payload = f"{self.seed}|{namespace}|{floor}".encode("utf-8")
        child_seed = int.from_bytes(hashlib.blake2s(payload, digest_size=8).digest(), "big")
        return Rng(child_seed)



    def get_state(self) -> tuple:
        return self._r.getstate()

    def set_state(self, state: tuple) -> None:
        self._r.setstate(state)
