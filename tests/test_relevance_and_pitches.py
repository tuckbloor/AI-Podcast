"""Regression tests for the real user feedback: unrelated 90% shows, UK proof and bad pitches."""
from datetime import datetime, timezone
from unittest.mock import patch
import unittest

from podcast_agent.agent import classify_uk_location, run_agent
from podcast_agent.ai import evaluate_batch
from podcast_agent.models import Podcast
from podcast_agent.ranking import rank_podcast
from podcast_agent.network import FetchedContent
from podcast_agent.rss import enrich_from_feed

NOW = datetime(2026, 10, 31, tzinfo=timezone.utc)
GOAL = 'software developer uk'


class RelevanceAndOutreachTests(unittest.TestCase):
    def setUp(self):
        self.web_patch = patch("podcast_agent.discovery.search_open_web", return_value=[])
        self.web_patch.start()
        self.addCleanup(self.web_patch.stop)

    def test_coworking_does_not_outscore_software_engineering(self):
        coworking = Podcast('Coworking Values Podcast', 'https://example.test/a',
                             description='Thought provoking conversations on coworking and remote work',
                             episodes=['Creating a productive remote workplace'])
        engineering = Podcast('Software Engineering Radio', 'https://example.test/b',
                               description='The podcast for professional software developers, programming and software engineering',
                               episodes=['Practical Python and testing in modern software development'])
        rank_podcast(GOAL, coworking, uk_focus=True, now=NOW)
        rank_podcast(GOAL, engineering, uk_focus=True, now=NOW)
        self.assertEqual(coworking.topic_points, 0)
        self.assertGreater(engineering.score, coworking.score)
        self.assertGreater(engineering.topic_points, 30)
        self.assertIn('Topic', engineering.score_breakdown)

    def test_unrelated_job_hunting_not_relevant_to_software(self):
        pod = Podcast('Open To Work', 'https://example.test/job',
                      description='Advice for job seekers and recruiters',
                      episodes=['How recruiters can support job seekers'])
        rank_podcast(GOAL, pod, now=NOW)
        self.assertEqual(pod.match_quality, 'Weak topic match')

    def test_activity_scoring_uses_real_rss_date(self):
        old = Podcast('Software Engineers', 'https://example.test/old',
                      description='Programming, software and coding',
                      latest_episode_date='2019-02-12')
        new = Podcast('Software Engineers', 'https://example.test/new',
                      description='Programming, software and coding',
                      latest_episode_date='2026-10-12')
        rank_podcast(GOAL, old, now=NOW)
        rank_podcast(GOAL, new, now=NOW)
        self.assertEqual(new.score - old.score, 15)
        self.assertIn('6 months', new.activity_status)

    def test_published_contact_only_adds_ten_points(self):
        p = Podcast('Coder Stories', 'https://example.test/show', description='A podcast about programming')
        baseline = rank_podcast(GOAL, p, now=NOW)
        p.email = 'hello@example.test'; p.contact_source = 'https://example.test/contact'
        self.assertEqual(rank_podcast(GOAL, p, now=NOW) - baseline, 10)

    def test_explicit_city_based_location_from_official_page(self):
        pod = Podcast('UK Developer Show', 'https://example.test/feed',
                      description='Software development across the world',
                      location_page_text='Our podcast is recorded in Manchester and produced by local hosts.')
        self.assertTrue(classify_uk_location(pod))
        self.assertEqual(pod.location_status, 'UK location stated')
        self.assertIn('Manchester', pod.location_evidence)

    def test_general_uk_topic_is_not_country_proof(self):
        pod = Podcast('UK Software News', 'https://example.test/feeds',
                      description='News about British software companies and their products')
        self.assertFalse(classify_uk_location(pod))

    @patch('podcast_agent.rss.safe_fetch')
    def test_rss_records_latest_publish_date(self, fetch):
        feed = b'''<rss version="2.0"><channel><title>Developers United</title><description>About software engineering</description>
            <link>https://podcasts.example/</link>
            <item><title>Episode A</title><pubDate>Fri, 10 Oct 2025 12:00:00 GMT</pubDate></item>
            <item><title>Episode B</title><pubDate>Fri, 30 Oct 2026 12:00:00 GMT</pubDate></item>
            </channel></rss>'''
        fetch.return_value = FetchedContent(feed, 'https://podcasts.example/rss', 'application/rss+xml')
        pod = Podcast('Original', 'https://podcasts.example/rss')
        enrich_from_feed(pod)
        self.assertEqual(pod.latest_episode_date, '2026-10-30')
        self.assertEqual(pod.episodes, ['Episode A', 'Episode B'])

    @patch('podcast_agent.ai.ask_json')
    def test_one_line_advert_becomes_complete_host_email(self, ask):
        ask.return_value = {'results': [{
            'id': 1, 'score': 99, 'reason': 'Great show', 'subject': 'Tech',
            'introduction': 'Hello, join us for conversations about the latest tech trends.'}]}
        pod = Podcast('CoRecursive: Coding Stories', 'https://example.test/rss',
                      episodes=['Story: The Aging Programmer'])
        evaluate_batch(GOAL, [pod], 'llama3.2:3b', guest_profile='Jamie Jones, UK engineer, can discuss Laravel and factory software.')
        self.assertGreater(len(pod.outreach_intro), 300)
        self.assertIn('team behind CoRecursive', pod.outreach_intro)
        self.assertIn('Story: The Aging Programmer', pod.outreach_intro)
        self.assertIn('Jamie Jones', pod.outreach_intro)
        self.assertIn('Would you be open', pod.outreach_intro)
        self.assertIn('Best regards', pod.outreach_intro)
        self.assertNotIn('join us for', pod.outreach_intro)
        self.assertIn('replaced', pod.research_notes)

    @patch('podcast_agent.ai.ask_json')
    def test_no_guest_details_uses_explicit_placeholders(self, ask):
        ask.return_value = {'results': [{
            'id': 1, 'score': 100, 'reason': 'Great show', 'subject': '', 'introduction': 'Hello'}]}
        pod = Podcast('Engineering Weekly', 'https://example.test/rss')
        evaluate_batch(GOAL, [pod], 'llama3.2:3b')
        self.assertIn('[Guest name]', pod.outreach_intro)
        self.assertIn('[Your name]', pod.outreach_intro)
        self.assertNotIn('my friend', pod.outreach_intro.lower())

    @patch('podcast_agent.agent.evaluate_batch')
    @patch('podcast_agent.agent.find_public_contact')
    @patch('podcast_agent.agent.enrich_from_feed')
    @patch('podcast_agent.agent.search_apple')
    @patch('podcast_agent.agent.propose_tool')
    @patch('podcast_agent.agent.check_model')
    def test_final_agent_ranking_overrides_llm_score(self, check, decide, discover, rss, contact, draft):
        from podcast_agent.ai import AIError
        decide.side_effect = AIError('tool choice timeout')
        discover.side_effect = [
            [Podcast('Coworking Values', 'https://feeds.example/cowork', description='Remote work and shared offices')],
            [Podcast('Software Engineering Radio', 'https://feeds.example/ser', description='Software development, programmers and coding')],
            [],
        ]
        rss.side_effect = lambda p: setattr(p, 'episodes', ['Programming and architecture'] if 'Engineering' in p.title else ['Home working and community'])
        def fake_draft(goal, pods, model, **kwargs):
            for p in pods:
                p.score = 98  # Artificially inflated by mocked Ollama
                p.outreach_intro = 'Hello, draft'
        draft.side_effect = fake_draft
        result = run_agent(GOAL, max_candidates=4)
        scores = {p.title: p.score for p in result.podcasts}
        self.assertIn('Software Engineering Radio', scores)
        self.assertNotIn('Coworking Values', scores)  # rejected BEFORE contact/draft
        self.assertGreaterEqual(result.rejected_leads, 1)
        self.assertEqual(contact.call_count, 1)


if __name__ == '__main__':
    unittest.main()
