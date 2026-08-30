import sys
import trace

def main():
    import torch
    from transformers import AutoModel, AutoTokenizer
    print("Loading...")
    model_name = 'baidu/Unlimited-OCR'
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        model_name,
        trust_remote_code=True,
        use_safetensors=True,
        torch_dtype=torch.float32,
    )
    print("Loaded")

tracer = trace.Trace(count=False, trace=True, ignoredirs=[sys.prefix, sys.exec_prefix])
# We will just run it directly to see if we can catch the last line printed
if __name__ == '__main__':
    main()
