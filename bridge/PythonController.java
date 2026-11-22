import forge.LobbyPlayer;
import forge.ai.ComputerUtilCost;
import forge.ai.PlayerControllerAi;
import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Forge AI for everything EXCEPT the main priority decision, which Python makes.
 *
 * Options sent to Python (index 0 is always Pass):
 *   0           Pass
 *   1 (if any)  "AI suggestion: ..."  -> exactly what the stock AI would have played,
 *               already targeted, so it is always safe to accept
 *   rest        every playable non-mana ability that needs NO targets
 *
 * Targeted plays other than the AI's own suggestion are not offered yet (setting targets
 * ourselves is the next step). Mana payment, combat, mulligans, etc. all stay on Forge's AI.
 *
 * Unverified-from-source calls: ComputerUtilCost.canPayCost(sa, player, false) and
 * SpellAbility.usesTargeting()/isManaAbility(). Expect to fix signatures at compile time.
 */
public class PythonController extends PlayerControllerAi {
    public static final AtomicInteger DECISIONS = new AtomicInteger();

    private static final ZoneType[] PLAY_ZONES = {
        ZoneType.Hand, ZoneType.Battlefield, ZoneType.Graveyard,
        ZoneType.Exile, ZoneType.Command, ZoneType.Flashback
    };

    private final Game g;
    private final Player me;

    public PythonController(Game game, Player p, LobbyPlayer lp) {
        super(game, p, lp);
        this.g = game;
        this.me = p;
    }

    @Override
    public List<SpellAbility> chooseSpellAbilityToPlay() {
        DECISIONS.incrementAndGet();

        // results.get(i) is what we return if Python picks index i. null == pass priority.
        List<List<SpellAbility>> results = new ArrayList<>();
        List<String> labels = new ArrayList<>();
        results.add(null);
        labels.add("Pass");

        List<SpellAbility> aiPick = super.chooseSpellAbilityToPlay();
        if (aiPick != null && !aiPick.isEmpty()) {
            results.add(aiPick);
            labels.add("AI suggestion: " + describe(aiPick.get(0)));
        }

        for (SpellAbility sa : untargetedPlays()) {
            List<SpellAbility> one = new ArrayList<>();
            one.add(sa);
            results.add(one);
            labels.add(describe(sa));
        }

        int idx = BridgeClient.ask("priority", stateJson(), labels);
        return results.get(idx);
    }

    private List<SpellAbility> untargetedPlays() {
        List<SpellAbility> res = new ArrayList<>();
        for (ZoneType z : PLAY_ZONES) {
            for (Card c : me.getCardsIn(z)) {
                for (SpellAbility sa : c.getAllPossibleAbilities(me, true)) {
                    if (sa.isManaAbility()) continue;                    // mana is auto-paid by Forge AI
                    if (sa.usesTargeting()) continue;                    // targets: next step
                    if (!ComputerUtilCost.canPayCost(sa, me, false)) continue;
                    res.add(sa);
                }
            }
        }
        return res;
    }

    private static String describe(SpellAbility sa) {
        return sa.getHostCard().getName() + ": " + sa;
    }

    /** Deliberately small for now. Only what this player can legally see. */
    private String stateJson() {
        StringBuilder sb = new StringBuilder("{");
        sb.append("\"turn\":").append(g.getPhaseHandler().getTurn());
        sb.append(",\"phase\":").append(BridgeClient.q(String.valueOf(g.getPhaseHandler().getPhase())));
        sb.append(",\"my_life\":").append(me.getLife());
        for (Player p : g.getPlayers()) {
            if (p != me) sb.append(",\"opp_life\":").append(p.getLife());
        }
        List<String> hand = new ArrayList<>();
        for (Card c : me.getCardsIn(ZoneType.Hand)) hand.add(c.getName());
        sb.append(",\"hand\":").append(BridgeClient.arr(hand));
        return sb.append("}").toString();
    }
}
