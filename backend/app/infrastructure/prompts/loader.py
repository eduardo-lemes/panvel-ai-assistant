from functools import lru_cache
from pathlib import Path


import os
from pathlib import Path

# Try environment variable first, then fallback to relative path searches
PROMPTS_PATH_ENV = os.getenv("PROMPTS_ROOT")
if PROMPTS_PATH_ENV:
    PROMPTS_ROOT = Path(PROMPTS_PATH_ENV)
else:
    # Look for prompts in common relative locations (local development vs docker)
    base_paths = [
        Path(__file__).resolve().parents[4] / "prompts", # Local dev from backend/app/infrastructure/prompts/
        Path(__file__).resolve().parents[3] / "prompts", # Local dev/Docker from root or /app/
        Path("/app/prompts"),                            # Docker absolute mount
        Path("/prompts"),                                # Fallback root mount
    ]
    PROMPTS_ROOT = next((p for p in base_paths if p.exists() and p.is_dir()), base_paths[0])



@lru_cache
def load_prompt(filename: str) -> str:
    return (PROMPTS_ROOT / filename).read_text(encoding="utf-8").strip()
