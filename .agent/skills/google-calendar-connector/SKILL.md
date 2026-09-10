---
name: Google Calendar Connector
description: A skill to interact with Google Calendar API for fetching schedules, sweeping weekly focus, and generating calendar summaries.
---

# Google Calendar Connector Skill

Connect to Google Calendar to fetch events, sweep weekly schedules, and generate structured summaries for Dashboard integration.

## Capabilities
- **List** events for a custom date range.
- **Sweep** events grouped by Today / This Week / Last Week (text or markdown output).
- Supports multiple profiles: `default` (personal) and `work`.
- **Timeouts**: Scripts have a built-in **180-second global timeout**. Always wrap background calls in `timeout 180s` for safety.

## Commands

### Sweep (Recommended for Dashboard)
```powershell
# Personal calendar sweep (markdown for Dashboard)
timeout 180s python3 .agent/skills/google-calendar-connector/gcal_manager.py sweep --profile default --output markdown

# Work calendar sweep
timeout 180s python3 .agent/skills/google-calendar-connector/gcal_manager.py sweep --profile work --output markdown

# Plain text sweep
python .agent/skills/google-calendar-connector/gcal_manager.py sweep --profile default

### Create (Schedule Event)
```powershell
# Create a 1-hour meeting
timeout 180s python3 .agent/skills/google-calendar-connector/gcal_manager.py create --summary "Meeting Title" --start "2026-04-08T08:00:00" --end "2026-04-08T09:00:00" --profile default

# Create with description
python .agent/skills/google-calendar-connector/gcal_manager.py create --summary "Sync with Team" --start "2026-04-08T10:00:00" --end "2026-04-08T11:00:00" --desc "Weekly sync to discuss PRDs"

# External event (no Meet link), with location and a custom reminder 4h20m (260 min) before
python .agent/skills/google-calendar-connector/gcal_manager.py create --summary "Webinar" --start "2026-04-08T14:00:00" --end "2026-04-08T16:00:00" --no-meet --location "https://zoom.us/j/123" --reminder-minutes "260"
```

**Reminder flag**: `--reminder-minutes` takes a comma-separated list of minutes-before (e.g. `260` or `260,30`). Each value creates BOTH a popup and an email reminder, and replaces the calendar's default reminders for that event. Times are always interpreted as `Asia/Jakarta`.
```

### List (Raw event listing)
```powershell
# Default profile
timeout 180s python3 .agent/skills/google-calendar-connector/gcal_manager.py list --days-back 7 --days-forward 7

# Work profile
python .agent/skills/google-calendar-connector/gcal_manager.py list --days-back 7 --days-forward 7 --profile work
```

## Authentication
- **Default**: Uses `credentials.json` and `token_calendar.json` in the project root.
- **Work**: Uses `credentials.json` and `token_calendar_work.json` in `.agent/skills/work-drive-connector/`.
- First run per profile requires OAuth browser authorization.

## Integration Points
- **Daily Update Workflow** (`/daily-update`): Step 1.5 runs a calendar sweep.
- **Weekly Report Generator**: Uses sweep data for the "Key Deliverables" section.
- **Dashboard.md**: Output can be pasted into the `📅 Calendar Focus` section.
