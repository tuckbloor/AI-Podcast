"""Offline regression tests proving the existing Streamlit application uses tools."""
import unittest
from unittest.mock import patch

from podcast_agent.agent import (
    _validate_proposal,
    fallback_queries,
    run_agent,
    MAX_SEARCHES,
)
from podcast_agent.ai import AIError, evaluate_batch
from podcast_agent.models import Podcast


DESCRIPTION = "A weekly podcast about industrial engineering, robotics and automation in British factories"


class AgentToolTests(unittest.TestCase):
    def setUp(self):
        self.web_patch = patch("podcast_agent.discovery.search_open_web", return_value=[])
        self.web_patch.start()
        self.addCleanup(self.web_patch.stop)

    def test_fallback_searches_use_actual_topic_words(self):
        terms = fallback_queries(DESCRIPTION)
        self.assertGreaterEqual(len(terms), 2)
        self.assertTrue(any("engineering" in q for q in terms))

    def test_rejects_unauthorised_and_unsafe_tool_commands(self):
        for value in [
            {"tool": "send_email", "ids": [1]},
            {"tool": "delete_files", "ids": [1]},
            {"tool": "discover", "query": "http://localhost/"},
            {"tool": "discover", "query": "guest@example.com"},
            {"tool": "read_rss", "ids": [True]},
            {"tool": "check_contact", "ids": [1]},  # RSS not read yet
            {"tool": "draft", "ids": [1]},
            {"tool": "finish"},
        ]:
            with self.subTest(value=value):
                self.assertIsNone(_validate_proposal(value, DESCRIPTION, [Podcast("Show", "https://example.com/rss")], [], set(), set(), set()))

    def test_valid_model_tool_id_is_one_based_and_validated(self):
        choices = _validate_proposal({"tool": "read_rss", "ids": [1, 1, 0, 30]}, DESCRIPTION,
                                    [Podcast("Show", "https://example.com/rss")], [], set(), set(), set())
        self.assertEqual(choices, ("read_rss", [0]))

    @patch("podcast_agent.agent.evaluate_batch")
    @patch("podcast_agent.agent.find_public_contact")
    @patch("podcast_agent.agent.enrich_from_feed")
    @patch("podcast_agent.agent.search_apple")
    @patch("podcast_agent.agent.propose_tool")
    @patch("podcast_agent.agent.check_model")
    def test_model_actually_selects_tools_and_researches_before_drafting(self, check, choose, apple, rss, contacts, assess):
        choose.return_value = {"tool": "discover", "query": "industrial engineering"}
        apple.side_effect = [
            [Podcast("Engineering Today", "https://feeds.example/one")],
            [Podcast("Robotics Weekly", "https://feeds.example/two")],
            [],
        ]
        def read(p):
            p.episodes = ["Automation in UK factories"]
            p.website = "https://podcasts.example/"
        rss.side_effect = read
        def contact(p):
            self.assertTrue(p.episodes)
            p.email = "hello@example.org"
            p.contact_source = "https://podcasts.example/contact"
        contacts.side_effect = contact
        def evaluate(_, batch, model):
            self.assertTrue(all(p.contact_source for p in batch))
            for p in batch:
                p.score = 86
                p.outreach_intro = f"Hello, your recent episode on {p.episodes[0]} caught my eye."
        assess.side_effect = evaluate
        progress = []
        activity = []
        result = run_agent(DESCRIPTION, max_candidates=4,
                           progress=lambda x, msg: progress.append((x, msg)),
                           on_activity=activity.append)
        self.assertEqual(result.model_decisions, 1)
        self.assertFalse(result.fallback_used)
        self.assertGreaterEqual(result.tool_calls, 7)
        self.assertEqual(len(result.podcasts), 2)
        self.assertEqual(len(result.queries), 3)
        self.assertTrue(all(p.outreach_intro for p in result.podcasts))
        self.assertEqual(progress[-1][0], 1.0)
        self.assertTrue(any("Ollama proposed" in s for s in activity))
        self.assertEqual(apple.call_count, 3)

    @patch("podcast_agent.agent.evaluate_batch")
    @patch("podcast_agent.agent.find_public_contact")
    @patch("podcast_agent.agent.enrich_from_feed")
    @patch("podcast_agent.agent.search_apple")
    @patch("podcast_agent.agent.propose_tool")
    @patch("podcast_agent.agent.check_model")
    def test_when_model_tool_choice_times_out_recovery_completes(self, check, choose, apple, rss, contacts, assess):
        choose.side_effect = AIError("Ollama took too long")
        apple.side_effect = [
            [Podcast("Industrial Engineering Stories", "https://feeds.example/one")],
            [Podcast("Robotics Automation Report", "https://feeds.example/two")],
            [],
        ]
        def fake_score(_, batch, model):
            for p in batch:
                p.score = 60
                p.outreach_intro = "Hello, interested in a collaboration?"
        assess.side_effect = fake_score
        result = run_agent(DESCRIPTION, max_candidates=4)
        self.assertTrue(result.fallback_used)
        self.assertEqual(choose.call_count, 1)  # No repeating 12s stalls
        self.assertEqual(len(result.podcasts), 2)
        self.assertEqual(assess.call_count, 1)
        self.assertEqual(len(result.queries), 3)

    @patch("podcast_agent.agent.propose_tool")
    @patch("podcast_agent.agent.search_apple")
    @patch("podcast_agent.agent.check_model")
    def test_empty_provider_results_finish_cleanly(self, check, apple, choose):
        choose.side_effect = AIError("offline decision")
        apple.return_value = []
        result = run_agent(DESCRIPTION)
        self.assertEqual(result.podcasts, [])
        self.assertLessEqual(apple.call_count, MAX_SEARCHES)
        self.assertEqual(len(result.activity) > 0, True)

    @patch("podcast_agent.agent.evaluate_batch")
    @patch("podcast_agent.agent.find_public_contact")
    @patch("podcast_agent.agent.enrich_from_feed")
    @patch("podcast_agent.agent.search_apple")
    @patch("podcast_agent.agent.propose_tool")
    @patch("podcast_agent.agent.check_model")
    def test_web_source_failure_does_not_invent_contacts_or_scores(self, check, choose, apple, rss, contact, assess):
        choose.side_effect = AIError("timeout")
        apple.side_effect = [
            [Podcast("Industrial Engineering", "https://x.example/a")],
            [Podcast("Robotics Automation", "https://x.example/b")],
            [],
        ]
        contact.side_effect = RuntimeError("403 access denied")
        assess.side_effect = AIError("model unavailable")
        result = run_agent(DESCRIPTION, max_candidates=4)
        self.assertGreaterEqual(result.research_errors, 3)
        self.assertTrue(all(not p.email for p in result.podcasts))
        self.assertTrue(all(p.score >= 12 for p in result.podcasts))  # independently evidenced topic, not Ollama score
        self.assertTrue(all('AI draft unavailable' in p.rationale for p in result.podcasts))


class BatchedEvaluationTests(unittest.TestCase):
    @patch("podcast_agent.ai.ask_json")
    def test_batch_scores_and_personalised_introductions(self, fake):
        fake.return_value = {"results": [
            {"id": 1, "score": 72, "reason": "Both discuss robotics", "subject": "Robotics guest", "introduction": "I saw your automation episode."},
            {"id": 2, "score": 120, "reason": "Industry overlap", "subject": "Guest invitation", "introduction": "Your show covers industrial automation."},
        ]}
        items = [Podcast("A", "https://x.example/a"), Podcast("B", "https://x.example/b")]
        evaluate_batch(DESCRIPTION, items, "llama3.2:3b")
        self.assertEqual([p.score for p in items], [72, 100])
        self.assertTrue(items[0].outreach_intro)

    @patch("podcast_agent.ai.ask_json")
    def test_missing_batch_result_gets_zero_not_fake_analysis(self, fake):
        fake.return_value = {"results": [{"id": 1, "score": 50}]}
        items = [Podcast("A", "https://x.example/a"), Podcast("B", "https://x.example/b")]
        evaluate_batch(DESCRIPTION, items, "llama3.2:3b")
        self.assertEqual(items[1].score, 0)
        self.assertIn("omitted", items[1].rationale)


if __name__ == '__main__':
    unittest.main()
