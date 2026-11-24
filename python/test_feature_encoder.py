import unittest

from feature_encoder import build_vocabulary, encode_decision


def sample_decision():
    return {
        "schema_version": 2,
        "kind": "priority",
        "turn": 5,
        "phase": "MAIN1",
        "oracle_action_id": "g:1:1",
        "state": {
            "turn": 5,
            "phase": "MAIN1",
            "acting_player": "player_1",
            "players": [
                {
                    "id": "player_1", "life": 16, "poison": 0, "hand_size": 1,
                    "hand": [{"card": "Lightning Bolt"}],
                    "battlefield": [
                        {"card": "Goblin", "types": ["Creature"], "power": 2,
                         "toughness": 2, "damage": 0, "tapped": False,
                         "summoning_sick": False, "keywords": []},
                        {"card": "Holy Strength", "types": ["Enchantment"]},
                    ],
                    "graveyard": [{"card": "Shock"}],
                },
                {
                    "id": "player_2", "life": 12, "poison": 1, "hand_size": 3,
                    "battlefield": [
                        {"card": "Air Elemental", "types": ["Creature"], "power": 4,
                         "toughness": 4, "damage": 1, "tapped": False,
                         "summoning_sick": False, "keywords": ["Flying"]},
                    ],
                    "graveyard": [],
                },
            ],
        },
        "available_actions": [
            {"action_id": "g:1:0", "kind": "pass", "label": "Pass"},
            {
                "action_id": "g:1:1", "kind": "cast_spell", "source_card": "Lightning Bolt",
                "card_types": ["Instant"], "source_zone": "Hand", "mana_cost": "{R}",
                "mana_value": 1, "ability_api": "Damage", "uses_targeting": True,
                "legal_targets": [{"target_type": "card", "target_card": "Air Elemental"}],
                "selected_targets": [{"target_type": "card", "target_card": "Air Elemental"}],
            },
        ],
    }


class FeatureEncoderTests(unittest.TestCase):
    def setUp(self):
        self.encoded = encode_decision(sample_decision())

    def test_numeric_player_and_board_summaries(self):
        numbers = self.encoded["state_numeric"]
        self.assertEqual(numbers["acting_life"], 16)
        self.assertEqual(numbers["opponent_life"], 12)
        self.assertEqual(numbers["acting_battlefield_count"], 2)
        self.assertEqual(numbers["opponent_graveyard_count"], 0)
        self.assertEqual(numbers["acting_total_power"], 2)
        self.assertEqual(numbers["opponent_total_toughness"], 4)

    def test_effective_creature_stats_are_retained_per_entity(self):
        goblin = self.encoded["state_entities"]["acting_creatures"][0]
        self.assertEqual((goblin["power"], goblin["toughness"]), (2, 2))
        self.assertEqual(goblin["summoning_sick"], 0)

    def test_opponent_hand_is_only_a_count(self):
        self.assertEqual(self.encoded["state_numeric"]["opponent_hand_size"], 3)
        self.assertNotIn("opponent_hand_cards", self.encoded["state_categorical"])

    def test_action_rows_preserve_legal_order_and_ids(self):
        self.assertEqual([a["action_id"] for a in self.encoded["actions"]], ["g:1:0", "g:1:1"])
        self.assertEqual(self.encoded["label_action_id"], "g:1:1")
        self.assertEqual(self.encoded["actions"][0]["numeric"]["is_pass"], 1)
        self.assertEqual(self.encoded["actions"][1]["numeric"]["is_spell"], 1)

    def test_oracle_selected_target_is_not_used_as_an_input_feature(self):
        action = self.encoded["actions"][1]
        self.assertNotIn("selected_target_count", action["numeric"])
        self.assertNotIn("selected_targets", action["categorical"])
        self.assertEqual(action["numeric"]["legal_target_count"], 1)

    def test_action_source_and_legal_target_tokens_are_kept(self):
        categories = self.encoded["actions"][1]["categorical"]
        self.assertEqual(categories["source_card"], ["Lightning Bolt"])
        self.assertEqual(categories["target_cards"], ["Air Elemental"])

    def test_vocabulary_is_deterministic_and_has_unknown_bucket(self):
        vocab = build_vocabulary([self.encoded])
        self.assertEqual(vocab["phase"]["<UNK>"], 0)
        self.assertIn("MAIN1", vocab["phase"])
        self.assertIn("Goblin", vocab["creature_card"])
        self.assertEqual(vocab, build_vocabulary([self.encoded]))

    def test_empty_input_uses_safe_defaults(self):
        encoded = encode_decision({"state": {}, "available_actions": []})
        self.assertEqual(encoded["state_numeric"]["acting_life"], 0)
        self.assertEqual(encoded["actions"], [])
        self.assertIsNone(encoded["label_action_id"])


if __name__ == "__main__":
    unittest.main()
