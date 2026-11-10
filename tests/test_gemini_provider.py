from types import SimpleNamespace

import pytest
from google.genai import errors

from core.providers.base import ProviderError
from core.providers.gemini import GeminiProvider


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "some-model")
    return GeminiProvider()


def stub_client(provider, *, response=None, error=None):
    def generate_content(**kwargs):
        if error:
            raise error
        return response
    provider.client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))


def test_missing_config_fails_visibly(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiProvider()


def test_usage_is_read_from_response_metadata(provider):
    usage = SimpleNamespace(prompt_token_count=10, candidates_token_count=4, thoughts_token_count=6)
    stub_client(provider, response=SimpleNamespace(text="[]", usage_metadata=usage, prompt_feedback=None))
    r = provider.generate("p", [b"img"], {})
    assert (r.text, r.input_tokens, r.output_tokens) == ("[]", 10, 10)


@pytest.mark.parametrize("code,retryable", [(429, True), (503, True), (400, False), (401, False), (404, False)])
def test_api_errors_are_classified_as_retryable_or_not(provider, code, retryable):
    stub_client(provider, error=errors.APIError(code, {"error": {"message": "boom"}}))
    with pytest.raises(ProviderError) as e:
        provider.generate("p", [b"img"], {})
    assert e.value.retryable is retryable


def test_empty_response_is_a_non_retryable_error(provider):
    stub_client(provider, response=SimpleNamespace(text=None, usage_metadata=None, prompt_feedback=None))
    with pytest.raises(ProviderError) as e:
        provider.generate("p", [b"img"], {})
    assert e.value.retryable is False
