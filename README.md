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
- `FORGE_VERSION`: Forge dependency version (default: `2.0.17-SNAPSHOT`).

Use `--verbose` to retain Forge's full game log. The runner writes Forge output to `last_bridge_output.txt` and prints a decision-count summary.
