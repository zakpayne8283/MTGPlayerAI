# Project roadmap

Forge runs games, Java intercepts the Python-controlled player's priority decisions, and Python selects from the choices Java sends. The initial learning target is supervised imitation: for each observable state and legal action set, learn to select the action Forge's AI selected. The first model will be a small neural policy that scores legal state-action pairs.

## Next steps to a first trained policy

1. **Observable state and versioned transport:** define and emit player life/poison, hand sizes, the acting player's known hand, battlefield permanents with current creature stats, graveyards, turn/phase, and perspective. Never expose opponent hidden cards or library contents.
2. **Structured legal actions:** give each candidate a decision-scoped stable ID and explicit kind, source card, ability/API, mana value/cost, legal targets, and selected targets where available.
3. **Forge supervision labels:** log Forge's original selected action separately from the policy's action. A target label is available only when Forge chose that same targeting decision; otherwise preserve it as unlabeled.
4. **Feature encoder:** turn logs into numeric summaries plus categorical tokens/entity lists for cards, keywords, and actions. Fit vocabularies on training data only; keep raw JSON as the durable source of truth.
5. **Dataset and neural policy:** split by game/run, train a masked choice/ranking model over only the legal actions, save model and encoder versions.
6. **Evaluation and inference:** measure held-out agreement with Forge and win rate against Forge/pass/random baselines; integrate model scoring into Python with a legal-action fallback.

The Java/Python decision protocol and JSONL records are the stable boundary. Feature encoders and model architectures can change without rewriting old game records.

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

Schema version 1 logs display-label actions. Schema version 2 is the structured state/action protocol, and includes `oracle_action_id` for Forge's selected priority action separately from Python's `chosen_action_id`. Target decisions are linked to their parent priority decision; target-choice oracle labels are not assumed when the target was selected by Python.

## 3. State representation

**Necessary for useful policies; grow the features incrementally.** Schema 1 had only turn, phase, life totals, and the Python player's hand. Schema 2 emits structured state from Forge game objects using Gson.

Do not try to finalize every future model feature before choosing a learning setup. First define a versioned, observable snapshot with information the acting player is allowed to know. A useful first expansion is:

- Player identities, active player, priority player, phase/step, turn, life, poison, and other relevant counters.
- Each player's battlefield permanents with controller, tapped/untapped state, combat status, counters, and relevant characteristics.
- The acting player's hand and known public zones, graveyards, exile, and stack.
- Publicly known opponent information only; do not leak hidden hand or library contents.
- Legal actions represented separately from state and with stable IDs. Treat the legal-action list as the action mask for a model.

Keep raw game facts as structured fields and derive model-specific tensors/features in Python. This makes the log useful for debugging and lets the encoder change without needing to change Forge integration each time. Add fields by schema version or explicit compatibility rules.

**Steps**

- [x] Write down the observable-state boundary and a compact version-2 state schema.
- [x] Replace hand-built JSON concatenation with Gson serialization.
- [x] Add player life/poison/hand sizes, acting-player hand identities, battlefield cards/current creature stats, and graveyards.
- [x] Give actions structured fields and decision-scoped IDs; retain legal targets and Forge's selected targets on its suggestion.
- [ ] Ensure state and legal actions describe the same decision point and validate against real decision logs.
- [ ] Add runtime checks for hidden-information leakage and missing/ambiguous fields.
- [ ] Extend state with stack/combat data once the current baseline schema is validated.

## 4. Learning approach

**Necessary to make the agent improve; not necessary to decide before instrumentation.** The current random policy and stock-AI suggestion are useful baselines, but neither constitutes a learning pipeline. Game outcomes alone are a sparse learning signal, so first collect trustworthy examples and compare against simple baselines.

Suggested progression:

1. **Baselines:** random legal choice, always pass, and accept the stock AI suggestion. Run repeated games with controlled decks/seeds where possible, swapping seats to reduce first-player/seat bias.
2. **Data capture:** store versioned state, candidate actions, chosen action, game ID, and terminal result. Verify records and track decisions/games completed.
3. **First learner:** train a small neural policy to score each legal state-action pair, using Forge's original priority action as the label. This provides dense decision labels without inventing reward shaping. Compare its behavior and results to the baselines.
4. **Outcome-driven learning:** once data and evaluation are reliable, consider a contextual bandit or a policy/value model trained from game outcomes. Full reinforcement learning/self-play is possible, but it requires many games, careful reward/evaluation design, and repeatable runs.
5. **Evaluation:** keep held-out games or seeds, report win rate with uncertainty, compare seats/decks, and preserve model/data versions.

**Steps**

- [x] Decide that one training example is a priority decision with its legal candidates; target choices are linked sub-decisions and need their own oracle labels before supervised target training.
- [ ] Capture/validate Forge's oracle action label and tie every decision to its game's result.
- [ ] Establish baseline win rates with repeated runs and seat swaps.
- [x] Record Forge's selected suggestion in the same candidate list using its exact action ID.
- [x] Choose supervised neural imitation as the first learner.
- [ ] Define held-out evaluation before tuning a policy.

## 5. Neural feature encoder

The first encoder returns fixed numeric state summaries, categorical tokens for phases/cards/actions, per-creature entity features, and one feature row per legal action. This supports an initial neural architecture with embeddings and pooling while keeping raw schema-2 JSON as the source of truth.

- [x] Implement a model-independent schema-2 feature extraction boundary in Python.
- [ ] Add normalization, training-only vocabularies, unknown-category handling, and serialized encoder metadata.
- [ ] Define the exact neural tensor shapes and masked choice loss when implementing training.

## Current implementation notes

- Python has random, Forge-suggestion, and always-pass baseline policies.
- The Java controller delegates most gameplay decisions to Forge's AI and asks Python for the priority action; this is a useful scope for the first learning task.
- Schema 2 reports turn/phase, player life/poison/hand counts, known acting hand cards, battlefield cards and current creature stats, and graveyards.
- Existing saved run artifacts show 100 completed same-deck games, but they are not a controlled evaluation of a learned policy.
- The Java source now lives in `src/main/java` and builds as the `forge-bridge` Maven artifact.
- The runner resolves project and Forge paths from the script location and environment variables, and asks Maven for the runtime classpath.
- Decision and game-result JSONL records now carry schema version 1, run/game IDs, per-game decision IDs, parent links for target choices, and the terminal winner/draw.
- Action records currently use stable per-decision IDs, coarse categories, and display labels; detailed card/mode/target fields remain part of the state/action refactor.
