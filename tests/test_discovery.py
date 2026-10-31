import unittest
from unittest.mock import Mock, patch

from podcast_agent.discovery import search_apple, unique_podcasts
from podcast_agent.models import Podcast


class DiscoveryTests(unittest.TestCase):
    @patch("podcast_agent.discovery.requests.get")
    def test_apple_result_mapping(self, fetch):
        fetch.return_value = Mock(
            json=lambda: {"results": [
                {"collectionName": "Engineering Now", "feedUrl": "https://feeds.example/1", "collectionViewUrl": "https://podcasts.apple.com/id1"},
                {"collectionName": "No RSS"},
            ]}
        )
        podcasts = search_apple("engineering")
        self.assertEqual(len(podcasts), 1)
        self.assertEqual(podcasts[0].title, "Engineering Now")

    def test_interleaves_and_deduplicates(self):
        a = Podcast("A", "https://rss.example/a")
        b = Podcast("B", "https://rss.example/b")
        c = Podcast("C", "https://rss.example/c")
        self.assertEqual(unique_podcasts([[a, b], [a, c]], limit=3), [a, b, c])


if __name__ == "__main__":
    unittest.main()
