"""Turn schema-2 decisions into model-ready numeric and categorical features.

This intentionally keeps variable-size card groups as token lists and exposes a
fixed numeric summary. A neural policy can embed/pool the lists and concatenate
them with these numeric features when its architecture is added.
"""
from collections import Counter


def _player_by_id(state, player_id):
    return next((p for p in state.get("players", []) if p.get("id") == player_id), {})


def _numeric_state(state, decision):
    players = state.get("players", [])
    acting_id = state.get("acting_player")
    acting = _player_by_id(state, acting_id)
    opponent = next((p for p in players if p.get("id") != acting_id), {})
    own_board = acting.get("battlefield", [])
    opp_board = opponent.get("battlefield", [])
    own_creatures = [c for c in own_board if "Creature" in c.get("types", "")]
    opp_creatures = [c for c in opp_board if "Creature" in c.get("types", "")]
    numeric = {
        "turn": float(state.get("turn", decision.get("turn", 0))),
        "acting_life": float(acting.get("life", 0)),
        "opponent_life": float(opponent.get("life", 0)),
        "acting_poison": float(acting.get("poison", 0)),
        "opponent_poison": float(opponent.get("poison", 0)),
        "acting_hand_size": float(acting.get("hand_size", len(acting.get("hand", [])))),
        "opponent_hand_size": float(opponent.get("hand_size", 0)),
        "acting_battlefield_count": float(len(own_board)),
        "opponent_battlefield_count": float(len(opp_board)),
        "acting_graveyard_count": float(len(acting.get("graveyard", []))),
        "opponent_graveyard_count": float(len(opponent.get("graveyard", []))),
        "acting_creature_count": float(len(own_creatures)),
        "opponent_creature_count": float(len(opp_creatures)),
        "acting_total_power": float(sum(c.get("power", 0) for c in own_creatures)),
        "opponent_total_power": float(sum(c.get("power", 0) for c in opp_creatures)),
        "acting_total_toughness": float(sum(c.get("toughness", 0) for c in own_creatures)),
        "opponent_total_toughness": float(sum(c.get("toughness", 0) for c in opp_creatures)),
    }
    categorical = {
        "phase": [str(state.get("phase", decision.get("phase", "UNKNOWN")))],
        "decision_kind": [str(decision.get("kind", "UNKNOWN"))],
        "acting_hand_cards": [c.get("card", "UNKNOWN") for c in acting.get("hand", [])],
        "acting_battlefield_cards": [c.get("card", "UNKNOWN") for c in own_board],
        "opponent_battlefield_cards": [c.get("card", "UNKNOWN") for c in opp_board],
        "acting_graveyard_cards": [c.get("card", "UNKNOWN") for c in acting.get("graveyard", [])],
        "opponent_graveyard_cards": [c.get("card", "UNKNOWN") for c in opponent.get("graveyard", [])],
    }
    # Preserve per-creature detail for an entity encoder, instead of relying only on sums.
    entities = {
        "acting_creatures": [_creature_features(c) for c in own_creatures],
        "opponent_creatures": [_creature_features(c) for c in opp_creatures],
    }
    return numeric, categorical, entities


def _creature_features(card):
    return {
        "card": card.get("card", "UNKNOWN"),
        "power": float(card.get("power", 0)),
        "toughness": float(card.get("toughness", 0)),
        "damage": float(card.get("damage", 0)),
        "tapped": float(bool(card.get("tapped", False))),
        "summoning_sick": float(bool(card.get("summoning_sick", False))),
        "keywords": list(card.get("keywords", [])),
    }


def encode_decision(decision):
    """Return state features and one feature row per legal action, preserving labels."""
    state = decision.get("state", {})
    state_numeric, state_categorical, state_entities = _numeric_state(state, decision)
    actions = []
    for action in decision.get("available_actions", decision.get("actions", [])):
        action = action if isinstance(action, dict) else {"label": str(action)}
        action_numeric = {
            "mana_value": float(action.get("mana_value", 0)),
            "uses_targeting": float(bool(action.get("uses_targeting", False))),
            "legal_target_count": float(len(action.get("legal_targets", []))),
            "is_pass": float(action.get("kind") == "pass"),
            "is_spell": float(action.get("kind") == "cast_spell"),
        }
        actions.append({
            "action_id": action.get("action_id"),
            "numeric": action_numeric,
            "categorical": {
                "kind": [str(action.get("kind", "UNKNOWN"))],
                "source_card": [str(action.get("source_card", "NONE"))],
                "source_card_types": [str(token) for token in action.get("card_types", [])],
                "source_zone": [str(action.get("source_zone", "UNKNOWN"))],
                "mana_cost": [str(action.get("mana_cost", "UNKNOWN"))],
                "ability_api": [str(action.get("ability_api", "NONE"))],
                "target_cards": [str(t.get("target_card", "NONE")) for t in action.get("legal_targets", [])],
                "target_types": [str(t.get("target_type", "UNKNOWN")) for t in action.get("legal_targets", [])],
            },
        })
    return {
        "state_numeric": state_numeric,
        "state_categorical": state_categorical,
        "state_entities": state_entities,
        "actions": actions,
        "label_action_id": decision.get("oracle_action_id"),
    }


def build_vocabulary(records):
    """Build deterministic vocabularies from encoded training records only."""
    values = Counter()
    for record in records:
        for group in (record["state_categorical"],):
            for feature, tokens in group.items():
                values.update((feature, token) for token in tokens)
        for action in record["actions"]:
            for feature, tokens in action["categorical"].items():
                values.update((feature, token) for token in tokens)
        for side in record["state_entities"].values():
            for entity in side:
                values.update([("creature_card", entity["card"])])
                values.update(("creature_keyword", token) for token in entity["keywords"])
    grouped = {}
    for feature, token in sorted(values):
        grouped.setdefault(feature, {"<UNK>": 0})
        if token != "<UNK>" and token not in grouped[feature]:
            grouped[feature][token] = len(grouped[feature])
    return grouped
