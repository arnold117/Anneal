from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass(frozen=True)
class LLMConfig:
    provider: str        # "openai" | "anthropic"
    api_key: str
    model: str
    base_url: str | None = None

def load_llm_config() -> LLMConfig | None:
    """Load LLM config from ANNEAL_LLM_* env vars. Returns None if key missing."""
    load_dotenv()
    key = os.getenv("ANNEAL_LLM_KEY", "")
    if not key:
        return None
    model = os.getenv("ANNEAL_LLM_MODEL", "")
    if not model:
        return None
    return LLMConfig(
        provider=os.getenv("ANNEAL_LLM_PROVIDER", "openai").lower(),
        api_key=key,
        model=model,
        base_url=os.getenv("ANNEAL_LLM_BASE_URL") or None,
    )
