"""The provider contract. Only files in core/providers/ may import a vendor SDK."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Capabilities:
    images: bool
    native_json_schema: bool  # False -> extractor embeds the schema in the prompt
    max_images_per_call: int


@dataclass
class GenerateResponse:
    text: str
    model: str
    input_tokens: int | None  # None if the API reports no usage; never estimated
    output_tokens: int | None
    latency_ms: int


class ProviderError(Exception):
    """retryable=True for 429/5xx/timeouts; False for 400/401/403 (retrying can't help)."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ModelProvider(ABC):
    name: str
    model: str
    capabilities: Capabilities

    @abstractmethod
    def generate(self, prompt: str, images: list[bytes], schema: dict) -> GenerateResponse: ...
