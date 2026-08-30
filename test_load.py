import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

from transformers import AutoModel, AutoTokenizer
model_name = 'baidu/Unlimited-OCR'

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
print("Loading model weights to CPU...")
model = AutoModel.from_pretrained(
    model_name,
    trust_remote_code=True,
    use_safetensors=True,
    torch_dtype=torch.bfloat16,
)
print("Model loaded to CPU. Moving to eval()...")
model = model.eval()
print("Moving to CUDA...")
model = model.cuda()
print("Done!")
