"""Configuration for brain MCP server and monitoring daemon."""

from __future__ import annotations

from pathlib import Path

# Vault
VAULT_PATH = Path("/root/vault")

# Git sync
SYNC_DEBOUNCE = 30  # seconds — batch writes within this window

# Monitoring thresholds
CPU_THRESHOLD = 80  # percent
CPU_CONSECUTIVE = 3  # checks before alert
RAM_MIN_AVAILABLE_GB = 1.0  # alert if available RAM drops below
DISK_THRESHOLD = 85  # percent

# Monitoring interval
MONITOR_INTERVAL = 300  # seconds (5 minutes)

# Alert cooldown — don't repeat same alert within this period
ALERT_COOLDOWN = 1800  # seconds (30 minutes)

# Semantic search
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
EMBEDDING_CHUNK_WORDS = 200
EMBEDDING_INDEX_DIR = VAULT_PATH / ".brain"

# Takopi config path (bot_token + chat_id)
TAKOPI_CONFIG = Path("/root/.takopi/takopi.toml")


def get_telegram_config() -> tuple[str, int]:
    """Read bot_token and chat_id from takopi config."""
    import tomli

    with open(TAKOPI_CONFIG, "rb") as f:
        config = tomli.load(f)

    tg = config["transports"]["telegram"]
    return tg["bot_token"], tg["chat_id"]
