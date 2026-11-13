from cards.abilities.combat_ability import CombatAbility
from cards.abilities.keywords.reach import REACH

FLYING = CombatAbility(
    name = 'Flying',
    can_be_blocked_by=lambda me, blk: blk.has(FLYING) or blk.has(REACH)
)