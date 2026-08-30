import torch
from transformers import AutoModel, AutoTokenizer

model_name = 'baidu/Unlimited-OCR'
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModel.from_pretrained(
    model_name,
    trust_remote_code=True,
    use_safetensors=True,
    torch_dtype=torch.float16,
)
model = model.eval().cuda()

print("Model loaded with float16. Testing infer...")
model.infer(
    tokenizer,
    prompt='<image>document parsing.',
    image_file='your_image.jpg',
    output_path='.',
    base_size=1024, image_size=640, crop_mode=True,
    max_length=10,
    save_results=False,
)
print("Infer success!")
