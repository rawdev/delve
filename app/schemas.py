
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class NewGameRequest(BaseModel):
    seed: int | None = None


class ActionRequest(BaseModel):
    type: Literal["move", "wait", "descend", "pickup", "use", "equip"]
    dir: str | None = None
    item_id: str | None = None


class ActorView(BaseModel):
    id: str
    kind: str
    glyph: str
    x: int
    y: int
    hp: int
    max_hp: int


class ItemView(BaseModel):
    id: str
    kind: str
    glyph: str
    name: str


class FloorItemView(BaseModel):
    kind: str
    glyph: str
    x: int
    y: int


class GameView(BaseModel):
    game_id: str
    seed: int
    turn: int
    floor: int
    status: str  # "playing" | "dead" | "won"

    width: int
    height: int
    tiles: list[str]
    lit: list[str]

    player: ActorView
    level: int
    xp: int
    xp_needed: int
    actors: list[ActorView]
    log: list[str]

    inventory: list[ItemView]
    equipped: dict[str, ItemView | None]  # "weapon" / "armor"
    floor_items: list[FloorItemView]


class TurnEvent(BaseModel):

    t: str  # move | attack | wait | death | levelup | descend | floor | win | pickup | use | equip
    actor: str | None = None
    target: str | None = None
    to: list[int] | None = None
    dmg: int | None = None
    level: int | None = None
    floor: int | None = None
    item: str | None = None
    heal: int | None = None
    slot: str | None = None


class ActionResponse(BaseModel):

    view: GameView
    events: list[TurnEvent]
