"""Podcast Outreach AI: original one-page Streamlit workflow, polished and evidence-led."""
from __future__ import annotations

import csv
from io import StringIO

import streamlit as st

from podcast_agent.agent import run_agent
from podcast_agent.ai import AIError, DEFAULT_MODEL, installed_models
from podcast_agent.discovery import DiscoveryError

st.set_page_config(page_title="Podcast Outreach AI | Research Studio", page_icon="🎙️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root { color-scheme: light; }
[data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at 82% 3%, rgba(20,184,166,.10) 0, transparent 38%),
              linear-gradient(180deg,#f4f8fa 0%,#f9fbfd 60%,#f4f8fa 100%);
}
[data-testid="stAppViewContainer"] > .main { background: transparent; }
[data-testid="stMainBlockContainer"] { max-width: 1220px; padding-top: 1.5rem; padding-bottom: 4rem; }
[data-testid="stHeader"] { background: rgba(248,251,253,.8); }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#eaf6f4 0%,#f5f9fc 100%); border-right: 1px solid #cddfdf; }
h1,h2,h3 { color:#102c39 !important; letter-spacing:-.035em; }
h2 { font-weight: 750 !important; }
p,li { color:#274457; }
.hero-panel { background: linear-gradient(112deg,#0d3040 0%,#0e5960 55%,#0c796e 100%); border-radius:23px;
   padding:29px 35px 32px; color:white; box-shadow:0 18px 44px rgba(8,55,65,.15); margin:0 0 25px 0; }
.hero-eyebrow { font-weight:800; text-transform:uppercase; font-size:12px; letter-spacing:.16em; color:#9aeee2; margin:0 0 10px; }
.hero-panel h1 { color:#fff !important; margin:0 0 8px; font-size:clamp(30px,4vw,45px); font-weight:850; line-height:1.13; }
.hero-panel p { color:#d9f4f3 !important; font-size:15px; max-width:760px; line-height:1.7; margin:0; }
.hero-tags { display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; }
.hero-tags span { display:inline-block; border:1px solid rgba(187,248,236,.25); border-radius:80px;
   padding:5px 11px; color:#ecfffd; background:rgba(255,255,255,.095); font-size:12px; font-weight:650; }
.step-heading { display:flex; align-items:center; gap:12px; margin-top:15px; margin-bottom:6px; }
.step-num { width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center; flex-shrink:0;
   color:#006d65;background:#daf5ee;border:1px solid #99decf;border-radius:11px; font-size:15px;font-weight:850; }
.step-heading h2 { font-size:23px !important; margin:0 !important; }
.step-detail { color:#61798a;font-size:14px;line-height:1.55;margin-bottom:16px; }
.small-note { color:#54717b;font-size:13px;margin-top:7px; }
[data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
   border-radius:16px; }
[data-testid="stForm"] { background:#fff; border:1px solid #d5e5e8 !important;
   border-radius:20px !important; padding:23px !important; box-shadow:0 8px 24px rgba(29,67,82,.05); }
[data-testid="stTextArea"] textarea, [data-testid="stTextArea"] textarea:disabled {
   background-color:#fff !important; color:#102a37 !important; -webkit-text-fill-color:#102a37 !important;
   caret-color:#0f766e !important; border:2px solid #0f766e !important; border-radius:12px !important;
   font-size:17px !important;line-height:1.65 !important;opacity:1 !important; min-height:94px;
   box-shadow:0 2px 5px rgba(16,99,92,.03) !important;
}
[data-testid="stTextArea"] textarea::placeholder { color:#6f8592 !important; opacity:1 !important; }
[data-testid="stTextArea"] [data-baseweb="textarea"], [data-testid="stTextArea"] [data-baseweb="base-input"] {
   background:#fff !important; border-radius:12px !important; }
[data-testid="stTextArea"] textarea:focus {border-color:#0ba89b !important;
   box-shadow:0 0 0 4px rgba(13,148,136,.17) !important; outline:none !important;}
/* Keep the main action visibly ENABLED: Streamlit's default pale/grey button is
   deliberately replaced. Scope to the form submit, not unrelated controls. */
[data-testid="stFormSubmitButton"] button,
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primary"],
div[data-testid="stFormSubmitButton"] button {
  appearance:none !important;
  background:linear-gradient(105deg,#007a69 0%,#006c82 100%) !important;
  background-color:#007a69 !important;
  color:#ffffff !important;
  -webkit-text-fill-color:#ffffff !important;
  border:2px solid #005a62 !important;
  border-radius:14px !important;
  min-height:60px !important;
  font-size:18px !important;
  font-weight:900 !important;
  letter-spacing:.015em !important;
  box-shadow:0 7px 0 #004e57,0 15px 25px rgba(0,91,99,.22) !important;
  opacity:1 !important;
  filter:none !important;
  cursor:pointer !important;
  transition:transform .14s ease, box-shadow .14s ease, background .14s ease !important;
}
[data-testid="stFormSubmitButton"] button * {
  color:#ffffff !important;
  -webkit-text-fill-color:#ffffff !important;
  font-weight:900 !important;
  opacity:1 !important;
}
[data-testid="stFormSubmitButton"] button:not(:disabled):hover {
  background:linear-gradient(105deg,#00977d 0%,#087b99 100%) !important;
  transform:translateY(-2px) !important;
  box-shadow:0 9px 0 #004e57,0 19px 28px rgba(0,91,99,.25) !important;
}
[data-testid="stFormSubmitButton"] button:not(:disabled):active {
  transform:translateY(4px) !important;
  box-shadow:0 2px 0 #004e57,0 4px 12px rgba(0,91,99,.18) !important;
}
[data-testid="stFormSubmitButton"] button:focus-visible {
  outline:4px solid #f7ba56 !important;
  outline-offset:4px !important;
}
[data-testid="stFormSubmitButton"] button:disabled {
  opacity:.45 !important;
  cursor:not-allowed !important;
}
[data-testid="stMetric"] {background:#fff; border:1px solid #d5e5e8; border-radius:15px;
  padding:14px 16px; min-height:95px; box-shadow:0 4px 13px rgba(11,51,65,.035);}
[data-testid="stMetricLabel"] {font-size:12px;color:#476878;}
[data-testid="stMetricValue"] {color:#0c5662; font-weight:750;}
[data-testid="stExpander"], [data-testid="stDataFrame"] {border-radius:15px !important; overflow:hidden;}
[data-testid="stExpander"] {background:#fff;border:1px solid #d6e7e9 !important; margin-bottom:12px;}
[data-testid="stAlert"] {border-radius:13px;}
[data-testid="stProgressBar"] > div > div {background:#0f9285;}
@media(max-width:780px){.hero-panel{padding:23px 20px}.hero-panel h1{font-size:29px}
 [data-testid="stMainBlockContainer"]{padding-left:.7rem;padding-right:.7rem}}
</style>
""", unsafe_allow_html=True)

st.markdown('''<div class="hero-panel">
<div class="hero-eyebrow">Local AI &nbsp;·&nbsp; Podcast intelligence studio</div>
<h1>🎙️ Podcast Outreach AI</h1>
<p>Find genuinely relevant podcasts, inspect recent episodes and public contact sources, and prepare thoughtful guest pitches with your local Ollama agent.</p>
<div class="hero-tags"><span>✧ Research agent</span><span>✓ Evidence-based matching</span><span>✉ Host-ready draft review</span><span>🔒 Nothing sent automatically</span></div>
</div>''', unsafe_allow_html=True)


@st.cache_data(ttl=40, show_spinner=False)
def models_for_sidebar() -> tuple[list[str], str]:
    try:
        return installed_models(), ""
    except AIError as exc:
        return [], str(exc)


with st.sidebar:
    st.markdown("### 🎛️ Research settings")
    st.caption("Choose a local model and control the size of the investigation.")
    models, model_error = models_for_sidebar()
    if models:
        default_index = models.index(DEFAULT_MODEL) if DEFAULT_MODEL in models else 0
        model = st.selectbox("Installed Ollama model", models, index=default_index,
                             help="A smaller instruction-tuned model often plans tools more quickly.")
        st.success(f"Ollama connected · {len(models)} model(s) available")
    else:
        st.error(model_error or "Ollama unavailable")
        model = st.text_input("Ollama model", value=DEFAULT_MODEL)
        st.caption("Start Ollama, then refresh the browser to detect installed models.")
    max_results = st.slider("Maximum podcasts to investigate", min_value=3, max_value=20, value=8)
    st.divider()
    st.markdown("**Research safeguards**")
    st.caption("No email is sent. Off-topic shows are rejected before contact research. Location restrictions apply only when you type them in your request.")
    st.caption("Discovery: Apple Podcasts + public web; optional Podcast Index with API keys set in the environment. Provider errors are shown, not hidden.")

st.markdown('<div class="step-heading"><span class="step-num">01</span><h2>Tell the agent what to find</h2></div>', unsafe_allow_html=True)
st.markdown('<div class="step-detail">Enter a subject and any location restrictions. This is an active typing field—write your own research request.</div>', unsafe_allow_html=True)
with st.form("podcast_search", clear_on_submit=False):
    description = st.text_area(
        "Podcast research prompt — type here",
        key="research_prompt", height=142,
        placeholder="e.g. Software and web development podcasts that interview working developers. Look for active shows, recent episodes and public host contact pages.",
        help="Search any country by default. Mention a country only if you want to narrow the results.",
    )
    with st.expander("＋ Optional guest profile — improve personalised outreach pitches", expanded=False):
        st.caption("Add the real guest's name, relevant experience and subjects they can discuss. Leave blank to receive a draft with clear placeholders, not invented credentials.")
        guest_profile = st.text_area(
            "Guest details (optional)", key="guest_profile", height=110,
            placeholder="e.g. Alex Smith — software engineer with 12 years in manufacturing systems. Can discuss Laravel, practical AI and modernising legacy factory software.")
    submitted = st.form_submit_button("🔎  FIND MATCHING PODCASTS  →", type="primary", use_container_width=True)

st.caption("**Example:** Software and web developer podcasts — find active shows, recent episodes and publicly listed host contact pages. Add a country only if it matters to you.")

if submitted:
    if len(description.strip()) < 5:
        st.warning("Please type a research subject (at least five characters) in the white box.")
    elif not models:
        st.error("Ollama isn't connected. Start it, refresh the browser and choose a model.")
    else:
        st.markdown('<div class="step-heading"><span class="step-num">02</span><h2>Live agent investigation</h2></div>', unsafe_allow_html=True)
        st.caption("Watch each tool as it works. The agent may take longer while Ollama generates text on your computer.")
        stage_area = st.empty()
        progress_bar = st.progress(0)
        status_area = st.empty()
        metric_columns = st.columns(4)
        metric_areas = [column.empty() for column in metric_columns]
        st.markdown("**Live research activity · newest first**")
        activity_area = st.empty()
        live_log: list[str] = []
        counters = {"searches": 0, "rss": 0, "contacts": 0}
        nonlocal_vars = {"chunks": 0, "last_in_response": 0}

        def render_metrics() -> None:
            metric_areas[0].metric("Podcast searches", counters["searches"])
            metric_areas[1].metric("RSS feeds inspected", counters["rss"])
            metric_areas[2].metric("Contact pages checked", counters["contacts"])
            metric_areas[3].metric("Ollama output chunks", nonlocal_vars["chunks"])

        render_metrics()

        def on_progress(value: float, message: str) -> None:
            progress_bar.progress(min(100, max(0, round(value * 100))))
            stage_area.markdown(f"**Current stage:** {message}")

        def on_activity(entry: str) -> None:
            live_log.append(entry)
            if " discovered · " in entry:
                counters["searches"] += 1
            elif "RSS inspected:" in entry:
                counters["rss"] += 1
            elif "Contact checked:" in entry or "Website blocked/unavailable:" in entry:
                counters["contacts"] += 1
            render_metrics()
            activity_area.markdown("\n\n".join(f"- {item}" for item in reversed(live_log[-14:])))

        def on_status(event: dict) -> None:
            stage = event.get("kind", "")
            if stage == "start":
                nonlocal_vars["last_in_response"] = 0
                status_area.info("🧠 Ollama request sent — waiting for the first generated text. Research is continuing; no email is being sent.")
            elif stage in {"chunk", "done"}:
                latest = max(0, int(event.get("chunks", 0)))
                nonlocal_vars["chunks"] += max(0, latest - nonlocal_vars["last_in_response"])
                nonlocal_vars["last_in_response"] = max(latest, nonlocal_vars["last_in_response"])
                metric_areas[3].metric("Ollama output chunks", nonlocal_vars["chunks"])
                if stage == "chunk":
                    status_area.info(f"🧠 Ollama is generating a reply · {latest} chunks · {event.get('elapsed', 0):.0f}s")
                else:
                    status_area.success(f"✅ Ollama completed this response · {latest} output chunks")
            elif stage == "thinking":
                status_area.info("🧠 Ollama is reasoning locally. Waiting for response text.")
            elif stage == "retry":
                status_area.warning("🔄 Ollama's response was incomplete. Retrying that podcast separately.")
            elif stage == "retry_failed":
                status_area.warning("⚠️ An Ollama assessment failed. The fallback draft is clearly labelled and based only on known details.")

        for key in ("results", "agent_log", "agent_stats", "terms", "uk_focus", "uk_only", "region_excluded", "research_query"):
            st.session_state.pop(key, None)
        try:
            research = run_agent(
                description, model=model, max_candidates=max_results,
                **({"guest_profile": guest_profile} if guest_profile else {}),
                progress=on_progress, on_activity=on_activity, on_status=on_status,
            )
        except (AIError, DiscoveryError, ValueError) as exc:
            st.error(f"Research stopped: {exc}")
        else:
            st.session_state["results"] = research.podcasts
            st.session_state["research_query"] = description.strip()
            st.session_state["terms"] = research.queries
            st.session_state["agent_log"] = research.activity
            st.session_state["agent_stats"] = {
                "Model-selected tools": research.model_decisions,
                "Research tool calls": research.tool_calls,
                "Source errors": research.research_errors,
                "Ollama requests": research.ollama_requests,
                "Ollama retries": research.retry_events,
            }
            st.session_state["fallback_used"] = research.fallback_used
            st.session_state["uk_only"] = research.uk_only
            st.session_state["uk_focus"] = research.uk_focus
            st.session_state["region_excluded"] = research.region_excluded
            st.session_state["weak_topic"] = research.weak_topic
            st.session_state["rejected_leads"] = research.rejected_leads
            if research.podcasts:
                status_area.success(f"✅ Research complete · {len(research.podcasts)} podcast(s) retained · {research.tool_calls} tool calls · {research.research_errors} source error(s)")
            elif research.uk_only:
                status_area.warning("No podcast had sufficient evidence of UK production. The agent will not label international/unknown shows as UK-based.")
            else:
                status_area.warning("Research finished without suitable results. Try a more specific subject or a broader region.")
            counters["searches"] = sum(" discovered · " in line for line in research.activity)
            counters["rss"] = sum("RSS inspected:" in line for line in research.activity)
            counters["contacts"] = sum("Contact checked:" in line for line in research.activity)
            render_metrics()

results = st.session_state.get("results", [])
if results:
    st.divider()
    st.markdown('<div class="step-heading"><span class="step-num">03</span><h2>Research results & outreach drafts</h2></div>', unsafe_allow_html=True)
    previous_query = st.session_state.get("research_query", "")
    if previous_query:
        st.caption("**Results for:** " + previous_query)
        if not submitted and description.strip() != previous_query:
            st.info("The prompt has changed, but these are results from your previous search. Select Find Matching Podcasts to research the new prompt.")
    st.caption("Match scores are calculated from retrieved evidence, not invented AI percentages. A public contact address is not proof of marketing consent.")
    terms = st.session_state.get("terms", [])
    st.caption("Search phrases: " + " · ".join(terms))
    st.caption(f"**{st.session_state.get('rejected_leads', 0)} off-topic feeds rejected before any contact research.** Results are sorted by final evidence score; source errors are in the activity log.")

    statcols = st.columns(4)
    statcols[0].metric("Relevant shows", len(results))
    statcols[1].metric("Strong matches", sum(p.topic_points >= 30 for p in results))
    statcols[2].metric("Published emails found", sum(bool(p.email and p.contact_source) for p in results))
    if st.session_state.get("uk_focus"):
        statcols[3].metric("Confirmed UK", sum(p.location_status == "UK location stated" for p in results))
    else:
        statcols[3].metric("Contact pages found", sum(bool(p.contact_page) for p in results))

    if st.session_state.get("uk_only"):
        st.info(f"Strict UK-only filter · {st.session_state.get('region_excluded', 0)} unverified show(s) excluded. Apple GB listings do not prove a UK location.")
    elif st.session_state.get("uk_focus"):
        st.info("UK was requested. Confirmed UK podcasts appear first; unknown-location podcasts are separated below as research leads, not claimed UK matches.")
    if not any(p.email and p.contact_source for p in results):
        st.caption("No publicly listed email addresses were found on the pages checked. Where available, open the publisher's contact page instead; addresses are never guessed.")
    if st.session_state.get("fallback_used"):
        st.info("Ollama did not provide a reliable search suggestion, so the evidence-first research plan continued. Ollama still writes the outreach drafts; tool and retry details are in the activity log.")
    stats = st.session_state.get("agent_stats", {})
    if stats:
        with st.expander("🧠 Agent performance & complete research activity", expanded=False):
            performance_cols = st.columns(3)
            performance_cols[0].metric("Model-selected actions", stats.get("Model-selected tools", 0))
            performance_cols[1].metric("Total tool calls", stats.get("Research tool calls", 0))
            performance_cols[2].metric("Ollama requests", stats.get("Ollama requests", 0))
            st.caption(f"Source errors: {stats.get('Source errors', 0)} · Model retries: {stats.get('Ollama retries', 0)}")
            st.markdown("\n\n".join(f"- {entry}" for entry in st.session_state.get("agent_log", [])))

    rows = [item.to_row() for item in results]
    if not st.session_state.get("uk_focus"):
        for row in rows:
            row.pop("UK location", None)
            row.pop("Location evidence", None)
            row.pop("Location source", None)
    table_rows = []
    for pod in results:
        row = {"Podcast": pod.title, "Evidence score": pod.score,
               "Relevance": pod.match_quality, "Latest episode": pod.latest_episode_date or "Unknown",
               "Public email": pod.email or "Not found",
               "Contact page": pod.contact_page or "Not found"}
        if st.session_state.get("uk_focus"):
            row["UK status"] = pod.location_status
        table_rows.append(row)
    st.dataframe(table_rows, hide_index=True, use_container_width=True)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button("⬇️ Download results as CSV", buffer.getvalue().encode("utf-8-sig"),
                       file_name="podcast_research.csv", mime="text/csv")

    def show_podcasts(items: list, category: str) -> None:
        if not items:
            return
        st.markdown(f"#### {category} · {len(items)}")
        for pod in items:
            label = f"{pod.title}   ·   {pod.score}/100 evidence score   ·   {pod.match_quality}"
            with st.expander(label, expanded=False):
                cols = st.columns(3)
                cols[0].metric("Topic fit", f"{pod.topic_points}/65")
                cols[1].metric("Evidence score", f"{pod.score}/100")
                cols[2].metric("Contact", "Found" if pod.email and pod.contact_source else "Not found")
                st.caption(pod.score_breakdown)
                st.write("**Evidence basis:**", pod.rank_evidence or "Not evaluated")
                st.write("**Ollama assessment (review independently):**", pod.rationale or "Not established")
                if st.session_state.get("uk_focus"):
                    st.write("**UK location:**", pod.location_status)
                    st.caption("Location evidence: " + (pod.location_evidence or "No production location established"))
                    if pod.location_source:
                        st.write("**Location statement source:**", pod.location_source)
                st.write("**Recent activity:**", pod.activity_status,
                         "· Last dated episode:", pod.latest_episode_date or "Unknown")
                st.write("**Discovery provider:**", pod.discovery_source)
                st.write("**Podcast website:**", pod.website or "Not found")
                st.write("**Apple Podcasts:**", pod.apple_url or "Not found")
                st.write("**Public contact email:**", pod.email or "Not found")
                st.write("**Email source:**", pod.contact_source or "Not available")
                if pod.contact_page:
                    st.write("**Publisher contact page:**", pod.contact_page)
                st.caption("Please verify the address's purpose and outreach permissions before contacting anyone.")
                if pod.episodes:
                    st.write("**Recent episode titles:**", "; ".join(pod.episodes[:5]))
                st.divider()
                st.markdown("**✉ Outreach draft — edit before using**")
                st.write("**Subject:**", pod.outreach_subject or "Not drafted")
                st.text_area("Review and edit before copying", value=pod.outreach_intro or "Not drafted",
                             key=f"pitch_{pod.feed_url}", height=250, label_visibility="collapsed")
                if pod.research_notes:
                    st.caption("Research notes: " + pod.research_notes)

    uk_focus = st.session_state.get("uk_focus", False)
    if uk_focus:
        verified = [p for p in results if p.location_status == "UK location stated" and p.topic_points >= 16]
        unknown = [p for p in results if p.location_status != "UK location stated" and p.topic_points >= 16]
        weak = [p for p in results if p.topic_points < 16]
        show_podcasts(verified, "✓ Confirmed UK · topic-relevant podcasts")
        if not verified:
            st.warning("No UK location was independently confirmed among the topic-relevant results. Unknown-location shows are not UK-verified.")
        show_podcasts(unknown, "◷ Location unverified · investigate before UK outreach")
        if weak:
            show_podcasts(weak, "Low-priority / weak topic matches")
    else:
        strong = [p for p in results if p.topic_points >= 30]
        possible = [p for p in results if 16 <= p.topic_points < 30]
        show_podcasts(strong, "✓ Strong topic matches — prioritise these hosts")
        show_podcasts(possible, "◷ Possible matches — review evidence before outreach")
else:
    st.markdown("---")
    st.caption("How it works: your request → Apple Podcasts / public web / optional Podcast Index → RSS topic validation → off-topic rejection → verified public contact pages → Ollama drafts. Nothing sent.")

if not submitted and st.session_state.get("agent_log"):
    with st.expander("🧠 Previous research activity", expanded=False):
        st.markdown("\n\n".join(f"- {entry}" for entry in st.session_state["agent_log"]))
st.caption("Read-only research and draft preparation. Nothing is sent automatically. Always review evidence, outreach wording and applicable privacy requirements.")
