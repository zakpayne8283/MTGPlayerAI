"""Compile the Java bridge and run games, all from Python.

Put this next to forge_sim.py. Usage:  python build_and_run.py [num_games]
"""
from collections import Counter
import os
import re
import subprocess
import sys
from pathlib import Path

import agent

# ---- CONFIGS ----------------------------------------------------------------
FORGE_CLONE = Path("/Users/zak/repos/forge")                        # the repo you built with mvn
FORGE_DIR = Path("/Users/zak/repos/forge/forge-gui-desktop/target") # folder containing res/ (cwd for the game)
BRIDGE_SRC = Path('/Users/zak/repos/mtg-ai-player/bridge')          # folder with Launcher.java etc.
OUT_DIR = Path('/Users/zak/repos/mtg-ai-player/out')                # compiled classes go here
DECKS = ['AI Deck #1.dck', 'AI Deck #1.dck']                        # use the SAME deck twice for the sanity test
DECK_DIR = Path('/Users/zak/repos/mtg-ai-player/decks/')            # optional abs path to decks
FORGE_JAR = None                                                    # set explicitly to skip auto-detection
# -----------------------------------------------------------------------------


def find_jar():
    if FORGE_JAR:
        return Path(FORGE_JAR)
    jars = sorted((FORGE_CLONE / "forge-gui-desktop" / "target").glob("*jar-with-dependencies.jar"))
    if not jars:
        sys.exit(f"No *jar-with-dependencies.jar under {FORGE_CLONE}/forge-gui-desktop/target. "
                 "Set FORGE_JAR explicitly.")
    return jars[-1]


def compile_bridge(jar):
    OUT_DIR.mkdir(exist_ok=True)
    sources = [str(p) for p in BRIDGE_SRC.glob("*.java")]
    cmd = ["javac", "-cp", str(jar), "-d", str(OUT_DIR), *sources]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("javac not found. Install a JDK (not just a JRE) and make sure it's on PATH.")
    if proc.returncode != 0:
        print(proc.stdout + proc.stderr)
        sys.exit("Compile failed. Paste the errors above and we'll fix the signatures.")
    print(f"Compiled {len(sources)} files -> {OUT_DIR}")


def run_games(decks, launcher=None, n=10, quiet=True, deck_dir=None, timeout=3600):
    """Returns the combined stdout/stderr text of one `sim` invocation."""
    if launcher is None:
        raise Exception('LAUNCHER not set!')

    # NOTE: all decks follow ONE -d flag. Repeating -d silently drops all but the last.
    cmd = launcher + ["sim", "-d", *decks, "-n", str(n)]
    if deck_dir:
        cmd += ["-D", str(deck_dir)]
    if quiet:
        cmd.append("-q")
    proc = subprocess.run(cmd, cwd=FORGE_DIR, capture_output=True, text=True, timeout=timeout)
    return proc.stdout + proc.stderr


def parse_winners(output):
    """Count wins per player name.

    UNVERIFIED: the exact result line format is from memory ("Game outcome: <player> has won ...").
    Run once, look at the raw output, and adjust this regex if it returns nothing.
    """
    winners = re.findall(r"Game Result.*(Ai\(\d\))", output)
    return Counter(winners)

def main():
    # number of games to run
    num_games = 100

    # grab our jar file
    jar = find_jar()
    print("Using jar:", jar)
    # compile our bridge against that jar
    compile_bridge(jar)

    # Set the launcher value
    laucnher = ["java", "-Xmx4g", "-cp", os.pathsep.join([str(jar.resolve()), str(OUT_DIR.resolve())]), "Launcher"]

    # Run the simulated games
    # out = run_games(DECKS, launcher=laucnher, n=num_games, quiet=False, deck_dir=DECK_DIR)
    out, stats, messages, actions = agent.run_with_agent(
            launcher=laucnher,
            decks=DECKS,
            deck_dir=DECK_DIR,
            n=num_games,
            forge_dir=FORGE_DIR,
            quiet=True,
            policy=agent.random_policy
        )
    # output the results to a text file
    Path("last_bridge_output.txt").write_text(out)
    # Path('last_bridge_messages.txt').write_text('\n'.join([str(m) for m in messages]))
    
    # for a in actions:
    #     print(a)

    # count up the results
    counts = parse_winners(out)
    print(f"parsed {sum(counts.values())}/{num_games} games:", dict(counts))


    # if not counts:
    #     print("No results parsed. See last_bridge_output.txt")


if __name__ == "__main__":
    main()
