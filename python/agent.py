"""Python side of the bridge: listen on a socket, launch Forge, answer every decision.

Protocol: Java sends one JSON line per decision:
    {"type":"decision","kind":"priority","state":{...},"actions":["Pass","AI suggestion: ...", ...]}
Python replies with one line containing an integer, the index into "actions".
Index 0 is always "Pass".
"""
import json
import random
import socket
import subprocess
import tempfile
import time

# ---- policies: msg dict -> index into msg["actions"] --------------------------------------------
def random_policy(msg):
    return random.randrange(len(msg["actions"]))


def accept_ai_policy(msg):
    """Take the stock AI's suggestion when there is one, else pass. Should play like the stock AI."""
    for i, a in enumerate(msg["actions"]):
        if a.startswith("AI suggestion"):
            return i
    return 0


# ---- runner -------------------------------------------------------------------------------------
def run_with_agent(launcher, decks, n, forge_dir, policy, deck_dir=None, quiet=True,
                   port=5555, connect_timeout=120, timeout=3600):
    """Run n games with Python making seat 1's priority decisions.

    Returns (java_output_text, stats_dict).
    """
    # messages_sent = []

    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", port))
    server.listen(1)
    server.settimeout(1.0)

    cmd = list(launcher) + ["sim", "-d", *decks, "-n", str(n), "-port", str(port)]
    if deck_dir:
        cmd += ["-D", str(deck_dir)]
    if quiet:
        cmd.append("-q")

    # Java's stdout goes to a temp file so we never deadlock on a full pipe while serving the socket.
    out_file = tempfile.TemporaryFile("w+")
    proc = subprocess.Popen(cmd, cwd=forge_dir, stdout=out_file, stderr=subprocess.STDOUT, text=True)

    stats = {"decisions": 0, "kinds": {}}
    conn = None
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
        f = conn.makefile("rw", encoding="utf-8")
        for line in f:  # ends when Java closes the socket
            msg = json.loads(line)
            # messages_sent.append(msg)
            idx = int(policy(msg))
            stats["decisions"] += 1
            stats["kinds"][msg["kind"]] = stats["kinds"].get(msg["kind"], 0) + 1
            f.write(f"{idx}\n")
            f.flush()
    finally:
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
        server.close()

    out_file.seek(0)
    text = out_file.read()
    out_file.close()
    if proc.returncode != 0:
        print(f"Java exited with code {proc.returncode}. Tail of output:\n{text[-2000:]}")
    return text, stats#, messages_sent
