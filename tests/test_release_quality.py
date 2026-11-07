"""Release gates based on actual October 2026 feedback, without live providers."""
from unittest import TestCase
from unittest.mock import patch

from podcast_agent.agent import run_agent
from podcast_agent.ai import AIError
from podcast_agent.contacts import find_addresses, find_public_contact, contact_links
from podcast_agent.models import Podcast
from podcast_agent.network import FetchedContent
from podcast_agent.ranking import rank_podcast


class ReleaseQualityTests(TestCase):
    def test_web_development_evidence_beats_generic_technology_careers(self):
        goal = "software developers and web developers"
        syntax = Podcast("Syntax", "https://podcasts.example/syntax", description=(
            "Modern web development with JavaScript, React, CSS, HTML and frontend engineering"),
            episodes=["Building with TypeScript and React", "CSS layouts for web developers"])
        jobs = Podcast("Open To Work", "https://podcasts.example/jobs", description=(
            "Jobs, careers, recruiting, hiring and workplace culture"),
            episodes=["Getting an interview", "Salary negotiation"])
        rank_podcast(goal, syntax)
        rank_podcast(goal, jobs)
        self.assertGreaterEqual(syntax.topic_points, 30)
        self.assertGreater(syntax.score, jobs.score)
        self.assertLess(jobs.topic_points, 16)
        self.assertEqual(syntax.match_quality, "Strong topic match")

    def test_cloudflare_published_contact_email_can_be_verified_from_page(self):
        address = "podcast@example.org"
        clear = bytes([42]) + bytes(x ^ 42 for x in address.encode())
        html = f'<a class="__cf_email__" data-cfemail="{clear.hex()}">[email protected]</a>'
        self.assertEqual(find_addresses(html), [address])
        self.assertEqual(find_addresses('<span data-cfemail="malformed">x</span>'), [])

    def test_contact_research_includes_guest_booking_and_keeps_source(self):
        html = '<a href="/guests">Pitch a guest</a><a href="/booking">Booking</a><a href="/contact-us">Contact</a>'
        links = contact_links(html, "https://show.example/")
        self.assertIn("https://show.example/guests", links)
        self.assertIn("https://show.example/contact-us", links)
        def fetched(url, **_):
            pages = {
                "https://show.example/": html,
                "https://show.example/guests": '<p>Pitch your guest using our form</p>',
                "https://show.example/booking": '<p>Bookings and enquiries</p>',
                "https://show.example/contact-us": '<a href="mailto:podcast@show.example">Email us</a>',
            }
            return FetchedContent(pages[url].encode(), url, "text/html")
        pod = Podcast("Web Dev Interviews", "https://feeds.example/rss", website="https://show.example/")
        with patch("podcast_agent.contacts.safe_fetch", side_effect=fetched):
            find_public_contact(pod)
        self.assertEqual(pod.email, "podcast@show.example")
        self.assertEqual(pod.contact_source, "https://show.example/contact-us")
        self.assertTrue(pod.contact_page.startswith("https://show.example/"))

    @patch("podcast_agent.discovery.search_open_web", return_value=[])
    @patch("podcast_agent.agent.evaluate_batch")
    @patch("podcast_agent.agent.find_public_contact")
    @patch("podcast_agent.agent.enrich_from_feed")
    @patch("podcast_agent.agent.search_apple")
    @patch("podcast_agent.agent.propose_tool", side_effect=AIError("planning unavailable"))
    @patch("podcast_agent.agent.check_model")
    def test_low_relevance_triggers_focused_search_and_sorted_shortlist(
            self, check, planning, apple, rss, contacts, drafting, web):
        weak = [Podcast(f"The Dancing Show {i}", f"https://feeds.example/dance{i}",
                        description="Ballroom celebrities and dance competitions") for i in range(13)]
        strong = Podcast("Software Engineering Radio", "https://feeds.example/ser",
                         description="Software engineers coding and programming")
        follow = Podcast("Syntax Web Dev", "https://feeds.example/syntax",
                         description="Web development JavaScript React CSS frontend and programming")
        apple.side_effect = [weak + [strong], [], [], [follow]]
        def enrich(p):
            p.episodes = ["Frontend JavaScript web development" if p == follow else
                          "Software engineering programming interview" if p == strong else "Tango"]
        rss.side_effect = enrich
        def contact(p):
            if p == follow:
                p.email = "hello@syntax.example"
                p.contact_source = "https://syntax.example/contact"
        contacts.side_effect = contact
        def draft(goal, batch, model, **kwargs):
            for pod in batch:
                pod.outreach_intro = "Reviewable guest pitch"
                pod.score = 5 # Model output must not determine final score or sorting
        drafting.side_effect = draft
        result = run_agent("software developers and web developers", max_candidates=4)
        self.assertEqual(result.followup_searches, 1)
        self.assertEqual(apple.call_count, 4)
        self.assertEqual(set(p.title for p in result.podcasts), {"Software Engineering Radio", "Syntax Web Dev"})
        self.assertEqual([p.score for p in result.podcasts], sorted((p.score for p in result.podcasts), reverse=True))
        self.assertEqual(contacts.call_count, 2)
        self.assertGreaterEqual(result.rejected_leads, 13)
        self.assertTrue(any("follow-up search" in event for event in result.activity))
        self.assertEqual(result.suitable_contacts_found, 1)
        self.assertFalse(any("UK:" in event for event in result.activity))

    def test_ui_sections_release_readiness(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / 'app/app.py').read_text(encoding='utf-8')
        self.assertIn('Find matching podcasts', source)
        self.assertIn('Evidence-ranked matches', source)
        self.assertIn('Refresh status', source)
        self.assertIn('Download results as CSV', source)
        self.assertIn('Nothing is emailed', source)
