"""Run Forge AI-vs-AI games headless via `forge sim` and summarize the results.

Run from anywhere; the subprocess runs with cwd = FORGE_DIR so Forge finds res/.
"""
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


FORGE_DIR = Path('/Users/zak/repos/forge/forge-gui-desktop/target') # folder containing res/ and the launcher
LAUNCHER = ["./forge.sh"]                                           # or ["java", "-Xmx4g", "-jar", "forge-gui-desktop-<ver>-jar-with-dependencies.jar"]
DECK_DIR = Path('/Users/zak/repos/mtg-ai-player/decks/')            # e.g. Path("/abs/path/to/decks") if the .dck files aren't in Forge's userdata decks folder
DECKS = ['AI Deck #1.dck', 'AI Deck #2.dck']

NUM_GAMES = 10


def run_games(decks, n=10, quiet=True, deck_dir=None, timeout=3600):
    """Returns the combined stdout/stderr text of one `sim` invocation."""
    # NOTE: all decks follow ONE -d flag. Repeating -d silently drops all but the last.
    cmd = LAUNCHER + ["sim", "-d", *decks, "-n", str(n)]
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
    winners = re.findall(r"(?im)game outcome:\s*(.+?)\s+has won", output)
    return Counter(winners)


if __name__ == "__main__":
    # Run the games
    out = run_games(DECKS, n=NUM_GAMES, quiet=False, deck_dir=DECK_DIR)
    Path("last_sim_output.txt").write_text(out)  # keep the raw output for debugging the parser
    counts = parse_winners(out)
