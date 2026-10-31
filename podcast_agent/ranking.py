"""Transparent podcast relevance scoring from retrieved evidence, not LLM percentages."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from .models import Podcast

# Domain keywords are not substitutes for evidence: they make a short query
# intelligible (e.g. "software developer" includes "programming").
DOMAINS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "software": (
        ("software develop", "software engineer", "programming", "programmer", "developer", "coding", "codebase", "web develop", "coding stor", "devops", "backend develop", "frontend develop", "computer science"),
        ("technology", "technical", "tech industry", "computing", "engineering", "python", "javascript", "c#", "open source", "git", "cloud computing"),
    ),
    "history": (("history", "historian", "historical", "archaeolog", "heritage", "ancient", "medieval"), ("museum", "culture", "archive")),
    "science": (("science", "scientific", "researcher", "physics", "biology", "chemistry", "astronomy"), ("discovery", "research", "engineering")),
    "business": (("entrepreneur", "small business", "startup", "business growth", "founder", "commerce"), ("marketing", "leadership", "finance", "strategy")),
    "health": (("health", "medicine", "medical", "wellbeing", "wellness", "fitness", "nutrition"), ("exercise", "diet", "mindfulness")),
}
STOP = set("a an and are as at be by can find for from guest guests in is it near of on only or podcast podcasts show shows the to uk united kingdom british england scotland wales with about i want me you my your please that recent best software developer".split())


def _contains(text: str, phrase: str) -> bool:
    # Prefixes such as "develop" match "development", but not embedded fragments.
    pattern = r"(?<![a-z0-9])" + re.escape(phrase).replace(r"\ ", r"\s+")
    # Only deliberately stemmed phrases may match longer words; e.g.
    # "software develop" -> developers/development. But "React" must not
    # match "reactions" and "web app" must not match "web appointments".
    if not phrase.endswith(("develop", "developer", "engineer", "programmer", "coder", "archaeolog", "histor", "stor", "collaborat")):
        pattern += r"(?![a-z0-9])"
    return bool(re.search(pattern, text, flags=re.I))


def _domain_for(query: str) -> str | None:
    q = query.lower()
    if any(_contains(q, t) for t in ("software", "developer", "programming", "coder", "coding", "web development", "devops", "software engineer")):
        return "software"
    for domain in ("history", "science", "business", "health"):
        if any(_contains(q, t) for t in DOMAINS[domain][0]):
            return domain
    return None


def _topic_points(query: str, podcast: Podcast) -> tuple[int, str]:
    title = podcast.title.lower()
    description = podcast.description.lower()
    episodes = " ".join(podcast.episodes[:5]).lower()
    domain = _domain_for(query)
    if domain:
        core, adjacent = DOMAINS[domain]
        # A web-development request includes the actual vocabulary used by
        # modern web-development shows. "Syntax" does not literally contain
        # "software developer" in its title, but episodes on JavaScript,
        # React, CSS and frontend engineering are directly on topic.
        if domain == "software" and re.search(r"\b(?:web|front.?end|full.?stack|website|javascript|html|css|react|vue)\b", query, re.I):
            core = core + (
                "web develop", "web design", "web app", "frontend", "front-end",
                "front end", "full stack", "full-stack", "javascript", "typescript",
                "react", "vue", "html", "css", "node.js", "browser", "website development",
            )
        title_hits = sum(_contains(title, word) for word in set(core))
        desc_hits = sum(_contains(description, word) for word in set(core))
        episode_hits = sum(_contains(episodes, word) for word in set(core))
        adjacent_hits = sum(_contains(title + ' ' + description + ' ' + episodes, word) for word in adjacent)
        # An unrelated coworking or job-search podcast cannot receive a high
        # score just because it shares the generic term "work".
        core_points = min(24, title_hits * 12) + min(23, desc_hits * 8) + min(18, episode_hits * 7)
        points = min(65, core_points + (min(6, adjacent_hits * 2) if core_points else 0))
        reason = f"{domain} topic evidence: {title_hits} title, {desc_hits} description, {episode_hits} episode term matches"
        return points, reason
    tokens = [w for w in re.findall(r"[a-z0-9]{3,}", query.lower()) if w not in STOP]
    tokens = list(dict.fromkeys(tokens))[:8]
    if not tokens:
        return 0, "No specific subject terms supplied"
    ti = sum(_contains(title, w) for w in tokens)
    de = sum(_contains(description, w) for w in tokens)
    ep = sum(_contains(episodes, w) for w in tokens)
    points = min(65, ti * 17 + de * 10 + ep * 5)
    return points, f"Topic evidence: {ti} title, {de} description, {ep} episode term matches"


def rank_podcast(query: str, podcast: Podcast, *, uk_focus: bool = False,
                 now: datetime | None = None) -> int:
    """Score by topic, recency, and sourced contact info.

    Geography is a scoring component ONLY when explicitly requested.
    No-country queries never lose ten points for failing a UK test.
    Scores describe evidence fit, not the model's confidence.
    """
    now = now or datetime.now(timezone.utc)
    topic, explanation = _topic_points(query, podcast)
    recent = 0
    if podcast.latest_episode_date:
        try:
            published = datetime.fromisoformat(podcast.latest_episode_date.replace('Z', '+00:00'))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            age = now - published
            if timedelta(0) <= age <= timedelta(days=180):
                recent = 15
                podcast.activity_status = "Episode within 6 months"
            elif timedelta(0) <= age <= timedelta(days=365):
                recent = 10
                podcast.activity_status = "Episode within 12 months"
            elif timedelta(0) <= age <= timedelta(days=730):
                recent = 4
                podcast.activity_status = "Episode within 24 months"
            else:
                podcast.activity_status = "Last dated episode over 2 years ago"
        except ValueError:
            podcast.activity_status = "Activity date unavailable"
    else:
        podcast.activity_status = "Activity date unavailable"
    location = 10 if uk_focus and podcast.location_status == "UK location stated" else 0
    contact = 10 if podcast.email and podcast.contact_source else 0
    podcast.topic_points = topic
    if uk_focus:
        podcast.score = min(100, topic + recent + location + contact)
        podcast.score_breakdown = f"Topic {topic}/65 · Recent activity {recent}/15 · Verified UK {location}/10 · Public contact {contact}/10"
    else:
        # Without a requested location, the score should use all 100 points
        # for subject fit, podcast activity and publicly sourced contact info.
        topic_scaled = round(topic * 75 / 65)
        podcast.score = min(100, topic_scaled + recent + contact)
        podcast.score_breakdown = f"Topic {topic_scaled}/75 · Recent activity {recent}/15 · Public contact {contact}/10"
    podcast.rank_evidence = explanation
    if topic < 16:
        podcast.match_quality = "Weak topic match"
    elif topic < 30:
        podcast.match_quality = "Possible match — review before outreach"
    else:
        podcast.match_quality = "Strong topic match"
    return podcast.score
