#!/usr/bin/env python3
"""Calendar sync -- hourly cron job.

Three responsibilities:
1. Process sync queue (Claude-submitted remove/update actions)
2. Fail-safe source check (verify task statuses in source-of-truth files)
3. Cleanup old events (>14 days past)

Principle: fail-safe -- if unsure, do NOT delete. Worst case = event lingers.

CUSTOMIZATION:
- Update sys.path entries to point to your brain MCP server and any task integrations
- Update TASKS_MD to point to your project's task file (or remove if not needed)
- Update LOG_FILE path
- The Trello integration requires a trello MCP server with config module
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import date, timedelta
from pathlib import Path

# CUSTOMIZE: Add your brain MCP server and integration paths
sys.path.insert(0, "/root/brain/src")
# sys.path.insert(0, "/root/trello/src")  # Uncomment if using Trello integration

try:
    import httpx  # noqa: F401
except ImportError:
    pass  # Trello checks will fail-safe (return None)

from brain.calendar.db import (
    list_sync_queue,
    clear_sync_queue,
    remove_event,
    update_event,
    get_event,
    list_events_with_source,
    remove_old_events,
)

# CUSTOMIZE: Update these paths for your setup
LOG_FILE = Path("/root/scripts/calendar-sync.log")
TASKS_MD = Path("/root/vault/work/project/tasks/TASKS.md")  # Your project task file
CLEANUP_DAYS = 14

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# --- Part 1: Process sync queue ---

def process_sync_queue() -> int:
    """Process pending sync actions from Claude."""
    queue = list_sync_queue()
    if not queue:
        return 0

    processed = []
    for item in queue:
        event_id = item["event_id"]
        action = item["action"]
        try:
            if action == "remove":
                ev = get_event(event_id)
                if ev:
                    remove_event(event_id=event_id)
                    log.info(f"Queue: removed event #{event_id} ({ev['title']})")
                else:
                    log.info(f"Queue: event #{event_id} already gone, skipping")
            elif action == "update":
                kwargs = {}
                if item.get("new_date"):
                    kwargs["date"] = item["new_date"]
                if item.get("new_title"):
                    kwargs["title"] = item["new_title"]
                if kwargs:
                    update_event(event_id, **kwargs)
                    log.info(f"Queue: updated event #{event_id} -> {kwargs}")
                else:
                    log.info(f"Queue: update for #{event_id} but no changes, skipping")
            processed.append(item["id"])
        except Exception as e:
            log.error(f"Queue: failed to process #{item['id']}: {e}")

    if processed:
        clear_sync_queue(processed)
        log.info(f"Queue: cleared {len(processed)} items")

    return len(processed)


# --- Part 2: Fail-safe source check ---

def check_task_file_status(source_id: str) -> str | None:
    """Check task status by grepping the tasks markdown file.

    CUSTOMIZE: Adapt the parsing logic to match your task file format.
    Returns "done" if task is completed, None if can't determine (fail-safe).
    """
    if not TASKS_MD.exists():
        log.warning(f"Tasks file not found at {TASKS_MD}")
        return None

    content = TASKS_MD.read_text(encoding="utf-8")

    # CUSTOMIZE: Adapt this pattern to match your task ID format
    # Example: source_id = "task_42" -> extract task number 42
    match = re.match(r"task_(\d+)", source_id)
    if not match:
        return None

    task_num = match.group(1)

    # Look for row like: | 4 | ... | done_marker |
    for line in content.splitlines():
        line_stripped = line.strip()
        if not line_stripped.startswith("|"):
            continue
        cells = [c.strip() for c in line_stripped.split("|")]
        if len(cells) >= 3 and cells[1] == task_num:
            # CUSTOMIZE: Change the done marker to match your convention
            if "done" in line.lower() or "completed" in line.lower():
                return "done"
            return None  # found row but not done

    return None  # row not found -- fail-safe: do nothing


def check_trello_card_status(source_id: str) -> str | None:
    """Check Trello card status via API.

    CUSTOMIZE: Requires trello MCP server with config module.
    Returns "done" if card is in Done list or has done/fail label, None otherwise.
    """
    try:
        from trello.config import get_credentials, BASE_URL, LISTS
        import httpx

        key, token = get_credentials()
        resp = httpx.get(
            f"{BASE_URL}/cards/{source_id}",
            params={"key": key, "token": token, "fields": "idList,labels"},
            timeout=15.0,
        )
        if resp.status_code == 404:
            # Card deleted or archived -- treat as done
            return "done"
        resp.raise_for_status()
        card = resp.json()

        # Check if card is in Done list
        done_list_id = LISTS.get("done", "")
        if card.get("idList") == done_list_id:
            return "done"

        # Check for done/fail label
        for label in card.get("labels", []):
            if label.get("name", "").lower() in ("done", "fail"):
                return "done"

        return None  # card exists and is not done
    except Exception as e:
        log.warning(f"Trello API error for card {source_id}: {e}")
        return None  # fail-safe


def check_sources() -> int:
    """Check all calendar events with sources, remove if task is done."""
    events = list_events_with_source()
    if not events:
        return 0

    removed = 0
    for ev in events:
        source_type = ev["source_type"]
        source_id = ev["source_id"]
        status = None

        # CUSTOMIZE: Add/remove source type handlers as needed
        if source_type == "task_file" and source_id:
            status = check_task_file_status(source_id)
        elif source_type == "trello" and source_id:
            status = check_trello_card_status(source_id)
        # "manual" and others -- skip (fail-safe)

        if status == "done":
            remove_event(event_id=ev["id"])
            log.info(f"Source check: removed event #{ev['id']} ({ev['title']}) -- {source_type}:{source_id} is done")
            removed += 1

    return removed


# --- Part 3: Cleanup old events ---

def cleanup_old() -> int:
    """Remove events older than CLEANUP_DAYS."""
    removed = remove_old_events(CLEANUP_DAYS)
    if removed:
        log.info(f"Cleanup: removed {removed} events older than {CLEANUP_DAYS} days")
    return removed


# --- Main ---

def main():
    log.info("=== Calendar sync started ===")

    # 1. Queue (highest priority -- explicit Claude commands)
    queue_count = process_sync_queue()

    # 2. Source check (fail-safe reconciliation)
    source_count = check_sources()

    # 3. Cleanup (hygiene)
    cleanup_count = cleanup_old()

    total = queue_count + source_count + cleanup_count
    if total:
        log.info(f"=== Done: queue={queue_count}, sources={source_count}, cleanup={cleanup_count} ===")
    else:
        log.info("=== Done: nothing to sync ===")


if __name__ == "__main__":
    main()
