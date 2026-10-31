"""Critical offline tests: no unrelated shows, independent discovery and honest sources."""
import hashlib
import os
import unittest
from unittest.mock import Mock, patch
from podcast_agent.ai import AIError
from podcast_agent.models import Podcast
from podcast_agent.agent import run_agent
from podcast_agent.discovery import search_podcast_index, search_open_web
from podcast_agent.network import FetchedContent

TOPIC = 'software developer uk'


class QualityResearchTests(unittest.TestCase):
    def setUp(self):
        web = patch('podcast_agent.discovery.search_open_web', return_value=[])
        web.start()
        self.addCleanup(web.stop)

    @patch('podcast_agent.agent.check_model')
    @patch('podcast_agent.agent.propose_tool', side_effect=AIError('decision timeout'))
    @patch('podcast_agent.agent.search_apple')
    @patch('podcast_agent.agent.enrich_from_feed')
    @patch('podcast_agent.agent.find_public_contact')
    @patch('podcast_agent.agent.evaluate_batch')
    def test_dancing_show_is_rejected_before_contact_or_draft(self, drafting, contact, enrich, search, choose, check):
        search.side_effect = [
            [Podcast('Dancing with the Stars Official Podcast', 'https://feeds.example/dancing'),
             Podcast('Software Engineering Radio', 'https://feeds.example/software')], [], []
        ]
        def rss(p):
            if 'Dancing' in p.title:
                p.description = 'Dance celebrity competitions and ballroom performances'
                p.episodes = ['The best tango of the season']
                p.website = 'https://dance.example/'
            else:
                p.description = 'Software development, coding, programming and engineers'
                p.episodes = ['Practical Python and software engineering']
                p.website = 'https://software.example/'
        enrich.side_effect = rss
        def draft(_, group, model):
            self.assertEqual([p.title for p in group], ['Software Engineering Radio'])
            for p in group:
                p.outreach_intro = 'Hello Software Engineering Radio team, would you consider a guest interview? Best regards, [Your name]'
        drafting.side_effect = draft
        result = run_agent(TOPIC, max_candidates=5)
        self.assertEqual([p.title for p in result.podcasts], ['Software Engineering Radio'])
        self.assertEqual(contact.call_count, 1)
        self.assertGreaterEqual(result.rejected_leads, 1)
        self.assertTrue(any('REJECTED off-topic: Dancing with the Stars' in s for s in result.activity))
        self.assertTrue(result.fallback_used)

    @patch('podcast_agent.agent.check_model')
    @patch('podcast_agent.agent.propose_tool', side_effect=AIError('decision timeout'))
    @patch('podcast_agent.agent.search_apple', return_value=[])
    @patch('podcast_agent.discovery.search_podcast_index')
    @patch('podcast_agent.agent.enrich_from_feed')
    @patch('podcast_agent.agent.find_public_contact')
    @patch('podcast_agent.agent.evaluate_batch')
    def test_second_directory_researches_podcasts_missing_from_apple(self, drafting, contact, enrich, index, apple, choose, check):
        index.return_value = [Podcast('UK Software Developers', 'https://feed.example/dev')]
        enrich.side_effect = lambda p: setattr(p, 'description', 'Produced in the UK, software engineers and programming')
        with patch.dict(os.environ, {'PODCAST_INDEX_API_KEY': 'example-key',
                                    'PODCAST_INDEX_API_SECRET': 'example-secret'}):
            result = run_agent('software developer uk only', max_candidates=4)
        self.assertEqual(len(result.podcasts), 1)
        self.assertEqual(result.podcasts[0].discovery_source, 'Podcast Index')
        self.assertEqual(contact.call_count, 1)
        self.assertEqual(index.call_count, 2)
        self.assertTrue(all(x.location_status == 'UK location stated' for x in result.podcasts))

    @patch('podcast_agent.agent.check_model')
    @patch('podcast_agent.agent.propose_tool', side_effect=AIError('decision timeout'))
    @patch('podcast_agent.agent.search_apple')
    @patch('podcast_agent.agent.enrich_from_feed')
    @patch('podcast_agent.agent.find_public_contact')
    @patch('podcast_agent.agent.evaluate_batch')
    def test_strict_uk_only_does_not_draft_unknown_location(self, drafting, contact, enrich, search, choose, check):
        search.side_effect = [[Podcast('Software Programming Podcast', 'https://feed.example/unknown',
                                        description='Programming and software engineering')], [], []]
        result = run_agent('software developer uk only', max_candidates=4)
        self.assertEqual(result.podcasts, [])
        self.assertEqual(drafting.call_count, 0)
        self.assertEqual(contact.call_count, 1)  # only after passing topic gate
        self.assertEqual(result.region_excluded, 1)


class DiscoveryProviderTests(unittest.TestCase):
    @patch('podcast_agent.discovery.requests.get')
    def test_podcast_index_headers_and_sourced_records(self, http):
        fake = Mock()
        fake.json.return_value = {'feeds': [{'title': 'Coding from Britain', 'url': 'https://feed.example/rss',
                                             'description': 'UK software engineering', 'link': 'https://pod.example/'}]}
        http.return_value = fake
        with patch('time.time', return_value=1730000000):
            result = search_podcast_index('software developer', api_key='KEY', api_secret='SECRET')
        headers = http.call_args.kwargs['headers']
        self.assertEqual(headers['Authorization'], hashlib.sha1(b'KEYSECRET1730000000').hexdigest())
        self.assertEqual(headers['X-Auth-Key'], 'KEY')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].discovery_source, 'Podcast Index')
        self.assertEqual(result[0].website, 'https://pod.example/')
        self.assertEqual(result[0].apple_url, '')

    @patch('podcast_agent.network.safe_fetch')
    def test_web_search_needs_original_page_with_actual_rss_link(self, fetch):
        # search_open_web imports safe_fetch inside function; replace network module.
        rss = b'''<rss><channel><item><title>Podcast show</title><link>https://example.org/show</link></item></channel></rss>'''
        page = b'''<html><head><title>UK Coding Podcast</title>
            <meta name="description" content="Engineering interviews"/>
            <link rel="alternate" type="application/rss+xml" href="/podcast/feed.xml"/>
            </head><body>Podcast</body></html>'''
        fetch.side_effect = [FetchedContent(rss, 'https://www.bing.com/search?format=rss', 'application/rss+xml'),
                             FetchedContent(page, 'https://example.org/show', 'text/html')]
        shows = search_open_web('UK coding', limit=2)
        self.assertEqual(len(shows), 1)
        self.assertEqual(shows[0].feed_url, 'https://example.org/podcast/feed.xml')
        self.assertEqual(shows[0].discovery_source, 'Public web (RSS verified)')

    @patch('podcast_agent.network.safe_fetch')
    def test_web_search_does_not_treat_search_headline_as_podcast(self, fetch):
        rss = b'''<rss><channel><item><title>Podcast show</title><link>https://example.org/show</link></item></channel></rss>'''
        page = b'<html><head><title>Some article about podcasts</title></head></html>'
        fetch.side_effect = [FetchedContent(rss, 'https://www.bing.com/search', 'application/rss+xml'),
                             FetchedContent(page, 'https://example.org/show', 'text/html')]
        self.assertEqual(search_open_web('software developer'), [])


if __name__ == '__main__':
    unittest.main()
