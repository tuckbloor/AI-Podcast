"""Bounded Ollama tool-using agent for the *original* Streamlit podcast UI.

The model proposes tool calls; the controller checks every proposal, applies
resource limits and runs only read-only tools. A deterministic recovery plan
keeps work moving if local model tool selection is slow or invalid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import time
from collections.abc import Callable

from .ai import AIError, ask_json, check_model, evaluate_batch
from .contacts import find_public_contact
from .discovery import DiscoveryError, search_apple
from .models import Podcast
from .rss import enrich_from_feed
from .ranking import rank_podcast

Progress = Callable[[float, str], None]
Activity = Callable[[str], None]
Status = Callable[[dict], None]

MAX_STEPS = 32
MAX_SEARCHES = 3
BATCH_SIZE = 5
MODEL_DECISION_TIMEOUT = 12

@dataclass
class ResearchRun:
    podcasts: list[Podcast] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    activity: list[str] = field(default_factory=list)
    model_decisions: int = 0
    fallback_used: bool = False
    tool_calls: int = 0
    research_errors: int = 0
    ollama_chunks: int = 0
    ollama_requests: int = 0
    retry_events: int = 0
    uk_only: bool = False
    region_excluded: int = 0
    uk_focus: bool = False
    weak_topic: int = 0
    rejected_leads: int = 0
    followup_searches: int = 0
    contact_pages_found: int = 0
    suitable_contacts_found: int = 0



def requires_uk_only(goal: str) -> bool:
    """An explicitly restrictive UK request is not the same as UK storefront search."""
    lower = goal.lower()
    return bool(re.search(r"\b(?:uk|united kingdom|british|england|scotland|wales)\b.{0,38}\bonly\b|\bonly\b.{0,38}\b(?:uk|united kingdom|british|england|scotland|wales)\b|\buk[- ]based\b", lower))


def classify_uk_location(pod: Podcast) -> bool:
    """Use explicit host/production-location evidence, NOT country=gb storefront."""
    rules = [
        r"\b(?:based|hosted|produced|recorded|broadcast)\s+(?:in|from)\s+(?:the\s+)?(?:uk|united kingdom|england|scotland|wales|northern ireland)\b",
        r"\b(?:uk|united kingdom|british|england|scotland|welsh|scottish)[- ](?:based|produced|hosted)\b",
        r"\b(?:podcast|show|hosts?)\s+(?:based|produced|hosted)\s+(?:in|from)\s+(?:the\s+)?(?:uk|united kingdom|england|scotland|wales)\b",
    ]
    # Explicit UK city statements are useful, but a passing reference to a
    # city is not. Require a production/base phrase next to the city.
    cities = r"london|manchester|birmingham|bristol|leeds|liverpool|sheffield|edinburgh|glasgow|cardiff|belfast|nottingham|newcastle|brighton|cambridge|oxford"
    rules.extend([
        rf"\b(?:based|produced|recorded|hosted|broadcast)\s+(?:in|from)\s+(?:the\s+)?(?:{cities})\b",
        rf"\b(?:{cities})[- ]based\s+(?:podcast|show|hosts?|producer)\b",
    ])
    for evidence, source in ((pod.description, pod.feed_url),
                             (pod.location_page_text, pod.website or pod.contact_source),
                             (pod.title, pod.feed_url)):
        for rule in rules:
            found = re.search(rule, evidence or "", flags=re.I)
            if found:
                pod.location_status = "UK location stated"
                pod.location_evidence = found.group(0)[:140]
                pod.location_source = source
                return True
    pod.location_status = "Not verified"
    pod.location_evidence = "Apple GB search does not prove a podcast is UK-based"
    pod.location_source = ""
    return False

_STOPWORDS = set("""a an and are as at be been but by can could do does for from guest guests has have how i in into is it its just like my of on or our podcast podcasts show shows that the their them there they this to uk us we weekly what which who will with you your exploring about interviews interview featuring features talking talk discussing discussion focused focus""".split())


def fallback_queries(description: str) -> list[str]:
    """Three *distinct* topic-driven searches even when the prompt is very short."""
    words = []
    for match in re.findall(r"[a-zA-Z][a-zA-Z0-9-]*", description.lower()):
        if match not in _STOPWORDS and (len(match) > 2 or match == "uk") and match not in words:
            words.append(match)
    words = [w for w in words if w not in {"only", "uk"}]
    base = " ".join(words[:3]) or "podcast interview"
    location = bool(re.search(r"\b(?:uk|british|united kingdom|england|wales|scotland)\b", description, re.I))
    if location:
        if re.search(r"\b(?:software|developer|programming|coding)\b", description, re.I):
            return ["UK software developer podcast", "British programming podcast", "UK software engineering interview"]
        return [f"UK {base} podcast", f"British {base} interviews", f"{base} UK"]
    return list(dict.fromkeys([f"{base} podcast", f"{base} interview", f"{base} discussions"]))[:3]


def propose_tool(model: str, description: str, candidates: list[Podcast],
                 queries: list[str], fed: set[int], contacted: set[int], assessed: set[int],
                 *, on_stream: Status | None = None) -> dict:
    """Obtain a single constrained model-proposed tool call, never execute JSON blindly."""
    state = {
        "target_description": description[:1100],
        "searches_already_used": queries,
        "podcasts": [
            {
                "id": i + 1,
                "title": p.title[:130],
                "description": p.description[:200],
                "episodes": p.episodes[:2],
                "rss_read": i in fed,
                "contact_checked": i in contacted,
                "drafted": i in assessed,
            }
            for i, p in enumerate(candidates)
        ],
    }
    result = ask_json(
        model,
        "You control a bounded podcast research agent. Select ONE next tool that genuinely helps find matching podcasts and prepare evidence-based introductory drafts. "
        "Respond with a JSON object containing 'tool' and either 'query' for discover or 'ids' for other tools. "
        "Tools: discover (Apple Podcasts: short 2-5 word query grounded in target description); "
        "read_rss (IDs of candidates to inspect, up to five); check_contact (IDs to inspect public contact pages, up to five); "
        "draft (IDs to assess and draft using researched evidence, up to five); finish (only after results assessed). "
        "Try at least two distinct discovery queries where possible. Do RSS before contacts and contacts before drafting. "
        "Don't repeat completed actions. Use candidate IDs, never make up podcast names or email addresses. "
        "Never issue email/send/delete commands. Prefer finishing once candidates have been researched. "
        "Example response: {\"tool\":\"read_rss\",\"ids\":[1,2,3]}.",
        state,
        timeout=(4, MODEL_DECISION_TIMEOUT),
        num_predict=150,
        **({"on_stream": on_stream} if on_stream else {}),
    )
    return result


def _ids(value: object, total: int, completed: set[int], prerequisites: set[int] | None = None) -> list[int]:
    if not isinstance(value, list):
        return []
    found = []
    for entry in value:
        # A bool isn't a real ID even though bool subclasses int.
        if type(entry) is not int or not 1 <= entry <= total:
            continue
        index = entry - 1
        if index in completed or (prerequisites is not None and index not in prerequisites):
            continue
        if index not in found:
            found.append(index)
    return found[:BATCH_SIZE]


def preferred_search_count(description: str) -> int:
    """Short country-targeted prompts require one extra discovery pass."""
    return 3 if len(description.split()) <= 5 and re.search(r"\b(?:uk|british|united kingdom)\b", description, re.I) else 2


def _decide_fallback(description: str, candidates: list[Podcast], queries: list[str],
                     fed: set[int], contacted: set[int], assessed: set[int]) -> tuple[str, object]:
    more_search = len(queries) < MAX_SEARCHES
    if more_search and (len(queries) < preferred_search_count(description) or len(candidates) < 1):
        for query in fallback_queries(description):
            if query.lower() not in {q.lower() for q in queries}:
                return "discover", query
    todo = [i for i in range(len(candidates)) if i not in fed]
    if todo:
        return "read_rss", todo[:BATCH_SIZE]
    todo = [i for i in range(len(candidates)) if i in fed and i not in contacted]
    if todo:
        return "check_contact", todo[:BATCH_SIZE]
    todo = [i for i in range(len(candidates)) if i in contacted and i not in assessed]
    if todo:
        return "draft", todo[:BATCH_SIZE]
    if more_search and len(candidates) < 1:
        return "discover", f"{fallback_queries(description)[0]} audio"
    return "finish", None


def _validate_proposal(result: dict, description: str, candidates: list[Podcast],
                       queries: list[str], fed: set[int], contacted: set[int], assessed: set[int]) -> tuple[str, object] | None:
    if not isinstance(result, dict):
        return None
    action = result.get("tool")
    if action == "discover":
        query = result.get("query")
        if len(queries) >= MAX_SEARCHES or not isinstance(query, str):
            return None
        query = " ".join(query.split())[:70]
        if not 3 <= len(query) <= 70 or "@" in query or "http" in query.lower() or query.lower() in {q.lower() for q in queries}:
            return None
        return "discover", query
    if action == "read_rss":
        selected = _ids(result.get("ids"), len(candidates), fed)
    elif action == "check_contact":
        selected = _ids(result.get("ids"), len(candidates), contacted, fed)
    elif action == "draft":
        selected = _ids(result.get("ids"), len(candidates), assessed, contacted)
    elif action == "finish":
        # Don't accept premature finish when the agent has no evaluated candidates.
        if candidates and len(assessed) == len(candidates) and len(queries) >= preferred_search_count(description):
            return "finish", None
        if not candidates and len(queries) >= MAX_SEARCHES:
            return "finish", None
        return None
    else:
        return None
    return (action, selected) if selected else None


def run_agent(description: str, *, model: str = "llama3.2:3b", max_candidates: int = 8,
              guest_profile: str = "", progress: Progress | None = None,
              on_activity: Activity | None = None, on_status: Status | None = None) -> ResearchRun:
    """Evidence-first bounded research agent. Nothing is sent to contacts.

    Discover broadly from directories and the public web; inspect the RSS before
    attempting contacts; reject off-topic podcasts before expensive AI drafting.
    Ollama suggests research search terms and writes drafts, but cannot bypass
    minimum relevance/region criteria or issue side-effecting commands.
    """
    from .discovery import search_open_web, search_podcast_index
    from .ai import _host_facing_fallback
    import os

    description = description.strip()
    if len(description) < 5:
        raise ValueError("Enter at least five characters describing the podcasts you want to find")
    max_candidates = max(1, min(20, int(max_candidates)))
    run = ResearchRun()
    run.uk_only = requires_uk_only(description)
    run.uk_focus = bool(re.search(r"\b(?:uk|united kingdom|british|england|scotland|wales)\b", description, re.I))
    guest_profile = guest_profile.strip()[:700]
    started = time.monotonic()
    last_model_chunks = 0

    def log(message: str) -> None:
        entry = f"{time.monotonic() - started:.1f}s · {message}"
        run.activity.append(entry)
        if on_activity:
            on_activity(entry)
        if on_status:
            on_status({"kind": "activity", "message": entry, "tool_calls": run.tool_calls, "errors": run.research_errors})

    def update(frac: float, message: str) -> None:
        if progress:
            progress(min(.98, frac), message)
        if on_status:
            on_status({"kind": "stage", "message": message, "progress": min(.98, frac)})

    def stream_status(event: dict) -> None:
        nonlocal last_model_chunks
        kind = event.get("kind")
        if kind == "start":
            run.ollama_requests += 1
            last_model_chunks = 0
        elif kind in ("chunk", "done"):
            current = max(0, int(event.get("chunks", 0)))
            run.ollama_chunks += max(0, current - last_model_chunks)
            last_model_chunks = max(current, last_model_chunks)
        elif kind in ("retry", "retry_failed"):
            run.retry_events += 1
            log("Ollama draft recovery: " + str(event.get("reason", ""))[:150])
        if on_status:
            on_status({**event, "ollama_requests": run.ollama_requests})

    update(.01, "Checking your local Ollama model")
    check_model(model)
    log(f"Started evidence-first research with {model}; target {max_candidates} relevant shows")
    if run.uk_only:
        log("STRICT UK-only requirement: unverified or international podcasts will not be recommended")

    # Ollama can select the first discovery phrase, while all subsequent source
    # checks are guaranteed. No repeated 12-second tool-planning stall.
    phrases = fallback_queries(description)
    try:
        update(.035, "Asking Ollama for one focused podcast search")
        suggestion = propose_tool(model, description, [], [], set(), set(), set(),
                                  **({"on_stream": stream_status} if on_status else {}))
        proposal = _validate_proposal(suggestion, description, [], [], set(), set(), set())
        if proposal and proposal[0] == "discover":
            query = str(proposal[1])
            # Reject wildly unrelated AI query plans; let the deterministic
            # synonym searches cover the user's original subject.
            if (set(re.findall(r"[a-z]{4,}", query.lower())) &
                    set(re.findall(r"[a-z]{4,}", " ".join(phrases).lower()))):
                phrases = [query] + [p for p in phrases if p.lower() != query.lower()]
                run.model_decisions = 1
                log(f"Ollama proposed a relevant search: {query}")
            else:
                run.fallback_used = True
                log("Ollama suggested an off-topic search; subject-specific queries retained")
        else:
            run.fallback_used = True
            log("Ollama search suggestion was invalid; subject-specific queries retained")
    except AIError as exc:
        run.fallback_used = True
        log(f"Ollama search planning unavailable ({str(exc)[:100]}); evidence-first search continues")

    phrases = list(dict.fromkeys(phrases))[:MAX_SEARCHES]
    seen_feeds: set[str] = set()
    pool: list[Podcast] = []
    max_pool = max(45, min(75, max_candidates * 8))

    def add_results(provider: str, results: list[Podcast]) -> None:
        added = 0
        for pod in results:
            key = pod.feed_url.lower().strip().rstrip("/")
            if not key or key in seen_feeds or len(pool) >= max_pool:
                continue
            seen_feeds.add(key)
            pod.discovery_source = provider
            pool.append(pod)
            added += 1
        log(f"{provider}: {len(results)} discovered · {added} new unique podcast leads")

    index_enabled = bool(os.getenv("PODCAST_INDEX_API_KEY") and os.getenv("PODCAST_INDEX_API_SECRET"))
    if not index_enabled:
        log("Podcast Index: optional API keys not configured (set both environment variables to enable)")
    for i, query in enumerate(phrases):
        run.queries.append(query)
        update(.05 + .30 * i / max(1, len(phrases)), f"Discovering shows: {query}")
        run.tool_calls += 1
        try:
            add_results("Apple Podcasts", search_apple(query, limit=16))
        except DiscoveryError as exc:
            run.research_errors += 1
            log(f"Apple Podcasts unavailable: {str(exc)[:180]}")
        if index_enabled and i < 2:
            run.tool_calls += 1
            try:
                add_results("Podcast Index", search_podcast_index(query, limit=12))
            except DiscoveryError as exc:
                run.research_errors += 1
                log(f"Podcast Index unavailable: {str(exc)[:160]}")
        if i == 0:
            run.tool_calls += 1
            try:
                add_results("Public web (RSS verified)", search_open_web(query, limit=3))
            except DiscoveryError as exc:
                run.research_errors += 1
                log(f"Public-web discovery unavailable: {str(exc)[:150]} — directory searches continue")

    # First-pass ranking prioritises obvious subject matches but leaves room
    # for generic titles that may have strong episode evidence inside the RSS.
    pool.sort(key=lambda p: rank_podcast(description, p, uk_focus=False), reverse=True)
    inspected: list[Podcast] = []
    max_feeds = min(len(pool), max(20, min(30, max_candidates * 4)))
    read_feeds: set[str] = set()
    for i, pod in enumerate(pool[:max_feeds]):
        update(.37 + .34 * i / max(1, max_feeds), f"Reading RSS and checking topic: {pod.title}")
        run.tool_calls += 1
        read_feeds.add(pod.feed_url.lower().strip().rstrip("/"))
        try:
            enrich_from_feed(pod)
        except Exception as exc:
            run.research_errors += 1
            pod.research_notes += f" | RSS error: {type(exc).__name__}"
            log(f"RSS read failed for {pod.title}: {type(exc).__name__}")
        if run.uk_focus:
            classify_uk_location(pod)
        rank_podcast(description, pod, uk_focus=run.uk_focus)
        log(f"RSS inspected: {pod.title} · {len(pod.episodes)} episode(s) · topic {pod.topic_points}/65")
        if pod.topic_points < 16:
            run.weak_topic += 1
            log(f"REJECTED off-topic: {pod.title} (topic evidence {pod.topic_points}/65) — no contact check or email draft")
            continue
        inspected.append(pod)
        log(f"QUALIFIED: {pod.title} · topic {pod.topic_points}/65 · source {pod.discovery_source}")
        # Search at least 2x the final desired leads for diversity, but avoid
        # inspecting dozens more once strong candidates are established.
        if len(inspected) >= max_candidates + 5 and i + 1 >= min(max_feeds, 18):
            break

    # Genuine follow-up investigation when many directory leads exist but too
    # few are relevant. One bounded extra search is enough; it is not a loop
    # that burns provider requests until an arbitrary result count is reached.
    if len(pool) >= 12 and len(inspected) < max_candidates and run.tool_calls < MAX_STEPS + 8:
        base = description.lower()
        if re.search(r"\b(?:web|frontend|javascript|html|css)\b", base):
            focused_query = "web development programming podcast"
        elif re.search(r"\b(?:software|programming|developer|coding)\b", base):
            focused_query = "software engineering developer podcast"
        else:
            focused_query = (" ".join(re.findall(r"[a-z]{3,}", description.lower())[:3]) + " expert interview podcast").strip()
        if focused_query and focused_query.lower() not in {q.lower() for q in run.queries}:
            run.queries.append(focused_query)
            run.followup_searches += 1
            log(f"Evidence gap: {len(inspected)} qualified out of {len(pool)} leads · follow-up search: {focused_query}")
            run.tool_calls += 1
            try:
                add_results("Apple Podcasts (targeted follow-up)", search_apple(focused_query, limit=18))
            except DiscoveryError as exc:
                run.research_errors += 1
                log(f"Targeted follow-up unavailable: {str(exc)[:160]}")
            remaining = [p for p in pool if p.feed_url.lower().strip().rstrip("/") not in read_feeds]
            remaining.sort(key=lambda p: rank_podcast(description, p, uk_focus=False), reverse=True)
            for pod in remaining[:max(0, 36-len(read_feeds))]:
                update(.69, f"Focused follow-up · checking RSS: {pod.title}")
                run.tool_calls += 1
                read_feeds.add(pod.feed_url.lower().strip().rstrip("/"))
                try:
                    enrich_from_feed(pod)
                except Exception as exc:
                    run.research_errors += 1
                    log(f"RSS follow-up failed for {pod.title}: {type(exc).__name__}")
                if run.uk_focus:
                    classify_uk_location(pod)
                rank_podcast(description, pod, uk_focus=run.uk_focus)
                log(f"RSS inspected: {pod.title} · {len(pod.episodes)} episode(s) · topic {pod.topic_points}/65 · focused follow-up")
                if pod.topic_points < 16:
                    run.weak_topic += 1
                    log(f"REJECTED off-topic: {pod.title} (topic {pod.topic_points}/65) — no contact or draft")
                    continue
                inspected.append(pod)
                log(f"QUALIFIED after follow-up: {pod.title} · topic {pod.topic_points}/65")
                if len(inspected) >= max_candidates + 5:
                    break

    run.rejected_leads = run.weak_topic
    if not inspected:
        log("No podcast passed the subject-relevance gate. No contact pages were opened and no drafts were generated.")
        run.podcasts = []
        if progress:
            progress(1.0, "Research complete — no relevant podcasts verified")
        return run

    # Contact details and location evidence are fetched ONLY for topic-matched
    # candidates, never for entertainment shows or unrelated search leads.
    inspected.sort(key=lambda p: (p.score, p.topic_points), reverse=True)
    # Research more official contact routes than final slots: the shortlist
    # may contain podcasts without working sites or published addresses.
    contact_budget = min(len(inspected), max_candidates * (3 if run.uk_only else 2))
    contacted: list[Podcast] = []
    for i, pod in enumerate(inspected[:contact_budget]):
        update(.74 + .15 * i / max(1, contact_budget), f"Checking official contact: {pod.title}")
        run.tool_calls += 1
        try:
            prev_notes = pod.research_notes
            find_public_contact(pod)
            if "Website unavailable:" in pod.research_notes[len(prev_notes):]:
                run.research_errors += 1
                log(f"Website blocked/unavailable: {pod.title} — evidence retained without contact")
        except Exception as exc:
            run.research_errors += 1
            pod.research_notes += f" | Contact check failed: {type(exc).__name__}"
            log(f"Contact source failed: {pod.title} · {type(exc).__name__}")
        if run.uk_focus:
            classify_uk_location(pod)
        rank_podcast(description, pod, uk_focus=run.uk_focus)
        contact_summary = ('sourced public email' if pod.email and pod.contact_source else
                           'publisher contact page found' if pod.contact_page else 'no public contact found')
        location_summary = f" · UK: {pod.location_status}" if run.uk_focus else ""
        log(f"Contact checked: {pod.title} · {contact_summary}{location_summary}")
        if pod.contact_page:
            run.contact_pages_found += 1
        if pod.email and pod.contact_source:
            run.suitable_contacts_found += 1
        contacted.append(pod)

    if run.uk_only:
        eligible = [p for p in contacted if p.location_status == "UK location stated"]
        run.region_excluded = len(inspected) - len(eligible)
        log(f"UK-only filter excluded {run.region_excluded} show(s); {len(eligible)} verified UK match(es)")
    else:
        eligible = contacted
    eligible.sort(key=lambda p: (p.location_status == "UK location stated" if run.uk_focus else True,
                                 p.score, p.topic_points), reverse=True)
    eligible = eligible[:max_candidates]
    if not eligible:
        log("No location-verified matches for this strict request; no emails drafted")
        run.podcasts = []
        if progress:
            progress(1.0, "Research finished — no podcasts meet the required location")
        return run

    # Ollama provides reasoned copy, but if a batch is malformed the existing
    # per-show retry + verified safe-template logic avoids fabricated details.
    for start in range(0, len(eligible), BATCH_SIZE):
        batch = eligible[start:start + BATCH_SIZE]
        update(.9 + .08 * start / max(1, len(eligible)),
               f"Ollama drafting {len(batch)} researched, on-topic podcast introduction(s)")
        try:
            evaluate_batch(description, batch, model,
                           **({"guest_profile": guest_profile} if guest_profile else {}),
                           **({"on_stream": stream_status} if on_status else {}))
            log(f"Ollama completed {len(batch)} outreach draft(s) for qualified podcasts")
        except AIError as exc:
            run.research_errors += 1
            log(f"Ollama draft error ({str(exc)[:130]}); safe guest placeholders used")
            for pod in batch:
                if not pod.outreach_intro:
                    pod.outreach_subject, pod.outreach_intro = _host_facing_fallback(
                        pod, description, guest_profile)
                    pod.rationale = "AI draft unavailable; factual topic relevance independently assessed"

    for pod in eligible:
        rank_podcast(description, pod, uk_focus=run.uk_focus)
    run.podcasts = sorted(eligible, key=lambda p: (p.location_status == "UK location stated" if run.uk_focus else True,
                                                   p.score, p.topic_points), reverse=True)
    log(f"Research complete: {len(run.podcasts)} relevant show(s), {run.rejected_leads} off-topic rejected, {run.tool_calls} tool calls")
    if progress:
        progress(1.0, "Research complete — review evidence and host-facing drafts; nothing sent")
    return run
