# Project roadmap

This project has a working prototype: Forge runs games, Java intercepts the Python-controlled player's priority decisions, and Python selects from the choices Java sends. The next goal is to make that loop reproducible and observable before collecting data for learning.

## Recommended order

1. **Make the Java bridge build reproducible** so every later change compiles against the intended Forge version.
2. **Define a versioned decision record and improve logging**; use it as both human-readable diagnostics and the eventual training-data format.
3. **Expand the game-state snapshot** to support meaningful decisions, while keeping the external record stable as features evolve.
4. **Collect baseline games and decide on a learning method** using the state, legal actions, choices, and results produced above.

The exact order can change if preserving the current build flow is useful, but the record schema should be agreed before building a large dataset.

## 1. Java bridge as a Maven module

**Practical and recommended.** The Java bridge imports Forge classes and currently compiles by locating a Forge fat jar and invoking `javac` itself. A Maven module would declare these dependencies, manage Java 17 compilation, and make API mismatches visible during a normal build.

Forge already has a Maven reactor with separate `forge-game`, `forge-ai`, and `forge-gui-desktop` modules. The bridge needs the desktop implementation used by `Launcher` as well as game/AI APIs. Prefer depending on the narrowest Forge modules that cover the imports; use `forge-gui-desktop` if needed, since it brings the appropriate runtime graph.

The main setup decision is dependency resolution because Forge is a sibling checkout and uses a snapshot version. Options:

- **Recommended for this two-checkout setup:** build/install the required Forge modules from the Forge checkout into the local Maven repository, then build the bridge against that declared Forge version. Add a small script or documented command that makes this repeatable.
- **Tighter coupled alternative:** place the bridge in Forge's Maven reactor as another module. This gives reactor-aware builds, but couples this project to the Forge checkout and may be awkward if the bridge is meant to stay independent.
- Avoid `systemPath` references to a jar or compiled Forge `target` directory; they preserve the current machine-specific setup in a different form.

**Steps**

- [x] Choose an independent bridge module; Forge stays a dependency rather than a required parent checkout.
- [x] Add a `pom.xml` with Forge dependency coordinates, Java 17 settings, and an executable entry point.
- [x] Move Java sources into Maven's standard source layout.
- [x] Replace `build_and_run.py`'s `javac` and fixed jar discovery with Maven packaging/classpath invocation.
- [x] Document the Forge version and the clean build/run commands.
- [x] Confirm the bridge compiles without relying on ignored `out/` classes.

Forge's POMs use `${revision}` and flatten them only during the flatten goal. The documented Forge install command runs that goal before `install`, then this project's build consumes the flattened Maven artifacts.

## 2. Decision logging and data records

**Necessary before learning; practical now.** The current socket message already contains `state` and `actions`, and Python records those messages in an artifact. Expand this into structured, newline-delimited JSON records so each decision can be inspected and later joined to its result. Keep console output concise and make detailed records a separate file to avoid flooding the terminal.

Suggested decision record (field names can be finalized before implementation):

```json
{
  "schema_version": 1,
  "game_id": "...",
  "decision_id": 42,
  "turn": 7,
  "active_player": "...",
  "priority_player": "...",
  "phase": "MAIN1",
  "state": {},
  "available_actions": [],
  "chosen_action_id": "...",
  "chosen_action": {},
  "result": null
}
```

Action options should become objects with stable IDs and explicit fields (action kind, source card, ability/mode, target requirements, and selected targets) instead of relying on display strings as identity. Keep a readable label for logs. A target-selection exchange should be tied to its parent decision or represented as a sub-decision, so the action and its target are not separated in training data. Record terminal game outcome and player identity, then attach it to each game record or make it joinable by `game_id`.

**Steps**

- [x] Pick one versioned decision schema for logging and the Python/Java protocol.
- [x] Add game ID, monotonically increasing decision ID, turn number, active player, priority player, and phase.
- [x] Log state, available actions, chosen action, and any target selection with structured fields.
- [x] Record game end, winner/draw, and reason, linked by game ID.
- [x] Write JSONL records to a configurable output path; keep summary logging readable.
- [x] Include validation or a small reader that checks records are parseable and internally consistent.

Schema version 1 writes `decision` and `game_result` records to one JSONL file per run. Decision records contain action IDs, coarse action kinds, and display labels; card identity, ability mode, and target requirements can be split into richer fields as the action/state model is refactored. Target decisions carry a parent decision ID. Outcomes are separate records linked by `game_id`.

## 3. State representation

**Necessary for useful policies; design the contract now, grow the features incrementally.** The current state is intentionally small: turn, phase, life totals, and the Python player's hand. That is enough to test the bridge but not enough to evaluate most choices. The state snapshot is currently assembled in Java as a JSON string.

Do not try to finalize every future model feature before choosing a learning setup. First define a versioned, observable snapshot with information the acting player is allowed to know. A useful first expansion is:

- Player identities, active player, priority player, phase/step, turn, life, poison, and other relevant counters.
- Each player's battlefield permanents with controller, tapped/untapped state, combat status, counters, and relevant characteristics.
- The acting player's hand and known public zones, graveyards, exile, and stack.
- Publicly known opponent information only; do not leak hidden hand or library contents.
- Legal actions represented separately from state and with stable IDs. Treat the legal-action list as the action mask for a model.

Keep raw game facts as structured fields and derive model-specific tensors/features in Python. This makes the log useful for debugging and lets the encoder change without needing to change Forge integration each time. Add fields by schema version or explicit compatibility rules.

**Steps**

- [ ] Write down the observable-state boundary and a compact version-1 state schema.
- [ ] Replace hand-built JSON concatenation with a JSON library or typed serialization, if compatible with the chosen Maven setup.
- [ ] Add public board, stack, graveyard, and relevant player/combat information in useful increments.
- [ ] Ensure state and legal actions describe the same decision point and use consistent card/player identifiers.
- [ ] Add checks for hidden-information leakage and missing/ambiguous fields.

## 4. Learning approach

**Necessary to make the agent improve; not necessary to decide before instrumentation.** The current random policy and stock-AI suggestion are useful baselines, but neither constitutes a learning pipeline. Game outcomes alone are a sparse learning signal, so first collect trustworthy examples and compare against simple baselines.

Suggested progression:

1. **Baselines:** random legal choice, always pass, and accept the stock AI suggestion. Run repeated games with controlled decks/seeds where possible, swapping seats to reduce first-player/seat bias.
2. **Data capture:** store versioned state, candidate actions, chosen action, game ID, and terminal result. Verify records and track decisions/games completed.
3. **First learner:** start with imitation of the stock AI's selected action if the action can be mapped into the same candidate set. This provides dense decision labels without inventing reward shaping. Compare its behavior and results to the baselines.
4. **Outcome-driven learning:** once data and evaluation are reliable, consider a contextual bandit or a policy/value model trained from game outcomes. Full reinforcement learning/self-play is possible, but it requires many games, careful reward/evaluation design, and repeatable runs.
5. **Evaluation:** keep held-out games or seeds, report win rate with uncertainty, compare seats/decks, and preserve model/data versions.

**Steps**

- [ ] Decide what one training example represents (priority decision, target choice, or both).
- [ ] Capture a reliable result label and tie every decision to its game's result.
- [ ] Establish baseline win rates with repeated runs and seat swaps.
- [ ] Check whether stock-AI choices can be mapped to the exact structured action IDs.
- [ ] Choose imitation learning as the first learner, or document why a reward-based method is the better first experiment.
- [ ] Define held-out evaluation before tuning a policy.

## Current implementation notes

- Python currently has `random_policy` and `accept_ai_policy` helpers.
- The Java controller delegates most gameplay decisions to Forge's AI and asks Python for the priority action; this is a useful scope for the first learning task.
- `stateJson` currently reports turn, phase, life totals, and the acting player's hand.
- Existing saved run artifacts show 100 completed same-deck games, but they are not a controlled evaluation of a learned policy.
- The Java source now lives in `src/main/java` and builds as the `forge-bridge` Maven artifact.
- The runner resolves project and Forge paths from the script location and environment variables, and asks Maven for the runtime classpath.
- Decision and game-result JSONL records now carry schema version 1, run/game IDs, per-game decision IDs, parent links for target choices, and the terminal winner/draw.
- Action records currently use stable per-decision IDs, coarse categories, and display labels; detailed card/mode/target fields remain part of the state/action refactor.
