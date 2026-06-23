"""FlexCSS LoRA Training Script.

Trains a LoRA adapter for CSS/Tailwind code generation.
Target: Qwen2.5-Coder-7B-Instruct base model.

Usage:
    python -m flexbox.training.train_flexcss \
        --dataset path/to/css_dataset.jsonl \
        --output adapters/flexcss \
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
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer


CSS_SYSTEM_PROMPT = """You are a CSS/Tailwind specialist. Generate responsive, modern styling using:
- Tailwind CSS utility classes
- CSS Grid and Flexbox layouts
- Responsive breakpoints (sm:, md:, lg:, xl:)
- Hover, focus, and active states
- Modern design patterns (glassmorphism, gradients, shadows)
Output only the code, no explanations."""


def load_dataset_from_jsonl(path: str) -> Dataset:
    """Load training data from JSONL format."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            data.append({
                "messages": [
                    {"role": "system", "content": CSS_SYSTEM_PROMPT},
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
                {"role": "system", "content": CSS_SYSTEM_PROMPT},
                {"role": "user", "content": "Style a hero section with gradient background"},
                {"role": "assistant", "content": """<section className="min-h-screen bg-gradient-to-br from-purple-600 via-blue-500 to-cyan-400 flex items-center justify-center relative overflow-hidden">
  <div className="absolute inset-0 bg-black/20" />
  <div className="relative z-10 text-center px-4">
    <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 drop-shadow-lg">
      Welcome
    </h1>
    <p className="text-xl text-white/90 max-w-2xl mx-auto mb-8">
      Beautiful modern design
    </p>
    <button className="px-8 py-3 bg-white text-purple-600 rounded-full font-semibold hover:bg-white/90 transition-all hover:scale-105 shadow-lg">
      Get Started
    </button>
  </div>
</section>"""},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": CSS_SYSTEM_PROMPT},
                {"role": "user", "content": "Create a responsive card grid layout"},
                {"role": "assistant", "content": """<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 p-6">
  {items.map(item => (
    <div key={item.id} className="bg-white rounded-xl shadow-md hover:shadow-xl transition-shadow duration-300 overflow-hidden group">
      <div className="relative h-48 overflow-hidden">
        <img
          src={item.image}
          alt={item.title}
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
        />
      </div>
      <div className="p-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-2">{item.title}</h3>
        <p className="text-gray-600 text-sm">{item.description}</p>
      </div>
    </div>
  ))}
</div>"""},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": CSS_SYSTEM_PROMPT},
                {"role": "user", "content": "Style a navigation bar with glassmorphism effect"},
                {"role": "assistant", "content": """<nav className="fixed top-0 left-0 right-0 z-50 bg-white/10 backdrop-blur-lg border-b border-white/20">
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div className="flex items-center justify-between h-16">
      <div className="flex-shrink-0">
        <span className="text-2xl font-bold text-white">Logo</span>
      </div>
      <div className="hidden md:block">
        <div className="flex items-center space-x-8">
          {links.map(link => (
            <a
              key={link.href}
              href={link.href}
              className="text-white/80 hover:text-white transition-colors px-3 py-2 rounded-lg hover:bg-white/10"
            >
              {link.label}
            </a>
          ))}
        </div>
      </div>
    </div>
  </div>
</nav>"""},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": CSS_SYSTEM_PROMPT},
                {"role": "user", "content": "Create a dark mode form with validation states"},
                {"role": "assistant", "content": """<form className="space-y-4 bg-gray-800 p-6 rounded-xl">
  <div>
    <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
    <input
      type="email"
      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all placeholder-gray-400"
      placeholder="you@example.com"
    />
  </div>
  <div>
    <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
    <input
      type="password"
      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
    />
    <p className="mt-1 text-sm text-green-400">Strong password</p>
  </div>
  <button
    type="submit"
    className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800"
  >
    Sign In
  </button>
</form>"""},
            ]
        },
    ]
    return Dataset.from_list(samples)


def train_flexcss(
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    dataset_path: Optional[str] = None,
    output_dir: str = "adapters/flexcss",
    epochs: int = 3,
    learning_rate: float = 2e-4,
    batch_size: int = 4,
    max_seq_length: int = 2048,
    rank: int = 8,
):
    """Train the FlexCSS LoRA adapter."""
    print(f"Loading base model: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto",
    )
    
    lora_config = LoraConfig(
        r=rank,
        lora_alpha=rank * 2,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
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
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_steps=10,
        logging_steps=5,
        save_strategy="epoch",
        fp16=False,
        bf16=False,
        report_to="none",
        remove_unused_columns=False,
    )
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        max_seq_length=max_seq_length,
    )
    
    print("Starting training...")
    trainer.train()
    
    print(f"Saving adapter to {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print("Training complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train FlexCSS LoRA adapter")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--dataset", default=None, help="JSONL dataset path")
    parser.add_argument("--output", default="adapters/flexcss")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--rank", type=int, default=8)
    
    args = parser.parse_args()
    
    train_flexcss(
        model_name=args.model,
        dataset_path=args.dataset,
        output_dir=args.output,
        epochs=args.epochs,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        rank=args.rank,
    )
