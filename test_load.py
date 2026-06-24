import sys
sys.path.insert(0, 'src')
import torch
print(f"PyTorch: {torch.__version__}")
print(f"GPU available: {torch.cuda.is_available()}")

print("Loading tokenizer...")
tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")
print("Tokenizer loaded")

print("Loading model (this takes a while on CPU, ~10GB RAM needed)...")
from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    torch_dtype=torch.float32,
)
print("Model loaded successfully!")
