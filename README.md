# Claude Server Kit

Turn a VPS into an AI-powered personal server with persistent memory, knowledge management, and Telegram integration.

Two weeks of daily iteration distilled into one repo. Clone it, run `setup.sh`, and get a personal AI assistant that remembers everything, manages your tasks, transcribes voice messages, and talks to you on Telegram.

## What You Get

- **Brain MCP Server** — Obsidian vault as Claude's persistent memory with 20 tools: search, semantic search, read, write, dashboard, audio transcription, calendar, server monitoring
- **Vault** — Structured Obsidian vault with git sync, YAML frontmatter, bidirectional links, context files per folder
- **Semantic Search** — Find documents by meaning, not just keywords (ONNX embeddings, runs on CPU, no GPU needed)
- **Calendar** — Event tracking with source linking and automatic sync to task systems
- **Dashboard** — Safe task management directly in the vault (never overwrites, atomic operations)
- **Whisper** — OpenAI-compatible transcription server (short audio → local faster-whisper, long audio → Groq API)
- **Monitoring** — CPU/RAM/disk alerts to Telegram when things go wrong
- **Librarian** — Weekly autonomous vault audit agent that finds orphans, broken links, stale files
- **Dual-Channel Ask** — Ask questions in both VS Code and Telegram simultaneously. First answer wins
- **Skills** — Extensible slash-command system for recurring workflows (retro, reflection, task routing)
- **Escalating Reminders** — Cron-based reminders that get more insistent over time

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Claude Code                    │
│  CLAUDE.md + Memory + MCP Servers + Skills      │
└───────┬───────────────────┬──────────┬──────────┘
        │                   │          │
  ┌─────▼─────┐    ┌───────▼────┐  ┌──▼──────────┐
  │ Brain MCP │    │   Takopi   │  │  Librarian  │
  │ 20 tools  │    │ (Telegram) │  │ (weekly     │
  │           │◄──►│  port 9877 │  │  audit)     │
  └──┬──┬──┬──┘    └──────┬─────┘  └─────────────┘
     │  │  │              │
┌────▼┐ │ ┌▼────┐  ┌──────▼──────┐
│Vault│ │ │Cal. │  │  Telegram   │
│ .md │ │ │ DB  │  │   (you)     │
└─────┘ │ └─────┘  └─────────────┘
    ┌───▼────┐
    │Whisper │
    │ :8787  │
    └────────┘
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USER/claude-server-kit.git
cd claude-server-kit

# 2. Run setup (installs uv, Node.js, PM2, Brain, vault, ML models)
bash setup.sh

# 3. Configure credentials (interactive wizard)
bash configure.sh

# 4. Start Claude Code
claude
```

## Credentials Setup

Run `bash configure.sh` for an interactive wizard, or set up manually:

| What | How | Required? |
|------|-----|-----------|
| **Takopi** (Telegram bot) | `uv tool install takopi && takopi` | Yes, for Telegram |
| **Groq API** (fast transcription) | `echo '{"api_key":"gsk_..."}' > ~/.groq-api-key.json && chmod 600 ~/.groq-api-key.json` | Optional (long audio) |
| **Vault git remote** | `cd ~/vault && git remote add origin <url>` | Optional (cloud backup) |
| **Backup passphrase** | `echo 'your-passphrase' > ~/.backup-passphrase && chmod 600 ~/.backup-passphrase` | Optional (backups) |
| **CLAUDE.md** | Edit `~/CLAUDE.md` — set your name, customize workflow | Recommended |

All credential files are `chmod 600` and listed in `.gitignore`.

## Requirements

- Ubuntu 20.04+ (or similar Linux)
- 2+ GB RAM (4+ GB recommended for Whisper + embeddings)
- Git, internet access
- `setup.sh` installs everything else: uv, Python 3.12+, Node.js, PM2, ffmpeg

## Repository Structure

```
claude-server-kit/
├── brain/                    # Brain MCP server (Python, FastMCP)
│   ├── src/brain/
│   │   ├── server.py         # 20 MCP tool definitions
│   │   ├── config.py         # All configuration (env-driven)
│   │   ├── whisper_server.py # OpenAI-compatible Whisper API
│   │   ├── vault/            # Vault operations
│   │   │   ├── tools.py      # search, read, write, list, dashboard
│   │   │   ├── embeddings.py # ONNX semantic search engine
│   │   │   ├── frontmatter.py# YAML frontmatter parser
│   │   │   ├── ingest.py     # Audio + document ingestion
│   │   │   └── sync.py       # Debounced git sync
│   │   ├── calendar/         # Calendar system
│   │   │   ├── db.py         # SQLite schema + queries
│   │   │   └── tools.py      # Calendar API (get_today, events)
│   │   └── server_tools/     # Server monitoring
│   │       └── tools.py      # CPU/RAM/disk/PM2 status
│   ├── scripts/              # Utility scripts
│   │   ├── monitor.py        # Monitoring daemon (PM2)
│   │   ├── build_index.py    # Rebuild semantic search index
│   │   ├── download_model.py # Pre-download ONNX model
│   │   └── vault-sync.sh     # Cron git sync
│   ├── pyproject.toml        # Python dependencies
│   └── ecosystem.config.cjs  # PM2 process config
│
├── librarian/                # Autonomous vault audit agent
│   ├── SYSTEM.md             # Agent system prompt
│   ├── CHECKLIST.md          # 10-section audit checklist
│   └── run.sh                # Cron entry point
│
├── vault-template/           # Empty vault with context files
│   ├── dashboard.md          # Task dashboard
│   ├── _server-map.md        # Infrastructure reference
│   ├── inbox/INBOX.md        # Unprocessed items
│   ├── conversations/        # Session notes
│   ├── decisions/            # Decision log
│   ├── knowledge/            # Learning, projects, personal
│   ├── content/              # Content plans
│   ├── retro/                # Retrospectives (daily/weekly/monthly)
│   ├── work/                 # Work projects
│   └── templates/            # Obsidian templates
│       ├── audio-note.md
│       ├── project-card.md
│       ├── meeting-note.md
│       └── document.md
│
├── templates/                # Claude Code config templates
│   ├── CLAUDE.md             # Agent instructions (THE BRAIN)
│   ├── mcp.json              # MCP server registration
│   ├── settings.json         # Permissions config
│   └── memory/MEMORY.md      # Auto-memory bootstrap
│
├── scripts/                  # Server automation
│   ├── backup.sh             # Encrypted backup (GPG AES-256)
│   ├── git-push-all.sh       # Daily code backup to GitHub
│   ├── calendar-sync.py      # Hourly calendar reconciliation
│   └── reminders/            # Escalating reminder system
│       ├── reminder.sh       # Generic reminder template
│       ├── retro-reminder.sh # Weekly retro (4 levels)
│       └── mark_retro_done.sh# Marker to skip remaining levels
│
├── skills/                   # Example Claude Code skills
│   ├── example/SKILL.md      # How skills work
│   ├── track/SKILL.md        # Smart task routing
│   └── reflect/SKILL.md      # Daily reflection
│
├── docs/                     # Deep documentation
│   ├── ARCHITECTURE.md       # System design & patterns
│   └── FEATURES.md           # Non-obvious features guide
│
├── setup.sh                  # One-command setup
├── configure.sh              # Interactive credential wizard
└── .gitignore
```

## Brain MCP Tools (20 tools)

### Vault Operations
| Tool | What it does |
|------|-------------|
| `search_vault` | Full-text regex search across .md files |
| `semantic_search` | Find by meaning using ONNX embeddings (384-dim, multilingual) |
| `read_vault` | Read any vault document (path-safe) |
| `write_vault` | Create/update with auto-frontmatter + git sync + embedding update |
| `list_vault` | List files by folder and/or tags |
| `update_dashboard` | Safe task management — add/complete/remove (never overwrites) |

### Ingestion
| Tool | What it does |
|------|-------------|
| `ingest_audio` | Transcribe audio → vault (≤4min local, >4min Groq API, fallback) |
| `ingest_document` | Process PDF/text → vault with auto-chunking for large files |

### Calendar
| Tool | What it does |
|------|-------------|
| `get_today` | Current date + logical day boundary (03:00) + week calendar |
| `add_calendar_event` | Add event with source tracking (for task system sync) |
| `list_calendar_events` | Query events by date range and project |
| `remove_calendar_event` | Remove by ID or title substring |
| `update_calendar_event` | Partial field updates |
| `queue_calendar_sync` | Queue sync action for hourly cron processing |

### Telegram (Dual-Channel)
| Tool | What it does |
|------|-------------|
| `send_telegram_question` | Non-blocking question → returns question_id |
| `check_telegram_answer` | Poll for answer status |
| `cancel_telegram_question` | Cancel pending question |
| `ask_via_telegram` | Blocking question (legacy, still works) |

### Server
| Tool | What it does |
|------|-------------|
| `get_server_status` | CPU, RAM, disk, PM2 process health |
| `get_server_map` | Full service inventory from vault |

## Takopi (Telegram Bot)

[Takopi](https://github.com/miilv/takopi) is an open-source Telegram bridge for AI agents.

- Multi-engine: Claude Code, Codex, OpenCode, DeepSeek
- Voice message transcription (routes to Brain's Whisper server)
- File transfer, multi-session history, live streaming
- Dual-channel Q&A server on port 9877
- Install: `uv tool install -U takopi`

## Vault Conventions

| Convention | Description |
|-----------|-------------|
| **Context files** | Every folder has `FOLDER_NAME.md` that indexes its contents |
| **Frontmatter** | All files have YAML frontmatter: title, tags, created, source |
| **Bidirectional links** | Note A → Note B requires Note B → Note A |
| **Dashboard** | Use `update_dashboard()` tool, NEVER `write_vault("dashboard.md")` |
| **Decisions** | Significant decisions → `decisions/YYYY-MM-DD_slug.md` |
| **Session notes** | After VS Code work → `conversations/YYYY-MM-DD_slug.md` |
| **Day boundary** | Logical day ends at 03:00 (not midnight) — for night owls |

## Key Design Patterns

### Debounced Git Sync
Multiple vault writes within 30 seconds batch into a single git commit. Fire-and-forget — never blocks the tool response.

### Incremental Embedding Updates
When you write a document, only that document's embeddings are recomputed. No full index rebuild needed.

### Thread-Safe ONNX Inference
Global lock prevents concurrent embedding model access — safe for parallel tool calls.

### Fail-Safe Calendar Sync
Events linked to task systems via `source_type` + `source_id`. Hourly cron verifies task completion before removing events.

### Escalating Reminders
4-level system: detailed stats → simple nudge → last chance → auto-execute. Marker files prevent re-running after completion.

### Path Security
All vault paths validated against directory traversal and symlink attacks. Sensitive file patterns (.env, .ssh, tokens) blocked from ingestion.

## Creating Skills

Skills are instruction files that extend Claude's capabilities:

```
~/.claude/skills/my-skill/
├── SKILL.md      # Instructions + triggers
└── scripts/      # Supporting scripts (optional)
```

See `skills/example/SKILL.md` for a template, `skills/track/SKILL.md` and `skills/reflect/SKILL.md` for real examples.

**Key parts of SKILL.md:**
- **Triggers** — when the skill activates ("send to telegram", "/retro")
- **Instructions** — step-by-step workflow
- **Scripts** — shell scripts the skill can call via Bash tool

## Adding MCP Servers

Edit `~/.mcp.json` to add more servers:

```json
{
  "mcpServers": {
    "brain": {
      "command": "uv",
      "args": ["run", "--directory", "~/brain", "python", "-m", "brain"],
      "type": "stdio"
    },
    "your-server": {
      "command": "uv",
      "args": ["run", "--directory", "~/your-server", "python", "-m", "your_server"],
      "type": "stdio"
    }
  }
}
```

## Auto-Memory System

Claude Code persists knowledge across sessions in `~/.claude/projects/<project>/memory/`:

- `MEMORY.md` — core rules, always loaded into context (keep under 200 lines)
- Topic files (`whisper.md`, `trello.md`) — detailed domain knowledge, loaded on demand
- Claude updates these files as it learns your preferences and patterns

**What to save:** stable patterns, key paths, user preferences, recurring solutions.
**What NOT to save:** temporary state, unverified info, duplicates of CLAUDE.md.

## Monitoring

Brain Monitor (PM2 daemon) sends Telegram alerts when:
- CPU > 80% for 3 consecutive checks
- Available RAM < 1 GB
- Disk usage > 85%
- Any PM2 process goes offline

30-minute cooldown between same-type alerts.

## Backup Strategy

Three layers:
1. **Vault git sync** (every 5 min) — continuous knowledge backup
2. **Code git push** (daily) — all repos to GitHub
3. **Full encrypted backup** (daily) — GPG AES-256 → cloud storage

## Librarian (Vault Audit)

Weekly autonomous agent that audits your vault:
- Missing context files, orphaned documents, broken links
- Stale entries, bidirectional link violations
- Frontmatter issues, freshness scoring
- Cross-document contradictions
- Sends compressed report via Telegram

Set up as cron: `0 4 * * 1 bash ~/librarian/run.sh` (Monday 4 AM).

## Non-Obvious Features

See [docs/FEATURES.md](docs/FEATURES.md) for the full list, but highlights:

- **Logical day boundary at 03:00** — `get_today()` returns `logical_today` so late-night work counts as "today"
- **Voice message → vault pipeline** — transcribe → tag → save to inbox, all automatic
- **Dashboard is append-only safe** — `update_dashboard()` parses sections, modifies in place, never overwrites
- **Semantic search is multilingual** — the ONNX model (`paraphrase-multilingual-MiniLM-L12-v2`) works across languages
- **Session notes as institutional memory** — save what was done, decisions made, open questions after each work session

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BRAIN_VAULT_PATH` | `~/vault` | Obsidian vault location |
| `TAKOPI_CONFIG` | `~/.takopi/takopi.toml` | Takopi config path |
| `GROQ_KEY_FILE` | `~/.groq-api-key.json` | Groq API key for long audio |

## Credits

- [Takopi](https://github.com/miilv/takopi) by banteg — Telegram bridge for AI agents
- [FastMCP](https://github.com/jlowin/fastmcp) — lightweight MCP server framework
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — CTranslate2 Whisper
- [Obsidian](https://obsidian.md) — knowledge management
- [sentence-transformers](https://www.sbert.net/) — multilingual embeddings

## License

MIT
