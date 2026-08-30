import os
import threading
import tempfile
import asyncio
import re
import logging
import time

logger = logging.getLogger(__name__)

DET_RE = re.compile(r'<\|det\|>([^<\s]+)(?:\s*\[[^\]]*\])?\s*<\|/det\|>(.*)', re.DOTALL)

def remove_det(raw: str) -> str:
    blocks = []
    cur = None
    for line in raw.splitlines():
        line = line.rstrip()
        if not line:
            continue
        m = DET_RE.match(line)
        if m:
            category, content = m.group(1).strip(), m.group(2).strip()
            if category == 'image':
                continue
            if cur is not None:
                blocks.append(cur)
            cur = [content] if content else []
            continue
        if cur is None:
            cur = []
        cur.append(line)
    if cur is not None:
        blocks.append(cur)
    text = '\n\n'.join('\n'.join(b) for b in blocks).strip()
    return text

class UnlimitedOCRService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._loaded = False
        self._infer_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def load_model(self):
        if self._loaded:
            return
        
        with self._lock:
            if self._loaded:
                return
            import torch
            from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig
            model_name = 'baidu/Unlimited-OCR'
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float32,
                bnb_4bit_quant_type="nf4",
            )
            self.model = AutoModel.from_pretrained(
                model_name,
                trust_remote_code=True,
                use_safetensors=True,
                quantization_config=bnb_config,
                device_map="auto",
            )
            self.model = self.model.eval()
            self._patch_dtype_mismatch()
            self._loaded = True

    @staticmethod
    def _patch_dtype_mismatch():
        import torch
        orig = torch.Tensor.masked_scatter_
        def safe_masked_scatter_(self_tensor, mask, source):
            return orig(self_tensor, mask, source.to(self_tensor.dtype))
        torch.Tensor.masked_scatter_ = safe_masked_scatter_

    def _extract_text_sync(self, file_path: str, mime: str) -> str:
        self.load_model()
        import torch
        with self._infer_lock:
            with tempfile.TemporaryDirectory() as tmp_dir:
                if mime == "application/pdf":
                    import fitz
                    def pdf_to_images(pdf_path, dpi=300):
                        doc = fitz.open(pdf_path)
                        paths = []
                        mat = fitz.Matrix(dpi / 72, dpi / 72)
                        for i, page in enumerate(doc):
                            out = os.path.join(tmp_dir, f'page_{i+1:04d}.png')
                            page.get_pixmap(matrix=mat).save(out)
                            paths.append(out)
                        doc.close()
                        return paths

                    image_files = pdf_to_images(file_path, dpi=300)
                    
                    output_path = os.path.join(tmp_dir, 'out')
                    os.makedirs(output_path, exist_ok=True)
                    self.model.infer_multi(
                        self.tokenizer,
                        prompt='<image>Multi page parsing.',
                        image_files=image_files,
                        output_path=output_path,
                        image_size=1024,
                        max_length=32768,
                        no_repeat_ngram_size=35, ngram_window=1024,
                        save_results=True,
                    )

                    results = []
                    for i in range(len(image_files)):
                        md_path = os.path.join(output_path, f"page_{i+1:04d}.md")
                        if os.path.exists(md_path):
                            with open(md_path, "r", encoding="utf-8") as f:
                                results.append(remove_det(f.read()))
                    return "\n\n".join(results)
                else:
                    output_path = os.path.join(tmp_dir, 'out')
                    os.makedirs(output_path, exist_ok=True)
                    self.model.infer(
                        self.tokenizer,
                        prompt='<image>document parsing.',
                        image_file=file_path,
                        output_path=output_path,
                        base_size=1024, image_size=640, crop_mode=True,
                        max_length=32768,
                        no_repeat_ngram_size=35, ngram_window=128,
                        save_results=True,
                    )

                    filename_base = os.path.splitext(os.path.basename(file_path))[0]
                    md_path = os.path.join(output_path, f"{filename_base}.md")
                    
                    if os.path.exists(md_path):
                        with open(md_path, "r", encoding="utf-8") as f:
                            return remove_det(f.read())
                    
                    for f in os.listdir(output_path):
                        if f.endswith(".md"):
                            with open(os.path.join(output_path, f), "r", encoding="utf-8") as fp:
                                return remove_det(fp.read())
                    return ""

    async def extract_text(self, file_path: str, mime: str) -> str:
        return await asyncio.to_thread(self._extract_text_sync, file_path, mime)


QWEN3_VL_PROMPT = (
    "/no_think\n"
    "Extract structured data from this document image. "
    "Return ONLY valid JSON (no markdown fences) with this schema:\n"
    "{\n"
    '  "doc_type": "receipt|invoice|contract|id_card|note|other",\n'
    '  "title": "Short document title",\n'
    '  "summary": "1-2 sentence summary with key amounts",\n'
    '  "raw_text": "Full transcribed text from image",\n'
    '  "language": "uk|en|ru|other",\n'
    '  "doc_number": "Document number",\n'
    '  "doc_date": "Date in DD.MM.YYYY format",\n'
    '  "supplier": "Supplier or counterparty name",\n'
    '  "items": [{"num": 1, "name": "Item", "quantity": "10", "unit": "шт", "price_no_vat": "150.00", "total_no_vat": "1500.00"}],\n'
    '  "totals": {"total_no_vat": "0.00", "vat": "0.00", "total_with_vat": "0.00"}\n'
    "}\n"
    "If a field is not present in the document, use an empty string or empty array/object."
)


class Qwen3VLService:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.model = None
        self.processor = None
        self._loaded = False
        self._infer_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def load_model(self):
        if self._loaded:
            return

        with self._lock:
            if self._loaded:
                return
            import torch
            from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

            model_name = "Qwen/Qwen3-VL-2B-Instruct"
            logger.info("Qwen3-VL: loading model %s (FP16, CPU)...", model_name)
            t0 = time.perf_counter()
            self.model = Qwen3VLForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="cpu",
            )
            self.model.eval()
            self.processor = AutoProcessor.from_pretrained(model_name)
            self._loaded = True
            logger.info("Qwen3-VL: model loaded in %.1fs", time.perf_counter() - t0)

    def _process_image(self, image_path: str) -> str:
        self.load_model()
        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        logger.info("Qwen3-VL: processing image %dx%d from %s", img.width, img.height, os.path.basename(image_path))
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img},
                    {"type": "text", "text": QWEN3_VL_PROMPT},
                ],
            }
        ]

        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)
        n_input_tokens = inputs.input_ids.shape[-1]
        logger.info("Qwen3-VL: input tokens=%d, generating (max_new_tokens=8192)...", n_input_tokens)

        t0 = time.perf_counter()
        with __import__("torch").no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=8192)

        n_output_tokens = generated_ids.shape[-1] - n_input_tokens
        elapsed = time.perf_counter() - t0
        logger.info("Qwen3-VL: generated %d tokens in %.1fs (%.1f tok/s)", n_output_tokens, elapsed, n_output_tokens / elapsed if elapsed > 0 else 0)

        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return output[0] if output else ""

    def _extract_text_sync(self, file_path: str, mime: str) -> str:
        self.load_model()

        with self._infer_lock:
            if mime == "application/pdf":
                import fitz
                results = []
                doc = fitz.open(file_path)
                total = len(doc)
                logger.info("Qwen3-VL: PDF with %d pages", total)
                for i, page in enumerate(doc):
                    logger.info("Qwen3-VL: page %d/%d", i + 1, total)
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(img_bytes)
                        tmp_path = tmp.name
                    try:
                        results.append(self._process_image(tmp_path))
                    finally:
                        os.remove(tmp_path)
                doc.close()
                return "\n\n".join(results)
            else:
                return self._process_image(file_path)

    async def extract_text(self, file_path: str, mime: str) -> str:
        return await asyncio.to_thread(self._extract_text_sync, file_path, mime)
