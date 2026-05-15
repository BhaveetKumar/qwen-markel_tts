"""
.env_loader.py — Loads environment variables from a .env file in the project root.
"""
import os
from pathlib import Path

def load_dotenv(dotenv_path: str = None):
    """Load environment variables from a .env file (no override from shell or CLI)."""
    dotenv_file = dotenv_path or Path(__file__).parent.parent / ".env"
    if not os.path.exists(dotenv_file):
        return
    with open(dotenv_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Only set if not already set in os.environ
            if key not in os.environ:
                os.environ[key] = value
