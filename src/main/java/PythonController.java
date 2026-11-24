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
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
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
    private final String gameId;
    private int decisionSequence = 0;

    public PythonController(Game game, Player p, LobbyPlayer lp, String gameId) {
        super(game, p, lp);
        this.g = game;
        this.me = p;
        this.gameId = gameId;
    }

    @Override
    public List<SpellAbility> chooseSpellAbilityToPlay() {
        DECISIONS.incrementAndGet();

        // results.get(i) is what we return if Python picks index i. null == pass priority.
        List<List<SpellAbility>> results = new ArrayList<>();
        List<Map<String, Object>> actions = new ArrayList<>();
        results.add(null);
        actions.add(passAction(actionId(0), "Pass"));

        // Forge's choice is label metadata, never a special feature the learner could memorize.
        List<SpellAbility> aiPick = super.chooseSpellAbilityToPlay();
        int oracleIdx = aiPick == null || aiPick.isEmpty() ? 0 : -1;
        String oracleKey = oracleIdx == 0 ? null : actionKey(aiPick.get(0));
        for (SpellAbility sa : drivablePlays()) {
            List<SpellAbility> one = new ArrayList<>();
            one.add(sa);
            results.add(one);
            int index = results.size() - 1;
            actions.add(spellAction(sa, actionId(index), actionKind(sa)));
            if (oracleIdx < 0 && actionKey(sa).equals(oracleKey)) {
                oracleIdx = index;
                results.set(index, aiPick);
                copySelectedTargets(actions.get(index), aiPick.get(0));
            }
        }
        if (oracleIdx < 0) {
            // Preserve Forge plays outside the manually drivable subset as ordinary candidates.
            oracleIdx = results.size();
            results.add(aiPick);
            actions.add(spellAction(aiPick.get(0), actionId(oracleIdx), actionKind(aiPick.get(0))));
        }

        int priorityDecisionId = ++decisionSequence;
        // IDs are decision-scoped; rebuild them with the actual decision ID before sending.
        for (int i = 0; i < actions.size(); i++) actions.get(i).put("action_id", actionId(priorityDecisionId, i));
        String oracleActionId = actions.get(oracleIdx).get("action_id").toString();
        int idx = ask("priority", priorityDecisionId, null, stateSnapshot(null), actions, oracleActionId);
        List<SpellAbility> chosen = results.get(idx);

        // The oracle candidate already carries Forge's selected targets; our alternatives do not.
        if (chosen != null && idx != oracleIdx) {
            chooseTarget(chosen.get(0), priorityDecisionId);
        }
        return chosen;
    }

    /** Playable non-mana abilities with zero targets, or exactly one target that currently exists. */
    private List<SpellAbility> drivablePlays() {
        List<SpellAbility> res = new ArrayList<>();
        for (ZoneType z : PLAY_ZONES) {
            for (Card c : me.getCardsIn(z)) {
                for (SpellAbility sa : c.getAllPossibleAbilities(me, true)) {
                    // Mana abilities and payment remain Forge's responsibility.
                    if (sa.isManaAbility()) continue;
                    if (!ComputerUtilCost.canPayCost(sa, me, false)) continue;
                    if (sa.usesTargeting()) {
                        // Avoid abilities needing multiple or variable targets until that protocol exists.
                        if (!isSingleTarget(sa)) continue;
                        if (targetCandidates(sa).isEmpty()) continue;
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
    private void chooseTarget(SpellAbility sa, int parentDecisionId) {
        if (!sa.usesTargeting()) return;
        List<GameObject> cands = targetCandidates(sa);
        if (cands.isEmpty()) return;

        int targetDecisionId = ++decisionSequence;
        List<Map<String, Object>> actions = new ArrayList<>();
        for (int i = 0; i < cands.size(); i++) actions.add(targetAction(cands.get(i), actionId(targetDecisionId, i)));
        int i = ask("target", targetDecisionId, parentDecisionId,
                stateSnapshot(sa.getHostCard().getName()), actions, null);
        sa.resetTargets();
        sa.getTargets().add(cands.get(i));
    }

    private int ask(String kind, int decisionId, Integer parentDecisionId,
                    Object state, List<Map<String, Object>> actions, String oracleActionId) {
        Player active = g.getPhaseHandler().getPlayerTurn();
        Player priority = g.getPhaseHandler().getPriorityPlayer();
        return BridgeClient.ask(gameId, decisionId, parentDecisionId, kind,
                g.getPhaseHandler().getTurn(), active == null ? "" : active.getName(),
                priority == null ? "" : priority.getName(),
                String.valueOf(g.getPhaseHandler().getPhase()), state, actions, oracleActionId);
    }

    private List<GameObject> targetCandidates(SpellAbility sa) {
        List<GameObject> res = new ArrayList<>();
        // sa.canTarget applies the card's target restrictions; these zones are public information.
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

    private Map<String, Object> targetAction(GameObject o, String id) {
        Map<String, Object> action = new LinkedHashMap<>();
        action.put("action_id", id);
        action.put("kind", "target_choice");
        action.put("label", describeTarget(o));
        if (o instanceof Card) {
            Card c = (Card) o;
            action.put("target_type", "card");
            action.put("target_id", c.getId());
            action.put("target_card", c.getName());
            action.put("target_controller", c.getController() == me ? "acting_player" : "opponent");
        } else if (o instanceof Player) {
            Player p = (Player) o;
            action.put("target_type", "player");
            action.put("target_id", playerKey(p));
            action.put("target_player", p == me ? "acting_player" : "opponent");
        } else {
            action.put("target_type", "other");
        }
        return action;
    }

    private String describeTarget(GameObject o) {
        if (o instanceof Card) {
            Card card = (Card) o;
            return card.getName() + (card.getController() == me ? " [mine]" : " [opp]");
        }
        if (o instanceof Player) {
            Player player = (Player) o;
            return player.getName() + (player == me ? " [me]" : " [opp]");
        }
        return o.toString();
    }

    private Map<String, Object> passAction(String id, String label) {
        Map<String, Object> action = new LinkedHashMap<>();
        action.put("action_id", id);
        action.put("kind", "pass");
        action.put("label", label);
        return action;
    }

    private Map<String, Object> spellAction(SpellAbility sa, String id, String kind) {
        Card source = sa.getHostCard();
        Map<String, Object> action = new LinkedHashMap<>();
        action.put("action_id", id);
        action.put("kind", kind);
        action.put("label", describe(sa));
        action.put("source_card_id", source.getId());
        action.put("source_card", source.getName());
        action.put("source_zone", source.getZone() == null ? "unknown" : source.getZone().getZoneType().name());
        action.put("card_types", cardTypes(source));
        action.put("type_line", source.getType().toString());
        action.put("mana_cost", source.getManaCost().toString());
        action.put("mana_value", source.getCMC());
        action.put("ability_api", sa.getApi().name());
        action.put("ability", sa.toString());
        action.put("uses_targeting", sa.usesTargeting());
        List<Map<String, Object>> targets = new ArrayList<>();
        if (sa.usesTargeting()) {
            for (GameObject target : targetCandidates(sa)) targets.add(targetAction(target, null));
        }
        action.put("legal_targets", targets);
        List<Map<String, Object>> chosenTargets = new ArrayList<>();
        if (sa.getTargets() != null) {
            for (GameObject target : sa.getTargets().getTargetEntities()) chosenTargets.add(targetAction(target, null));
        }
        action.put("selected_targets", chosenTargets);
        return action;
    }

    private String actionKind(SpellAbility sa) {
        return sa.isSpell() ? "cast_spell" : "activate_ability";
    }

    private String actionKey(SpellAbility sa) {
        return sa.getHostCard().getId() + "|" + sa.getApi().name() + "|" + sa;
    }

    private void copySelectedTargets(Map<String, Object> action, SpellAbility oracle) {
        List<Map<String, Object>> targets = new ArrayList<>();
        if (oracle.getTargets() != null) {
            for (GameObject target : oracle.getTargets().getTargetEntities()) targets.add(targetAction(target, null));
        }
        action.put("selected_targets", targets);
    }

    private static String describe(SpellAbility sa) {
        return sa.getHostCard().getName() + ": " + sa;
    }

    private String actionId(int index) {
        return actionId(decisionSequence + 1, index);
    }

    private String actionId(int decisionId, int index) {
        return gameId + ":" + decisionId + ":" + index;
    }

    /** Observable facts for the acting player; opponent hand identities and libraries are omitted. */
    private Map<String, Object> stateSnapshot(String casting) {
        Map<String, Object> state = new LinkedHashMap<>();
        state.put("turn", g.getPhaseHandler().getTurn());
        state.put("phase", String.valueOf(g.getPhaseHandler().getPhase()));
        Player active = g.getPhaseHandler().getPlayerTurn();
        Player priority = g.getPhaseHandler().getPriorityPlayer();
        state.put("active_player", active == null ? null : playerKey(active));
        state.put("priority_player", priority == null ? null : playerKey(priority));
        state.put("acting_player", playerKey(me));
        List<Map<String, Object>> players = new ArrayList<>();
        for (Player p : g.getPlayers()) {
            Map<String, Object> player = new LinkedHashMap<>();
            player.put("id", playerKey(p));
            player.put("life", p.getLife());
            player.put("poison", p.getPoisonCounters());
            player.put("hand_size", p.getCardsIn(ZoneType.Hand).size());
            if (p == me) player.put("hand", cardList(p.getCardsIn(ZoneType.Hand), p));
            player.put("battlefield", cardList(p.getCardsIn(ZoneType.Battlefield), p));
            player.put("graveyard", cardList(p.getCardsIn(ZoneType.Graveyard), p));
            players.add(player);
        }
        state.put("players", players);
        if (casting != null) state.put("casting", casting);
        return state;
    }

    private List<Map<String, Object>> cardList(Iterable<Card> cards, Player perspective) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Card card : cards) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", card.getId());
            item.put("card", card.getName());
            item.put("types", cardTypes(card));
            item.put("type_line", card.getType().toString());
            item.put("controller", card.getController() == perspective ? "acting_player" : "opponent");
            item.put("mana_value", card.getCMC());
            if (card.isInPlay()) {
                item.put("tapped", card.isTapped());
                if (card.isCreature()) {
                    item.put("power", card.getNetPower());
                    item.put("toughness", card.getNetToughness());
                    item.put("damage", card.getDamage());
                    item.put("summoning_sick", card.isSick());
                    List<String> keywords = new ArrayList<>();
                    card.getKeywords().forEach(keyword -> keywords.add(keyword.toString()));
                    item.put("keywords", keywords);
                }
            }
            result.add(item);
        }
        return result;
    }

    private List<String> cardTypes(Card card) {
        List<String> types = new ArrayList<>();
        if (card.isCreature()) types.add("Creature");
        if (card.isLand()) types.add("Land");
        if (card.isInstant()) types.add("Instant");
        if (card.isSorcery()) types.add("Sorcery");
        if (card.isArtifact()) types.add("Artifact");
        if (card.isEnchantment()) types.add("Enchantment");
        if (card.isPlaneswalker()) types.add("Planeswalker");
        if (card.isBattle()) types.add("Battle");
        return types;
    }

    private String playerKey(Player player) {
        List<Player> players = g.getPlayers();
        return "player_" + (players.indexOf(player) + 1);
    }

}
