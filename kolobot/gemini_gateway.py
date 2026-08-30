"""GeminiGateway: thin adapter over google-genai for OCR, embed, RAG answer."""

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


class NvidiaClient:
    """Client for NVIDIA NIM / OpenAI-compatible chat completions and embeddings API."""

    def __init__(
        self,
        endpoint_url: str = "https://integrate.api.nvidia.com/v1/chat/completions",
        embed_endpoint_url: str = "https://integrate.api.nvidia.com/v1/embeddings",
    ) -> None:
        self.endpoint_url = endpoint_url
        self.embed_endpoint_url = embed_endpoint_url

    async def extract(self, key: str, image_bytes: bytes, mime: str, model: str) -> str:
        import base64
        import aiohttp

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime};base64,{b64_img}"

        prompt = (
            "Extract structured metadata and full text from this image. "
            "Return JSON with the following schema:\n"
            "{\n"
            '  "doc_type": "receipt|invoice|contract|id_card|note|other",\n'
            '  "title": "Short title describing the document",\n'
            '  "summary": "Brief 1-2 sentence summary of content, including key amounts and main items/services if present",\n'
            '  "key_value_pairs": [{"key": "Field name", "value": "Field value"}],\n'
            '  "raw_text": "Full transcribed text from image",\n'
            '  "language": "uk|en|ru|other",\n'
            '  "doc_number": "Document number if present (e.g. 3, INV-001)",\n'
            '  "doc_date": "Document date in DD.MM.YYYY format if present",\n'
            '  "items": [{"num": 1, "name": "Item name", "quantity": "10", "unit": "шт", "price_no_vat": "150.00", "total_no_vat": "1500.00"}],\n'
            '  "totals": {"total_no_vat": "1975.00", "vat": "395.00", "total_with_vat": "2370.00"}\n'
            "}\n\n"
            "IMPORTANT FOR key_value_pairs:\n"
            "- Prioritize CRITICAL business facts FIRST: Total Amount (Сума), Date (Дата), Main Items/Products with quantities (Товари/Послуги), Document Number, Main Parties (Supplier/Buyer).\n"
            "- DO NOT fill slots with secondary boilerplate (phone numbers, addresses, IBAN/bank details) before main items and totals.\n"
            "- Extract key-value pairs in Ukrainian if the document is in Ukrainian.\n\n"
            "IMPORTANT FOR items and totals:\n"
            "- Extract ALL line items from tables/lists in the document with their number, name, quantity, unit, price and total.\n"
            "- Extract totals: total without VAT, VAT amount, total with VAT.\n"
            "- If no table/items found, return empty arrays/objects."
        )

        clean_key = key.strip().strip("'\"")
        if clean_key.lower().startswith("bearer "):
            clean_key = clean_key[7:].strip().strip("'\"")

        headers = {
            "Authorization": f"Bearer {clean_key}",
            "Accept": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.2,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    if resp.status in (429, 503):
                        from kolobot.hardening import RetryableAPIError
                        raise RetryableAPIError(f"NVIDIA API error HTTP {resp.status}: {text}")
                    raise RuntimeError(f"NVIDIA API error HTTP {resp.status}: {text}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"] or ""

    async def embed(self, key: str, texts: List[str], model: str) -> List[List[float]]:
        import aiohttp

        clean_key = key.strip().strip("'\"")
        if clean_key.lower().startswith("bearer "):
            clean_key = clean_key[7:].strip().strip("'\"")

        # NVIDIA nv-embedqa-e5-v5 has a 512-token limit (~500 chars for Cyrillic text)
        max_chars = 500
        safe_texts = [t[:max_chars] if len(t) > max_chars else t for t in texts]

        headers = {
            "Authorization": f"Bearer {clean_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "input": safe_texts,
            "model": model,
            "input_type": "passage",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.embed_endpoint_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"NVIDIA Embeddings API error HTTP {resp.status}: {text}")
                data = await resp.json()
                embeddings = [item.get("embedding", []) for item in data.get("data", [])]
                return embeddings

    async def answer(self, key: str, question: str, contexts: List[str], model: str) -> str:
        import aiohttp

        context_block = "\n\n---\n\n".join(contexts)
        prompt = (
            "Answer the user's question based ONLY on the following provided context. "
            "If the answer cannot be determined from the context, say that you don't know based on the archive.\n\n"
            f"Context:\n{context_block}\n\n"
            f"Question: {question}"
        )

        clean_key = key.strip().strip("'\"")
        if clean_key.lower().startswith("bearer "):
            clean_key = clean_key[7:].strip().strip("'\"")

        headers = {
            "Authorization": f"Bearer {clean_key}",
            "Accept": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "max_tokens": 4096,
            "temperature": 0.2,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.endpoint_url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    if resp.status in (429, 503):
                        from kolobot.hardening import RetryableAPIError
                        raise RetryableAPIError(f"NVIDIA API error HTTP {resp.status}: {text}")
                    raise RuntimeError(f"NVIDIA API error HTTP {resp.status}: {text}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"] or ""


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
        use_qwen3_vl: bool = False,
        use_gmodel: bool = False,
    ) -> None:
        self._gen_pool = gen_pool
        self._emb_pool = emb_pool
        self._client = client if client is not None else GoogleGenAIClient()
        self._generate_model = generate_model
        self._embed_model = embed_model
        self._use_qwen3_vl = use_qwen3_vl
        self._use_gmodel = use_gmodel

    async def extract_document(self, image_bytes: bytes, mime: str, file_path: Optional[str] = None) -> str:
        from kolobot.doc_structurer import DocStructurer  # avoid circular at module level
        import tempfile
        import os
        import json

        if self._use_gmodel:
            key = await self._gen_pool.acquire(wait_sec=5)
            try:
                result = await self._client.extract(key, image_bytes, mime, self._generate_model)
                await self._gen_pool.release(key, ok=True)
                return result
            except Exception as exc:
                status = _extract_status(exc)
                await self._gen_pool.release(key, ok=False, http_status=status)
                raise

        if self._use_qwen3_vl:
            from kolobot.local_ocr import Qwen3VLService
            ocr_service = Qwen3VLService.get_instance()
        else:
            from kolobot.local_ocr import UnlimitedOCRService
            ocr_service = UnlimitedOCRService.get_instance()

        if file_path and os.path.exists(file_path):
            raw_text = await ocr_service.extract_text(file_path, mime)
        else:
            ext = ".pdf" if mime == "application/pdf" else ".png"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            try:
                raw_text = await ocr_service.extract_text(tmp_path, mime)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        return json.dumps({"raw_text": raw_text}, ensure_ascii=False)

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
                if isinstance(self._client, NvidiaClient):
                    raise GeminiError(
                        f"Помилка NVIDIA Embeddings API: {exc}. Перевірте NVIDIA_API_KEY у файлі .env."
                    ) from exc
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
                if isinstance(self._client, NvidiaClient):
                    raise GeminiError(
                        f"Помилка NVIDIA API: {exc}. Перевірте NVIDIA_API_KEY у файлі .env."
                    ) from exc
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
