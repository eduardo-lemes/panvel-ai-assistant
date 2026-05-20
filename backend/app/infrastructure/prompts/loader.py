from functools import lru_cache
from pathlib import Path


PROMPTS_ROOT = Path(__file__).resolve().parents[4] / "prompts"


@lru_cache
def load_prompt(filename: str) -> str:
    return (PROMPTS_ROOT / filename).read_text(encoding="utf-8").strip()
