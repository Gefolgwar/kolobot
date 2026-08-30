import torch
from transformers import AutoModel, AutoTokenizer, BitsAndBytesConfig

model_name = 'baidu/Unlimited-OCR'
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

# Try 4-bit quantization to fit into 4GB VRAM
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

print("Loading model with accelerate and bitsandbytes (4-bit)...")
model = AutoModel.from_pretrained(
    model_name,
    trust_remote_code=True,
    use_safetensors=True,
    device_map="auto",
    quantization_config=quantization_config,
    low_cpu_mem_usage=True
)
model = model.eval()
print("Model loaded successfully!")
print(f"Model device mapping: {model.hf_device_map}")
