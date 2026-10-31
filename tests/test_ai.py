import unittest
from unittest.mock import patch

from podcast_agent.ai import AIError, evaluate, plan_searches
from podcast_agent.models import Podcast


class AITests(unittest.TestCase):
    @patch("podcast_agent.ai.ask_json")
    def test_ai_generates_three_searches(self, ask):
        ask.return_value = {"queries": ["mechanical engineering", "industrial automation", "engineering design"]}
        terms = plan_searches("A friendly manufacturing and engineering podcast", "llama3.2:3b")
        self.assertEqual(terms, ["mechanical engineering", "industrial automation", "engineering design"])

    @patch("podcast_agent.ai.ask_json")
    def test_ai_score_is_bounded(self, ask):
        ask.return_value = {"score": 150, "reason": "Both cover manufacturing", "subject": "Guest idea", "introduction": "Hi there!"}
        candidate = Podcast("Machinery Hour", "https://rss.example/feed")
        evaluate("An engineering podcast", candidate, "llama3.2:3b")
        self.assertEqual(candidate.score, 100)
        self.assertEqual(candidate.rationale, "Both cover manufacturing")

    @patch("podcast_agent.ai.ask_json")
    def test_missing_ai_search_plan_is_an_error(self, ask):
        ask.return_value = {"queries": []}
        with self.assertRaises(AIError):
            plan_searches("A manufacturing podcast", "llama3.2:3b")


if __name__ == "__main__":
    unittest.main()
