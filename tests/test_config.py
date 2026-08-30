"""Config load behavior: fail fast on missing required env, no secrets hardcoded."""

from __future__ import annotations

import pytest

from kolobot.config import ConfigError, load_config


def test_load_config_fails_when_bot_token_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("OWNER_USER_ID", "42")
    monkeypatch.setenv("GEMINI_KEYS_GENERATE", "k1")
    monkeypatch.setenv("GEMINI_KEYS_EMBED", "k2")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("DOWNLOADS_PATH", str(tmp_path / "dl"))

    with pytest.raises(ConfigError, match="BOT_TOKEN"):
        load_config(dotenv_path="")


def test_load_config_fails_when_owner_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_TOKEN", "token-xyz")
    monkeypatch.delenv("OWNER_USER_ID", raising=False)
    monkeypatch.setenv("GEMINI_KEYS_GENERATE", "k1")
    monkeypatch.setenv("GEMINI_KEYS_EMBED", "k2")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("DOWNLOADS_PATH", str(tmp_path / "dl"))

    with pytest.raises(ConfigError, match="OWNER_USER_ID"):
        load_config(dotenv_path="")


def test_load_config_returns_settings_with_defaults(monkeypatch, tmp_path):
    chroma = tmp_path / "chroma"
    downloads = tmp_path / "dl"
    monkeypatch.setenv("BOT_TOKEN", "token-xyz")
    monkeypatch.setenv("OWNER_USER_ID", "99")
    monkeypatch.setenv("GEMINI_KEYS_GENERATE", "g1, g2")
    monkeypatch.setenv("GEMINI_KEYS_EMBED", "e1")
    monkeypatch.setenv("CHROMA_PATH", str(chroma))
    monkeypatch.setenv("DOWNLOADS_PATH", str(downloads))
    monkeypatch.setenv("AI_PROVIDER", "google")
    for key in (
        "RPM_LIMIT",
        "RPD_LIMIT",
        "COOLDOWN_SEC",
        "RAG_TOP_K",
        "RAG_MAX_DISTANCE",
        "CONFIRM_TIMEOUT_SEC",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = load_config(dotenv_path="")

    assert settings.bot_token == "token-xyz"
    assert settings.owner_user_id == 99
    assert settings.gemini_keys_generate == ["g1", "g2"]
    assert settings.gemini_keys_embed == ["e1"]
    assert settings.chroma_path == str(chroma)
    assert settings.downloads_path == str(downloads)
    assert settings.rpm_limit == 15
    assert settings.rpd_limit == 1500
    assert settings.cooldown_sec == 60
    assert settings.rag_top_k == 3
    assert settings.confirm_timeout_sec == 600


def test_load_config_fails_on_empty_generate_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_TOKEN", "token-xyz")
    monkeypatch.setenv("OWNER_USER_ID", "99")
    monkeypatch.setenv("GEMINI_KEYS_GENERATE", "  ,  ")
    monkeypatch.setenv("GEMINI_KEYS_EMBED", "e1")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("DOWNLOADS_PATH", str(tmp_path / "dl"))
    monkeypatch.setenv("AI_PROVIDER", "google")

    with pytest.raises(ConfigError, match="GEMINI_KEYS_GENERATE"):
        load_config(dotenv_path="")


def test_build_app_wires_nvidia_client(monkeypatch, tmp_path):
    from kolobot.gemini_gateway import NvidiaClient
    from kolobot.main import build_app

    monkeypatch.setenv("BOT_TOKEN", "123456:ABC-DEF")
    monkeypatch.setenv("OWNER_USER_ID", "99")
    monkeypatch.setenv("GEMINI_KEYS_GENERATE", "g1")
    monkeypatch.setenv("GEMINI_KEYS_EMBED", "e1")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("DOWNLOADS_PATH", str(tmp_path / "dl"))
    monkeypatch.setenv("AI_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_GENERATE_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-secret")

    dp, bot, settings = build_app()

    assert settings.ai_provider == "nvidia"
    assert settings.nvidia_generate_model == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    assert settings.nvidia_api_key == "nvapi-secret"


def test_load_config_nvidia_without_gemini_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("BOT_TOKEN", "123456:ABC-DEF")
    monkeypatch.setenv("OWNER_USER_ID", "99")
    monkeypatch.delenv("GEMINI_KEYS_GENERATE", raising=False)
    monkeypatch.delenv("GEMINI_KEYS_EMBED", raising=False)
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("DOWNLOADS_PATH", str(tmp_path / "dl"))
    monkeypatch.setenv("AI_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-secret")

    settings = load_config(dotenv_path="")

    assert settings.ai_provider == "nvidia"
    assert settings.gemini_keys_generate == ["nvapi-secret"]
    assert settings.gemini_keys_embed == ["nvapi-secret"]
