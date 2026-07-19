
from __future__ import annotations

from engine import actions, ai, dungeon, fov
from engine.rng import Rng
from engine.state import ENERGY_THRESHOLD, MAX_FLOOR, GameState


def new_game(game_id: str, seed: int | None = None) -> tuple[GameState, Rng]:
    rng = Rng(seed)
    game_map, actors, floor_items = dungeon.generate(1, rng)

    state = GameState(
        game_id=game_id,
        seed=rng.seed,
        turn=0,
        floor=1,
        map=game_map,
        actors=actors,
    )
    state.floor_items = floor_items
    state.log.append("You entered the dungeon. (Floor 1)")
    fov.compute(state.map, state.player.x, state.player.y)
    return state, rng


def process_turn(state: GameState, rng: Rng, action: dict) -> list[dict]:
    if state.status != "playing":
        raise actions.InvalidAction("The game is over")

    events = _apply_player(state, rng, action)


    state.turn += 1



    if any(e["t"] in ("floor", "win") for e in events):
        return events

    state.player.energy -= ENERGY_THRESHOLD

    if state.status == "playing":
        events += _advance_until_player_ready(state)
        fov.compute(state.map, state.player.x, state.player.y)

    return events


def _apply_player(state: GameState, rng: Rng, action: dict) -> list[dict]:
    kind = action.get("type")

    if kind == "move":
        direction = action.get("dir")
        if direction not in actions.DIRECTIONS:
            raise actions.InvalidAction(f"Unknown direction: {direction}")
        dx, dy = actions.DIRECTIONS[direction]
        return actions.move_or_attack(state, state.player, dx, dy)

    if kind == "wait":
        return actions.wait(state, state.player)

    if kind == "descend":
        events = actions.descend(state)
        return events + _next_floor(state, rng)

    if kind == "pickup":
        return actions.pickup(state)

    if kind == "use":
        return actions.use(state, action.get("item_id"))

    if kind == "equip":
        return actions.equip(state, action.get("item_id"))

    raise actions.InvalidAction(f"Unknown action: {kind}")


def _advance_until_player_ready(state: GameState) -> list[dict]:
    events: list[dict] = []

    while state.player.energy < ENERGY_THRESHOLD:
        for actor in state.actors:
            if actor.alive:
                actor.energy += actor.speed

        for enemy in state.enemies:
            while enemy.energy >= ENERGY_THRESHOLD:
                if state.status != "playing":
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
        return actions.wait(state, enemy)


def _next_floor(state: GameState, rng: Rng) -> list[dict]:
    if state.floor >= MAX_FLOOR:
        state.status = "won"
        state.log.append("You escaped the dungeon. Victory!")
        return [{"t": "win"}]

    state.floor += 1
    player = state.player

    game_map, actors, floor_items = dungeon.generate(state.floor, rng)
    new_player_pos = actors[0]
    player.x, player.y = new_player_pos.x, new_player_pos.y

    state.map = game_map
    state.actors = [player] + actors[1:]
    state.floor_items = floor_items



    player.energy = ENERGY_THRESHOLD

    state.log.append(f"You descended to floor {state.floor}.")
    fov.compute(state.map, player.x, player.y)
    return [{"t": "floor", "floor": state.floor}]
