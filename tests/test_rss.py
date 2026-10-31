import unittest
from unittest.mock import patch

from podcast_agent.models import Podcast
from podcast_agent.network import FetchedContent
from podcast_agent.rss import enrich_from_feed


class RSSTests(unittest.TestCase):
    @patch("podcast_agent.rss.safe_fetch")
    def test_rss_metadata_and_episodes(self, fetch):
        xml = b'''<rss version="2.0"><channel>
        <title>Factory Podcast</title><link>https://factory.example/</link>
        <description>People and machines</description>
        <item><title>Automation in industry</title></item>
        </channel></rss>'''
        fetch.return_value = FetchedContent(xml, "https://feeds.example/rss", "application/rss+xml")
        item = Podcast("Old", "https://feeds.example/rss")
        enrich_from_feed(item)
        self.assertEqual(item.title, "Factory Podcast")
        self.assertEqual(item.description, "People and machines")
        self.assertEqual(item.website, "https://factory.example/")
        self.assertEqual(item.episodes, ["Automation in industry"])


if __name__ == "__main__":
    unittest.main()
