import torch
from transformers import AutoModel, AutoTokenizer

model_name = 'baidu/Unlimited-OCR'
print("Loading model with offload_folder...")
model = AutoModel.from_pretrained(
    model_name,
    trust_remote_code=True,
    device_map="auto",
    torch_dtype=torch.float16,
    offload_folder="offload_cache",
    offload_state_dict=True,
)
print("Model loaded successfully!")
