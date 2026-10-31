import unittest
from unittest.mock import patch

from podcast_agent.contacts import contact_links, find_addresses, find_public_contact
from podcast_agent.models import Podcast
from podcast_agent.network import FetchedContent


class ContactTests(unittest.TestCase):
    def test_extracts_only_explicit_email_and_ignores_hidden_scripts(self):
        markup = '''<html><script>"secret@example.com"</script>
        <a href="mailto:hello@podcast.example?subject=Hello">Contact</a>
        <p>For guests email booking@podcast.example.</p>
        <span>no-reply@podcast.example</span></html>'''
        self.assertEqual(find_addresses(markup), ["hello@podcast.example", "booking@podcast.example"])

    def test_contact_pages_remain_on_same_domain(self):
        markup = '''<a href="/contact">Contact</a>
        <a href="https://evil.example/contact">Contact us</a>
        <a href="/about">About our team</a>'''
        found = contact_links(markup, "https://pod.example/")
        self.assertEqual(found, ["https://pod.example/contact", "https://pod.example/about"])

    @patch("podcast_agent.contacts.safe_fetch")
    def test_prefers_explicit_contact_page_and_cites_page(self, fetch):
        def fake_fetch(url, **_):
            pages = {
                "https://pod.example": '<a href="/contact">Contact</a><p>info@pod.example</p>',
                "https://pod.example/contact": "<p>Send guest enquiries to guests@pod.example</p>",
            }
            return FetchedContent(pages[url].encode(), url, "text/html")

        fetch.side_effect = fake_fetch
        p = Podcast(title="Sample", feed_url="https://rss.example/rss", website="https://pod.example")
        find_public_contact(p)
        self.assertEqual(p.email, "guests@pod.example")
        self.assertEqual(p.contact_source, "https://pod.example/contact")


if __name__ == "__main__":
    unittest.main()
