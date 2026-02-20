import os
from pathlib import Path

VAULT_DIR = Path(os.environ.get("SECOND_BRAIN_VAULT", "/home/ubuntu/second-brain"))
STATE_DB_PATH = Path(os.environ.get("SECOND_BRAIN_STATE_DB", "/home/ubuntu/second-brain-state/agents.db"))

TRIAGE_MODEL = os.environ.get("TRIAGE_MODEL", "anthropic:claude-sonnet-4-5")

# Token pricing (USD per token) — Claude Sonnet 4.5
INPUT_PRICE = 3.0 / 1_000_000   # $3/MTok
OUTPUT_PRICE = 15.0 / 1_000_000  # $15/MTok
