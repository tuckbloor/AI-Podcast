"""Regressions based on the real 31 October user run and UI feedback."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from podcast_agent.agent import (run_agent, fallback_queries, classify_uk_location,
                                  requires_uk_only)
from podcast_agent.ai import AIError, ask_json, evaluate_batch
from podcast_agent.models import Podcast

TOPIC = "software developer in the uk only"


class UserBriefTests(unittest.TestCase):
    def setUp(self):
        self.web_patch = patch("podcast_agent.discovery.search_open_web", return_value=[])
        self.web_patch.start()
        self.addCleanup(self.web_patch.stop)

    def test_short_keyword_brief_is_valid(self):
        with patch('podcast_agent.agent.check_model'), patch('podcast_agent.agent.propose_tool', side_effect=AIError('offline')), patch('podcast_agent.agent.search_apple', return_value=[]):
            result = run_agent('UK SaaS', max_candidates=4)
        self.assertEqual(result.podcasts, [])

    def test_search_terms_preserve_uk_restriction(self):
        self.assertTrue(requires_uk_only(TOPIC))
        self.assertTrue(all('UK' in q or 'British' in q for q in fallback_queries(TOPIC)))

    def test_usual_country_reference_does_not_automatically_trigger_restriction(self):
        self.assertFalse(requires_uk_only('Discuss UK software news and US software companies'))

    def test_explicit_uk_location_is_required_for_uk_only(self):
        verified = Podcast('Dev Voice', 'https://test.example/podcast', description='Produced in the UK by two software engineers')
        unknown = Podcast('American Tech', 'https://test.example/us', description='News and opinions about UK technology')
        self.assertTrue(classify_uk_location(verified))
        self.assertFalse(classify_uk_location(unknown))
        self.assertEqual(unknown.location_status, 'Not verified')

    @patch('podcast_agent.agent.evaluate_batch')
    @patch('podcast_agent.agent.find_public_contact')
    @patch('podcast_agent.agent.enrich_from_feed')
    @patch('podcast_agent.agent.search_apple')
    @patch('podcast_agent.agent.propose_tool')
    @patch('podcast_agent.agent.check_model')
    def test_uk_only_never_promotes_unverified_apple_storefront_shows(self, check, choose, search, feed, contact, evaluate):
        choose.side_effect = AIError('planning timeout')
        search.side_effect = [
            [Podcast('International Dev', 'https://feeds.example/one', description='US development talk')],
            [Podcast('UK Code', 'https://feeds.example/two', description='Produced in the UK by Manchester software developers discussing software engineering and programming')],
            [],
        ]
        def update_feed(pod):
            pod.episodes = ['Architecture and software']
            if pod.title == 'International Dev':
                pod.description = 'Software engineering and programming discussions about UK development trends'
        feed.side_effect = update_feed
        result = run_agent(TOPIC, max_candidates=4)
        self.assertTrue(result.uk_only)
        self.assertEqual([p.title for p in result.podcasts], ['UK Code'])
        self.assertEqual(result.region_excluded, 1)
        self.assertTrue(any('UK-only filter excluded' in log for log in result.activity))


class OllamaRecoveryTests(unittest.TestCase):
    @patch('podcast_agent.ai.ask_json')
    def test_truncated_two_podcast_json_retries_individually(self, fake):
        fake.side_effect = [
            AIError('Ollama returned incomplete JSON: Unterminated string'),
            {'score': 85, 'reason': 'Software engineering episodes', 'subject': 'Guest collaboration',
             'introduction': 'Hello, I would like to discuss a potential guest conversation about software engineering on your show.'},
            {'score': 62, 'reason': 'Programming interviews', 'subject': 'A guest for your show',
             'introduction': 'Hello, your podcast covers programming and I would love to discuss a suitable guest interview.'},
        ]
        p = [Podcast('A Show', 'https://f.example/a'), Podcast('B Show', 'https://f.example/b')]
        messages = []
        evaluate_batch(TOPIC, p, 'llama3.2:3b', on_stream=messages.append)
        self.assertEqual([x.score for x in p], [85, 62])
        self.assertTrue(all(x.outreach_intro.startswith('Hello') for x in p))
        self.assertEqual(fake.call_count, 3)
        self.assertTrue(any(x['kind'] == 'retry' for x in messages))

    @patch('podcast_agent.ai.ask_json')
    def test_bad_host_recipient_draft_is_replaced(self, fake):
        fake.return_value = {'results': [
            {'id': 1, 'score': 80, 'reason': 'Tech podcasts', 'subject': 'Podcast recommendations',
             'introduction': "Hi [Friend's Name], I thought you might enjoy this podcast. Would you like to give it a listen?"}
        ]}
        p = [Podcast('Coding Stories', 'https://feeds.example/coding', episodes=['Language design'])]
        evaluate_batch(TOPIC, p, 'llama3.2:3b')
        self.assertIn('team behind Coding Stories', p[0].outreach_intro)
        self.assertNotIn('[Friend', p[0].outreach_intro)
        self.assertIn('Incorrect/empty', p[0].research_notes)

    @patch('podcast_agent.ai.ask_json')
    def test_missing_item_and_failed_single_retry_provides_no_fake_ai_score(self, fake):
        fake.side_effect = [
            {'results': [{'id': 1, 'score': 78, 'reason': 'UK software', 'subject': 'Host collaboration',
                          'introduction': 'Hello, I am reaching out to discuss a relevant software-development guest interview.'}]},
            AIError('Unterminated string'),
        ]
        items = [Podcast('A', 'https://example/a'), Podcast('B', 'https://example/b')]
        evaluate_batch(TOPIC, items, 'llama3.2:3b')
        self.assertEqual(items[0].score, 78)
        self.assertEqual(items[1].score, 0)
        self.assertTrue(items[1].outreach_intro)
        self.assertIn('retry failed', items[1].rationale)

    @patch('podcast_agent.ai.requests.post')
    def test_streamed_json_shows_live_progress(self, post):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        parts = [
            {'response': '{"tool":', 'done': False},
            {'response': '"finish"}', 'done': False},
            {'response': '', 'done': True},
        ]
        response.iter_lines.return_value = [json.dumps(p).encode() for p in parts]
        post.return_value = response
        events = []
        self.assertEqual(ask_json('llama3.2:3b', 'plan', {'topic': TOPIC}, on_stream=events.append), {'tool': 'finish'})
        self.assertEqual([e['kind'] for e in events], ['start', 'chunk', 'done'])
        self.assertTrue(post.call_args.kwargs['stream'])
        self.assertTrue(post.call_args.kwargs['json']['stream'])

    @patch('podcast_agent.ai.requests.post')
    def test_streamed_incomplete_json_is_rejected_not_used(self, post):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_lines.return_value = [json.dumps({'response': '{"score": 40, "subject": "unterminated', 'done': False}).encode(), json.dumps({'done': True}).encode()]
        post.return_value = response
        with self.assertRaisesRegex(AIError, 'incomplete or malformed'):
            ask_json('llama3.2:3b', 'assess', {'title': 'Test'})


class UIRegressionTests(unittest.TestCase):
    def test_new_research_prompt_is_editable_and_not_disabled(self):
        app = (Path(__file__).parent.parent / 'app/app.py').read_text(encoding='utf-8')
        self.assertIn("ui.text_area('What podcasts should we find?'", app)
        self.assertIn("key='podcast_query'", app)
        self.assertNotIn('streamlit', app.lower())

    def test_progress_and_csv_export_are_visible(self):
        app = (Path(__file__).parent.parent / 'app/app.py').read_text(encoding='utf-8')
        self.assertIn('Refresh status', app)
        self.assertIn('Research activity', app)
        self.assertIn('Evidence-ranked matches', app)
        self.assertIn('Download results as CSV', app)
        worker = (Path(__file__).parent.parent / 'podcast_workspace.py').read_text(encoding='utf-8')
        self.assertIn("on_status=status", worker)
        self.assertIn("status='completed'", worker)


if __name__ == '__main__':
    unittest.main()
