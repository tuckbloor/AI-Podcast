"""Orchestrate search -> RSS research -> contact discovery -> AI ranking."""

from collections.abc import Callable

from .ai import AIError, check_model, evaluate, plan_searches
from .contacts import find_public_contact
from .discovery import DiscoveryError, search_apple, unique_podcasts
from .models import Podcast
from .rss import enrich_from_feed

Progress = Callable[[float, str], None]


def run_research(
    friend_description: str,
    *,
    model: str = "llama3.2:3b",
    max_candidates: int = 8,
    progress: Progress | None = None,
) -> tuple[list[Podcast], list[str]]:
    """Run an on-demand, bounded agent. No sending, no ongoing background jobs."""
    description = friend_description.strip()
    if len(description) < 25:
        raise ValueError("Describe your friend's podcast in at least 25 characters")
    max_candidates = max(1, min(int(max_candidates), 25))

    def update(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

    update(0.02, "Checking local AI model")
    check_model(model)
    update(0.06, "Asking AI to create podcast-search terms")
    queries = plan_searches(description, model)
    groups = []
    errors = []
    for i, query in enumerate(queries):
        update(0.10 + i * 0.07, f"Searching Apple Podcasts: {query}")
        try:
            groups.append(search_apple(query, limit=max(15, max_candidates * 2)))
        except DiscoveryError as exc:
            errors.append(str(exc))
    podcasts = unique_podcasts(groups, limit=max_candidates)
    if not podcasts:
        if errors:
            raise DiscoveryError("; ".join(errors))
        return [], queries

    for index, podcast in enumerate(podcasts):
        update(0.32 + 0.65 * index / len(podcasts), f"Researching {index + 1}/{len(podcasts)}: {podcast.title}")
        enrich_from_feed(podcast)
        find_public_contact(podcast)
        try:
            evaluate(description, podcast, model)
        except AIError as exc:
            podcast.research_notes += f" | AI evaluation unavailable: {exc}"
            # Scores are not silently substituted with a non-AI heuristic.
            podcast.score = 0
            podcast.rationale = "AI evaluation unavailable"
    update(1.0, "Research complete — review contacts before outreach")
    return sorted(podcasts, key=lambda p: p.score, reverse=True), queries
