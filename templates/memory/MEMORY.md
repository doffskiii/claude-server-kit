# Memory

## Core Rules (always apply)

### Dual-Channel Ask
- **NEVER use AskUserQuestion** — it does NOT reach Telegram
- **NEVER use EnterPlanMode / ExitPlanMode** — plan as text in chat, approve via dual-channel
- **ALL user questions = dual-channel** (VS Code text + Telegram buttons, first answer wins)
- Workflow: `send_telegram_question` → print in VS Code → background poll → first answer wins

### Session Notes
- After ANY significant work session → suggest "Save session notes?"
- Format: conversations/YYYY-MM-DD_slug.md

### Verification — STRICT RULES
- **Dates:** EVERY time you need a date → call `get_today()` first. NEVER compute in head
- **Counts:** after batch-creating files → ALWAYS `list_vault` and count before reporting to user
- **Before saving** documents with deadlines → call `get_today()` and verify ALL dates

### Day Boundary = 03:00 (not midnight!)
- `get_today()` returns `logical_today` (boundary at 03:00)
- **Reflections and sessions** → use `logical_today`
- **Deadlines, tasks, calendar** → use real date
- Session file `2024-03-06_slug.md` if work continues until 02:59 on March 7th

### Telegram Formatting
- **NEVER use markdown tables** in Telegram — they render as garbage
- NO code blocks in Telegram either
- Use em-dash (—) bullets, bold OK, flat structure
- Tables and code blocks OK in VS Code — restriction is Telegram only

### Calendar Sync (lifecycle)
- Calendar = date projection, NOT task hub. Source of truth = dashboard/task manager
- When adding event with deadline → ALWAYS set `source_type` and `source_id`
- When completing task → `queue_calendar_sync(event_id, "remove")`
- Hourly cron processes queue and verifies against source systems

## Domain Knowledge (load topic file when working on these)

<!-- Add topic files as you build domain knowledge. Examples:
### Whisper → `memory/whisper.md`
### Your Project → `memory/your-project.md`
-->
