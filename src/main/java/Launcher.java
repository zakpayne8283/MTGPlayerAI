import forge.GuiDesktop;
import forge.ai.PlayerControllerAi;
import forge.deck.Deck;
import forge.deck.io.DeckSerializer;
import forge.game.Game;
import forge.game.GameEndReason;
import forge.game.GameLogEntry;
import forge.game.GameLogEntryType;
import forge.game.GameRules;
import forge.game.GameType;
import forge.game.Match;
import forge.game.player.Player;
import forge.game.player.RegisteredPlayer;
import forge.gui.GuiBase;
import forge.localinstance.properties.ForgeConstants;
import forge.model.FModel;
import forge.player.GamePlayerUtil;
import forge.view.TimeLimitedCodeBlock;

import org.apache.commons.lang3.time.StopWatch;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Mirrors SimulateMatch, with one change: seat 1's controller is swapped for ours.
 *
 * CLI (subset of `forge sim`, plus -port):
 *   Launcher sim -d deck1.dck deck2.dck -n 10 [-D dir] [-q] [-port 5555]
 *
 * Without -port: seat 1 = PassThroughController (identical to stock AI).
 * With -port:    seat 1 = PythonController (Python decides priority actions).
 * Seat 2 is always the stock AI. Run with cwd = your Forge folder (the one containing res/).
 */
public class Launcher {
    private static boolean quiet = false;

    public static void main(String[] args) throws Exception {
        List<String> decks = new ArrayList<>();
        int nGames = 1;
        String deckDir = null;
        Integer port = null;
        String runId = UUID.randomUUID().toString();
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "sim": break;
                case "-q": quiet = true; break;
                case "-n": nGames = Integer.parseInt(args[++i]); break;
                case "-D": deckDir = args[++i]; break;
                case "-port": port = Integer.parseInt(args[++i]); break;
                case "-run-id": runId = args[++i]; break;
                case "-d":
                    // Forge's sim syntax uses one -d flag followed by both deck names.
                    while (i + 1 < args.length && !args[i + 1].startsWith("-")) decks.add(args[++i]);
                    break;
                default: System.err.println("Ignoring unknown arg " + args[i]);
            }
        }
        if (decks.size() != 2) {
            System.err.println("Need exactly two decks after -d");
            System.exit(1);
        }

        if (port != null) {
            // Python starts the listener before launching this process, so connect once per batch.
            BridgeClient.connect(port);
        }

        // Point Forge at the shared assets folder explicitly. GuiDesktop's default is relative to
        // its expected launch layout, which differs when we launch from the Maven classpath.
        String assetsDir = System.getProperty("forge.assetsDir");
        GuiBase.setInterface(new GuiDesktop() {
            @Override
            public String getAssetsDir() {
                if (assetsDir == null || assetsDir.isBlank()) {
                    return super.getAssetsDir();
                }
                return assetsDir.endsWith(File.separator) ? assetsDir : assetsDir + File.separator;
            }
        });
        FModel.initialize(null, null);

        GameType type = GameType.Constructed;
        GameRules rules = new GameRules(type);
        rules.setAppliedVariants(EnumSet.of(type));

        List<RegisteredPlayer> pp = new ArrayList<>();
        for (int i = 0; i < 2; i++) {
            Deck d = loadDeck(decks.get(i), deckDir);
            if (d == null) {
                System.err.println("Could not load deck - " + decks.get(i));
                System.exit(1);
            }
            String name = "Ai(" + (i + 1) + ")-" + d.getName();
            RegisteredPlayer rp = new RegisteredPlayer(d);
            rp.setPlayer(GamePlayerUtil.createAiPlayer(name, i, ""));
            pp.add(rp);
        }

        Match mc = new Match(rules, pp, "Test");
        // Reuse the match configuration while creating a fresh game state for each game.
        for (int g = 0; g < nGames; g++) {
            playOne(mc, g, runId);
        }
        System.err.println("PassThroughController priority calls: " + PassThroughController.PRIORITY_CALLS.get());
        System.err.println("PythonController decisions: " + PythonController.DECISIONS.get());
        System.out.flush();
        BridgeClient.close();
        System.exit(0); // Forge can leave non-daemon threads running
    }

    private static void playOne(Match mc, int idx, String runId) {
        StopWatch sw = new StopWatch();
        sw.start();
        final Game game = mc.createGame();
        game.setNoGUIUser();

        // setFirstController is one-shot and already used at game creation, so we temporarily
        // swap the controller for the duration of the game instead.
        final Player seat1 = game.getPlayers().get(0);
        final String gameId = runId + "-game-" + (idx + 1);
        final PlayerControllerAi mine = BridgeClient.enabled()
                ? new PythonController(game, seat1, seat1.getOriginalLobbyPlayer(), gameId)
                : new PassThroughController(game, seat1, seat1.getOriginalLobbyPlayer());

        try {
            TimeLimitedCodeBlock.runWithTimeout(() -> {
                seat1.runWithController(() -> { mc.startGame(game); }, mine);
            }, mc.getRules().getSimTimeout(), TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            System.out.println("Stopping slow match as draw");
        } catch (Exception | StackOverflowError e) {
            e.printStackTrace();
        } finally {
            if (sw.isStarted()) sw.stop();
            game.setGameOver(GameEndReason.Draw);
        }

        // Forge stores the newest log entry first; reverse it for normal chronological output.
        List<GameLogEntry> log = quiet
                ? game.getGameLog().getLogEntries(GameLogEntryType.MATCH_RESULTS)
                : game.getGameLog().getLogEntries(null);
        Collections.reverse(log);
        for (GameLogEntry entry : log) {
            System.out.println(entry);
        }

        if (game.getOutcome().isDraw()) {
            System.out.printf("%nGame Result: Game %d ended in a Draw! Took %d ms.%n", 1 + idx, sw.getTime());
            BridgeClient.sendGameResult(runId, gameId, "draw", null,
                    game.getOutcome().getWinCondition().name(), game.getPhaseHandler().getTurn());
        } else {
            String winner = game.getOutcome().getWinningLobbyPlayer().getName();
            System.out.printf("%nGame Result: Game %d ended in %d ms. %s has won!%n%n",
                    1 + idx, sw.getTime(), winner);
            BridgeClient.sendGameResult(runId, gameId, "win", winner,
                    game.getOutcome().getWinCondition().name(), game.getPhaseHandler().getTurn());
        }
    }

    private static Deck loadDeck(String name, String deckDir) {
        File direct = new File(name);
        if (direct.isFile()) return DeckSerializer.fromFile(direct);
        String base = deckDir != null ? deckDir : ForgeConstants.DECK_CONSTRUCTED_DIR;
        if (!base.endsWith(File.separator)) base += File.separator;
        return DeckSerializer.fromFile(new File(base + name));
    }
}
