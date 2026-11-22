import forge.LobbyPlayer;
import forge.ai.PlayerControllerAi;
import forge.game.Game;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;

import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Behaves exactly like Forge's built-in AI (every method inherits from PlayerControllerAi).
 * The only addition is a counter on the main priority decision. This is the no-bridge baseline;
 * when Python is connected, Launcher uses PythonController instead.
 */
public class PassThroughController extends PlayerControllerAi {
    public static final AtomicInteger PRIORITY_CALLS = new AtomicInteger();

    public PassThroughController(Game game, Player p, LobbyPlayer lp) {
        super(game, p, lp);
    }

    @Override
    public List<SpellAbility> chooseSpellAbilityToPlay() {
        PRIORITY_CALLS.incrementAndGet();
        return super.chooseSpellAbilityToPlay();
    }
}
