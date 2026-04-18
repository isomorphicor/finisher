"""Unit tests for ide_agent tool-call normalization (no LLM, no network)."""

from __future__ import annotations

from types import SimpleNamespace

from core.ide_agent import _function_to_dict, _tc_fn, _tool_call_to_openai_dict


def test_function_to_dict_plain_dict() -> None:
    d = _function_to_dict({"name": "workspace_read", "arguments": '{"path": "a"}'})
    assert d["name"] == "workspace_read"
    assert d["arguments"] == '{"path": "a"}'


def test_function_to_dict_dict_arguments_object() -> None:
    d = _function_to_dict({"name": "terminal_run", "arguments": {"cwd": "x", "command": "ls"}})
    assert d["name"] == "terminal_run"
    assert '"cwd"' in d["arguments"] and "x" in d["arguments"]


def test_function_to_dict_sdk_like_object() -> None:
    fn = SimpleNamespace(name="workspace_list", arguments='{"glob":"*.py"}')
    d = _function_to_dict(fn)
    assert d["name"] == "workspace_list"
    assert "glob" in d["arguments"]


def test_function_to_dict_empty_name_returns_empty() -> None:
    assert _function_to_dict({"name": "   ", "arguments": "{}"}) == {}
    assert _function_to_dict(None) == {}


def test_tool_call_to_openai_dict_from_nested_dict() -> None:
    tc = {
        "id": "abc",
        "type": "function",
        "function": {"name": "workspace_read", "arguments": '{"path":"p"}'},
    }
    out = _tool_call_to_openai_dict(tc, 0)
    assert out["id"] == "abc"
    assert out["function"]["name"] == "workspace_read"
    assert out["function"]["arguments"] == '{"path":"p"}'


def test_tc_fn_matches_tool_call_to_openai_dict() -> None:
    tc = _tool_call_to_openai_dict(
        {"id": "1", "function": {"name": "x", "arguments": "{}"}},
        0,
    )
    assert _tc_fn(tc)["name"] == "x"


def test_tool_call_to_openai_dict_sdk_like() -> None:
    tc = SimpleNamespace(
        id="call_0",
        function=SimpleNamespace(name="terminal_run", arguments='{"cwd":"."}'),
    )
    out = _tool_call_to_openai_dict(tc, 0)
    assert out["function"]["name"] == "terminal_run"
    assert "cwd" in out["function"]["arguments"]
