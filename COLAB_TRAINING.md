# Flex Box LoRA Training on Google Colab

## Quick Start

1. Open Google Colab: https://colab.research.google.com
2. Create a new notebook
3. Follow the steps below

---

## Step 1: Setup Environment (Runtime → Change runtime type → T4 GPU)

```python
# Check GPU availability
!nvidia-smi

# Install dependencies
!pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
!pip install transformers peft datasets accelerate bitsandbytes trl
```

---

## Step 2: Clone Repository & Upload Data

```python
# Clone the repo
!git clone https://github.com/YOUR_USERNAME/FlexBox.git
%cd FlexBox

# OR upload your own dataset
from google.colab import files
uploaded = files.upload()  # Upload your .jsonl training files
```

---

## Step 3: Prepare Dataset

```python
import json

# Option A: Use generated datasets from the repo
# The repo includes scripts to generate synthetic data
!python -c "
from src.flexbox.datasets.generators.react_generator import ReactGenerator
from src.flexbox.datasets.generators.css_generator import CSSGenerator
from src.flexbox.datasets.generators.config_generator import ConfigGenerator

react = ReactGenerator()
css = CSSGenerator()
config = ConfigGenerator()

react_data = react.generate(num_examples=500)
css_data = css.generate(num_examples=500)
config_data = config.generate(num_examples=500)

with open('datasets/react_train.jsonl', 'w') as f:
    for ex in react_data:
        f.write(json.dumps(ex) + '\n')

with open('datasets/css_train.jsonl', 'w') as f:
    for ex in css_data:
        f.write(json.dumps(ex) + '\n')

with open('datasets/config_train.jsonl', 'w') as f:
    for ex in config_data:
        f.write(json.dumps(ex) + '\n')

print(f'Generated {len(react_data)} React examples')
print(f'Generated {len(css_data)} CSS examples')
print(f'Generated {len(config_data)} Config examples')
"

# Option B: Upload your own dataset
# !cp /content/your_dataset.jsonl datasets/react_train.jsonl
```

---

## Step 4: Train FlexReact Adapter (Rank=8)

```python
# Train FlexReact adapter
!python train_flexreact.py \
    --model_name Qwen/Qwen2.5-Coder-7B-Instruct \
    --dataset_path datasets/react_train.jsonl \
    --output_dir adapters/flexreact \
    --num_epochs 3 \
    --batch_size 4 \
    --gradient_accumulation_steps 4 \
    --learning_rate 2e-4 \
    --lora_rank 8 \
    --warmup_steps 100 \
    --save_steps 500 \
    --logging_steps 10
```

---

## Step 5: Train FlexCSS Adapter (Rank=8)

```python
# Train FlexCSS adapter
!python train_flexcss.py \
    --model_name Qwen/Qwen2.5-Coder-7B-Instruct \
    --dataset_path datasets/css_train.jsonl \
    --output_dir adapters/flexcss \
    --num_epochs 3 \
    --batch_size 4 \
    --gradient_accumulation_steps 4 \
    --learning_rate 2e-4 \
    --lora_rank 8 \
    --warmup_steps 100 \
    --save_steps 500 \
    --logging_steps 10
```

---

## Step 6: Train FlexConfig Adapter (Rank=8)

```python
# Train FlexConfig adapter
!python train_flexconfig.py \
    --model_name Qwen/Qwen2.5-Coder-7B-Instruct \
    --dataset_path datasets/config_train.jsonl \
    --output_dir adapters/flexconfig \
    --num_epochs 3 \
    --batch_size 4 \
    --gradient_accumulation_steps 4 \
    --learning_rate 2e-4 \
    --lora_rank 8 \
    --warmup_steps 100 \
    --save_steps 500 \
    --logging_steps 10
```

---

## Step 7: Evaluate Adapters

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load base model
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    device_map="auto",
    load_in_4bit=True,
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")

# Test each adapter
adapters = ["flexreact", "flexcss", "flexconfig"]
test_prompts = [
    "Create a React button component with useState",
    "Add hover effects with Tailwind CSS",
    "Configure environment variables for API URL",
]

for adapter_name in adapters:
    print(f"\n{'='*60}")
    print(f"Testing adapter: {adapter_name}")
    print('='*60)
    
    # Load adapter
    model = PeftModel.from_pretrained(model, f"adapters/{adapter_name}")
    
    for prompt in test_prompts:
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(**inputs, max_new_tokens=200)
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"\nPrompt: {prompt}")
        print(f"Response: {response[:200]}...")
    
    # Unload adapter
    model = model.unload()
```

---

## Step 8: Download Trained Adapters

```python
# Zip adapters for download
!zip -r trained_adapters.zip adapters/flexreact adapters/flexcss adapters/flexconfig

# Download to your computer
from google.colab import files
files.download('trained_adapters.zip')
```

---

## Step 9: Upload to HuggingFace (Optional)

```python
# Upload adapters to HuggingFace Hub
!pip install huggingface_hub

from huggingface_hub import HfApi, login

# Login to HuggingFace
login()  # Enter your token

api = HfApi()

# Upload each adapter
for adapter_name in ["flexreact", "flexcss", "flexconfig"]:
    api.upload_folder(
        folder_path=f"adapters/{adapter_name}",
        repo_id=f"YOUR_USERNAME/flexbox-{adapter_name}",
        repo_type="model",
    )
    print(f"Uploaded {adapter_name}")
```

---

## Troubleshooting

### Out of Memory (OOM)
```python
# Reduce batch size and use gradient checkpointing
!python train_flexreact.py \
    --batch_size 2 \
    --gradient_accumulation_steps 8 \
    --gradient_checkpointing True \
    --fp16 True
```

### Slow Training
```python
# Enable mixed precision and flash attention
!pip install flash-attn --no-build-isolation
!python train_flexreact.py \
    --fp16 True \
    --bf16 False \
    --use_flash_attention True
```

### Dataset Issues
```python
# Verify dataset format
!head -n 2 datasets/react_train.jsonl | python -m json.tool
```

---

## Recommended Colab Settings

| Setting | Value |
|---------|-------|
| Runtime Type | GPU (T4) |
| GPU RAM | ~15GB |
| Disk | ~100GB |
| High RAM | Optional |

---

## Training Time Estimates

| Adapter | Examples | Epochs | Time (T4) |
|---------|----------|--------|-----------|
| FlexReact | 500 | 3 | ~45 min |
| FlexCSS | 500 | 3 | ~40 min |
| FlexConfig | 500 | 3 | ~35 min |
| **Total** | 1500 | 3 | **~2 hours** |

---

## Post-Training

After downloading the adapters, place them in your local `FlexBox/adapters/` directory:

```
FlexBox/
├── adapters/
│   ├── flexreact/
│   │   ├── adapter_config.json
│   │   └── adapter_model.safetensors
│   ├── flexcss/
│   │   ├── adapter_config.json
│   │   └── adapter_model.safetensors
│   └── flexconfig/
│       ├── adapter_config.json
│       └── adapter_model.safetensors
```

Then run locally:
```bash
flexbox generate "Create a React button" --adapter flexreact
```
