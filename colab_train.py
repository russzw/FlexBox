"""
Flex Box LoRA Training Script for Google Colab
Copy this into a Colab notebook cell-by-cell
"""

# ============================================================
# CELL 1: Install Dependencies
# ============================================================
# !nvidia-smi
# !pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
# !pip install transformers peft datasets accelerate bitsandbytes trl

# ============================================================
# CELL 2: Clone Repository
# ============================================================
# !git clone https://github.com/YOUR_USERNAME/FlexBox.git
# %cd FlexBox

# ============================================================
# CELL 3: Generate Training Data
# ============================================================
import json
import os
os.makedirs('datasets', exist_ok=True)

# Generate React training data
from src.flexbox.datasets.generators.react_generator import ReactGenerator
from src.flexbox.datasets.generators.css_generator import CSSGenerator
from src.flexbox.datasets.generators.config_generator import ConfigGenerator

print("Generating training data...")
react_gen = ReactGenerator()
css_gen = CSSGenerator()
config_gen = ConfigGenerator()

react_data = react_gen.generate(num_examples=500)
css_data = css_gen.generate(num_examples=500)
config_data = config_gen.generate(num_examples=500)

# Save datasets
for name, data in [('react', react_data), ('css', css_data), ('config', config_data)]:
    path = f'datasets/{name}_train.jsonl'
    with open(path, 'w') as f:
        for ex in data:
            f.write(json.dumps(ex) + '\n')
    print(f"Saved {len(data)} examples to {path}")

# ============================================================
# CELL 4: Train FlexReact Adapter
# ============================================================
# !python train_flexreact.py \
#     --model_name Qwen/Qwen2.5-Coder-7B-Instruct \
#     --dataset_path datasets/react_train.jsonl \
#     --output_dir adapters/flexreact \
#     --num_epochs 3 \
#     --batch_size 4 \
#     --gradient_accumulation_steps 4 \
#     --learning_rate 2e-4 \
#     --lora_rank 8 \
#     --warmup_steps 100 \
#     --save_steps 500 \
#     --logging_steps 10

# ============================================================
# CELL 5: Train FlexCSS Adapter
# ============================================================
# !python train_flexcss.py \
#     --model_name Qwen/Qwen2.5-Coder-7B-Instruct \
#     --dataset_path datasets/css_train.jsonl \
#     --output_dir adapters/flexcss \
#     --num_epochs 3 \
#     --batch_size 4 \
#     --gradient_accumulation_steps 4 \
#     --learning_rate 2e-4 \
#     --lora_rank 8 \
#     --warmup_steps 100 \
#     --save_steps 500 \
#     --logging_steps 10

# ============================================================
# CELL 6: Train FlexConfig Adapter
# ============================================================
# !python train_flexconfig.py \
#     --model_name Qwen/Qwen2.5-Coder-7B-Instruct \
#     --dataset_path datasets/config_train.jsonl \
#     --output_dir adapters/flexconfig \
#     --num_epochs 3 \
#     --batch_size 4 \
#     --gradient_accumulation_steps 4 \
#     --learning_rate 2e-4 \
#     --lora_rank 8 \
#     --warmup_steps 100 \
#     --save_steps 500 \
#     --logging_steps 10

# ============================================================
# CELL 7: Evaluate Adapters
# ============================================================
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    device_map="auto",
    load_in_4bit=True,
    torch_dtype=torch.float16,
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")

# Test prompts
test_cases = {
    "flexreact": [
        "Create a React button component with useState",
        "Build a navigation bar with React Router",
    ],
    "flexcss": [
        "Add hover effects with Tailwind CSS",
        "Create a gradient background",
    ],
    "flexconfig": [
        "Configure environment variables for API URL",
        "Set up ESLint configuration",
    ],
}

for adapter_name, prompts in test_cases.items():
    print(f"\n{'='*60}")
    print(f"Testing: {adapter_name}")
    print('='*60)
    
    model = PeftModel.from_pretrained(model, f"adapters/{adapter_name}")
    
    for prompt in prompts:
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=150)
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"\nPrompt: {prompt}")
        print(f"Output: {response[-200:]}")
    
    model = model.unload()

# ============================================================
# CELL 8: Download Trained Adapters
# ============================================================
# !zip -r trained_adapters.zip adapters/flexreact adapters/flexcss adapters/flexconfig

# from google.colab import files
# files.download('trained_adapters.zip')
