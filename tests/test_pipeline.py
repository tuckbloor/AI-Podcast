import unittest
from unittest.mock import patch

from podcast_agent.models import Podcast
from podcast_agent.pipeline import run_research


class PipelineTests(unittest.TestCase):
    @patch("podcast_agent.pipeline.evaluate")
    @patch("podcast_agent.pipeline.find_public_contact")
    @patch("podcast_agent.pipeline.enrich_from_feed")
    @patch("podcast_agent.pipeline.search_apple")
    @patch("podcast_agent.pipeline.plan_searches")
    @patch("podcast_agent.pipeline.check_model")
    def test_end_to_end_orchestration_offline(self, check, plan, search, enrich, contact, evaluate):
        plan.return_value = ["engineering", "automation", "industry"]
        search.side_effect = [
            [Podcast("Engineering Now", "https://feeds.example/a")],
            [Podcast("Robots Today", "https://feeds.example/b")],
            [],
        ]

        def score(_, item, __):
            item.score = 90 if item.title == "Robots Today" else 72
            item.rationale = "Related subject"

        evaluate.side_effect = score
        status = []
        results, queries = run_research(
            "A podcast about technology and engineering careers",
            max_candidates=4,
            progress=lambda fraction, label: status.append((fraction, label)),
        )
        self.assertEqual(queries, plan.return_value)
        self.assertEqual([p.title for p in results], ["Robots Today", "Engineering Now"])
        self.assertEqual(evaluate.call_count, 2)
        self.assertEqual(status[-1][0], 1.0)


if __name__ == "__main__":
    unittest.main()
