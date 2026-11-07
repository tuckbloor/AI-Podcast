"""Podcast Outreach AI web workspace on a private AI App Server instance."""
from __future__ import annotations
from contextlib import closing
import json
import ai_app_server as ui
from podcast_agent.ai import AIError, DEFAULT_MODEL, installed_models
from podcast_workspace import connect, queue_research, list_runs, get_run, latest_run, events, csv_for_run

ui.title('🎙️ Podcast Outreach AI')
ui.caption('RESEARCH WORKSPACE   /   PRIVATE AI APP SERVER')
ui.text('Find relevant shows, verify recent episodes and published contact routes, then prepare editable pitches with your local Ollama model. No email is sent.')

with ui.sidebar():
    ui.section('Research controls')
    try:models=installed_models()
    except AIError as exc:
        models=[];ui.warning(str(exc))
    if models:
        model=ui.selectbox('Installed Ollama model',models,key='podcast_model')
    else:
        model=ui.input('Ollama model',DEFAULT_MODEL,key='podcast_manual_model')
    limit=int(ui.number_input('Maximum podcasts (3–20)',8,key='podcast_max_candidates'))
    limit=min(20,max(3,limit))
    ui.guide('Install Ollama and pull a model, for example: ollama pull llama3.2:3b')
    ui.caption('Research only · No outbound emails · Independent SQLite data')

ui.section('01  Set up podcast research')
request=ui.text_area('What podcasts should we find?',height=145,key='podcast_query')
profile=ui.text_area('Guest background (optional — real qualifications only)',height=100,key='podcast_guest')
with closing(connect()) as db:
    current=latest_run(db)
    busy=bool(current and current['status'] in ('queued','running'))
    if busy:
        ui.warning('A research job is already queued or running. Use Refresh status below.')
    elif ui.button('Find matching podcasts',key='podcast_start'):
        try:
            ident=queue_research(db,request,model=model,guest_profile=profile,max_candidates=limit)
            ui.success('Research queued. Your local worker will investigate the podcast sources. Click Refresh status to monitor progress.')
            current=get_run(db,ident)
        except ValueError as exc:ui.error(str(exc))
    ui.section('02  Research activity')
    if ui.button('Refresh status',key='podcast_refresh'):
        ui.success('Latest status loaded.')
    if current:
        ui.text('Request: '+current['query'])
        stats=ui.columns(3)
        with stats[0]:ui.metric('Status',current['status'].title())
        with stats[1]:ui.metric('Progress',str(round(current['progress']*100))+'%')
        with stats[2]:ui.metric('Results',str(len(json.loads(current['results_json']))))
        ui.text('Current stage: '+current['stage'])
        if current['error']:ui.error(current['error'])
        for event in events(db,current['id'],limit=12):ui.caption(event['at']+' — '+event['message'])
        if current['status']=='interrupted':ui.warning('The worker stopped before completing this job. Start a new investigation to retry.')
        ui.divider()
        ui.section('03  Evidence-ranked matches')
        rows=json.loads(current['results_json'])
        if rows:
            cols=['Podcast','Evidence score (0-100)','Match quality','Last episode date','Public email (review before use)','Publisher contact page']
            ui.table([{k:row.get(k,'') for k in cols} for row in rows])
            titles=[f"{i+1}. {r['Podcast']}" for i,r in enumerate(rows)]
            selection=ui.selectbox('Inspect a podcast',titles,key='podcast_show')
            if selection:
                selected=rows[titles.index(selection)]
                for k,v in selected.items():
                    if v not in ('',None):
                        ui.section(k)
                        ui.text(str(v))
            ui.download_button('Download results as CSV', csv_for_run(current), 'podcast-outreach-results.csv')
        elif current['status']=='completed':ui.warning('No sufficiently relevant podcasts passed the evidence filters for this search.')
    else:
        ui.caption('No research has been run yet. Enter a topic and select Find matching podcasts.')
    ui.section('Research history')
    runs=list_runs(db,limit=20)
    for run in runs:
        ui.caption(f"{run['created_at']}  •  {run['status'].upper()}  •  {run['query'][:100]}")
ui.divider()
ui.caption('Nothing is emailed or submitted to third parties on your behalf. Review sources and draft wording before contacting any host.')
