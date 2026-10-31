# 🎙️ Podcast Outreach AI

**Research podcasts, identify genuinely relevant shows, investigate public contact routes, and prepare personalised guest pitches with a local Ollama model.**

Podcast Outreach AI is a Python + Streamlit research assistant with a tool-using AI workflow. It discovers podcasts through public directories and web sources, examines RSS descriptions and recent episodes, rejects off-topic shows **before** researching contacts, and produces editable outreach drafts addressed to podcast hosts.

**Release:** v1.0 release candidate · **Platform:** Windows (local), with a private Linux deployment example · **Licence:** MIT

> **No email is ever sent by this application.** It does not log in to Gmail, send messages, monitor inboxes, or schedule automatic outreach. All output must be reviewed by a human.

## Screenshots

The following images are stored in the repository's root-level `images/` directory. The filenames below are the original screenshot filenames — you do not need to rename them.

### 1. Research form and Ollama settings

![Podcast Outreach AI research prompt, sidebar settings, and search button](images/Screenshot%202026-10-31%20205145.png)

Enter a natural-language topic, optionally provide real guest details, select a locally installed Ollama model, and start research.

### 2. Live agent activity

![Live podcast research, RSS inspection, contact checking, and Ollama output](images/Screenshot%202026-10-31%20205157.png)

Watch source searches, RSS checks, rejected off-topic shows, contact investigations, and local AI drafting as the run progresses.

### 3. Evidence-ranked results

![Research statistics and evidence-ranked podcast results table](images/Screenshot%202026-10-31%20205409.png)

Review the ranked shortlist, publication dates where available, sourced contact addresses, and export the results as CSV.

### 4. Strong and possible matches

![Strong podcast matches and possible matches in expandable research cards](images/Screenshot%202026-10-31%20205421.png)

Prioritise strong matches and inspect possible matches before deciding whether to reach out.

## Features

- **Local AI with Ollama:** choose from installed models; no cloud AI subscription is required for the model itself.
- **Multiple podcast discovery routes:** Apple Podcasts Search API, best-effort public web/RSS discovery, and optional Podcast Index API.
- **Evidence-first filtering:** read real podcast metadata and episode titles; reject unrelated shows before investigating contacts or drafting pitches.
- **Adaptive research:** retry with a bounded, focused search when initial results have too few relevant podcasts.
- **Transparent 0–100 ranking:** subject relevance, dated podcast activity, public contact evidence, and geographic evidence **only when requested**.
- **Official contact-page investigation:** look for publicly published emails, podcast/producer contact pages, guest and booking pages; preserve original source URLs.
- **Host-facing outreach drafts:** Ollama prepares an introduction and subject line for each qualifying show. Incomplete or unsuitable drafts are rejected or replaced with editable templates.
- **Optional guest profile:** provide a real guest's name, expertise and talking points. The agent doesn't invent qualifications when the field is blank.
- **Live progress and metrics:** activity log, source requests, rejected shows, checked contact pages, streamed AI output and failure notices.
- **Strong and possible matches:** final ranking is sorted by calculated evidence score, not by the model's opinion.
- **CSV export:** download the results for further review.
- **Privacy-conscious workflow:** research and drafts only; **no automatic sending**.

## Requirements

| Requirement | Details |
|---|---|
| Operating system | Windows 10/11 for the included one-click scripts |
| Python | Python **3.11 or newer**; the launcher prefers Python 3.14 if available |
| Ollama | Installed and running on your PC |
| Ollama model | At least one local text/instruction model, e.g. `llama3.2:3b` |
| Internet | Needed for package installation and public podcast/web research |
| Browser | A recent browser for the local Streamlit interface |

Public providers may block requests or have availability/rate limits. A normal Internet connection does not guarantee every RSS feed or publisher website can be inspected.

## Full Windows installation

### Step 1 — Install Python

Install Python from [python.org](https://www.python.org/downloads/). Ensure the Windows Python launcher (`py`) is available. Open PowerShell:

```powershell
py -3 --version
```

A version of **3.11+** is required. If the command does not work, finish the Python installation and reopen PowerShell.

### Step 2 — Install Ollama and a model

Install [Ollama for Windows](https://ollama.com/download). Open/run Ollama, then check the locally available models:

```powershell
ollama list
```

If you do not have a suitable instruction-following model, an example is:

```powershell
ollama pull llama3.2:3b
```

The model is a starting point, not a guaranteed best performer. Smaller models generally run more comfortably on CPU, but can struggle with structured tool choices and long drafts. The app shows a bounded fallback when needed.

### Step 3 — Extract the project

Download the project's release ZIP and extract it **directly into `E:\`**, resulting in:

```text
E:\podcast-outreach-ai\
    app.py
    START-HERE.bat
    run-app.bat
    run-tests.bat
    prepare-env.bat
    requirements.txt
    podcast_agent\
    tests\
    images\
    README.md
    LICENSE
```

The screenshots belong in `E:\podcast-outreach-ai\images\` with their **unchanged filenames**. The `images` folder is needed to display the README screenshots on GitHub; it is not required to run the app.

You can use another drive; just substitute that path in the commands below. Avoid ending up with two nested `podcast-outreach-ai` folders.

### Step 4 — Run the application

Double-click **`START-HERE.bat`** inside the project folder, **or** run:

```powershell
cd E:\podcast-outreach-ai
.\START-HERE.bat
```

On the first run, the launcher automatically:

1. Creates a local Python virtual environment in `.venv`.
2. Installs the packages from `requirements.txt` if needed.
3. Starts the Streamlit web application.

Open **http://localhost:8501** (or the local URL printed in the terminal). Keep the launching terminal open while using the app.

**To stop:** press **Ctrl+C** in the terminal window.

### Running it again

```powershell
cd E:\podcast-outreach-ai
.\run-app.bat
```

You do **not** need to reinstall dependencies manually or recreate `.venv` every time.

### Manual installation if the launcher fails

```powershell
cd E:\podcast-outreach-ai
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If Python or pip reports a specific error, address that error first; do not disable security controls or expose Ollama to the Internet to work around it.

## User guide

### 1. Enter what you want the agent to find

Type into the **large white research prompt**. You can request a topic, genre, audience and/or geographic restriction. Examples:

```text
software developers and web developer podcasts
```

```text
Podcast interviews with manufacturing engineers and maintenance professionals
```

```text
UK software engineering podcasts only, with recent episodes and official contact details
```

**Country filtering:** the app only checks for UK evidence when the request calls for the UK. A global request **does not** silently require a UK-based show. An explicit **UK-only** request requires evidence of a UK base; appearing in Apple's GB storefront is not sufficient proof.

### 2. Add a guest profile (optional)

Expand **Optional guest profile** and enter accurate information about the person you'd like hosts to interview. For example:

```text
Alex Smith — software engineer with 12 years' experience in Laravel,
Vue and manufacturing software. Can discuss modernising legacy systems
and practical uses of AI in software teams.
```

The profile is **not** used to decide what topic you searched for. It helps the agent explain **why the guest would be appropriate** in outreach emails. Without a profile, drafts use clear placeholders such as `[Guest name]` rather than fabricating a person or their experience.

### 3. Select your local Ollama model and search size

In the **Research settings** sidebar, select an installed Ollama model. Use **Maximum podcasts to investigate** to limit how many qualifying shows the app researches (3–20; default 8).

### 4. Start research

Click the large teal **Find Matching Podcasts** button. The live research panel explains the current stage, including:

1. Planning suggested research terms with a short Ollama call (or using a safe topic-based fallback).
2. Discovering podcast feeds through the available sources.
3. Reading show descriptions, RSS entries and episode dates.
4. **Rejecting off-topic podcasts before contact research.**
5. Investigating official contact/guest pages for shortlisted podcasts.
6. Asking Ollama to write editable guest-pitch drafts.

The activity log reports rejected leads, source errors and AI retries. A fallback search plan does **not** mean that the model never contributed; Ollama may still generate the drafts.

### 5. Review the results

The results screen includes:

- **Relevant shows:** podcast leads retained after topic checks.
- **Strong matches:** the most topic-relevant leads, based on retrieved evidence.
- **Possible matches:** weaker leads that need additional human review.
- **Published emails found:** addresses observed on a retrieved source page, not guessed from a name.
- **Contact pages found:** original publisher contact routes, even if no email is displayed.
- **Research activity:** original tool actions, source failures and model feedback.
- **Results table:** podcast, evidence score, relevance label, latest known episode date and contact status.

Expand a podcast's research card to view its site, episode evidence, found contact pages and **editable draft introduction**. A contact-source link indicates where an address was observed; it does not verify deliverability, consent or permission to send marketing.

### 6. Check and use a draft

Before contacting a host, manually verify the podcast, host name, contact method, recent episode details and the guest's credentials. Edit the suggested subject and message as necessary, then copy it into **your own email application** if appropriate.

**This application has no Send Email button, no SMTP integration, and no automatic follow-ups.**

### 7. Export to CSV

Click **Download results as CSV** to save the research shortlist. The download is created by your browser; the app does not automatically upload it elsewhere.

## How evidence scores work

These scores are **heuristic research-priority scores**, not probability estimates or listening figures.

| Evidence component | No location restriction | UK-focused research |
|---|---:|---:|
| Podcast topic evidence | Up to 75 | Up to 65 |
| Dated recent episode activity | Up to 15 | Up to 15 |
| Sourced UK location statement | Not scored | Up to 10 |
| Published, sourced contact email | Up to 10 | Up to 10 |
| **Total** | **100** | **100** |

A show can be on topic without having an email address or a usable RSS date. Missing contact/recency evidence reduces its score, but it does not automatically establish that the show is unsuitable or inactive. The app distinguishes **strong topic matches** from **possible matches** separately from the numerical score.

## Optional: Podcast Index API

Apple Podcasts search does not require an API key. Podcast Index is an **additional discovery source** and needs your own Podcast Index API key and secret.

Configure them in the **PowerShell window used to launch the app**:

```powershell
cd E:\podcast-outreach-ai
$env:PODCAST_INDEX_API_KEY="YOUR_API_KEY"
$env:PODCAST_INDEX_API_SECRET="YOUR_API_SECRET"
.\START-HERE.bat
```

Do not put real credentials in a public README, a Git commit, screenshots or outreach prompts. If no credentials are set, the application simply skips this source. Public web discovery is best-effort and may be blocked.

## Automated tests

The project includes an offline regression suite covering discovery, source handling, ranking, location restrictions, contact evidence, malformed Ollama responses and draft validation.

```powershell
cd E:\podcast-outreach-ai
.\run-tests.bat
```

The test runner uses Python's built-in `unittest`; it prepares the same environment as the normal launcher. **Passing offline tests doesn't prove every live podcast provider or local Ollama model will work on a given network.**

## Troubleshooting

| Problem | What to do |
|---|---|
| `Python environment missing` | Use `START-HERE.bat` or `run-app.bat`; they call `prepare-env.bat` automatically. |
| Python not found | Install Python 3.11+ and reopen PowerShell; verify `py -3 --version`. |
| Ollama not connected | Ensure Ollama is running; check `ollama list` and access to `127.0.0.1:11434`. |
| Model produces malformed output | Try a more reliable instruction model; the application has bounded retries and fallback drafts. |
| Search seems slow | Local model generation may be CPU-bound; inspect the live stage and output chunk counter. |
| No podcast contact email | Many hosts use forms or don't publish addresses. Look for a sourced official contact page instead; don't guess an email. |
| Publisher website returns 403/redirect errors | Some sites block automated access. Consult the recorded original link manually. |
| RSS unavailable or too large | The app limits feed download size. The show may remain a lead with less supporting episode evidence. |
| Unexpected UK filtering | Include UK in the request only when you want it; use a location-neutral prompt for global searches. |
| Browser shows old colours/styles | Refresh with **Ctrl+F5** after restarting Streamlit. |
| App doesn't open on port 8501 | Look at the local URL printed by Streamlit; another app may already be using that port. |

## Repository structure

```text
podcast-outreach-ai/
├── app.py                     # Streamlit UI and live research feedback
├── podcast_agent/             # Discovery, RSS, ranking, contacts, Ollama, agent flow
├── tests/                     # Automated regression tests
├── images/                    # Four screenshots used by this README
├── .streamlit/config.toml     # Local app theme settings
├── START-HERE.bat             # Windows one-click launcher
├── prepare-env.bat            # Creates/repairs Python environment
├── run-app.bat                # Starts the Streamlit app
├── run-tests.bat              # Executes automated tests
├── requirements.txt           # Python dependencies
├── DEPLOYMENT.md              # Optional private Linux hosting example
├── LICENSE                   # MIT License
├── .gitignore
└── README.md
```

## Publishing and deployment

This repository can be published on GitHub as a **human-supervised release candidate**. Read [DEPLOYMENT.md](DEPLOYMENT.md) for a Windows run checklist and a private Linux setup with an HTTPS reverse proxy and authentication.

A hosted Streamlit application **cannot** reach Ollama on your own Windows PC through the hosted server's `localhost`. For private hosting, run Ollama on the same protected host or use an explicitly secured, controlled model endpoint. **Do not expose the Ollama API or an unauthenticated Streamlit instance directly to the Internet.** The included deployment example is not a production security certification.

## Responsible use and known limitations

- The tool performs research and **prepares drafts only**; it does not send messages or access your inbox.
- A published email address is not permission to send bulk or unsolicited marketing. Follow applicable privacy rules and service terms (including UK GDPR/PECR where relevant).
- Public podcast directory entries, RSS feeds and publisher sites can be stale, incomplete or unavailable.
- Automated relevance scores are aids to prioritisation, not guarantees of audience fit, episode recency, reach or host availability.
- Ollama may use a bounded fallback research plan if its proposed tool choice is invalid or slow. Describe this as a **tool-assisted, bounded research agent**, not an unrestricted autonomous system.
- Verify every proposed message and all relevant facts before contacting a podcast.

## Licence

MIT License — copyright © 2026 **tuckbloor**. See [LICENSE](LICENSE).

---

Built as an open-source, locally powered podcast research and outreach-drafting project.
