import unittest
from unittest.mock import patch

from podcast_agent.network import FetchError, validate_public_url


class NetworkSafetyTests(unittest.TestCase):
    def test_rejects_local_ips_and_file_urls(self):
        urls = [
            "http://127.0.0.1/secret",
            "http://192.168.1.2/config",
            "http://10.1.2.3/",
            "http://localhost:8000/",
            "file:///etc/passwd",
            "http://site.local/",
            "http://example.com:8080/",
        ]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(FetchError):
                validate_public_url(url)

    @patch("podcast_agent.network.socket.getaddrinfo")
    def test_rejects_dns_that_resolves_to_private_ip(self, resolve):
        resolve.return_value = [(2, 1, 6, "", ("172.16.0.3", 443))]
        with self.assertRaises(FetchError):
            validate_public_url("https://suspicious.example/")

    @patch("podcast_agent.network.socket.getaddrinfo")
    def test_allows_public_web_address(self, resolve):
        resolve.return_value = [(2, 1, 6, "", ("8.8.8.8", 443))]
        validate_public_url("https://podcasts.example/")


if __name__ == "__main__":
    unittest.main()
