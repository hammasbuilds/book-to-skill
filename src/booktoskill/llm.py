"""A minimal Ollama client with an on-disk generation cache, and a fake for tests.

Every generation is cached under ``sha256(model, system, prompt, options)``, so
an interrupted model run resumes where it stopped and re-running a finished
one costs nothing.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

DEFAULT_URL = "http://127.0.0.1:11434"
GEN_MODEL = "qwen2.5:14b-instruct"
DEFAULT_OPTIONS = {"temperature": 0.0, "seed": 0, "num_ctx": 16384}


class LLMError(RuntimeError):
    pass


class Client(Protocol):
    model: str

    def generate(self, prompt: str, system: str = "") -> str: ...


def cache_key(model: str, system: str, prompt: str, options: dict) -> str:
    payload = json.dumps(
        {"model": model, "system": system, "prompt": prompt, "options": options},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class DiskCache:
    root: Path

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> str | None:
        p = self._path(key)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))["response"]

    def put(self, key: str, record: dict) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8", newline="\n")
        tmp.replace(p)  # atomic: a killed run never leaves a half-written entry


@dataclass
class CachedClient:
    """Wraps a transport with the disk cache and counts real calls."""

    model: str
    transport: Callable[[str, str, str, dict], str]
    cache: DiskCache
    options: dict = field(default_factory=lambda: dict(DEFAULT_OPTIONS))
    calls: int = 0
    hits: int = 0

    def generate(self, prompt: str, system: str = "") -> str:
        key = cache_key(self.model, system, prompt, self.options)
        cached = self.cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        response = self.transport(self.model, system, prompt, self.options)
        self.calls += 1
        self.cache.put(
            key,
            {
                "model": self.model,
                "options": self.options,
                "system": system,
                "prompt": prompt,
                "response": response,
            },
        )
        return response


def ollama_transport(url: str = DEFAULT_URL, timeout: float = 600.0) -> Callable[..., str]:
    def call(model: str, system: str, prompt: str, options: dict) -> str:
        body = json.dumps(
            {
                "model": model,
                "system": system,
                "prompt": prompt,
                "options": options,
                "stream": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/api/generate", data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))["response"]
        except urllib.error.URLError as exc:
            raise LLMError(f"ollama at {url} failed for {model}: {exc}") from exc

    return call


def ollama_client(
    cache_dir: str | Path, model: str = GEN_MODEL, url: str = DEFAULT_URL
) -> CachedClient:
    return CachedClient(model, ollama_transport(url), DiskCache(Path(cache_dir)))


def list_models(url: str = DEFAULT_URL, timeout: float = 5.0) -> list[str]:
    """Names of the models the Ollama server has pulled."""
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LLMError(f"ollama is not reachable at {url}: {exc}") from exc
    return [m["name"] for m in data.get("models", [])]


@dataclass
class FakeClient:
    """Deterministic stand-in: ``responder(prompt, system)`` decides the reply."""

    responder: Callable[[str, str], str]
    model: str = "fake"
    prompts: list[str] = field(default_factory=list)

    def generate(self, prompt: str, system: str = "") -> str:
        self.prompts.append(prompt)
        return self.responder(prompt, system)
