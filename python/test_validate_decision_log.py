import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from validate_decision_log import validate


def valid_records(schema_version=2):
    decision = {
        "schema_version": schema_version,
        "record_type": "decision",
        "run_id": "run-1",
        "game_id": "game-1",
        "decision_id": 1,
        "kind": "priority",
        "turn": 1,
        "active_player": "player_1",
        "priority_player": "player_1",
        "phase": "MAIN1",
        "state": {"players": []},
        "available_actions": [
            {"action_id": "game-1:1:0", "kind": "pass", "label": "Pass"},
            {"action_id": "game-1:1:1", "kind": "cast_spell", "label": "Shock"},
        ],
        "chosen_action_id": "game-1:1:0",
        "chosen_action": {"action_id": "game-1:1:0", "kind": "pass", "label": "Pass"},
    }
    if schema_version == 2:
        decision["oracle_action_id"] = "game-1:1:1"
    result = {
        "schema_version": schema_version,
        "record_type": "game_result",
        "run_id": "run-1",
        "game_id": "game-1",
        "outcome": "draw",
        "winner": None,
        "reason": "test",
    }
    return [decision, result]


class DecisionLogValidatorTests(unittest.TestCase):
    def run_records(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.jsonl"
            with path.open("w", encoding="utf-8") as stream:
                for record in records:
                    stream.write(json.dumps(record) + "\n")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return validate(path)

    def test_accepts_valid_schema_two_with_forge_label(self):
        self.assertEqual(self.run_records(valid_records(2)), 0)

    def test_accepts_archived_schema_one(self):
        self.assertEqual(self.run_records(valid_records(1)), 0)

    def test_rejects_oracle_label_outside_candidate_set(self):
        records = valid_records(2)
        records[0]["oracle_action_id"] = "not-a-candidate"
        self.assertEqual(self.run_records(records), 1)

    def test_rejects_duplicate_action_ids(self):
        records = valid_records(2)
        records[0]["available_actions"][1]["action_id"] = "game-1:1:0"
        self.assertEqual(self.run_records(records), 1)

    def test_rejects_missing_game_result(self):
        self.assertEqual(self.run_records(valid_records(2)[:1]), 1)

    def test_rejects_missing_parent_decision(self):
        records = valid_records(2)
        child = dict(records[0])
        child["decision_id"] = 2
        child["parent_decision_id"] = 99
        child["available_actions"] = [{"action_id": "game-1:2:0", "kind": "pass"}]
        child["chosen_action_id"] = "game-1:2:0"
        child["chosen_action"] = child["available_actions"][0]
        child["oracle_action_id"] = None
        records.insert(1, child)
        self.assertEqual(self.run_records(records), 1)

    def test_rejects_malformed_json_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text("{not json}\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(validate(path), 1)


if __name__ == "__main__":
    unittest.main()
