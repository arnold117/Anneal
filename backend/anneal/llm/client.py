from __future__ import annotations
import json
import logging
import re
from typing import Protocol, runtime_checkable
from anneal.llm.errors import LLMResponseError

logger = logging.getLogger(__name__)

@runtime_checkable
class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...
    def complete_json(self, system: str, user: str, retries: int = 2) -> dict: ...


def _strip_markdown_fences(raw: str) -> str:
    raw = raw.strip()
    m = re.search(r"```\w*\n(.*?)\n```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    return raw


def _complete_json_with_retry(client: LLMClient, system: str, user: str, retries: int) -> dict:
    last_raw = ""
    for attempt in range(retries + 1):
        last_raw = client.complete(system, user)
        cleaned = _strip_markdown_fences(last_raw)
        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
            return {"data": result}
        except json.JSONDecodeError:
            logger.warning("JSON parse failed (attempt %d/%d): %s...", attempt + 1, retries + 1, cleaned[:200])
            if attempt == retries:
                raise LLMResponseError(f"Failed to parse JSON after {retries + 1} attempts. Last response: {last_raw[:500]}")
    raise LLMResponseError("Retry loop exhausted")


class OpenAIClient:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        from openai import OpenAI
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    def complete_json(self, system: str, user: str, retries: int = 2) -> dict:
        return _complete_json_with_retry(self, system, user, retries)


class AnthropicClient:
    def __init__(self, api_key: str, model: str) -> None:
        from anthropic import Anthropic
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.1,
        )
        return response.content[0].text

    def complete_json(self, system: str, user: str, retries: int = 2) -> dict:
        return _complete_json_with_retry(self, system, user, retries)


def create_client(config) -> LLMClient:
    from anneal.llm.config import LLMConfig
    if config.provider == "anthropic":
        return AnthropicClient(api_key=config.api_key, model=config.model)
    return OpenAIClient(api_key=config.api_key, model=config.model, base_url=config.base_url)
