import os
from typing import Optional

import litellm
from litellm import completion
from core.config import settings

# Configure LiteLLM
litellm.suppress_debug_info = True

# MLX 模型缓存，避免重复加载
_mlx_cache: dict = {}


class LLMCompletionError(RuntimeError):
    """Could not obtain an assistant message from the configured provider (network, API, or transport)."""


def _chat_completion_mlx(messages, model_id: str, temperature: float = 0.0, max_tokens: int = 4096):
    """无 tools 时用 MLX 推理；返回 OpenAI 风格 message（content 字符串）。"""
    if model_id not in _mlx_cache:
        from mlx_lm import load
        # 使用 HF 默认缓存（~/.cache/huggingface/hub 或 HF_HUB_CACHE）；不绑定项目目录，便于迁移最小可运行集
        _mlx_cache[model_id] = load(model_id)
    model, tokenizer = _mlx_cache[model_id]
    from mlx_lm import generate
    try:
        prompt_str = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False, truncation=True
        )
    except (TypeError, ValueError, KeyError, AttributeError):
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content") or ""
            if isinstance(content, list):
                content = " ".join(
                    (x.get("text", "") if isinstance(x, dict) else str(x) for x in content)
                )
            parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        prompt_str = "\n".join(parts) + "\n<|im_start|>assistant\n"
    full_text = generate(model, tokenizer, prompt=prompt_str, max_tokens=max_tokens, temperature=temperature, verbose=False)
    if isinstance(full_text, str):
        out_text = full_text[len(prompt_str):].lstrip() if full_text.startswith(prompt_str) else full_text
    else:
        out_text = getattr(full_text, "text", str(full_text))
    from pydantic import BaseModel

    class SimpleMessage(BaseModel):
        content: Optional[str] = None
        role: str = "assistant"

    return SimpleMessage(content=out_text or "", role="assistant")


def _normalize_target_model(provider: str, target_model: str) -> str:
    has_provider_prefix = "/" in target_model and target_model.split("/")[0] in (
        "openai",
        "anthropic",
        "ollama",
        "together_ai",
        "groq",
    )
    if (not has_provider_prefix) and provider == "ollama":
        return f"ollama/{target_model}"
    return target_model


def _ollama_chat_via_openai_sdk(
    messages,
    *,
    target_model: str,
    tools,
    temperature: float,
    timeout_sec: int,
    response_format=None,
):
    """
    Ollama exposes an OpenAI-compatible HTTP API. Use it directly so tool_calls are not broken or
    replaced with synthetic error JSON by LiteLLM's Ollama adapter.
    """
    from openai import OpenAI
    import httpx

    api_base = settings.llm.ollama.get("api_base", "http://localhost:11434")
    api_base = api_base.rstrip("/")
    if not api_base.endswith("/v1"):
        api_base = f"{api_base}/v1"
    client = OpenAI(
        base_url=api_base,
        api_key="ollama",
        http_client=httpx.Client(trust_env=False, timeout=timeout_sec),
    )
    tm = target_model
    if tm.startswith("ollama/"):
        tm = tm[len("ollama/") :]
    clean_model = tm
    kwargs: dict = {
        "model": clean_model,
        "messages": messages,
        "temperature": temperature,
        "timeout": timeout_sec,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    if response_format is not None:
        kwargs["response_format"] = response_format
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        raise LLMCompletionError(
            f"Ollama OpenAI-compatible chat failed (model={clean_model!r}, base={api_base!r}): {e}"
        ) from e
    return response.choices[0].message


class LLMService:
    def __init__(self):
        self.provider = settings.llm.provider
        self.default_model = settings.llm.default_model

        # Setup Environment for LiteLLM based on settings
        if settings.llm.openai:
            os.environ["OPENAI_API_BASE"] = settings.llm.openai.get("api_base", "https://api.openai.com/v1")

        # For Ollama, we usually just need the base URL if it's not localhost default
        if self.provider == "ollama":
            pass

    def chat_completion(self, messages, tools=None, model=None, temperature=0.0, response_format=None, timeout: Optional[int] = None):
        """
        Unified Chat Completion using LiteLLM / Ollama / MLX.
        MLX：仅当 tools=None 时使用；有 tools 时自动用 fallback_for_tools（如 ollama）。见 docs/inference_backends.md
        timeout: optional override in seconds; if None, uses settings.llm.timeout.

        On failure, raises LLMCompletionError (never returns None).
        """
        target_model = model or self.default_model
        req_timeout = timeout if timeout is not None else settings.llm.timeout
        mlx_cfg = getattr(settings.llm, "mlx", None) or {}
        fallback_to_ollama = False

        # MLX path: no-tools only; with tools, fallback to ollama-compatible route.
        if self.provider == "mlx":
            if tools:
                fallback = mlx_cfg.get("fallback_for_tools", "ollama")
                if fallback == "ollama":
                    fallback_to_ollama = True
                    target_model = f"ollama/{target_model}" if "/" not in target_model else target_model
            else:
                model_id = (model or mlx_cfg.get("model_id") or "mlx-community/Qwen3.5-9B-4bit").strip()
                if "/" not in model_id and mlx_cfg.get("model_id"):
                    model_id = mlx_cfg.get("model_id")
                return _chat_completion_mlx(messages, model_id, temperature=temperature)

        target_model = _normalize_target_model(self.provider, target_model)

        # Ollama (and MLX→Ollama): always use OpenAI-compatible endpoint — avoids LiteLLM Ollama tool bugs / error-in-content.
        if self.provider == "ollama" or fallback_to_ollama:
            return _ollama_chat_via_openai_sdk(
                messages,
                target_model=target_model,
                tools=tools,
                temperature=temperature,
                timeout_sec=req_timeout,
                response_format=response_format,
            )

        kwargs = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "timeout": req_timeout,
            "num_retries": settings.llm.max_retries,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        if target_model.startswith("ollama/"):
            kwargs["api_base"] = settings.llm.ollama.get("api_base", "http://localhost:11434")

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        try:
            response = completion(**kwargs)
            return response.choices[0].message
        except Exception as e:
            raise LLMCompletionError(f"LiteLLM completion failed (model={target_model!r}): {e}") from e
