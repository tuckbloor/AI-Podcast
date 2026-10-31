"""Small, explicit data structures for the research pipeline."""

from dataclasses import dataclass, field


@dataclass
class Podcast:
    title: str
    feed_url: str
    apple_url: str = ""
    description: str = ""
    website: str = ""
    episodes: list[str] = field(default_factory=list)
    email: str = ""
    contact_source: str = ""
    contact_page: str = ""
    score: int = 0
    rationale: str = ""
    outreach_subject: str = ""
    outreach_intro: str = ""
    research_notes: str = ""
    location_status: str = "Not verified"
    location_evidence: str = ""
    location_source: str = ""
    location_page_text: str = ""
    latest_episode_date: str = ""
    activity_status: str = "Activity date unavailable"
    topic_points: int = 0
    match_quality: str = "Not assessed"
    score_breakdown: str = ""
    rank_evidence: str = ""
    ai_score: int = 0
    discovery_source: str = "Apple Podcasts"

    def to_row(self) -> dict[str, str | int]:
        return {
            "Podcast": self.title,
            "Discovery source": self.discovery_source,
            "Evidence score (0-100)": self.score,
            "Why it matches": self.rationale,
            "Public email (review before use)": self.email,
            "Email source": self.contact_source,
            "Publisher contact page": self.contact_page,
            "Website": self.website,
            "Apple Podcasts": self.apple_url,
            "RSS feed": self.feed_url,
            "Suggested subject": self.outreach_subject,
            "Suggested introduction": self.outreach_intro,
            "Research notes": self.research_notes,
            "UK location": self.location_status,
            "Location evidence": self.location_evidence,
            "Location source": self.location_source,
            "Match quality": self.match_quality,
            "Score breakdown": self.score_breakdown,
            "Last episode date": self.latest_episode_date,
            "Activity status": self.activity_status,
        }
