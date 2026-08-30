import torch
from transformers import AutoModel, AutoTokenizer
from accelerate import init_empty_weights, load_checkpoint_and_dispatch

model_name = 'baidu/Unlimited-OCR'
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

print("Testing accelerate offload (fake weights)...")
with init_empty_weights():
    model = AutoModel.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
print("Empty model built.")
