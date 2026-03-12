#!/usr/bin/env python3
"""Server monitoring daemon — sends Telegram alerts when resources are critical.

Runs as a standalone PM2 process. Checks CPU, RAM, disk, and PM2 processes
every 5 minutes. Sends alerts through takopi's bot token.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

import httpx
import psutil

# Add brain to path
sys.path.insert(0, "/root/brain/src")

from brain.config import (
    ALERT_COOLDOWN,
    CPU_CONSECUTIVE,
    CPU_THRESHOLD,
    DISK_THRESHOLD,
    MONITOR_INTERVAL,
    RAM_MIN_AVAILABLE_GB,
    get_telegram_config,
)

# State
_cpu_high_count = 0
_last_alerts: dict[str, float] = {}  # alert_key -> timestamp


def send_alert(bot_token: str, chat_id: int, message: str) -> None:
    """Send a Telegram message via Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        httpx.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10)
    except Exception as e:
        print(f"[monitor] Failed to send alert: {e}", flush=True)


def should_alert(key: str) -> bool:
    """Check if enough time has passed since the last alert of this type."""
    now = time.time()
    last = _last_alerts.get(key, 0)
    if now - last < ALERT_COOLDOWN:
        return False
    _last_alerts[key] = now
    return True


def check_cpu() -> str | None:
    """Check CPU usage. Alert after N consecutive high readings."""
    global _cpu_high_count
    cpu = psutil.cpu_percent(interval=2)
    if cpu > CPU_THRESHOLD:
        _cpu_high_count += 1
        if _cpu_high_count >= CPU_CONSECUTIVE and should_alert("cpu"):
            return (
                f"*CPU Alert*\n"
                f"CPU at *{cpu:.0f}%* for {_cpu_high_count} consecutive checks\n"
                f"Threshold: {CPU_THRESHOLD}%"
            )
    else:
        _cpu_high_count = 0
    return None


def check_ram() -> str | None:
    """Check available RAM."""
    mem = psutil.virtual_memory()
    available_gb = mem.available / (1024 ** 3)
    if available_gb < RAM_MIN_AVAILABLE_GB and should_alert("ram"):
        return (
            f"*RAM Alert*\n"
            f"Available: *{available_gb:.2f} GB*\n"
            f"Used: {mem.used / (1024**3):.1f} / {mem.total / (1024**3):.1f} GB ({mem.percent}%)\n"
            f"Threshold: {RAM_MIN_AVAILABLE_GB} GB"
        )
    return None


def check_disk() -> str | None:
    """Check disk usage."""
    disk = psutil.disk_usage("/")
    if disk.percent > DISK_THRESHOLD and should_alert("disk"):
        return (
            f"*Disk Alert*\n"
            f"Usage: *{disk.percent}%*\n"
            f"Free: {disk.free / (1024**3):.1f} GB / {disk.total / (1024**3):.0f} GB\n"
            f"Threshold: {DISK_THRESHOLD}%"
        )
    return None


_pm2_down_counts: dict[str, int] = {}  # name -> consecutive non-online checks
PM2_CONSECUTIVE = 2  # alert after N consecutive failures (skip transient restarts)


def check_pm2() -> list[str]:
    """Check PM2 process health. Skips transient failures (timeouts, brief restarts)."""
    alerts = []
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            capture_output=True, text=True, timeout=10,
        )
        procs = json.loads(result.stdout)
        seen = set()
        for p in procs:
            name = p.get("name", "?")
            seen.add(name)
            status = p.get("pm2_env", {}).get("status", "?")
            if status != "online":
                _pm2_down_counts[name] = _pm2_down_counts.get(name, 0) + 1
                if _pm2_down_counts[name] >= PM2_CONSECUTIVE and should_alert(f"pm2_{name}"):
                    restarts = p.get("pm2_env", {}).get("restart_time", 0)
                    alerts.append(
                        f"*PM2 Alert*\n"
                        f"Process `{name}` is *{status}*\n"
                        f"Restarts: {restarts}"
                    )
            else:
                _pm2_down_counts.pop(name, None)
        # Clean up processes no longer in PM2
        for gone in set(_pm2_down_counts) - seen:
            _pm2_down_counts.pop(gone, None)
    except Exception as e:
        # PM2 jlist timeout/error — transient, skip alert (will retry next cycle)
        print(f"[monitor] PM2 check failed (transient, no alert): {e}", flush=True)
    return alerts


def run_check(bot_token: str, chat_id: int) -> None:
    """Run all checks and send alerts."""
    alerts = []

    cpu_alert = check_cpu()
    if cpu_alert:
        alerts.append(cpu_alert)

    ram_alert = check_ram()
    if ram_alert:
        alerts.append(ram_alert)

    disk_alert = check_disk()
    if disk_alert:
        alerts.append(disk_alert)

    pm2_alerts = check_pm2()
    alerts.extend(pm2_alerts)

    for alert in alerts:
        ts = datetime.now(timezone(timedelta(hours=3))).strftime("%H:%M MSK")
        send_alert(bot_token, chat_id, f"{alert}\n\n_{ts}_")
        print(f"[monitor] Alert sent: {alert[:60]}...", flush=True)


def main() -> None:
    """Main loop — run checks every MONITOR_INTERVAL seconds."""
    print("[monitor] Starting server monitor daemon", flush=True)

    bot_token, chat_id = get_telegram_config()
    print(f"[monitor] Bot token loaded, chat_id={chat_id}", flush=True)
    print(
        f"[monitor] Thresholds: CPU>{CPU_THRESHOLD}% x{CPU_CONSECUTIVE}, "
        f"RAM<{RAM_MIN_AVAILABLE_GB}GB, Disk>{DISK_THRESHOLD}%",
        flush=True,
    )
    print(f"[monitor] Check interval: {MONITOR_INTERVAL}s, cooldown: {ALERT_COOLDOWN}s", flush=True)

    # Send startup notification
    send_alert(bot_token, chat_id, "*Server Monitor* started\nChecking every 5 min.")

    while True:
        try:
            run_check(bot_token, chat_id)
        except Exception as e:
            print(f"[monitor] Error in check cycle: {e}", flush=True)
        time.sleep(MONITOR_INTERVAL)


if __name__ == "__main__":
    main()
