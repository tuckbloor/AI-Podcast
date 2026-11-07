# 🎙️ Podcast Outreach AI — v1.1.0-rc1

**An evidence-led podcast research and guest-outreach drafting agent, powered by your local Ollama model and the self-hosted [AI App Server](https://github.com/tuckbloor/AI-App-Server) framework.**

Research podcasts, inspect recent episodes, check publicly published contact routes, rank relevant shows, and prepare editable guest pitches. **The application never sends emails, submits booking forms, or contacts podcast hosts automatically.** You decide whom to contact and what to send.

This release replaces the old Streamlit dashboard and hard-coded Windows launchers with an independent AI App Server instance and a two-stage Windows installer.

## Requirements

| Requirement | Details |
| --- | --- |
| Windows | Windows 10 or 11; choose any writable install drive/folder |
| Python | Python **3.11+** on PATH or through the `py` launcher |
| AI App Server | **Required**; installer checks for an existing compatible installation or offers to install a separate v1.0.5 server first |
| Ollama | Run Ollama locally for AI research/drafting; select an installed model |
| Internet | Needed for Python dependencies on first install and public podcast/RSS searches |
| Browser | Recent Chrome, Edge, or Firefox to access the local dashboard |

### Two BAT files only

- **`INSTALL.bat`** — opens a persistent installation wizard, checks the AI App Server prerequisite, allows folder selection, installs or updates Podcast Outreach AI.
- **`START.bat`** — starts the installed independent application. Also accepts `--status`, `--stop`, and `--disable-autostart`.

No installation step assumes an `E:` drive. The installation files are in the **complete source ZIP**, not in a separate patch or downloader.

## Windows installation — complete walkthrough

1. Download the complete source ZIP from [GitHub Releases](https://github.com/tuckbloor/AI-Podcast/releases), or download the repository's source ZIP. Extract **all** files into a working folder, such as `Downloads\AI-Podcast`. Do not run the installer inside the ZIP.
2. Install Python 3.11 or newer if needed. Verify it in PowerShell with `py -3 --version`.
3. Double-click **`INSTALL.bat`**. The installer opens a window that **stays open and shows progress and errors**.
4. In **AI App Server prerequisite**, choose one of the following:
   - **Use an existing AI App Server (read-only):** the installer tries to locate a compatible, installed server. Select the server's directory with **Browse** if necessary. A typical installation is `%LOCALAPPDATA%\Programs\AI-App-Server`. This existing server is verified **without replacing its files or modifying its database**.
   - **Install a new AI App Server first:** if no compatible installation exists, choose this option. Select an **empty, writable** directory for the prerequisite. The bundle contains AI App Server **v1.0.5**, so there's no separate source download. The installer sets it up **before** installing the Podcast application.
5. Choose a **separate** Podcast Outreach AI directory. The default is `%LOCALAPPDATA%\Programs\AI-Podcast`, but `C:\AI-Podcast`, `D:\AI-Podcast`, or another writable folder is fine. The two directories **must not overlap**.
6. Optionally tick **Start Podcast now and enable automatic startup at Windows sign-in**. This is Windows sign-in startup, **not a system-level service**.
7. Select **Install / Update**. The window shows dependency installation and verification messages. For an existing recognised Podcast installation, the installer asks **Yes/No** before updating and creates a backup of its managed code. **No** cancels without changes.
8. On success, open the installed directory, then double-click **`START.bat`**. The browser opens the local application URL. The port is chosen and saved by AI App Server (typically **8501 if free**, otherwise a separate port). The admin page is at `/admin` on the same port.

**Do not choose the running AI App Server folder as the Podcast destination.** Your main server remains separate from Podcast's users, files, data, and port.

### First administrator login

On first startup, follow the AI App Server login and administrator setup prompts in your local browser. The Podcast instance has **its own administrator and users**, separate from your other installations. Change any initial administrator credentials immediately and keep the server local unless you have performed a proper production security review.

### Create a desktop shortcut

Open the **installed Podcast folder**, right-click `START.bat` → **Send to → Desktop (create shortcut)** (on Windows 11 use *Show more options* if needed). Rename the shortcut **Podcast Outreach AI**. The launcher may also be run from your extracted source folder: it can locate the last installed instance or ask you to select its location.

To start automatically when you sign in to Windows, use the installer option or place a shortcut to the **installed** `START.bat` inside `shell:startup` (press Win+R and enter that command). Avoid making duplicate startup entries. For an always-on service before sign-in, use a separately tested Windows service configuration with appropriate permissions; the installer does **not** silently register a Windows Service.

### Starting, stopping, and status

Open PowerShell in the *installed* Podcast directory and use:

```powershell
.\START.bat                  # starts the Podcast server and research worker
.\START.bat --status         # reports the running status
.\START.bat --stop           # stops Podcast, not your other AI App Servers
.\START.bat --disable-autostart
```

Starting your PC does not mean research will run automatically. It only starts the web server and its background worker. **You must choose to start a research job.**

## Set up Ollama

1. Install [Ollama](https://ollama.com/download/windows) and start it locally.
2. In PowerShell, run `ollama list` to see installed models, or `ollama pull llama3.2:3b` for an example.
3. Open Podcast Outreach AI. Choose an installed model in the left panel. Your computer may take some time to generate responses, especially with larger models.

Ollama listens at `127.0.0.1:11434` by default. Do not expose it to the public internet. Model execution is local; podcast directory searches still require internet access.

## How to use Podcast Outreach AI

1. In **Set up podcast research**, enter your topic, intended audience and optional country restriction. Example: *UK podcasts that interview software developers working on manufacturing and AI projects*.
2. Optionally add a **real** guest biography to improve pitch accuracy. The agent must not invent guest qualifications.
3. Choose the Ollama model and number of candidate podcasts (3–20).
4. Click **Find matching podcasts**. Research is queued to the independent background worker. The page does not lock while Ollama or publisher sites respond.
5. Click **Refresh status** to view progress and tool activity. Searches may take longer when feeds or local Ollama inference are slow.
6. Review **Evidence-ranked matches**. Compare recent episodes, relevance scores, official contact pages and draft introductory messages. Click **Inspect a podcast** for full evidence.
7. Click **Download results as CSV** and save the file for review in Excel.
8. Check sources yourself and edit each pitch before any manual outreach. **Nothing is sent automatically.**

### How the agent works

The underlying Python agent uses a bounded, tool-using research process: public podcast discovery, RSS inspection, contact-source checks, relevance ranking and local AI drafting. It can use Apple Podcasts searches, best-effort public web/RSS results, and optional Podcast Index credentials (`PODCAST_INDEX_API_KEY` and `PODCAST_INDEX_API_SECRET`). Source availability and third-party rate limits vary.

Results and research logs are stored in the Podcast instance's own SQLite database at `data/podcast-outreach.sqlite3`. A separate worker handles queued research and is started and stopped with the application's launcher. A server restart will mark any research still in progress as **interrupted**, so you can decide whether to run it again. No work is silently retried or emailed.

## Updating an existing installation without losing data

1. Stop Podcast from its **installed** directory using `START.bat --stop`.
2. Extract a new complete release ZIP into a **new source folder**, not over the installed application's `data/` folder.
3. Double-click the **new** `INSTALL.bat`, choose the same server prerequisite, and select the **existing Podcast installation directory**.
4. The wizard recognises supported older installations and asks whether you want to overwrite the managed application code. **Yes** creates a timestamped backup; **No** cancels. The installer preserves `data/`, `config/`, credentials and other user-owned files.
5. Test the updated application and its research worker before deleting any backup.

For **old Streamlit-based releases**, the installer recognises an existing installation only if the expected source and installed Python environment are present. It saves the previous code in a backup. Streamlit browser-session-only research was never stored in a persistent database and **cannot be migrated**. Export any old results before upgrading.

Never select an unrelated non-empty folder: the installer refuses it. This is deliberate safety protection.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Installer window does not appear | Run `INSTALL.bat` in an open PowerShell window and read the error. Verify Python 3.11+. |
| Server not found | Choose **Use existing** with its actual directory, or **Install new server first** with an empty directory. |
| Destination not empty | Select your real recognised Podcast installation and confirm the update, or choose a clean folder. |
| Browser doesn't open | Check the local URL printed by `START.bat --status`; open it manually. Check `data/logs/server.log`. |
| No Ollama models | Run `ollama list`; install a model and refresh the application. |
| Research stays queued | Confirm worker status with `START.bat --status` and check `data/logs/podcast-worker.log`. |
| Research fails | Inspect the displayed error and activity log. Provider availability and local Ollama responses can vary. |
| Another app already uses port 8501 | Podcast runs in a separate instance and chooses another available port. Use the URL printed by the launcher. |

The persistent Windows installer writes its log to `%LOCALAPPDATA%\AI-Podcast\installer.log` (or its equivalent under your user profile).

## Development and tests

The reusable AI App Server **v1.0.5** source is bundled under `framework/` to support installing the prerequisite when absent. `podcast_agent/` contains the research logic; `app/` contains the UI; `podcast_workspace.py` stores runs; `worker.py` processes queued jobs; and `tools/` contains installer and launcher Python code.

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m pip install -r requirements-dev.txt
py -3 -m pip install -e .\framework\engine
py -3 -m pytest -q tests
```

**Security note:** this is a **local, self-hosted application** with trusted Python code, not a sandbox for untrusted scripts. Public internet deployment needs HTTPS, authentication, reverse proxy configuration, backups, and a separate security assessment. No automatic outreach or bulk email capabilities are included.

## License

MIT — see [LICENSE](LICENSE).
