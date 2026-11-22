import java.io.*;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Tiny line-based client. Java sends one JSON line per decision; Python replies with one line
 * containing a single integer (the index into "actions"). No JSON library needed on this side.
 */
public class BridgeClient {
    private static BufferedReader in;
    private static PrintWriter out;
    private static Socket socket;

    public static boolean enabled() {
        return in != null;
    }

    /** Opens the single loopback connection shared by all decisions in one simulation batch. */
    public static void connect(int port) throws IOException {
        socket = new Socket("127.0.0.1", port);
        socket.setTcpNoDelay(true);
        in = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
        out = new PrintWriter(new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8), true);
    }

    public static void close() {
        try {
            if (socket != null) socket.close();
        } catch (IOException ignored) {
        }
    }

    /** synchronized: a timed-out game's leftover thread must not interleave with the next game. */
    public static synchronized int ask(String gameId, int decisionId, Integer parentDecisionId,
                                       String kind, int turn, String activePlayer, String priorityPlayer,
                                       String phase, String stateJson, List<String> actions) {
        StringBuilder sb = new StringBuilder();
        // Newline framing lets Python read one complete decision at a time without extra libraries.
        sb.append("{\"type\":\"decision\",\"schema_version\":1,\"game_id\":").append(q(gameId));
        sb.append(",\"decision_id\":").append(decisionId);
        if (parentDecisionId != null) sb.append(",\"parent_decision_id\":").append(parentDecisionId);
        sb.append(",\"kind\":").append(q(kind));
        sb.append(",\"turn\":").append(turn);
        sb.append(",\"active_player\":").append(q(activePlayer));
        sb.append(",\"priority_player\":").append(q(priorityPlayer));
        sb.append(",\"phase\":").append(q(phase));
        sb.append(",\"state\":").append(stateJson);
        sb.append(",\"actions\":").append(arr(actions)).append("}");
        out.println(sb);
        try {
            String line = in.readLine();
            if (line == null) throw new IllegalStateException("Python closed the connection");
            int idx = Integer.parseInt(line.trim());
            return (idx < 0 || idx >= actions.size()) ? 0 : idx; // clamp bad replies to index 0 (Pass)
        } catch (NumberFormatException e) {
            return 0;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** Send the terminal outcome for a game; unlike ask(), this message needs no reply. */
    public static synchronized void sendGameResult(String runId, String gameId, String outcome,
                                                   String winner, String reason, int turns) {
        if (!enabled()) return;
        StringBuilder sb = new StringBuilder("{\"type\":\"game_result\",\"schema_version\":1");
        sb.append(",\"run_id\":").append(q(runId));
        sb.append(",\"game_id\":").append(q(gameId));
        sb.append(",\"outcome\":").append(q(outcome));
        sb.append(",\"winner\":").append(winner == null ? "null" : q(winner));
        sb.append(",\"reason\":").append(q(reason));
        sb.append(",\"turns\":").append(turns).append("}");
        out.println(sb);
    }

    public static String q(String s) {
        // Escape JSON string content, including control characters, before writing protocol lines.
        StringBuilder sb = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default:
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                    else sb.append(c);
            }
        }
        return sb.append('"').toString();
    }

    public static String arr(List<String> items) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < items.size(); i++) {
            if (i > 0) sb.append(',');
            sb.append(q(items.get(i)));
        }
        return sb.append(']').toString();
    }
}
