import forge.LobbyPlayer;
import forge.ai.ComputerUtilCost;
import forge.ai.PlayerControllerAi;
import forge.game.Game;
import forge.game.GameObject;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.spellability.TargetRestrictions;
import forge.game.zone.ZoneType;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Forge AI for everything EXCEPT the main priority decision, which Python makes.
 *
 * Priority options sent to Python (index 0 is always Pass):
 *   0           Pass
 *   1 (if any)  "AI suggestion: ..."  -> what the stock AI would play, already targeted
 *   rest        every playable non-mana ability we can drive ourselves:
 *                 - abilities that need no targets
 *                 - abilities that need exactly ONE target (e.g. Swords to Plowshares),
 *                   provided at least one legal target exists
 *
 * If Python picks a single-target ability, we send a second message (kind "target") listing the
 * legal targets, and set the chosen target on the ability before returning it.
 *
 * Multi-target and variable-target abilities are skipped for now (only reachable through the AI
 * suggestion). Mana payment, combat, mulligans, etc. all stay on Forge's AI.
 *
 * Unverified-from-source calls (from memory; expect to fix signatures at compile time):
 *   ComputerUtilCost.canPayCost(sa, player, false), SpellAbility.usesTargeting()/isManaAbility()/
 *   canTarget(GameObject)/resetTargets()/getTargets().add(...), TargetRestrictions.getMin/MaxTargets
 *   (host, sa), Game.getCardsIn(ZoneType).
 */
public class PythonController extends PlayerControllerAi {
    public static final AtomicInteger DECISIONS = new AtomicInteger();

    private static final ZoneType[] PLAY_ZONES = {
        ZoneType.Hand, ZoneType.Battlefield, ZoneType.Graveyard,
        ZoneType.Exile, ZoneType.Command, ZoneType.Flashback
    };

    // Public zones only, so targeting never reveals hidden information.
    private static final ZoneType[] TARGET_ZONES = {
        ZoneType.Battlefield, ZoneType.Stack, ZoneType.Graveyard
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

        int aiIdx = -1;
        List<SpellAbility> aiPick = super.chooseSpellAbilityToPlay();
        if (aiPick != null && !aiPick.isEmpty()) {
            aiIdx = results.size();
            results.add(aiPick);
            labels.add("AI suggestion: " + describe(aiPick.get(0)));
        }

        for (SpellAbility sa : drivablePlays()) {
            List<SpellAbility> one = new ArrayList<>();
            one.add(sa);
            results.add(one);
            labels.add(describe(sa));
        }

        int idx = BridgeClient.ask("priority", stateJson(null), labels);
        List<SpellAbility> chosen = results.get(idx);

        // The AI's own suggestion already has its targets set. Ours do not, so set them now.
        if (chosen != null && idx != aiIdx) {
            chooseTarget(chosen.get(0));
        }
        return chosen;
    }

    /** Playable non-mana abilities with zero targets, or exactly one target that currently exists. */
    private List<SpellAbility> drivablePlays() {
        List<SpellAbility> res = new ArrayList<>();
        for (ZoneType z : PLAY_ZONES) {
            for (Card c : me.getCardsIn(z)) {
                for (SpellAbility sa : c.getAllPossibleAbilities(me, true)) {
                    if (sa.isManaAbility()) continue;                    // mana is auto-paid by Forge AI
                    if (!ComputerUtilCost.canPayCost(sa, me, false)) continue;
                    if (sa.usesTargeting()) {
                        if (!isSingleTarget(sa)) continue;
                        if (targetCandidates(sa).isEmpty()) continue;    // would be uncastable -> loop
                    }
                    res.add(sa);
                }
            }
        }
        return res;
    }

    private boolean isSingleTarget(SpellAbility sa) {
        TargetRestrictions tr = sa.getTargetRestrictions();
        if (tr == null) return false;
        Card host = sa.getHostCard();
        return tr.getMinTargets(host, sa) <= 1 && tr.getMaxTargets(host, sa) >= 1;
    }

    /** Ask Python which legal target to use, and set it on the ability. */
    private void chooseTarget(SpellAbility sa) {
        if (!sa.usesTargeting()) return;
        List<GameObject> cands = targetCandidates(sa);
        if (cands.isEmpty()) return;

        List<String> labels = new ArrayList<>();
        for (GameObject o : cands) labels.add(describeTarget(o));

        int i = BridgeClient.ask("target", stateJson(sa.getHostCard().getName()), labels);
        sa.resetTargets();
        sa.getTargets().add(cands.get(i));
    }

    private List<GameObject> targetCandidates(SpellAbility sa) {
        List<GameObject> res = new ArrayList<>();
        for (ZoneType z : TARGET_ZONES) {
            for (Card c : g.getCardsIn(z)) {
                if (sa.canTarget(c)) res.add(c);
            }
        }
        for (Player p : g.getPlayers()) {
            if (sa.canTarget(p)) res.add(p);
        }
        return res;
    }

    private String describeTarget(GameObject o) {
        if (o instanceof Card) {
            Card c = (Card) o;
            return c.getName() + (c.getController() == me ? " [mine]" : " [opp]");
        }
        if (o instanceof Player) {
            return ((Player) o).getName() + (o == me ? " [me]" : " [opp]");
        }
        return o.toString();
    }

    private static String describe(SpellAbility sa) {
        return sa.getHostCard().getName() + ": " + sa;
    }

    /** Deliberately small for now. Only what this player can legally see. */
    private String stateJson(String casting) {
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
        if (casting != null) sb.append(",\"casting\":").append(BridgeClient.q(casting));
        return sb.append("}").toString();
    }
}
