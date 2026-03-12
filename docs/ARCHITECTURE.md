# Architecture

Deep dive into how all the pieces connect.

## System Layers

```
Layer 4: Skills & Workflows     /retro, /reflect, /track, /overview
Layer 3: CLAUDE.md + Memory     Instructions, learned patterns, domain knowledge
Layer 2: MCP Servers             Brain (vault+calendar+monitor), Trello, Bitrix, etc.
Layer 1: Infrastructure          PM2, cron, git sync, backup, Telegram
Layer 0: Storage                 Obsidian vault (.md), SQLite (calendar), embeddings (.npz)
```

## Brain MCP Server

### How FastMCP Works

FastMCP turns Python functions into MCP tools that Claude Code can call. Each function decorated with `@mcp.tool()` becomes available as a tool in Claude's interface.

```python
mcp = FastMCP("brain", instructions="...")

@mcp.tool()
def search_vault(query: str, folder: str = "", tags: str = "") -> str:
    """Docstring becomes the tool description in Claude's UI."""
    return vault_search(query, folder, tags)
```

The server runs via stdio (standard input/output), launched by Claude Code on demand. No HTTP server needed for MCP itself.

### Module Architecture

```
brain/src/brain/
├── server.py              # Tool definitions (thin layer)
├── config.py              # All config in one place
├── vault/
│   ├── tools.py           # Core operations (the "business logic")
│   ├── embeddings.py      # Semantic search engine
│   ├── frontmatter.py     # YAML parsing (small, focused)
│   ├── ingest.py          # Audio + document pipelines
│   └── sync.py            # Git sync (debounced)
├── calendar/
│   ├── db.py              # SQLite schema + queries
│   └── tools.py           # Calendar API
└── server_tools/
    └── tools.py           # System monitoring
```

**Design principle:** `server.py` is a thin routing layer. All logic lives in the modules. This keeps tool definitions clean and testable.

### Data Flow: Writing a Document

```
write_vault("inbox/idea.md", content, tags="idea")
  │
  ├─► frontmatter.make_meta() → generate YAML header
  ├─► _resolve(path) → validate path, prevent traversal
  ├─► write file to ~/vault/inbox/idea.md
  ├─► _trigger_sync() → schedule git commit (debounced 30s)
  └─► _trigger_embedding_update() → re-index this file's chunks
```

### Data Flow: Semantic Search

```
semantic_search("how to set up monitoring")
  │
  ├─► _ensure_model() → lazy-load ONNX model (first call only)
  ├─► _encode(query) → tokenize + ONNX inference → 384-dim vector
  ├─► _load_index() → read embeddings.npz + metadata.json
  ├─► numpy cosine similarity against all chunks
  ├─► filter by folder/tags if specified
  └─► return top-K results with file paths + snippets
```

### Embedding Index Structure

```
~/vault/.brain/
├── embeddings.npz    # numpy array: N chunks × 384 dimensions
└── metadata.json     # [{path, chunk_idx, text_preview, mtime}, ...]
```

- **Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Dimensions:** 384 (compact, fast on CPU)
- **Chunking:** ~200 words per chunk, split by paragraphs
- **Staleness detection:** compares file mtime to index mtime

### Audio Transcription Pipeline

```
ingest_audio("/path/to/voice.ogg")
  │
  ├─► detect duration (ffprobe)
  │
  ├─► ≤4 min: local faster-whisper (base model, CPU, int8)
  │   └─► instant, no network needed
  │
  └─► >4 min: Groq API (whisper-large-v3)
      ├─► split if >25MB (Groq limit)
      ├─► send chunks sequentially
      └─► concatenate transcripts
  │
  ├─► FALLBACK: if primary fails → try other backend
  │
  └─► save to vault with audio-note template
```

### Whisper Server

Separate HTTP server on `127.0.0.1:8787` with OpenAI-compatible API:

```
POST /v1/audio/transcriptions
Content-Type: multipart/form-data
file: <audio file>

Response: {"text": "transcribed text..."}
```

Used by Takopi for voice message transcription. Same routing logic as `ingest_audio`.

## Calendar System

### Database Schema (SQLite)

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    date TEXT NOT NULL,        -- YYYY-MM-DD
    time TEXT,                 -- HH:MM (optional)
    end_date TEXT,             -- for multi-day events
    project TEXT,              -- project tag for filtering
    notes TEXT,
    source_type TEXT,          -- 'trello', 'task_file', 'manual'
    source_id TEXT             -- card_id, task_id, etc.
);

CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY,
    event_id INTEGER,
    action TEXT,               -- 'remove' or 'update'
    new_date TEXT,
    new_title TEXT,
    created_at TEXT
);
```

### Sync Lifecycle

```
1. Task created with deadline
   → add_calendar_event(title, date, source_type="trello", source_id="card123")

2. Task completed
   → queue_calendar_sync(event_id, action="remove")

3. Hourly cron (calendar-sync.py)
   ├─► process sync_queue: remove/update events
   ├─► fail-safe: verify task completion in source system
   └─► cleanup: remove events >14 days old
```

### Logical Day Boundary (03:00)

`get_today()` returns two dates:
- **Real date** — for deadlines, calendar events, task creation
- **Logical today** — for reflections, session notes, retros

If it's 2:30 AM on March 7th, `logical_today` = March 6th. This way late-night work counts as "today" for productivity tracking.

## Vault Design

### Context File Pattern

Every folder has a `FOLDER_NAME.md` that acts as a distributed index:

```markdown
---
title: "Inbox"
tags: [index]
---
# Inbox

Unprocessed items: ideas, voice memos, quick notes.

## Items
- [[my-idea]] — Quick thought about X (2024-03-01)
- [[voice-memo-20240302]] — Meeting notes (2024-03-02)
```

**Why?** Claude doesn't need to `list_vault` every time — it reads the context file to understand what's in a folder. This is faster and gives semantic context (descriptions, dates, status).

**Maintenance rule:** When adding a file to any folder, update the context file too. The Librarian audits for mismatches.

### Frontmatter Convention

Every markdown file has YAML frontmatter:

```yaml
---
title: "Document Title"
tags:
- tag1
- tag2
created: '2024-03-01T14:30:00'
source: manual  # or: voice_message, pdf, meeting, etc.
---
```

`write_vault()` auto-generates this if not provided.

### Bidirectional Links

If `project-a.md` references `decision-123.md`, then `decision-123.md` should reference back to `project-a.md`. This keeps the knowledge graph connected and navigable.

The Librarian audits for broken bidirectional links.

### Dashboard Protocol

`dashboard.md` has two sections: `## Active Tasks` and `## Completed`.

**NEVER** use `write_vault("dashboard.md", ...)` — it overwrites everything.

**ALWAYS** use `update_dashboard(action, task, project)`:
- `add` — appends to Active Tasks
- `complete` — moves matching task to Completed (with date)
- `remove` — removes matching task entirely

The tool parses the file, finds the right section, modifies it, and writes back atomically.

## Dual-Channel Ask

### Problem
When Claude needs user input, the user might be at their computer (VS Code) or on their phone (Telegram). Using `AskUserQuestion` only reaches VS Code.

### Solution
Send the question to BOTH channels simultaneously. First answer wins.

```
1. send_telegram_question(question, options)  → question_id
2. Print question in VS Code (formatted)
3. Background poll: curl loop on http://127.0.0.1:9877/ask/poll/{id}
4. Wait for either:
   - User types in VS Code → cancel_telegram_question(id)
   - Telegram answers → use that answer
```

### Takopi Ask Server

Takopi runs an HTTP server on port 9877:
- `POST /ask/send` — create question with inline keyboard buttons
- `GET /ask/poll/{id}` — check if answered
- `POST /ask/cancel/{id}` — cancel (edits Telegram message)

## Librarian

### Two-Pass Architecture

**Pass 1 (fast, 5-10 min):**
- Vault structure (missing context files, orphans)
- Inbox health
- Memory system (MEMORY.md size, outdated entries)
- Project index completeness
- Backup freshness

**Pass 2 (deep, 10-20 min):**
- Bidirectional link violations
- Frontmatter issues
- Semantic deduplication (similar documents)
- Cross-document contradictions
- CLAUDE.md drift (instructions vs reality)

### Evidence-Based Findings

Every finding cites specific file paths:
```
Finding: Context file inbox/INBOX.md missing entry for inbox/new-idea.md
Action: Add entry to INBOX.md
```

### Persistent History

`history.json` tracks all findings with unique IDs across runs. This prevents re-reporting fixed issues and enables trend analysis.

## Escalating Reminders

### 4-Level Pattern

```
Level 1 (gentle): Detailed message with stats/context
Level 2 (nudge):  Simple "don't forget" reminder
Level 3 (urgent): "Last chance" with yes/no buttons
Level 4 (auto):   Execute automatically (auto-retro, auto-mark-done)
```

### Marker Files

When the task is completed (manually or by Level 4), a marker file is created:
```
~/.retro_done_2024-W10
```

All remaining levels check for this marker and skip if it exists.

### Cron Schedule Example (Weekly Retro)

```cron
0 15 * * 0  bash reminders/retro-reminder.sh 1   # Sunday 18:00 MSK
0 17 * * 0  bash reminders/retro-reminder.sh 2   # Sunday 20:00 MSK
0 18 * * 0  bash reminders/retro-reminder.sh 3   # Sunday 21:00 MSK
30 21 * * 0 bash reminders/retro-reminder.sh 4   # Sunday 00:30 MSK+1
```

## Skills System

### How It Works

1. User says a trigger phrase (e.g., "/retro", "what did I do today")
2. Claude Code loads `~/.claude/skills/<name>/SKILL.md`
3. SKILL.md contains step-by-step instructions
4. Claude follows the instructions, using MCP tools as needed

### Anatomy of a Skill

```markdown
# Skill Name

## Triggers
/command-name, "natural language trigger", "another trigger"

## What It Does
Brief description.

## Steps
1. Call `get_today()` to get current date
2. Gather data from [sources]
3. Process and format
4. Present to user
5. Save results to vault

## Output Format
[template or example]

## Notes
- Edge cases
- Dependencies
```

### Why Skills > System Prompts

- **Modular:** Add/remove without editing CLAUDE.md
- **Focused:** Only loaded when triggered (saves context)
- **Portable:** Copy a skill folder to share it
- **Testable:** Each skill has clear inputs and outputs

## Git Sync Strategy

### Vault Sync (every 5 minutes via cron)

```bash
cd ~/vault
git pull --rebase origin main 2>/dev/null
git add -A
git diff --cached --quiet || git commit -m "vault sync $(date)"
git push origin main 2>/dev/null
```

### Write-Triggered Sync (debounced)

When `write_vault()` is called:
1. Cancel any pending sync timer
2. Start new 30-second timer
3. When timer fires: pull → add → commit → push

This batches rapid writes (e.g., creating multiple files) into one commit.

### Code Backup (daily)

`git-push-all.sh` iterates over all project repos, auto-commits any uncommitted changes, and pushes to origin.

## PM2 Process Management

```
brain-monitor    # Server health daemon (alerts to Telegram)
brain-whisper    # Whisper API server on :8787
```

Both managed by `ecosystem.config.cjs`. PM2 handles:
- Auto-restart on crash
- Log rotation
- Process monitoring
- Startup on boot (`pm2 startup && pm2 save`)
