"""Unit tests for GeminiGateway and GoogleGenAIClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kolobot.gemini_gateway import (
    GeminiError,
    GeminiGateway,
    GoogleGenAIClient,
    NvidiaClient,
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
    gateway = GeminiGateway(gen_pool=gen_pool, emb_pool=emb_pool, client=mock_client)

    res = await gateway.extract_document(b"fake_image", "image/jpeg")

    assert res == '{"title": "Test"}'
    mock_client.extract.assert_awaited_once_with(
        "gen_key_1", b"fake_image", "image/jpeg", "gemini-2.0-flash"
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
    gateway = GeminiGateway(gen_pool=gen_pool, emb_pool=emb_pool, client=mock_client)

    res = await gateway.answer_with_context("Q?", ["ctx1"])

    assert res == "Answer text"
    mock_client.answer.assert_awaited_once_with("gen_key_1", "Q?", ["ctx1"], "gemini-2.0-flash")


@pytest.mark.asyncio
async def test_google_genai_client_extract():
    client = GoogleGenAIClient()
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"doc_type": "receipt"}'
    mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("google.genai.Client", return_value=mock_genai_client):
        res = await client.extract("key123", b"img", "image/png", "gemini-2.0-flash")

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
async def test_nvidia_client_extract():
    client = NvidiaClient()
    mock_post = MagicMock()
    mock_cm = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "choices": [
                {"message": {"content": '{"doc_type": "invoice", "title": "Test"}'}}
            ]
        }
    )
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_post.return_value = mock_cm

    with patch("aiohttp.ClientSession.post", mock_post):
        res = await client.extract(
            key="nvapi-testkey",
            image_bytes=b"fake_image_bytes",
            mime="image/png",
            model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        )

    assert res == '{"doc_type": "invoice", "title": "Test"}'
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer nvapi-testkey"
    assert kwargs["json"]["model"] == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


@pytest.mark.asyncio
async def test_nvidia_client_strips_prefixed_bearer():
    client = NvidiaClient()
    mock_post = MagicMock()
    mock_cm = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={"choices": [{"message": {"content": "OK"}}]}
    )
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_post.return_value = mock_cm

    with patch("aiohttp.ClientSession.post", mock_post):
        await client.answer(
            key="Bearer nvapi-testkey",
            question="Q?",
            contexts=["ctx"],
            model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        )

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer nvapi-testkey"


@pytest.mark.asyncio
async def test_nvidia_client_answer():
    client = NvidiaClient()
    mock_post = MagicMock()
    mock_cm = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "choices": [
                {"message": {"content": "Answer from Nemotron"}}
            ]
        }
    )
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_post.return_value = mock_cm

    with patch("aiohttp.ClientSession.post", mock_post):
        res = await client.answer(
            key="nvapi-testkey",
            question="What is total?",
            contexts=["Doc context text"],
            model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        )

    assert res == "Answer from Nemotron"
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer nvapi-testkey"
    assert kwargs["json"]["model"] == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


@pytest.mark.asyncio
async def test_nvidia_client_embed():
    client = NvidiaClient()
    mock_post = MagicMock()
    mock_cm = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "data": [
                {"embedding": [0.1, 0.2, 0.3]}
            ]
        }
    )
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    mock_post.return_value = mock_cm

    with patch("aiohttp.ClientSession.post", mock_post):
        res = await client.embed(
            key="nvapi-testkey",
            texts=["test text"],
            model="nvidia/nv-embedqa-e5-v5",
        )

    assert res == [[0.1, 0.2, 0.3]]
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer nvapi-testkey"
    assert kwargs["json"]["model"] == "nvidia/nv-embedqa-e5-v5"
    assert kwargs["json"]["input"] == ["test text"]


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

