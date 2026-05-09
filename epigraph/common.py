import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(obj: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def stable_id(*parts: str, prefix: str = "item") -> str:
    import hashlib

    raw = "||".join(str(p) for p in parts)
    return f"{prefix}_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def option_letter(text: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(r"\b([ABCD])\b", text.upper())
    return match.group(1) if match else None


class ChatClient:
    """Small OpenRouter-compatible client used by all generation tasks."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1/chat/completions",
        temperature: float = 0.0,
        timeout: int = 120,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url
        self.temperature = temperature
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError("Set OPENROUTER_API_KEY or pass api_key explicitly.")

    def complete(self, messages: List[Dict[str, str]], max_tokens: int = 800) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/EpiVerse",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        for attempt in range(1, 4):
            response = requests.post(
                self.base_url, headers=headers, json=payload, timeout=self.timeout
            )
            if response.status_code == 429:
                time.sleep(min(30, 2**attempt))
                continue
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        raise RuntimeError("OpenRouter request failed after retries.")


def batch(iterable: Iterable[Any], size: int) -> Iterable[List[Any]]:
    chunk: List[Any] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

