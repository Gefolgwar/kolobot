"""Application configuration loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_user_id: int
    gemini_keys_generate: List[str]
    gemini_keys_embed: List[str]
    chroma_path: str
    downloads_path: str
    rpm_limit: int = 15
    rpd_limit: int = 1500
    cooldown_sec: int = 60
    rag_top_k: int = 3
    rag_max_distance: float = 1.2
    confirm_timeout_sec: int = 600
    generate_model: str = "gemini-2.0-flash"
    embed_model: str = "text-embedding-004"
    ai_provider: str = "google"
    nvidia_generate_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nvidia_embed_model: str = "nvidia/nemotron-3-embed-1b"
    nvidia_api_key: str = ""
    warehouse_db_path: str = ""
    web_enabled: bool = True
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    use_qwen3_vl: bool = False
    use_gmodel: bool = False


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        raise ConfigError(f"Missing required config: {name}")
    return str(value).strip().strip("'\"")


def _parse_key_list(name: str, optional: bool = False, default_key: str = "") -> List[str]:
    raw = os.getenv(name)
    if raw is None:
        if optional:
            return [default_key] if default_key else []
        raise ConfigError(f"Missing required config: {name}")
    keys = [part.strip().strip("'\"") for part in str(raw).split(",") if part.strip().strip("'\"")]
    if not keys:
        raise ConfigError(f"Missing required config: {name}")
    return keys


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError as exc:
        raise ConfigError(f"Invalid integer for {name}: {raw!r}") from exc


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError as exc:
        raise ConfigError(f"Invalid float for {name}: {raw!r}") from exc


def load_config(*, dotenv_path: str | None = None) -> Settings:
    """Load and validate settings. Fails fast on missing secrets/paths."""
    if dotenv_path != "":
        load_dotenv(dotenv_path=dotenv_path, override=False)

    owner_raw = _require("OWNER_USER_ID")
    try:
        owner_user_id = int(owner_raw)
    except ValueError as exc:
        raise ConfigError(f"Invalid OWNER_USER_ID: {owner_raw!r}") from exc

    web_enabled_raw = os.getenv("WEB_ENABLED", "true").strip().lower()
    web_enabled = web_enabled_raw not in ("0", "false", "no", "off")
    web_host = os.getenv("WEB_HOST", "127.0.0.1").strip() or "127.0.0.1"
    web_port = _int_env("WEB_PORT", 8000)

    ai_provider = os.getenv("AI_PROVIDER", "google").strip().lower() or "google"
    nvidia_api_key = os.getenv("NVIDIA_API_KEY", "").strip().strip("'\"")
    if ai_provider == "nvidia":
        if not nvidia_api_key:
            raise ConfigError("Missing required config: NVIDIA_API_KEY when AI_PROVIDER=nvidia")
        gemini_keys_gen = [nvidia_api_key]
        gemini_keys_emb = [nvidia_api_key]
    else:
        gemini_keys_gen = _parse_key_list("GEMINI_KEYS_GENERATE")
        gemini_keys_emb = _parse_key_list("GEMINI_KEYS_EMBED")

    chroma_path = _require("CHROMA_PATH")
    downloads_path = _require("DOWNLOADS_PATH")
    warehouse_db_path = os.getenv("WAREHOUSE_DB_PATH", "").strip()
    if not warehouse_db_path:
        warehouse_db_path = str(Path(chroma_path).parent / "warehouse.db")

    return Settings(
        bot_token=_require("BOT_TOKEN"),
        owner_user_id=owner_user_id,
        gemini_keys_generate=gemini_keys_gen,
        gemini_keys_embed=gemini_keys_emb,
        chroma_path=chroma_path,
        downloads_path=downloads_path,
        warehouse_db_path=warehouse_db_path,
        rpm_limit=_int_env("RPM_LIMIT", 15),
        rpd_limit=_int_env("RPD_LIMIT", 1500),
        cooldown_sec=_int_env("COOLDOWN_SEC", 60),
        rag_top_k=_int_env("RAG_TOP_K", 3),
        rag_max_distance=_float_env("RAG_MAX_DISTANCE", 1.2),
        confirm_timeout_sec=_int_env("CONFIRM_TIMEOUT_SEC", 600),
        generate_model=os.getenv("GEMINI_GENERATE_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash",
        embed_model=os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004").strip() or "text-embedding-004",
        ai_provider=ai_provider,
        nvidia_generate_model=os.getenv("NVIDIA_GENERATE_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning").strip() or "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        nvidia_embed_model=os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nemotron-3-embed-1b").strip() or "nvidia/nemotron-3-embed-1b",
        nvidia_api_key=nvidia_api_key,
        web_enabled=web_enabled,
        web_host=web_host,
        web_port=web_port,
    )
