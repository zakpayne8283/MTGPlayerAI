"""Check a run's JSONL decision log for valid records and game-result links.

Usage: python3 python/validate_decision_log.py decision_logs/<run-id>.jsonl
"""
import json
import sys
from pathlib import Path


def validate(path):
    errors = []
    decisions = {}
    game_results = {}
    run_ids = set()

    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
                continue

            run_id = record.get("run_id")
            game_id = record.get("game_id")
            if record.get("schema_version") not in (1, 2):
                errors.append(f"line {line_number}: unsupported schema_version")
            if not isinstance(run_id, str) or not isinstance(game_id, str) or not run_id or not game_id:
                errors.append(f"line {line_number}: missing run_id or game_id")
                continue
            run_ids.add(run_id)

            if record.get("record_type") == "decision":
                decision_id = record.get("decision_id")
                key = (game_id, decision_id)
                if not isinstance(decision_id, int):
                    errors.append(f"line {line_number}: decision_id must be an integer")
                    continue
                if key in decisions:
                    errors.append(f"line {line_number}: duplicate decision {key}")
                decisions[key] = (record, line_number)

                required = ("kind", "turn", "active_player", "priority_player", "phase", "state")
                for field in required:
                    if field not in record:
                        errors.append(f"line {line_number}: missing {field}")

                available = record.get("available_actions")
                if not isinstance(available, list) or not available:
                    errors.append(f"line {line_number}: available_actions must be a non-empty list")
                    continue
                ids = [item.get("action_id") for item in available if isinstance(item, dict)]
                if (len(ids) != len(available)
                        or not all(isinstance(action_id, str) for action_id in ids)
                        or len(set(ids)) != len(ids)):
                    errors.append(f"line {line_number}: actions must be objects with unique action_id values")
                chosen_id = record.get("chosen_action_id")
                if chosen_id not in ids:
                    errors.append(f"line {line_number}: chosen_action_id is not in available_actions")
                elif (not isinstance(record.get("chosen_action"), dict)
                        or record["chosen_action"].get("action_id") != chosen_id):
                    errors.append(f"line {line_number}: chosen_action does not match chosen_action_id")
                oracle_id = record.get("oracle_action_id")
                if oracle_id is not None and oracle_id not in ids:
                    errors.append(f"line {line_number}: oracle_action_id is not in available_actions")
                if record.get("schema_version") == 2:
                    if not isinstance(record.get("state"), dict):
                        errors.append(f"line {line_number}: schema 2 state must be an object")
                    if any(not isinstance(item, dict) for item in available):
                        errors.append(f"line {line_number}: schema 2 actions must be structured objects")

            elif record.get("record_type") == "game_result":
                if game_id in game_results:
                    errors.append(f"line {line_number}: duplicate game result for {game_id}")
                game_results[game_id] = (record, line_number)
                if record.get("outcome") not in ("win", "draw"):
                    errors.append(f"line {line_number}: outcome must be 'win' or 'draw'")
                if record.get("outcome") == "win" and not record.get("winner"):
                    errors.append(f"line {line_number}: winning result has no winner")
            else:
                errors.append(f"line {line_number}: unknown record_type {record.get('record_type')!r}")

    for (game_id, decision_id), (record, line_number) in decisions.items():
        parent_id = record.get("parent_decision_id")
        if parent_id is not None and (game_id, parent_id) not in decisions:
            errors.append(f"line {line_number}: parent decision {parent_id} is missing for {game_id}")
        if game_id not in game_results:
            errors.append(f"line {line_number}: no game_result record for {game_id}")

    for game_id, (_, line_number) in game_results.items():
        if not any(key[0] == game_id for key in decisions):
            errors.append(f"line {line_number}: game result has no decision records")

    if len(run_ids) > 1:
        errors.append("log contains multiple run_id values")
    if not decisions and not game_results:
        errors.append("log contains no records")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Valid log: {len(decisions)} decisions across {len(game_results)} games")
    return 0


def main():
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"Log file not found: {path}", file=sys.stderr)
        return 2
    return validate(path)


if __name__ == "__main__":
    raise SystemExit(main())
