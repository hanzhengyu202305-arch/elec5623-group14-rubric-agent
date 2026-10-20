"""OpenRouter gateway wiring. No network: the transport is replaced."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from rubric_agent.gateway import OPENROUTER_URL, OpenAICompatibleGateway, build_gateway
from rubric_agent.store import gateway_spec_for

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def test_openrouter_gateway_builds_url_and_authorization_from_env():
    seen = {}

    def transport(url, headers, body, timeout):
        seen["url"] = url
        seen["authorization"] = headers.get("Authorization")
        seen["body"] = body
        return '{"choices":[{"message":{"content":"{}"}}]}'

    gw = build_gateway("openrouter", env={"RMA_OPENROUTER_API_KEY": "test-key"})
    assert isinstance(gw, OpenAICompatibleGateway)
    assert gw.endpoint == OPENROUTER_URL
    assert gw.model == "openai/gpt-4o-mini"
    assert "test-key" not in gw.name
    gw._transport = transport
    gw._chat("system", "user")
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["authorization"] == "Bearer test-key"
    assert b'"model": "openai/gpt-4o-mini"' in seen["body"]
    assert b"test-key" not in seen["body"]

    custom = build_gateway(
        "openrouter:custom/model",
        env={
            "RMA_OPENROUTER_API_KEY": "test-key",
            "RMA_OPENROUTER_MODEL": "openai/gpt-4o-mini",
            "RMA_MODEL_ENDPOINT": "https://evil.example/v1",
            "RMA_MODEL_API_KEY": "other-secret",
        },
    )
    assert custom.endpoint == "https://openrouter.ai/api/v1"
    assert custom.model == "custom/model"
    assert custom._api_key == "test-key"

    named = build_gateway("openrouter", env={"RMA_OPENROUTER_API_KEY": "test-key", "RMA_OPENROUTER_MODEL": "custom/model"})
    assert named.model == "custom/model"
    assert gateway_spec_for("custom/model@openrouter.ai") == "openrouter:custom/model"

    with pytest.raises(RuntimeError, match="RMA_OPENROUTER_API_KEY"):
        build_gateway("openrouter", env={})


def test_ui_openrouter_lists_configuration_without_showing_the_key(monkeypatch):
    monkeypatch.delenv("RMA_OPENROUTER_API_KEY", raising=False)
    missing = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not missing.exception
    labels = list(missing.sidebar.radio[0].options)
    unconfigured = next(label for label in labels if "OpenRouter" in label)
    assert "not configured" in unconfigured
    missing.sidebar.radio[0].set_value(unconfigured).run()
    missing.sidebar.button[0].click().run()
    assert not missing.exception
    assert any("RMA_OPENROUTER_API_KEY" in error.value for error in missing.error)

    monkeypatch.setenv("RMA_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("RMA_OPENROUTER_MODEL", "openai/gpt-4o-mini")
    ready = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not ready.exception
    labels = list(ready.sidebar.radio[0].options)
    assert any(label == "OpenRouter · openai/gpt-4o-mini" for label in labels)
    shown = " ".join(str(widget.value) for group in (ready.caption, ready.markdown, ready.text, ready.error) for widget in group)
    assert "test-key" not in shown
    assert all("test-key" not in label for label in labels)
