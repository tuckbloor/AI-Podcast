"""Regressions for unwanted UK verification and grey action button reports."""
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from podcast_agent.agent import run_agent, ResearchRun
from podcast_agent.ai import AIError
from podcast_agent.models import Podcast
from podcast_agent.ranking import rank_podcast
from podcast_agent.network import FetchedContent
from podcast_agent.contacts import find_public_contact
from test_streamlit_smoke import StreamlitAppSmokeTests, Widget

QUERY = "software and web developer podcasts"


class LocationNeutralResearchTests(unittest.TestCase):
    def setUp(self):
        web = patch("podcast_agent.discovery.search_open_web", return_value=[])
        web.start()
        self.addCleanup(web.stop)

    @patch("podcast_agent.agent.evaluate_batch")
    @patch("podcast_agent.agent.find_public_contact")
    @patch("podcast_agent.agent.enrich_from_feed")
    @patch("podcast_agent.agent.search_apple")
    @patch("podcast_agent.agent.propose_tool", side_effect=AIError("planning timeout"))
    @patch("podcast_agent.agent.check_model")
    def test_unrestricted_query_has_no_uk_check_or_contact_log_suffix(self, model, choice, apple, rss, contact, draft):
        apple.side_effect = [[Podcast("Software Engineering Radio", "https://feeds.example/eng",
                                      description="Software development and programming interviews")], [], []]
        rss.side_effect = lambda p: setattr(p, "episodes", ["JavaScript architecture with developers"])
        def contact_stub(p):
            p.contact_page = "https://show.example/contact"
        contact.side_effect = contact_stub
        run = run_agent(QUERY, max_candidates=4)
        self.assertFalse(run.uk_focus)
        self.assertFalse(run.uk_only)
        self.assertEqual(len(run.podcasts), 1)
        self.assertNotIn("UK", "\n".join(run.activity))
        self.assertEqual(run.podcasts[0].location_source, "")
        self.assertNotIn("UK", run.podcasts[0].score_breakdown)
        self.assertIn("publisher contact page found", "\n".join(run.activity))
        self.assertEqual(run.podcasts[0].contact_page, "https://show.example/contact")

    def test_without_country_scoring_allocates_all_100_points_to_relevance_activity_contact(self):
        podcast = Podcast("Software engineering podcast", "https://feeds.example/test",
                          description="Software engineering programming development coding web developers",
                          episodes=["Computer science and Python coding"],
                          latest_episode_date="2026-10-30", email="hosts@example.org",
                          contact_source="https://show.example/contact")
        rank_podcast(QUERY, podcast, uk_focus=False)
        self.assertIn("/75", podcast.score_breakdown)
        self.assertNotIn("UK", podcast.score_breakdown)
        self.assertTrue(0 <= podcast.score <= 100)
        rank_podcast("UK software developers only", podcast, uk_focus=True)
        self.assertIn("Verified UK", podcast.score_breakdown)

    @patch("podcast_agent.contacts.safe_fetch")
    def test_contact_page_is_retained_even_when_no_email_is_found(self, fetch):
        def fake_fetch(url, **kwargs):
            html = {
                "https://show.example/": '<html><a href="/contact">Contact the podcast</a></html>',
                "https://show.example/contact": "<html><body>Use our contact form</body></html>",
            }[url]
            return FetchedContent(html.encode(), url, "text/html")
        fetch.side_effect = fake_fetch
        pod = Podcast("Software Shows", "https://rss.example/feed", website="https://show.example/")
        find_public_contact(pod)
        self.assertEqual(pod.email, "")
        self.assertEqual(pod.contact_page, "https://show.example/contact")

    def test_ui_has_high_contrast_button_and_location_neutral_example(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf8")
        self.assertIn('FIND MATCHING PODCASTS', source)
        self.assertIn('background:linear-gradient(105deg,#007a69', source)
        self.assertIn('font-weight:900 !important;', source)
        self.assertIn('if st.session_state.get("uk_focus"):', source)
        self.assertIn('Contact pages found', source)

    def test_streamlit_result_render_has_no_uk_status_for_unrestricted_search(self):
        smoke = StreamlitAppSmokeTests()
        st = smoke.fake_streamlit(submitted=True)
        st.text_area = lambda *a, **kw: ("" if "Guest details" in a[0] else QUERY)
        metrics = []
        write_log = []
        def metric(_, label, *args, **kwargs):
            metrics.append(label)
        def write(*args, **kwargs):
            write_log.extend(str(v) for v in args)
        pod = Podcast("Software Engineering Podcast", "https://feeds.example/software",
                      topic_points=42, score=70, outreach_intro="Hello, I propose a guest interview.",
                      contact_page="https://show.example/contact")
        result = ResearchRun(podcasts=[pod], queries=[QUERY], tool_calls=2)
        with patch.object(Widget, "metric", metric), patch.dict(sys.modules, {"streamlit": st}), \
             patch("podcast_agent.ai.installed_models", return_value=["llama3.2:3b"]), \
             patch("podcast_agent.agent.run_agent", return_value=result):
            st.write = write
            runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.py"), run_name="__main__")
        self.assertNotIn("Confirmed UK", metrics)
        self.assertIn("Contact pages found", metrics)
        self.assertNotIn("**UK location:**", write_log)


if __name__ == "__main__":
    unittest.main()
