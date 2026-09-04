"""Provider wiring — no network, just that the right class is built."""
import pytest

from strands_issue_writer.provider import ProviderConfig, build_model, describe


def test_unknown_provider_is_explicit():
    with pytest.raises(ValueError, match="unknown provider"):
        build_model(ProviderConfig(kind="telepathy"))


def test_describe_mentions_endpoint():
    d = describe(ProviderConfig(kind="ollama", model_id="issue-writer"))
    assert "ollama" in d and "issue-writer" in d and "11434" in d


def test_temperature_defaults_to_zero():
    """Structured JSON output; sampling only produces malformed objects."""
    assert ProviderConfig().temperature == 0.0


def test_vllm_uses_base_url():
    d = describe(ProviderConfig(kind="vllm", base_url="http://x:8000/v1"))
    assert "http://x:8000/v1" in d
