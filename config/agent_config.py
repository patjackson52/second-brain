import os
from pathlib import Path

# Vault directory - where notes live
# Default: ~/second-brain-vault (separate from code repo)
_default_vault = Path.home() / "second-brain-vault"
VAULT_DIR = Path(os.environ.get("SECOND_BRAIN_VAULT", str(_default_vault)))

# State database - where agent state is stored
# Default: inside vault's .state directory
_default_state_db = VAULT_DIR / ".state" / "agents.db"
STATE_DB_PATH = Path(os.environ.get("SECOND_BRAIN_STATE_DB", str(_default_state_db)))

# Model configuration
TRIAGE_MODEL = os.environ.get("TRIAGE_MODEL", "anthropic:claude-sonnet-4-5")

# Token pricing (USD per token) — Claude Sonnet 4.5
INPUT_PRICE = 3.0 / 1_000_000   # $3/MTok
OUTPUT_PRICE = 15.0 / 1_000_000  # $15/MTok
