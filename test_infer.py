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

print("Testing infer with automatic autocast wrapper around model.infer()...")

# Try to use torch.autocast to force the model components to run in float16
with torch.autocast(device_type='cuda', dtype=torch.float16):
    model.infer(
        tokenizer,
        prompt='<image>document parsing.',
        image_file='D:\Project\kolobot\kolobot_test_data\Приклад накладної.jpg',
        output_path='.',
        base_size=1024, image_size=640, crop_mode=True,
        max_length=50,
        no_repeat_ngram_size=35, ngram_window=128,
        save_results=False,
    )
print("Infer success!")
