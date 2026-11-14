from cards.card_def import CardDef, CardType, ManaCost
from cards.abilities.ability import Ability, AbilityKind, Trigger
from engine.effects import DealDamage
from engine.events import ZoneChange
from engine.state import Target, Zone

def land_entered(state, source, ev) -> bool:
    return (ev.to_zone is Zone.BATTLEFIELD and ev.new_id in state.objects
            and CardType.LAND in state.characteristics(ev.new_id).types)

def land_controller(state, source, ev) -> tuple[Target, ...]:
    return (Target("player", state.objects[ev.new_id].controller),)

class AnkhOfMishra(CardDef):
    # Card Info
    name = 'Ankh of Mishra'
    cost = ManaCost(generic=2)
    types = frozenset({CardType.ARTIFACT})
    abilities = (Ability(
        kind=AbilityKind.TRIGGERED,
        effects=(DealDamage(2),),
        trigger=Trigger(ZoneChange, land_entered, bind=land_controller)
    ),)


