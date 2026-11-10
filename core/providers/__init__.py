import os

from core.providers.base import ModelProvider
from core.providers.fake import FakeProvider
from core.providers.gemini import GeminiProvider

PROVIDERS: dict[str, type[ModelProvider]] = {"fake": FakeProvider, "gemini": GeminiProvider}


def get_provider(name: str | None = None) -> ModelProvider:
    name = name or os.getenv("LLM_PROVIDER", "fake")
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown LLM_PROVIDER '{name}'. Available: {', '.join(PROVIDERS)}.")
    return cls()
