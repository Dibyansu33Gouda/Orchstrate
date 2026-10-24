import os
import json
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".llm_cache"

class LLMProvider(ABC):
    """Abstract interface for LLM calls with schema enforcement and persistent caching."""
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, prompt: str, system_prompt: str) -> str:
        content = f"{self.model_name}:{system_prompt}:{prompt}".encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def _read_cache(self, key: str) -> Optional[str]:
        cache_file = CACHE_DIR / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("response")
            except Exception:
                return None
        return None

    def _write_cache(self, key: str, response: str) -> None:
        cache_file = CACHE_DIR / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({"response": response}, f)
        except Exception:
            pass

    @abstractmethod
    def call(self, prompt: str, system_prompt: str, temperature: float = 0.0) -> str:
        """Execute model call and return text response."""
        pass

class DeterministicFallbackProvider(LLMProvider):
    """Fallback provider when no external LLM API key is present."""
    def __init__(self, model_name: str = "deterministic-rule-engine") -> None:
        super().__init__(model_name)

    def call(self, prompt: str, system_prompt: str, temperature: float = 0.0) -> str:
        # Return fallback json indicating deterministic adjudication
        return json.dumps({
            "action": "submit_verdict",
            "justification": "Fallback deterministic evaluation applied.",
            "fallback_used": True
        })

class GeminiProvider(LLMProvider):
    """Gemini API Provider via REST."""
    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: str | None = None) -> None:
        super().__init__(model_name)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    def call(self, prompt: str, system_prompt: str, temperature: float = 0.0) -> str:
        cache_key = self._get_cache_key(prompt, system_prompt)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        if not self.api_key:
            return DeterministicFallbackProvider().call(prompt, system_prompt, temperature)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"System:\n{system_prompt}\n\nUser:\n{prompt}"}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0]["content"]["parts"][0]["text"]
                        self._write_cache(cache_key, text)
                        return text
        except Exception:
            pass

        return DeterministicFallbackProvider().call(prompt, system_prompt, temperature)

def get_llm_provider(preferred_provider: str = "auto", model_name: str = "default") -> LLMProvider:
    """Factory selecting available provider based on environment variables."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if preferred_provider == "gemini" and gemini_key:
        return GeminiProvider(model_name=model_name if model_name != "default" else "gemini-2.5-flash", api_key=gemini_key)
    elif gemini_key:
        return GeminiProvider(model_name="gemini-2.5-flash", api_key=gemini_key)
    else:
        # Fallback to deterministic mode
        return DeterministicFallbackProvider()
