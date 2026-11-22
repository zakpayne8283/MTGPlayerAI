import forge.LobbyPlayer;
import forge.ai.PlayerControllerAi;
import forge.game.Game;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Behaves exactly like Forge's built-in AI (every method inherits from PlayerControllerAi).
 * The only addition is a counter on the main priority decision, which proves that Forge is
 * really calling YOUR class. Later, this is where decisions get routed to Python.
 */
public class PassThroughController extends PlayerControllerAi {
    public static final AtomicInteger PRIORITY_CALLS = new AtomicInteger();

    public PassThroughController(Game game, Player p, LobbyPlayer lp) {
        super(game, p, lp);
    }

    @Override
    public List<SpellAbility> chooseSpellAbilityToPlay() {
        PRIORITY_CALLS.incrementAndGet();
        // FUTURE HOOK: ask Python here instead of (or before) delegating.
        return super.chooseSpellAbilityToPlay();
    }
}
