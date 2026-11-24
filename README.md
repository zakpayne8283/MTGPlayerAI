# MTG AI Player

This project runs Forge simulations with a Python policy making priority decisions through a small Java bridge.

## Build the Java bridge

The bridge is a standalone Maven project. It depends on Forge `forge-gui-desktop` version `2.0.17-SNAPSHOT`; Forge itself must be installed into your local Maven repository first. From this repository, run:

```sh
cd ../forge
mvn -Drevision=2.0.17-SNAPSHOT \
  -pl forge-gui-desktop -am \
  org.codehaus.mojo:flatten-maven-plugin:1.6.0:flatten \
  -DskipTests install

cd -
mvn -Drevision=2.0.17-SNAPSHOT -DskipTests package
```

The `flatten` goal is required because Forge uses `${revision}` in its Maven parent coordinates. It creates consumer-ready POMs for the local install. The first command builds Forge and its required modules; the second compiles and packages this bridge.

## Run simulations

```sh
python3 python/build_and_run.py 10
```

The game count defaults to 100. Forge's runtime working directory defaults to `forge-gui-desktop/target`; its shared assets are loaded from `forge-gui/`. Decks are read from this repository's `decks/` directory. Set these environment variables if your layout differs:

- `FORGE_REPO`: path to the Forge checkout (default: `../forge`).
- `FORGE_DIR`: Forge runtime directory containing `res/` (default: `$FORGE_REPO/forge-gui-desktop/target`).
- `FORGE_ASSETS_DIR`: Forge assets directory containing `res/` (default: `$FORGE_REPO/forge-gui`).
- `DECK_DIR`: deck directory (default: this repository's `decks/`).
- `DECISION_LOG_DIR`: directory for per-run JSONL decision/outcome logs (default: this repository's `decision_logs/`).
- `FORGE_VERSION`: Forge dependency version (default: `2.0.17-SNAPSHOT`).

Use `--verbose` to retain Forge's full game log. The runner writes Forge output to `last_bridge_output.txt` and one JSONL file per run with decision context, structured available actions, the Python choice, Forge's oracle choice when available, and game outcomes. Decision records use schema version 2; the validator still accepts archived schema-1 logs.

Run the ordered 5×5 v1 deck matchup grid with 400 games per cell for all three baseline policies:

```sh
python3 python/build_and_run.py --matrix --games-per-matchup 400
```

The rows are the deck controlled by Python in seat 1; columns are the stock Forge AI deck in seat 2. The default policies are `forge` (select Forge's labeled priority choice), `pass` (always pass priority), and `random` (choose a random offered option). Select policies with, for example, `--policies forge random`. Each cell prints seat 1's win count and rate. Forge randomly picks an initial player for the first game; its AI then keeps that choice, so starting seat is randomized across simulations rather than fixed by deck order.

Validate a completed decision log with:

```sh
python3 python/validate_decision_log.py decision_logs/your-run-id.jsonl
```

Run the Python unit tests with:

```sh
python3 -m unittest discover -s python -p 'test_*.py' -v
```
