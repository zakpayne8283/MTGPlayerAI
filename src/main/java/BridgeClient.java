import com.google.gson.Gson;

import java.io.*;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Line-based JSON client between Forge and the Python policy. */
public class BridgeClient {
    private static BufferedReader in;
    private static PrintWriter out;
    private static Socket socket;
    private static final Gson GSON = new Gson();

    public static boolean enabled() { return in != null; }

    public static void connect(int port) throws IOException {
        socket = new Socket("127.0.0.1", port);
        socket.setTcpNoDelay(true);
        in = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
        out = new PrintWriter(new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8), true);
    }

    public static void close() {
        try { if (socket != null) socket.close(); } catch (IOException ignored) { }
    }

    public static synchronized int ask(String gameId, int decisionId, Integer parentDecisionId,
                                       String kind, int turn, String activePlayer, String priorityPlayer,
                                       String phase, Object state, List<Map<String, Object>> actions,
                                       String oracleActionId) {
        Map<String, Object> message = new LinkedHashMap<>();
        message.put("type", "decision");
        message.put("schema_version", 2);
        message.put("game_id", gameId);
        message.put("decision_id", decisionId);
        if (parentDecisionId != null) message.put("parent_decision_id", parentDecisionId);
        message.put("kind", kind);
        message.put("turn", turn);
        message.put("active_player", activePlayer);
        message.put("priority_player", priorityPlayer);
        message.put("phase", phase);
        message.put("state", state);
        message.put("actions", actions);
        message.put("oracle_action_id", oracleActionId);
        out.println(GSON.toJson(message));
        try {
            String line = in.readLine();
            if (line == null) throw new IllegalStateException("Python closed the connection");
            int idx = Integer.parseInt(line.trim());
            return (idx < 0 || idx >= actions.size()) ? 0 : idx;
        } catch (NumberFormatException e) {
            return 0;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public static synchronized void sendGameResult(String runId, String gameId, String outcome,
                                                   String winner, String reason, int turns) {
        if (!enabled()) return;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("type", "game_result");
        result.put("schema_version", 2);
        result.put("run_id", runId);
        result.put("game_id", gameId);
        result.put("outcome", outcome);
        result.put("winner", winner);
        result.put("reason", reason);
        result.put("turns", turns);
        out.println(GSON.toJson(result));
    }
}
