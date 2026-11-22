"""Python side of the bridge: listen on a socket, launch Forge, answer decisions.

Java sends line-delimited decision messages and a game-result message after each game.
Python replies to decisions with one line containing an integer action index. Index 0
is always "Pass". The runner stores versioned decision and result records as JSONL.
"""
import json
import random
import socket
import subprocess
import tempfile
import time
import uuid
from pathlib import Path


# ---- policies: msg dict -> index into msg["actions"] ------------------------------------------
def random_policy(msg):
    return random.randrange(len(msg["actions"]))


def accept_ai_policy(msg):
    """Take the stock AI's suggestion when there is one, else pass. Should play like the stock AI."""
    for i, action in enumerate(msg["actions"]):
        if action.startswith("AI suggestion"):
            return i
    return 0


def action_kind(decision_kind, label, index):
    """Return a coarse category while available actions are still display labels."""
    if decision_kind == "target":
        return "target_choice"
    if index == 0:
        return "pass"
    if label.startswith("AI suggestion:"):
        return "ai_suggestion"
    return "play_ability"


def write_jsonl(stream, record):
    stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    stream.flush()


# ---- runner -------------------------------------------------------------------------------------
def run_with_agent(launcher, decks, n, forge_dir, policy, deck_dir=None, quiet=True,
                   port=5555, connect_timeout=120, timeout=3600, run_id=None,
                   log_dir="decision_logs"):
    """Run games with Python controlling seat 1 and write one JSONL log for the run.

    Returns (java_output_text, stats_dict, decision_messages, chosen_action_labels).
    """
    run_id = run_id or uuid.uuid4().hex
    log_path = Path(log_dir) / f"{run_id}.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")

    messages_sent = []
    actions = []

    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(1)
    server.settimeout(1.0)

    cmd = list(launcher) + ["sim", "-d", *decks, "-n", str(n),
                            "-run-id", run_id, "-port", str(port)]
    if deck_dir:
        cmd += ["-D", str(deck_dir)]
    if quiet:
        cmd.append("-q")

    # Java's stdout goes to a temp file so we never deadlock on a full pipe while serving the socket.
    out_file = tempfile.TemporaryFile("w+")
    proc = subprocess.Popen(cmd, cwd=forge_dir, stdout=out_file, stderr=subprocess.STDOUT, text=True)

    stats = {
        "decisions": 0,
        "kinds": {},
        "games": 0,
        "run_id": run_id,
        "decision_log": str(log_path),
    }
    conn = None
    stream = None
    try:
        # Wait for Java to connect, but notice if it dies first (bad classpath, compile mismatch, etc.).
        deadline = time.time() + connect_timeout
        while conn is None:
            try:
                conn, _ = server.accept()
            except socket.timeout:
                if proc.poll() is not None or time.time() > deadline:
                    break
        if conn is None:
            proc.kill()
            out_file.seek(0)
            raise RuntimeError("Java never connected. Its output:\n" + out_file.read()[-3000:])

        conn.settimeout(timeout)
        stream = conn.makefile("rw", encoding="utf-8")
        for line in stream:  # ends when Java closes the socket
            msg = json.loads(line)
            if msg.get("type") == "game_result":
                stats["games"] += 1
                write_jsonl(log_file, msg)
                continue
            if msg.get("type") != "decision":
                raise ValueError(f"Unknown bridge message type: {msg.get('type')!r}")

            messages_sent.append(msg)
            idx = int(policy(msg))
            if idx < 0 or idx >= len(msg["actions"]):
                idx = 0
            stats["decisions"] += 1
            stats["kinds"][msg["kind"]] = stats["kinds"].get(msg["kind"], 0) + 1
            actions.append(msg["actions"][idx])

            available_actions = [
                {
                    "action_id": f"{msg['game_id']}:{msg['decision_id']}:{i}",
                    "index": i,
                    "kind": action_kind(msg["kind"], label, i),
                    "label": label,
                }
                for i, label in enumerate(msg["actions"])
            ]
            chosen_action = available_actions[idx]
            write_jsonl(log_file, {
                "schema_version": 1,
                "record_type": "decision",
                "run_id": run_id,
                "game_id": msg["game_id"],
                "decision_id": msg["decision_id"],
                "parent_decision_id": msg.get("parent_decision_id"),
                "kind": msg["kind"],
                "turn": msg["turn"],
                "active_player": msg["active_player"],
                "priority_player": msg["priority_player"],
                "phase": msg["phase"],
                "state": msg["state"],
                "available_actions": available_actions,
                "chosen_action_id": chosen_action["action_id"],
                "chosen_action": chosen_action,
                "result": None,
            })
            stream.write(f"{idx}\n")
            stream.flush()
    finally:
        if stream is not None:
            stream.close()
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
        server.close()
        log_file.close()

    out_file.seek(0)
    text = out_file.read()
    out_file.close()
    if proc.returncode != 0:
        print(f"Java exited with code {proc.returncode}. Tail of output:\n{text[-2000:]}")
    return text, stats, messages_sent, actions
