#!/usr/bin/env bash
# Weekly retro reminder with 4-level escalation.
# Called by cron at different times (e.g., Sunday).
#
# ESCALATION PATTERN:
#   Level 1 (early): Detailed message with stats from task system
#   Level 2 (mid):   Simpler nudge reminder
#   Level 3 (late):  Last chance warning before auto-retro
#   Level 4 (final): Auto-retro runs automatically
#
# Each level is a separate cron entry. If retro is done manually
# at any point (marker file created), remaining levels are skipped.
#
# Example crontab (Sunday, adjust times to your timezone):
#   0 15 * * 0 /path/to/retro-reminder.sh 1
#   0 17 * * 0 /path/to/retro-reminder.sh 2
#   0 18 * * 0 /path/to/retro-reminder.sh 3
#   30 18 * * 0 /path/to/retro-reminder.sh 4
#
# CUSTOMIZATION:
# - Update SEND_SCRIPT to point to your notification script
#   (Telegram bot, Slack webhook, email, etc.)
# - Update AUTO_RETRO to point to your auto-retro script (or remove Level 4)
# - Update the stats-fetching logic in Level 1 for your task system
# - The marker mechanism works with any task/retro system
#
# Skips if retro already done this week (marker file exists).

set -euo pipefail

LEVEL="${1:-1}"
# CUSTOMIZE: Path to your notification/send script
SEND_SCRIPT="/path/to/send-notification.sh"
MARKER_DIR="/root/scripts/reminders/.markers"
# CUSTOMIZE: Path to your auto-retro script (for Level 4)
AUTO_RETRO="/root/scripts/reminders/auto-retro.py"
LOG="/root/scripts/reminders/retro.log"

mkdir -p "$MARKER_DIR"

# Get current ISO week for marker filename
WEEK=$(date +%G-W%V)
MARKER="$MARKER_DIR/retro_done_$WEEK"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"
}

# Skip if already done (marker file exists)
if [[ -f "$MARKER" ]]; then
    log "L$LEVEL: Retro already done for $WEEK, skipping"
    exit 0
fi

log "L$LEVEL: Sending retro reminder"

case "$LEVEL" in
    1)
        # CUSTOMIZE: Replace this with stats from your task system
        # Example: fetch completed task count, time spent, etc.
        STATS=$(python3 -c "
# CUSTOMIZE: Import your task system's API/stats module
# Example with a generic task API:
# from my_tasks import get_weekly_stats
# stats = get_weekly_stats()
# print(f'Completed: {stats.done_count}')
# print(f'Failed: {stats.fail_count}')
# print(f'Total time: {stats.total_hours}h')
print('Task stats not configured. Edit retro-reminder.sh Level 1.')
" 2>/dev/null || echo "Failed to load task stats")

        MSG="Time for your weekly retro!

$WEEK -- time to review the week.

$STATS

Run your retro command or reply to start."

        # CUSTOMIZE: Send via your notification method
        bash "$SEND_SCRIPT" message "$MSG"
        ;;

    2)
        MSG="Reminder: weekly retro for $WEEK is not done yet.

Run your retro or reply 'skip' to skip this week."

        bash "$SEND_SCRIPT" message "$MSG"
        ;;

    3)
        MSG="Last chance to do the retro manually.

Auto-retro will run in 30 minutes (stats only, no analysis).

Run your retro now, or reply: yes / no / skip"

        bash "$SEND_SCRIPT" message "$MSG"
        ;;

    4)
        log "L4: Running auto-retro"
        if python3 "$AUTO_RETRO" >> "$LOG" 2>&1; then
            touch "$MARKER"
            log "L4: Auto-retro completed, marker created"
        else
            log "L4: Auto-retro failed"
            bash "$SEND_SCRIPT" message "Auto-retro failed. Please run manually."
        fi
        ;;

    *)
        log "Unknown level: $LEVEL"
        exit 1
        ;;
esac
