"""FlexConfig LoRA Training Script.

Trains a LoRA adapter for configuration file generation.
Target: Qwen2.5-Coder-7B-Instruct base model.

Usage:
    python -m flexbox.training.train_flexconfig \
        --dataset path/to/config_dataset.jsonl \
        --output adapters/flexconfig \
        --epochs 3 \
        --lr 2e-4
"""

import argparse
import json
from pathlib import Path
from typing import Optional

from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer


CONFIG_SYSTEM_PROMPT = """You are a configuration specialist. Generate valid, properly formatted:
- JSON/YAML/TOML configuration files
- Environment variable files (.env)
- Build tool configs (webpack, vite, rollup)
- Package manifests (package.json, pyproject.toml)
Output only the code, no explanations."""


def load_dataset_from_jsonl(path: str) -> Dataset:
    """Load training data from JSONL format."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            data.append({
                "messages": [
                    {"role": "system", "content": CONFIG_SYSTEM_PROMPT},
                    {"role": "user", "content": entry["prompt"]},
                    {"role": "assistant", "content": entry["completion"]},
                ]
            })
    return Dataset.from_list(data)


def create_sample_dataset() -> Dataset:
    """Create a small sample dataset for testing."""
    samples = [
        {
            "messages": [
                {"role": "system", "content": CONFIG_SYSTEM_PROMPT},
                {"role": "user", "content": "Create a Next.js project with TypeScript and Tailwind"},
                {"role": "assistant", "content": """{
  "name": "my-nextjs-app",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.0.1",
    "eslint": "^8",
    "eslint-config-next": "14.2.0",
    "postcss": "^8",
    "tailwindcss": "^3.3.0",
    "typescript": "^5"
  }
}"""},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": CONFIG_SYSTEM_PROMPT},
                {"role": "user", "content": "Configure Vite with React and path aliases"},
                {"role": "assistant", "content": """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@styles': path.resolve(__dirname, './src/styles'),
    },
  },
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});"""},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": CONFIG_SYSTEM_PROMPT},
                {"role": "user", "content": "Create environment variables for a React app with API keys"},
                {"role": "assistant", "content": """# App Configuration
REACT_APP_NAME=MyApp
REACT_APP_VERSION=1.0.0

# API Configuration
REACT_APP_API_URL=https://api.example.com/v1
REACT_APP_API_KEY=your-api-key-here

# Authentication
REACT_APP_AUTH_DOMAIN=auth.example.com
REACT_APP_AUTH_CLIENT_ID=your-client-id

# Feature Flags
REACT_APP_ENABLE_ANALYTICS=true
REACT_APP_ENABLE_NOTIFICATIONS=true

# Environment
REACT_APP_ENV=development
DEBUG=true"""},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": CONFIG_SYSTEM_PROMPT},
                {"role": "user", "content": "Create a TypeScript config with strict mode and path aliases"},
                {"role": "assistant", "content": """{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@utils/*": ["./src/utils/*"],
      "@hooks/*": ["./src/hooks/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}"""},
            ]
        },
    ]
    return Dataset.from_list(samples)


def train_flexconfig(
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    dataset_path: Optional[str] = None,
    output_dir: str = "adapters/flexconfig",
    epochs: int = 3,
    learning_rate: float = 2e-4,
    batch_size: int = 4,
    max_seq_length: int = 2048,
    rank: int = 8,
):
    """Train the FlexConfig LoRA adapter."""
    print(f"Loading base model: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype="float16",
        bnb_4bit_use_double_quant=True,
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    
    lora_config = LoraConfig(
        r=rank,
        lora_alpha=rank * 2,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        use_rslora=False,
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    if dataset_path:
        dataset = load_dataset_from_jsonl(dataset_path)
    else:
        print("Using sample dataset (provide --dataset for full training)")
        dataset = create_sample_dataset()
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=batch_size,
        learning_rate=learning_rate,
        warmup_steps=10,
        logging_steps=5,
        save_strategy="epoch",
        fp16=False,
        bf16=False,
        report_to="none",
        remove_unused_columns=False,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        max_grad_norm=0.3,
        weight_decay=0.01,
    )
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )
    
    print("Starting training...")
    trainer.train()
    
    print(f"Saving adapter to {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print("Training complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train FlexConfig LoRA adapter")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--dataset", default=None, help="JSONL dataset path")
    parser.add_argument("--output", default="adapters/flexconfig")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--rank", type=int, default=8)
    
    args = parser.parse_args()
    
    train_flexconfig(
        model_name=args.model,
        dataset_path=args.dataset,
        output_dir=args.output,
        epochs=args.epochs,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        rank=args.rank,
    )
