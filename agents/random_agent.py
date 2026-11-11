from __future__ import annotations
import random

from engine.actions import legal_actions
from .base import (Pass, PriorityRequest, DeclareAttackersRequest,
                   DeclareBlockersRequest, DiscardRequest)


class RandomAgent:
    """Plays random legal actions. act_prob = chance to act (vs pass) whenever it has options."""

    def __init__(self, seed: int = 0, act_prob: float = 0.8, attack_prob: float = 0.5,
                 block_prob: float = 0.5):
        self.rng = random.Random(seed)
        self.act_prob, self.attack_prob, self.block_prob = act_prob, attack_prob, block_prob

    def choose(self, request):
        r = self.rng
        if isinstance(request, PriorityRequest):
            acts = legal_actions(request.state, request.player)
            return r.choice(acts) if acts and r.random() < self.act_prob else Pass()
        if isinstance(request, DeclareAttackersRequest):
            return [a for a in request.legal_attackers if r.random() < self.attack_prob]
        if isinstance(request, DeclareBlockersRequest):
            return {b: r.choice(request.attackers) for b in request.legal_blockers
                    if r.random() < self.block_prob}
        if isinstance(request, DiscardRequest):
            return r.sample(request.state.players[request.player].hand, request.count)
        raise NotImplementedError(type(request))
