"""Build the Maven bridge and run Forge simulations through the Python agent.

Usage: python build_and_run.py [num_games]

Set FORGE_REPO when the Forge checkout is not next to this repository. Forge's
matching Maven modules must be installed locally; see the project README.
"""
import argparse
from collections import Counter
import os
import re
import subprocess
import sys
from pathlib import Path

import agent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORGE_REPO = Path(os.environ.get("FORGE_REPO", PROJECT_ROOT.parent / "forge")).expanduser()
FORGE_VERSION = os.environ.get("FORGE_VERSION", "2.0.17-SNAPSHOT")
FORGE_DIR = Path(os.environ.get(
    "FORGE_DIR", FORGE_REPO / "forge-gui-desktop" / "target"
)).expanduser()
FORGE_ASSETS_DIR = Path(os.environ.get(
    "FORGE_ASSETS_DIR", FORGE_REPO / "forge-gui"
)).expanduser().resolve()
DECK_DIR = Path(os.environ.get("DECK_DIR", PROJECT_ROOT / "decks")).expanduser()
DECISION_LOG_DIR = Path(os.environ.get(
    "DECISION_LOG_DIR", PROJECT_ROOT / "decision_logs"
)).expanduser()
DECKS = ["AI Deck #1.dck", "AI Deck #1.dck"]
MAIN_CLASS = "Launcher"


def run_checked(command, *, cwd, description):
    try:
        return subprocess.run(command, cwd=cwd, check=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required executable not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{description} failed (exit code {exc.returncode}).") from exc


def build_bridge():
    # Compile the standard Maven source tree against the selected Forge snapshot.
    run_checked(["mvn", "-q", f"-Drevision={FORGE_VERSION}",
                 f"-Dforge.version={FORGE_VERSION}", "-DskipTests", "package"],
                cwd=PROJECT_ROOT, description="Maven bridge build")
    classpath_file = PROJECT_ROOT / "target" / "dependency-classpath.txt"
    run_checked([
        "mvn", "-q", f"-Drevision={FORGE_VERSION}",
        f"-Dforge.version={FORGE_VERSION}", "-DincludeScope=runtime",
        f"-Dmdep.outputFile={classpath_file}", "dependency:build-classpath",
    ], cwd=PROJECT_ROOT, description="Maven runtime classpath generation")
    if not classpath_file.is_file():
        raise RuntimeError(f"Maven did not create the runtime classpath at {classpath_file}")
    # Launch with bridge classes first, followed by Forge's transitive runtime dependencies.
    return os.pathsep.join([
        str(PROJECT_ROOT / "target" / "classes"),
        classpath_file.read_text(encoding="utf-8").strip(),
    ])


def run_games(classpath, n, quiet=True):
    if not FORGE_DIR.is_dir():
        raise RuntimeError(f"Forge runtime directory not found: {FORGE_DIR}")
    launcher = [
        "java", f"-Dforge.assetsDir={FORGE_ASSETS_DIR}", "-Xmx4g",
        "-cp", classpath, MAIN_CLASS,
    ]
    output, stats, messages, actions = agent.run_with_agent(
        launcher=launcher,
        decks=DECKS,
        deck_dir=DECK_DIR,
        n=n,
        forge_dir=FORGE_DIR,
        quiet=quiet,
        policy=agent.random_policy,
        log_dir=DECISION_LOG_DIR,
    )
    (PROJECT_ROOT / "last_bridge_output.txt").write_text(output, encoding="utf-8")
    print(f"Python decisions: {stats['decisions']} ({stats['kinds']})")
    print(f"Completed games: {stats['games']}; decision log: {stats['decision_log']}")
    return output, messages, actions


def parse_args():
    parser = argparse.ArgumentParser(description="Build the bridge and run Forge simulations.")
    parser.add_argument("num_games", nargs="?", type=int, default=100)
    parser.add_argument("--verbose", action="store_true", help="Keep Forge's full game log.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        classpath = build_bridge()
        output, _, _ = run_games(classpath, args.num_games, quiet=not args.verbose)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        print(
            "If Forge dependencies are missing, install the matching Forge modules with:\n"
            f"  cd '{FORGE_REPO}' && mvn -Drevision={FORGE_VERSION} "
            "-pl forge-gui-desktop -am "
            "org.codehaus.mojo:flatten-maven-plugin:1.6.0:flatten "
            "-DskipTests install",
            file=sys.stderr,
        )
        return 1

    winners = Counter(re.findall(
        r"Game Result: Game \d+ ended in \d+ ms\. (Ai\(\d+\))", output
    ))
    if winners:
        print(f"parsed {sum(winners.values())}/{args.num_games} games: {dict(winners)}")
    else:
        print(f"Saved Forge output for {args.num_games} games to last_bridge_output.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
