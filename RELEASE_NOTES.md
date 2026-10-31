# Podcast Outreach AI — v1.0.0 release candidate

- Preserves the original polished single-page Streamlit workflow, visible white input area and high-contrast research button.
- Three podcast discovery routes: Apple Podcasts, best-effort public web/RSS discovery, and optional Podcast Index with user-provided credentials.
- Adds targeted follow-up discovery when the first candidate pool contains too few relevant shows.
- Ranks by *final evidence score*, not a stale intermediate score or Ollama's arbitrary percentage. Software/web-development shows get credit for matching JavaScript, React, CSS, HTML, frontend and full-stack episode evidence.
- Strong matches and possible matches are separated; weak-topic shows are rejected before contact lookup and drafting.
- Improves official contact-page investigation, retains contact form links, and decodes only addresses explicitly published through common obfuscation.
- The local Ollama model helps select a search and drafts outreach emails; bounded fallback continues when tool-choice JSON is unreliable. Invalid drafts are replaced with a clearly reviewable guest-pitch template.
- No UK verification appears unless a location is requested. No email sending or inbox access is implemented.
- Windows launcher creates the virtual environment and starts the app automatically. Includes tests and a private-server deployment example.

**Limitations:** Source websites may block automated research. Credentials are optional for Podcast Index but mandatory to use its API. Live provider access and locally installed Ollama models must be verified on the target computer. Automated tests are offline; the release is not proof of production security or commercial readiness.
