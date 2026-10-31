# Podcast Outreach AI — publishing and live hosting

This is **the local Streamlit research agent**. It is ready for a **human-supervised beta/release candidate** after the end-to-end checks below, but it is **not already hosted online**. No email is sent by the application.

## Option A — Run it live on your Windows computer (recommended first)

1. Install Python 3.11+, Ollama and a text model. Run `ollama list` to verify the model.
2. Extract the full release ZIP directly into `E:\` so the project is `E:\podcast-outreach-ai`.
3. Double-click `START-HERE.bat`. The launcher prepares `.venv` and dependencies.
4. Open `http://localhost:8501`. Choose an installed Ollama model and search for `software developers and web developers`.
5. Inspect the sorted high-quality matches and verify each official contact source before copying a draft.
6. Run `run-tests.bat`. It invokes the **built-in unittest suite**; no separate pytest installation is required.

The app is available locally while the launching terminal and Ollama process remain running. Do not open Windows firewall port 8501 to the internet.

## Option B — Publish the source to GitHub and tag a release

With a GitHub repository already created and an `origin` remote configured:

```powershell
cd E:\podcast-outreach-ai
.\run-tests.bat
git status --short
git remote -v
git add .
git diff --cached --name-only
git commit -m "Podcast Outreach AI v1.0 release candidate - research quality"
git push -u origin main
```

Before committing, confirm that `.venv`, `.env`, `.streamlit/secrets.toml` and any API credentials are absent. If GitHub rejects a non-fast-forward push, **do not force-push**; fetch and resolve the remote history first.

After pushing, use **GitHub → Releases → Draft a new release** and create tag `v1.0.0-rc.1` from `main`. Mark it as a **pre-release**. Attach the complete Windows ZIP if you want users to have the one-click launcher in addition to GitHub's source-code archive. Source downloads do not contain `.venv`.

## Option C — Host privately on a Linux server with Ollama

A hosted Streamlit application cannot use the Ollama service running on *your Windows computer* at `127.0.0.1`. `localhost` means the server on which Streamlit is running. For hosting, run Ollama and the application on the **same Linux server**; do **not** publish Ollama's API to the internet.

1. Provision a Linux server with enough CPU/RAM for your chosen local Ollama model, and install Python 3.11+, Ollama and Caddy. Make sure `ollama list` works **on that server**, not only on your PC.
2. Install the project into `/opt/podcast-outreach-ai` and create a restricted Linux account named `podcastai` with permission to access the project. Create its Python environment using:
   ```bash
   cd /opt/podcast-outreach-ai
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python -m unittest discover -s tests -v
   ```
3. Ensure the **service account** can reach `http://127.0.0.1:11434` and can access a model with the same name you choose in the app. Local Ollama may have separate home directories/model visibility per account; verify this before enabling the service.
4. Adapt `deploy/podcast-outreach-ai.service.example` to your server and copy it to `/etc/systemd/system/podcast-outreach-ai.service`. Check the username and project path. Then:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now podcast-outreach-ai
   sudo systemctl status podcast-outreach-ai
   ```
5. Configure an actual domain pointing to the server. Generate a password hash with `caddy hash-password`, replace the example hostname and the placeholder hash in `deploy/Caddyfile.example`, and incorporate the site block into your Caddy configuration. Validate and reload Caddy using your distribution's service commands.
6. Leave Streamlit bound to `127.0.0.1:8501`; expose **only HTTPS (443)** through Caddy, protected by authentication. Do not expose port 8501 or Ollama port 11434 externally. Treat any podcast/contact research data as personal data where applicable.
7. Verify HTTPS login, Ollama connectivity, source retrieval and CSV export using a permitted test account before inviting anyone else.

### Security/operational caveats

This example provides a basic private beta hosting path, **not a certified production security architecture**. Add stronger identity management, audit logging, rate limits, outbound request isolation, backups, data retention rules and capacity planning before a commercial multiuser deployment. The current HTTP fetcher rejects nonpublic addresses, but it is not a complete SSRF defence against DNS rebinding and other network-layer attacks; restrict outbound network access independently on a public server. Follow site terms, privacy rules and opt-out preferences. **No automatic email sending is included.**

### Why not Streamlit Community Cloud directly?

The app expects a local Ollama API at `127.0.0.1:11434`. A Streamlit Community Cloud instance runs remotely and cannot connect to the Ollama installation on your home PC through its own localhost address. Hosting also needs authentication and controlled access to the model. See [Streamlit's deployment guidance](https://docs.streamlit.io/knowledge-base/deploy/remote-start).

## Release verification checklist

- Run all tests and inspect the results (`run-tests.bat` or `python -m unittest discover -s tests -v`).
- Confirm `software developers and web developers` produces no unwanted UK verification text.
- Confirm unrelated shows (e.g. dance competitions) are **rejected before contact checks**.
- Confirm the main shortlist is sorted by evidence score, with strong matches separated from possible matches.
- Confirm only public emails with original source URLs are shown; no guessed email addresses.
- Check every draft is to a podcast host, includes a specific guest proposal and is editable.
- Check a failed Ollama search suggestion still permits the bounded fallback research to finish.
- Verify real Apple Podcasts, optional Podcast Index, RSS sources and Ollama on the computer where the app will run.
- For hosted deployments, require HTTPS and access control.
