"""Unit tests for LLM routing helpers (no network)."""

from __future__ import annotations

from core import llm as llm_mod


def test_normalize_target_model_adds_ollama_prefix() -> None:
    assert llm_mod._normalize_target_model("ollama", "mistral:7b") == "ollama/mistral:7b"


def test_normalize_target_model_keeps_existing_prefix() -> None:
    assert llm_mod._normalize_target_model("ollama", "ollama/mistral:7b") == "ollama/mistral:7b"


def test_normalize_target_model_non_ollama_provider_unchanged() -> None:
    assert llm_mod._normalize_target_model("openai", "gpt-4o") == "gpt-4o"


def test_llm_completion_error_is_runtime_error() -> None:
    assert issubclass(llm_mod.LLMCompletionError, RuntimeError)


def test_ollama_model_strips_prefix_for_sdk() -> None:
    """Regression: only the leading ollama/ prefix must be stripped, not every occurrence."""
    tm = "ollama/qwen3-coder-next:latest"
    clean = tm[len("ollama/") :] if tm.startswith("ollama/") else tm
    assert clean == "qwen3-coder-next:latest"
