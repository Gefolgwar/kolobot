import sys
import torch
from transformers import AutoModel, AutoTokenizer

model_name = 'baidu/Unlimited-OCR'
print("loading tokenizer", flush=True)
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
print("loading model", flush=True)
model = AutoModel.from_pretrained(
    model_name,
    trust_remote_code=True,
    use_safetensors=True,
    torch_dtype=torch.float16,
)
print("calling eval", flush=True)
model = model.eval()
print("calling cuda", flush=True)
model = model.cuda()

print("Model loaded with float16. Testing infer...", flush=True)
try:
    model.infer(
        tokenizer,
        prompt='<image>document parsing.',
        image_file='your_image.jpg',
        output_path='.',
        base_size=1024, image_size=640, crop_mode=True,
        max_length=10,
        save_results=False,
    )
    print("Infer success!", flush=True)
except Exception as e:
    print(f"Exception: {e}", flush=True)
