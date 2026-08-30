"""Unit tests for GeminiGateway and GoogleGenAIClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kolobot.gemini_gateway import (
    GeminiError,
    GeminiGateway,
    GoogleGenAIClient,
)
from kolobot.key_pool import KeyPool, PoolKind


@pytest.fixture
def gen_pool():
    return KeyPool(keys=["gen_key_1"], kind=PoolKind.GENERATE)


@pytest.fixture
def emb_pool():
    return KeyPool(keys=["emb_key_1"], kind=PoolKind.EMBED)


def test_gateway_default_client(gen_pool, emb_pool):
    gateway = GeminiGateway(gen_pool=gen_pool, emb_pool=emb_pool)
    assert isinstance(gateway._client, GoogleGenAIClient)


@pytest.mark.asyncio
async def test_extract_document_success(gen_pool, emb_pool):
    mock_client = AsyncMock()
    mock_client.extract.return_value = '{"title": "Test"}'
    gateway = GeminiGateway(
        gen_pool=gen_pool,
        emb_pool=emb_pool,
        client=mock_client,
        generate_model="gemini-2.5-flash",
    )

    res = await gateway.extract_document(b"fake_image", "image/jpeg")

    assert res == '{"title": "Test"}'
    mock_client.extract.assert_awaited_once_with(
        "gen_key_1", b"fake_image", "image/jpeg", "gemini-2.5-flash"
    )


@pytest.mark.asyncio
async def test_extract_document_error_releases_key(gen_pool, emb_pool):
    mock_client = AsyncMock()
    err = Exception("API error")
    err.status_code = 429
    mock_client.extract.side_effect = err

    gateway = GeminiGateway(gen_pool=gen_pool, emb_pool=emb_pool, client=mock_client)

    with pytest.raises(GeminiError):
        await gateway.extract_document(b"fake_image", "image/jpeg")

    assert gen_pool.status()["cooldown"] == 1


@pytest.mark.asyncio
async def test_embed_texts_success(gen_pool, emb_pool):
    mock_client = AsyncMock()
    mock_client.embed.return_value = [[0.1, 0.2, 0.3]]
    gateway = GeminiGateway(gen_pool=gen_pool, emb_pool=emb_pool, client=mock_client)

    res = await gateway.embed_texts(["hello"])

    assert res == [[0.1, 0.2, 0.3]]
    mock_client.embed.assert_awaited_once_with("emb_key_1", ["hello"], "text-embedding-004")


@pytest.mark.asyncio
async def test_answer_with_context_success(gen_pool, emb_pool):
    mock_client = AsyncMock()
    mock_client.answer.return_value = "Answer text"
    gateway = GeminiGateway(
        gen_pool=gen_pool,
        emb_pool=emb_pool,
        client=mock_client,
        generate_model="gemini-2.5-flash",
    )

    res = await gateway.answer_with_context("Q?", ["ctx1"])

    assert res == "Answer text"
    mock_client.answer.assert_awaited_once_with("gen_key_1", "Q?", ["ctx1"], "gemini-2.5-flash")


@pytest.mark.asyncio
async def test_google_genai_client_extract():
    client = GoogleGenAIClient()
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"doc_type": "receipt"}'
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("google.genai.Client", return_value=mock_genai_client):
        res = await client.extract("key123", b"img", "image/png", "gemini-2.5-flash")

    assert res == '{"doc_type": "receipt"}'
    mock_genai_client.aio.models.generate_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_google_genai_client_embed():
    client = GoogleGenAIClient()
    mock_genai_client = MagicMock()
    mock_emb = MagicMock()
    mock_emb.values = [0.1, 0.2]
    mock_res = MagicMock()
    mock_res.embeddings = [mock_emb]
    mock_genai_client.aio.models.embed_content = AsyncMock(return_value=mock_res)

    with patch("google.genai.Client", return_value=mock_genai_client):
        res = await client.embed("key123", ["test"], "text-embedding-004")

    assert res == [[0.1, 0.2]]
    mock_genai_client.aio.models.embed_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_embed_texts_invalid_api_key_raises_friendly_error(gen_pool, emb_pool):
    mock_client = AsyncMock()
    err = Exception("400 INVALID_ARGUMENT. {'error': {'code': 400, 'message': 'API key not valid. Please pass a valid API key.', 'reason': 'API_KEY_INVALID'}}")
    mock_client.embed.side_effect = err

    gateway = GeminiGateway(gen_pool=gen_pool, emb_pool=emb_pool, client=mock_client)

    with pytest.raises(GeminiError) as excinfo:
        await gateway.embed_texts(["hello"])

    assert "GEMINI_KEYS_EMBED" in str(excinfo.value)
    assert emb_pool.status()["cooldown"] == 1


@pytest.mark.asyncio
async def test_extract_document_multi_key_failover():
    gen_pool = KeyPool(keys=["bad_key_1", "good_key_2"], kind=PoolKind.GENERATE)
    emb_pool = KeyPool(keys=["emb_key_1"], kind=PoolKind.EMBED)

    mock_client = AsyncMock()
    # First key fails with 400 invalid, second key succeeds
    mock_client.extract.side_effect = [
        Exception("400 API key not valid"),
        '{"doc_type": "накладна"}',
    ]

    status_updates = []

    async def _on_status(msg: str) -> None:
        status_updates.append(msg)

    gateway = GeminiGateway(
        gen_pool=gen_pool,
        emb_pool=emb_pool,
        client=mock_client,
    )

    res = await gateway.extract_document(
        b"img_bytes", "image/jpeg", on_status_update=_on_status
    )

    assert res == '{"doc_type": "накладна"}'
    assert mock_client.extract.await_count == 2
    # bad_key_1 is in cooldown
    assert gen_pool.status()["cooldown"] == 1
    # Check that status updates informed about keys
    assert any("Ключ #1" in u for u in status_updates)
    assert any("Ключ #2" in u for u in status_updates)


@pytest.mark.asyncio
async def test_embed_texts_multi_key_failover():
    gen_pool = KeyPool(keys=["gen_key_1"], kind=PoolKind.GENERATE)
    emb_pool = KeyPool(keys=["bad_emb_1", "good_emb_2"], kind=PoolKind.EMBED)

    mock_client = AsyncMock()
    mock_client.embed.side_effect = [
        Exception("429 ResourceExhausted"),
        [[0.5, 0.6]],
    ]

    status_updates = []

    async def _on_status(msg: str) -> None:
        status_updates.append(msg)

    gateway = GeminiGateway(
        gen_pool=gen_pool,
        emb_pool=emb_pool,
        client=mock_client,
    )

    res = await gateway.embed_texts(["sample text"], on_status_update=_on_status)

    assert res == [[0.5, 0.6]]
    assert mock_client.embed.await_count == 2
    assert emb_pool.status()["cooldown"] == 1
    assert any("Ключ #1" in u for u in status_updates)
    assert any("Ключ #2" in u for u in status_updates)

