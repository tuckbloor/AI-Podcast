## Location-neutral UI and visible action-button correction — 31 October 2026

- Geography is now considered only when the user actually mentions the UK. Unrestricted searches do not show UK verification in results, scoring, contact logs, CSV or per-show panels.
- Non-geographic evidence scores are reweighted to 75 topic / 15 recent activity / 10 contact points, rather than silently losing ten points for an unrequested UK location.
- Start button receives a high-contrast active teal design with white text, clear hover/focus feedback and an unmistakable call to action.
- Research captures a publisher contact-page link when available, even if no public email appears. It never guesses email addresses or sends messages.

# Changelog

## 2026-10-31 — Research quality and multi-source discovery

- Enforces topic relevance **before** researching contact pages or generating outreach drafts.
- Rejects irrelevant entertainment and generic results; shows the reason in the activity log.
- Searches Apple Podcasts, best-effort public web podcast feed links, and optional credentialed Podcast Index.
- Allows one bounded Ollama search suggestion; subsequent source checks follow an evidence-first plan without repeated tool-selection delays.
- Collects a larger deduplicated candidate pool, checks RSS before filtering, and tracks each discovery provider.
- Maintains UK-only evidence requirements, guest-profile placeholders and manual-only outreach.
- Adds regression tests based on the user's actual failed search.


## 2026-10-31 — Polished Research Studio and evidence-first agent repair

- Refreshed the original Streamlit page with a modern navy-and-teal design, high-contrast input, clear progress, research metrics and individual lead cards.
- Added optional guest background information so pitches use supplied experience, not invented facts.
- Replaced arbitrary model-scored 90% matches with transparent scoring across topic, podcast activity, proven UK base and published contact source.
- Verified UK / unverified country / weak topic results are separated for UK-focused searches. Strict UK-only still excludes unverified locations.
- Improved short UK prompt fallback queries and diversified candidate collection across searches.
- Parses RSS item publication dates and expands bounded feed download size.
- Adds explicit location statements from public publisher pages to the location assessment.
- Rejects one-line podcast advertisements, emails addressed to a listener and drafts missing a guest proposal and sign-off; provides a full host-addressed fallback.
- Retains the original agent tools, safe restrictions, Ollama streaming, CSV and automatic Windows installer.

## 2026-10-31 — Original interface UX and agent reliability repair

- Clear white prompt field, local-model dropdown and streaming tool feedback.
- Malformed Ollama output recovery; safe host-facing draft fallback.
- Source-error reporting and explicit UK-only verification.

## 2026-10-31 — Release candidate: ranking and research quality

- Sorts the shortlist by final evidence score, with clear strong/possible match sections.
- Expands topical evidence to web-development stacks without mistaking generic job/coworking shows for developer shows.
- Adds one focused follow-up search when an initial large pool produces too few matches.
- Checks more relevant official contact routes and preserves public email source URLs.
- Recognises Cloudflare-obfuscated public email addresses without guessing contacts.
- Maintains strict evidence-first filtering, optional geography, safe manual-only outreach and the original Streamlit interface.
- Adds release-regression tests and a guarded private-Linux-hosting sample.
