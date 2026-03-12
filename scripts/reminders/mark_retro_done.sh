#!/usr/bin/env bash
# Sets the retro-done marker for the current ISO week.
# Run this at the end of ANY manual retro session to prevent
# the Level 4 auto-retro from firing.
#
# The escalation system (retro-reminder.sh) checks for this marker
# file before sending reminders. Once it exists, all remaining
# reminder levels for the current week are skipped.
#
# Usage: bash /path/to/mark_retro_done.sh
#
# CUSTOMIZATION:
# - Update MARKER_DIR to match the path in retro-reminder.sh
# - Call this from your retro skill/script after a successful retro

# CUSTOMIZE: Must match MARKER_DIR in retro-reminder.sh
MARKER_DIR="/root/scripts/reminders/.markers"
WEEK=$(date +%G-W%V)
MARKER="$MARKER_DIR/retro_done_$WEEK"

mkdir -p "$MARKER_DIR"
touch "$MARKER"
echo "Marker set: retro_done_$WEEK (auto-retro will be skipped)"
