#!/bin/bash
# Librarian Agent -- weekly autonomous vault & server audit
# Runs via cron (e.g., Sunday 04:00 local time)
# Read-only analysis -> report to notification channel
#
# CUSTOMIZATION:
# - Update LIBRARIAN_DIR to match your librarian installation path
# - Update SEND_SCRIPT to your notification script (Telegram, Slack, etc.)
# - Replace TG_CHAT_ID and TG_BOT_TOKEN with your values or use env vars
# - Adjust --max-turns if audits need more/fewer turns
# - Adjust --allowedTools to match your MCP server names
#
# Example crontab entry:
#   0 1 * * 0 /root/librarian/run.sh  # Sunday 01:00 UTC
set -euo pipefail

LIBRARIAN_DIR="/root/librarian"
STATE_DIR="${LIBRARIAN_DIR}/state"
SYSTEM_PROMPT="${LIBRARIAN_DIR}/SYSTEM.md"
# CUSTOMIZE: Path to your notification/send script
SEND_SCRIPT="/path/to/send-notification.sh"
LOG_FILE="${STATE_DIR}/last-run.log"
REPORT_FILE="${STATE_DIR}/last-report.md"
DATE=$(date +%Y-%m-%d)

log() { echo "[librarian] $(date '+%H:%M:%S') $*" | tee -a "$LOG_FILE"; }

# Fresh log
echo "=== Librarian run: $DATE ===" > "$LOG_FILE"

# Verify system prompt exists
if [ ! -f "$SYSTEM_PROMPT" ]; then
    log "ERROR: System prompt not found at $SYSTEM_PROMPT"
    exit 1
fi

log "Starting audit..."

# Run Claude in print mode with the system prompt
# --max-turns limits the agent to prevent runaway loops
# MCP tools are available from global claude config
# env -u CLAUDECODE: prevent "nested session" block if run from inside claude
#
# CUSTOMIZE: Adjust --allowedTools to match your MCP server tool names.
# The pattern below uses "mcp__brain__*" -- replace "brain" with your MCP server name.
REPORT=$(cd /root && env -u CLAUDECODE claude -p \
    --system-prompt "$(cat "$SYSTEM_PROMPT")" \
    --max-turns 200 \
    --permission-mode default \
    --allowedTools "Read Glob Grep Bash(ls:*) Bash(cat:*) Bash(wc:*) Bash(stat:*) Bash(du:*) Bash(find:*) Bash(head:*) Bash(tail:*) Bash(date:*) mcp__brain__search_vault mcp__brain__semantic_search mcp__brain__read_vault mcp__brain__list_vault mcp__brain__get_server_status mcp__brain__get_server_map mcp__brain__get_today mcp__brain__list_calendar_events Write(/root/librarian/state/*) Edit(/root/librarian/state/*)" \
    --verbose \
    "Run a full system audit per the checklist at /root/librarian/CHECKLIST.md.

Architecture: TWO PASSES (described in SYSTEM.md):
-- Pass 1: quick structural checks (server, backups, inbox, projects)
-- Pass 2: deep analysis (orphans, broken links, freshness, semantics, contradictions)

Workflow:
1. Read /root/librarian/SYSTEM.md and /root/librarian/CHECKLIST.md
2. Read /root/librarian/state/history.json (if exists) -- compare with last run
3. Pass 1: quick checks -> save intermediate results to state/pass1-results.md
4. Pass 2: deep checks (orphans, broken links, freshness scoring, semantic dedup, cross-doc consistency)
5. Update /root/librarian/state/history.json with results
6. Save FULL report to /root/librarian/state/last-report-full.md (no length limit)
7. Save COMPRESSED report to /root/librarian/state/last-report.md (for messaging, <4000 chars)

At the end, output ONLY the compressed report text (no code blocks, no tables, em-dash bullets, max 4000 chars).
Format described in SYSTEM.md under Report Format." \
    2>>"$LOG_FILE") || {
    log "ERROR: Claude exited with code $?"
    # CUSTOMIZE: Send error notification via your preferred method
    bash "$SEND_SCRIPT" message "Librarian -- ERROR during audit ($DATE). Check logs: $LOG_FILE" 2>/dev/null || true
    exit 1
}

log "Audit complete. Report length: ${#REPORT} chars"

# Save the raw report
echo "$REPORT" > "$REPORT_FILE"

# CUSTOMIZE: Send report to your notification channel
# Option A: Send as text message (if short enough)
# Option B: Send as file attachment (if too long)
if [ ${#REPORT} -gt 4000 ]; then
    log "Report exceeds 4000 chars, sending as file"
    bash "$SEND_SCRIPT" file "$REPORT_FILE" "Librarian Audit Report -- $DATE (full report attached)" 2>>"$LOG_FILE" || {
        log "WARNING: Failed to send report file"
    }
else
    # CUSTOMIZE: Replace with your notification method
    # Example for Telegram (replace YOUR_CHAT_ID and YOUR_BOT_TOKEN):
    # curl -s -d "chat_id=YOUR_CHAT_ID" --data-urlencode "text=$REPORT" \
    #     "https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage" \
    #     >>"$LOG_FILE" 2>&1
    bash "$SEND_SCRIPT" message "$REPORT" 2>>"$LOG_FILE" || {
        log "WARNING: Failed to send report"
        # Fallback: try sending as file
        bash "$SEND_SCRIPT" file "$REPORT_FILE" "Librarian Audit Report -- $DATE" 2>>"$LOG_FILE" || true
    }
fi

log "Report sent"
log "Done."
