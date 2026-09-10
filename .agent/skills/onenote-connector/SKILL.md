---
name: OneNote Connector
description: A skill to sync daily logs and weekly reflections from Microsoft OneNote to local markdown.
---

# Microsoft OneNote Connector

This connector allows the AI Second Brain to synchronize daily notes, weekly reflections, and project-specific pages from Microsoft OneNote using the Microsoft Graph API.

## Capabilities

1. **Authentication**: Uses the secure OAuth 2.0 Device Code flow to obtain access and refresh tokens.
2. **List Notebooks, Sections, and Pages**: Helper commands to retrieve structure information.
3. **HTML to Markdown Parsing**: Converts OneNote page HTML content (including to-do check list structures) into clean, standard Markdown.
4. **Syncing Pages**: Automatically scans designated notebooks and sections to sync pages (e.g. for daily logs and weekly reflections) into the local `journal/onenote/` directory.

## Usage

All commands should be executed from the repository root using the workspace's virtual environment:

### Authenticate
Initiates the device code flow for first-time authentication or manual re-auth:
```bash
python3 .agent/skills/onenote-connector/scripts/onenote_client.py --action auth
```

### List Notebooks
```bash
python3 .agent/skills/onenote-connector/scripts/onenote_client.py --action list-notebooks
```

### Synchronize Logs
Downloads current-month notes and weekly reflections to `journal/onenote/`:
```bash
python3 .agent/skills/onenote-connector/scripts/onenote_client.py --action sync-journal
```
