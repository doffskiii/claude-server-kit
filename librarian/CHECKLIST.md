# Librarian Audit Checklist

Execute each section in order. Record findings as you go.

---

## 1. Vault Structure Integrity

### 1.1 Context Files (DYNAMIC -- discover folders, don't hardcode)
For each folder in the vault, verify:
- [ ] Context file exists (FOLDER_NAME.md)
- [ ] Every file in the folder is listed in the context file
- [ ] No entries in context file point to non-existent files (stale entries)

How to discover folders:
1. `list_vault()` to get full file list
2. Extract unique folder paths from the listing
3. For each folder, check if a context file exists (convention: FOLDER_NAME.md in uppercase)
4. Read context file and compare with actual folder contents

### 1.2 Orphan Files (deep check)
Full orphan analysis -- not just context files, but vault-wide backlink coverage.

1. `list_vault()` -> get ALL vault files
2. For each file, search the entire vault for references to it:
   - `search_vault(filename_without_extension)` -- checks for wikilinks [[filename]] and markdown links
   - Also check if the file is listed in its folder's context file
3. A file is an ORPHAN if it has ZERO incoming references (not mentioned anywhere else in the vault)
4. Classify orphans:
   - **True orphan** -- no references anywhere, not in any context file
   - **Context-only** -- listed in context file but not linked from any other note
   - **Root file** -- context files themselves (FOLDER_NAME.md) are expected to have no incoming links -- skip these
5. For each orphan, report: file path, age (stat mtime), suggested action (link from relevant note, or move/delete)

Priority: true orphans first, then context-only orphans.
Skip: templates/, audio/ transcriptions (these are leaf nodes by design).

### 1.3 Bidirectional Links (spot check)
- [ ] Pick 5-10 recent notes, verify that referenced notes link back
- [ ] Check `decisions/` -- do decision notes reference the relevant project files?

### 1.4 YAML Frontmatter
- [ ] Spot-check 10 recent files for proper frontmatter (title, tags, created)
- [ ] Flag any files missing required fields

### 1.5 File Placement (structural)
- [ ] Are there any misplaced files? (e.g., decision notes not in `decisions/`, ideas not in `inbox/`)
- [ ] Check `conversations/` -- are all session note filenames in YYYY-MM-DD_slug.md format?

### 1.6 Content-Location Mismatch (deep check)
Scan folders that act as catch-all/dump zones for content that should live elsewhere.
This is a MANDATORY check -- do not skip it even if other checks took many turns.

CHECK THESE FOLDERS:

1. `list_vault(folder="documents")` -- list all files
   - documents/ should ONLY contain ingested external docs (PDFs, specs, raw text dumps)
   - For each file/subfolder: read its title and tags (from frontmatter)
   - Flag if content is about: job search, meetings, project work, personal notes -- these belong elsewhere

2. `list_vault(folder="inbox")` -- check for stale/processed items
   - If any item is marked "done"/"implemented"/"processed" but still in inbox -> flag it

3. `list_vault(folder="audio")` -- scan transcriptions
   - If a transcription is about a project meeting or decision, check if a summary note exists in the proper folder

For each flagged file, report: CURRENT location -> EXPECTED location, and reason.

### 1.7 Broken Internal Links (deep check)
Validate all internal links across the vault -- both [[wikilinks]] and markdown [text](path) links.

1. For a SAMPLE of 20-30 vault files (prioritize recent files, conversations/, decisions/):
   - Read the file content
   - Extract all internal links:
     - `[[wikilink]]` patterns -> resolve to vault path
     - `[text](relative/path.md)` patterns -> resolve to vault path
   - For each extracted link, verify the target file exists
2. Classify broken links:
   - **Dead link** -- target file doesn't exist (was deleted or renamed)
   - **Wrong path** -- target exists but at a different path (file was moved)
   - **Typo** -- close match exists (fuzzy: edit distance <=2 on filename)
3. For each broken link, report: source file + line reference, broken link text, suggested fix

This is a HIGH VALUE check -- broken links silently rot the knowledge graph.

### 1.8 Stale Redirect Files
- [ ] Search vault for files that contain only a redirect/link to another file (e.g., "moved to X", "see Y")
- [ ] If the redirect is older than 1 month, flag it -- the redirect should be removed and references updated

### 1.9 Context File Freshness Scoring (deep check)
Context files (FOLDER_NAME.md) should reflect the current state of their folder. Score each one.

1. For each folder that has a context file:
   - `list_vault(folder=X)` -> get actual file list with count
   - Read the context file -> count entries/mentions
   - `stat` the context file -> get last modified time
   - `stat` the newest file in the folder -> get its modified time
2. Freshness score (0-100):
   - **Coverage** (0-50): % of actual files mentioned in context file. 100% coverage = 50 points
   - **Recency** (0-30): context file modified within 7 days of newest file = 30 pts, 14 days = 20, 30 days = 10, older = 0
   - **Accuracy** (0-20): no stale entries (pointing to deleted files) = 20 pts, deduct 5 per stale entry
3. Report a freshness table:
   - Each folder: name, score, newest file date, context file date, missing files count
   - Flag folders scoring below 50 as WARNING
   - Flag folders scoring below 25 as CRITICAL
4. Save detailed freshness data to `/root/librarian/state/freshness-scores.md`

---

## 2. Inbox Health

- [ ] Count files in `inbox/` (excluding INBOX.md)
- [ ] Check age of oldest unprocessed item
- [ ] Flag items older than 3 weeks as candidates for processing
- [ ] Note: this is a SOFT reminder, not critical

---

## 3. Memory System

### 3.1 MEMORY.md Size & Optimization (deep check)
- [ ] Count lines in MEMORY.md (typically at `/root/.claude/projects/-root/memory/MEMORY.md`)
- [ ] If approaching the size limit -- flag as warning
- [ ] If over the limit -- flag as CRITICAL
- [ ] Read the full MEMORY.md and analyze EVERY section for optimization opportunities:
  - Sections >10 lines that could move to a topic-specific memory file
  - Entries that duplicate what's already in CLAUDE.md (no need to store in both)
  - Entries about completed/past events that are no longer relevant
  - Verbose entries that could be condensed
  - Related entries scattered across sections that could merge
  - Stale dates, past deadlines, references to finished work
- [ ] Save a DETAILED mini-report to `/root/librarian/state/memory-suggestions.md`
- [ ] In the main report: just one line "MEMORY.md: N suggestions -- see state/memory-suggestions.md"

### 3.2 Memory Freshness
- [ ] Check for outdated entries (past dates, completed projects, stale references)
- [ ] Check if any memory entries contradict CLAUDE.md
- [ ] Look for dates in memory entries -- if they reference past deadlines or events, flag for cleanup

### 3.3 Topic Memory Files
- [ ] List files in the memory directory
- [ ] For each topic file: is it still referenced from MEMORY.md? If not, is it orphaned?
- [ ] Check for stale/outdated topic files (read first 10 lines to assess freshness)

---

## 4. Projects Audit

### 4.1 Projects Index (DYNAMIC -- discover, don't assume)
- [ ] `ls -d /root/*/` to find actual project directories
- [ ] Read the projects index file for registered projects
- [ ] Compare the two lists -- flag dirs missing from the index
- [ ] Ignore known non-project dirs: `.cache`, `.local`, `.npm`, `.config`, `node_modules`, `snap`, `downloads`

### 4.2 Project Health (for each discovered project in /root/)
- [ ] Has a CLAUDE.md or .claude/ directory?
- [ ] Has a .gitignore?
- [ ] Is tracked in git? (`ls /root/<project>/.git`)
- [ ] Read backup script -- is this project included?
- [ ] Read git-push-all.sh -- if project has a git remote, is it in the push list?

### 4.3 PM2 Processes
- [ ] Run `get_server_status()` -- check all processes are online
- [ ] Flag any processes with high restart counts (>5 in 24h)

---

## 5. Backup Verification

### 5.1 Backup Freshness
- [ ] Check latest backup file
- [ ] Verify it's from today or yesterday
- [ ] Check file size is reasonable (compare to previous)

### 5.2 Backup Coverage (DYNAMIC -- read scripts, compare with reality)
- [ ] Read backup script -- extract all paths from the tar/archive command
- [ ] `ls -d /root/*/` -- list actual project dirs
- [ ] Compare: flag any project dirs NOT in backup
- [ ] Note: some dirs are intentionally excluded (node_modules, .cache, etc.) -- that's fine

### 5.3 Git Push Coverage (DYNAMIC)
- [ ] Read git-push-all.sh -- extract the REPOS array
- [ ] For each project in `/root/` -- check if it has `.git` and a remote
- [ ] Flag repos that have remotes but are NOT in git-push-all.sh

### 5.4 Vault Sync
- [ ] Check last vault git commit timestamp
- [ ] Verify it's within expected interval (e.g., 15 minutes if cron runs every 5 min)

### 5.5 Restore Readiness
- [ ] Verify restore script exists
- [ ] Check if backup credentials/passphrase file exists
- [ ] Note: can't test actual restore, just verify components exist

---

## 6. Dashboard & Tasks

### 6.1 Dashboard
- [ ] Read dashboard.md -- general health check
- [ ] Are all tasks still relevant? (don't flag as critical -- just note very old ones)

### 6.2 Calendar
- [ ] Check for past events that weren't cleaned up
- [ ] Check for events with broken source references

---

## 7. Server Health

### 7.1 Disk Space
- [ ] Check available disk space
- [ ] Flag if below 20GB

### 7.2 Services
- [ ] All PM2 services running?
- [ ] Any unusual restart patterns?

### 7.3 Cron Jobs
- [ ] Verify key crons are active: backup, git-push, vault-sync
- [ ] Check for any failed cron indicators (log files, error output)

---

## 8. Cross-System Consistency

### 8.1 Server Map
- [ ] Read server-map file -- does it match actual server state?
- [ ] Any services listed that don't exist anymore?
- [ ] Any running services not listed?

### 8.2 Duplicate Information (deep check)
- [ ] Check if any vault files contain substantially overlapping content
- [ ] Spot-check: are there redirect files that should be cleaned up?
- [ ] Check for same-topic files in different folders
- [ ] Search for key topics across vault to find scattered info
- [ ] For any topic found in 3+ locations, flag as potential consolidation candidate

### 8.3 Folder Purpose Compliance
For folders with a defined purpose (from context files or CLAUDE.md), verify files match:
- [ ] `documents/` -- external ingested docs only (not vault-native notes)
- [ ] `decisions/` -- only decision records with context/options/reasoning
- [ ] `conversations/` -- only session notes in the right format
- [ ] `content/` -- only content scripts and plans
- [ ] `work/` -- only work/employment projects

### 8.4 CLAUDE.md Drift (deep check)
CLAUDE.md is the "constitution" -- if it drifts from reality, every session starts with wrong assumptions.
Read CLAUDE.md and cross-check key sections against actual state:

- [ ] Vault Structure tree -- compare with `list_vault()`. Any folders exist that aren't in the tree? Any listed that don't exist?
- [ ] PM2 services list -- compare with `get_server_status()`. Mismatches?
- [ ] MCP server list -- are all actual MCP servers documented?
- [ ] Task Routing table -- does it cover all current task systems?
- [ ] Cron schedule descriptions -- compare with actual `crontab -l` output
- [ ] Any references to paths/files that no longer exist?

Flag drift as warning with specific section + what needs updating.

### 8.5 Cross-Document Consistency (deep check)
Find contradictions and inconsistencies ACROSS vault documents.

1. Pick 5-7 key topics that appear in multiple places:
   - Task routing rules (CLAUDE.md vs MEMORY.md vs dashboard.md)
   - Project descriptions (index vs individual project files)
   - Service configs (server-map vs actual PM2 / crontab)
   - Workflow descriptions (CLAUDE.md vs conversation/decision notes)
   - Dates and deadlines (task files vs calendar events)
2. For each topic:
   - `search_vault(topic_keyword)` -> find all files mentioning it
   - Read the relevant sections from each file
   - Compare facts: do they agree? Are there contradictions?
3. For each contradiction, report: the two (or more) sources, what each says, which is likely correct

### 8.6 Semantic Deduplication (deep check)
Use semantic search to find documents that cover the same topic but aren't explicitly linked.

1. Pick 10-15 key vault documents (recent conversations, decisions, project files)
2. For each, run `semantic_search(query=document_title_or_summary, top_k=5)`
3. Examine the top results:
   - **Score > 0.85** -- likely duplicate or near-duplicate -> flag for merge/consolidation
   - **Score 0.7-0.85** -- related content -> check if they should cross-reference each other
   - **Score < 0.7** -- different topics, ignore
4. For flagged pairs, report: file A, file B, similarity assessment, recommended action

Skip obvious matches (a file matching itself, context files matching their folder contents).

---

## 9. Decisions Audit

### 9.1 Index Freshness
- [ ] `list_vault(folder="decisions")` -- get all decision files
- [ ] Read decisions index -- get index entries
- [ ] Compare: flag any files NOT in the index, or index entries pointing to non-existent files

### 9.2 Staleness Check (deep check)
For each decision file in `decisions/`:
- [ ] Read the decision note (at least Context + Decision + Consequences sections)
- [ ] Cross-check with current CLAUDE.md and MEMORY.md
- [ ] If the decision contradicts current rules/conventions -> flag as "possibly outdated"
- [ ] If the decision describes a system/tool that no longer exists -> flag as "stale"

### 9.3 Coverage -- Undocumented Decisions
- [ ] `list_vault(folder="conversations")` -- get recent session notes (last 2 weeks)
- [ ] For each session note, check if it has a "Decisions made" section
- [ ] If a session note documents a significant decision that does NOT have a corresponding file in `decisions/` -> flag as "undocumented decision"
- [ ] Significance filter: skip trivial choices. Flag only: new tools/services, workflow changes, data model changes, integration decisions

### 9.4 Backlinks
- [ ] For each decision note: check if it references the session note where the decision was made
- [ ] For session notes that led to decisions: check if they link back to the decision file
- [ ] Flag missing backlinks (warning, not critical)

---

## 10. Comparison with Previous Run

- [ ] Read `history.json` from last run
- [ ] For each previous finding: is it resolved, still open, or worse?
- [ ] Update finding statuses
- [ ] Flag "chronic" findings (open >3 runs / >3 weeks)
