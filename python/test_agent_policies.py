import unittest

import agent


class AgentPolicyTests(unittest.TestCase):
    def test_forge_policy_uses_oracle_action_id(self):
        message = {
            "oracle_action_id": "game:3:2",
            "actions": [
                {"action_id": "game:3:0", "kind": "pass", "label": "Pass"},
                {"action_id": "game:3:1", "kind": "cast_spell", "label": "Shock"},
                {"action_id": "game:3:2", "kind": "activate_ability", "label": "Tap"},
            ],
        }
        self.assertEqual(agent.accept_ai_policy(message), 2)

    def test_forge_policy_falls_back_to_pass_when_oracle_missing(self):
        message = {"actions": [{"action_id": "a", "label": "Cast"}, {"label": "Pass"}]}
        self.assertEqual(agent.accept_ai_policy(message), 0)

    def test_forge_policy_supports_archived_string_actions(self):
        message = {"actions": ["Pass", "AI suggestion: Shock"]}
        self.assertEqual(agent.accept_ai_policy(message), 1)

    def test_always_pass_policy_returns_first_action(self):
        self.assertEqual(agent.always_pass_policy({"actions": [{}, {}]}), 0)

    def test_random_policy_always_returns_a_legal_index(self):
        for size in range(1, 20):
            result = agent.random_policy({"actions": [None] * size})
            self.assertGreaterEqual(result, 0)
            self.assertLess(result, size)


if __name__ == "__main__":
    unittest.main()
