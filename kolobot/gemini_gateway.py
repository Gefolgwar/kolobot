"""GeminiGateway: adapter over google-genai for OCR extraction, embeddings, and RAG answer."""

from __future__ import annotations

from typing import Any, List, Optional

from kolobot.key_pool import KeyPool

OCR_PROMPT = (
    "Extract structured metadata and full text from this image. "
    "Return JSON with the following schema:\n"
    "{\n"
    '  "doc_type": "receipt|invoice|contract|id_card|note|other",\n'
    '  "title": "Short title describing the document",\n'
    '  "summary": "Brief 1-2 sentence summary of content, including key amounts and main items/services if present",\n'
    '  "key_value_pairs": [{"key": "Field name", "value": "Field value"}],\n'
    '  "raw_text": "Full transcribed text from image",\n'
    '  "language": "uk|en|ru|other",\n'
    '  "nomenclature_number": "Номенклатурний номер (артикул, SKU) товару, якщо вказано в документі",\n'
    '  "item_name": "Найменування (головний товар або послуга)",\n'
    '  "doc_date": "Дата документа у форматі DD.MM.YYYY",\n'
    '  "incoming": "Прихід (кількість, що надійшла, якщо є)",\n'
    '  "outgoing": "Розхід (кількість, що витрачена, якщо є)",\n'
    '  "balance": "Залишок (якщо вказано в документі)",\n'
    '  "unit": "Одиниці виміру (шт, кг, л, тощо)",\n'
    '  "doc_number": "Номер накладної або документа (наприклад 3, INV-001)",\n'
    '  "supplier": "Постачальник або контрагент",\n'
    '  "notes": "Примітки (додаткова важлива інформація)",\n'
    '  "items": [{"num": 1, "nomenclature_number": "355513018010", "name": "Item name", "quantity": "10", "unit": "шт", "price_no_vat": "150.00", "total_no_vat": "1500.00"}],\n'
    '  "totals": {"total_no_vat": "1975.00", "vat": "395.00", "total_with_vat": "2370.00"}\n'
    "}\n\n"
    "IMPORTANT FOR INVENTORY FIELDS:\n"
    "- Extract 'nomenclature_number', 'item_name', 'doc_date', 'incoming', 'outgoing', 'balance', 'unit', 'doc_number', 'supplier', 'notes' based on the main content of the document.\n"
    "- These fields will be displayed as a single row in an inventory ledger.\n"
    "- If a field is not present, leave it as an empty string.\n\n"
    "IMPORTANT FOR items and totals:\n"
    "- Still extract ALL line items from tables/lists in the document with their number, nomenclature_number, name, quantity, unit, price and total.\n"
    "- Extract totals: total without VAT, VAT amount, total with VAT.\n"
    "- If no table/items found, return empty arrays/objects."
)


class GeminiError(RuntimeError):
    """Wrap Gemini API errors with pool-aware context."""


class GoogleGenAIClient:
    """Default production client wrapping google-genai SDK."""

    async def extract(self, key: str, image_bytes: bytes, mime: str, model: str) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
        prompt = OCR_PROMPT
        response = await client.aio.models.generate_content(
            model=model,
            contents=[part, prompt],
        )
        return response.text or ""

    async def embed(self, key: str, texts: List[str], model: str) -> List[List[float]]:
        from google import genai

        client = genai.Client(api_key=key)
        embeddings = []
        for text in texts:
            response = await client.aio.models.embed_content(
                model=model,
                contents=text,
            )
            if response.embeddings:
                embeddings.append(response.embeddings[0].values)
            else:
                embeddings.append([])
        return embeddings

    async def answer(self, key: str, question: str, contexts: List[str], model: str) -> str:
        from google import genai

        client = genai.Client(api_key=key)
        context_block = "\n\n---\n\n".join(contexts)
        prompt = (
            "Answer the user's question based ONLY on the following provided context. "
            "If the answer cannot be determined from the context, say that you don't know based on the archive.\n\n"
            f"Context:\n{context_block}\n\n"
            f"Question: {question}"
        )
        response = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
        )
        return response.text or ""


class GeminiGateway:
    """
    Thin adapter: extract_document (vision), embed_texts, answer_with_context.
    Pools injected; client injected for testability.
    """

    def __init__(
        self,
        gen_pool: KeyPool,
        emb_pool: KeyPool,
        *,
        client: Any = None,
        generate_model: str = "gemini-2.0-flash",
        embed_model: str = "text-embedding-004",
    ) -> None:
        self._gen_pool = gen_pool
        self._emb_pool = emb_pool
        self._client = client if client is not None else GoogleGenAIClient()
        self._generate_model = generate_model
        self._embed_model = embed_model

    async def extract_document(
        self, image_bytes: bytes, mime: str, file_path: Optional[str] = None
    ) -> str:
        key = await self._gen_pool.acquire(wait_sec=5)
        try:
            result = await self._call_generate(key, image_bytes, mime)
            await self._gen_pool.release(key, ok=True)
            return result
        except Exception as exc:
            status = _extract_status(exc)
            await self._gen_pool.release(key, ok=False, http_status=status)
            if status in (400, 403) or _is_key_invalid_error(exc):
                raise GeminiError(
                    "Недійсний API ключ (API key not valid). Перевірте GEMINI_KEYS_GENERATE у файлі .env."
                ) from exc
            raise GeminiError(str(exc)) from exc

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        key = await self._emb_pool.acquire(wait_sec=5)
        try:
            result = await self._call_embed(key, texts)
            await self._emb_pool.release(key, ok=True)
            return result
        except Exception as exc:
            status = _extract_status(exc)
            await self._emb_pool.release(key, ok=False, http_status=status)
            if status in (400, 403) or _is_key_invalid_error(exc):
                raise GeminiError(
                    "Недійсний API ключ для ембеддінгів (GEMINI_KEYS_EMBED). Перевірте ключ у файлі .env."
                ) from exc
            raise GeminiError(str(exc)) from exc

    async def answer_with_context(
        self, question: str, contexts: List[str]
    ) -> str:
        key = await self._gen_pool.acquire(wait_sec=5)
        try:
            result = await self._call_answer(key, question, contexts)
            await self._gen_pool.release(key, ok=True)
            return result
        except Exception as exc:
            status = _extract_status(exc)
            await self._gen_pool.release(key, ok=False, http_status=status)
            if status in (400, 403) or _is_key_invalid_error(exc):
                raise GeminiError(
                    "Недійсний API ключ (API key not valid). Перевірте GEMINI_KEYS_GENERATE у файлі .env."
                ) from exc
            raise GeminiError(str(exc)) from exc

    async def _call_generate(self, key: str, image_bytes: bytes, mime: str) -> str:
        if self._client is None:
            raise GeminiError("No Gemini client configured")
        return await self._client.extract(key, image_bytes, mime, self._generate_model)

    async def _call_embed(self, key: str, texts: List[str]) -> List[List[float]]:
        if self._client is None:
            raise GeminiError("No Gemini client configured")
        return await self._client.embed(key, texts, self._embed_model)

    async def _call_answer(self, key: str, question: str, contexts: List[str]) -> str:
        if self._client is None:
            raise GeminiError("No Gemini client configured")
        return await self._client.answer(key, question, contexts, self._generate_model)


def _extract_status(exc: Exception) -> Optional[int]:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status, int):
        return status
    msg = str(exc)
    if "400" in msg or "API_KEY_INVALID" in msg or "API key not valid" in msg:
        return 400
    if "403" in msg or "PERMISSION_DENIED" in msg:
        return 403
    if "503" in msg or "ResourceExhausted" in msg:
        return 503
    return None


def _is_key_invalid_error(exc: Exception) -> bool:
    msg = str(exc)
    return "API_KEY_INVALID" in msg or "API key not valid" in msg or "INVALID_ARGUMENT" in msg
