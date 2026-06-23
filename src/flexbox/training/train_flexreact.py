"""FlexReact LoRA Training Script.

Trains a LoRA adapter for React/JSX code generation.
Target: Qwen2.5-Coder-7B-Instruct base model.

Usage:
    python -m flexbox.training.train_flexreact \
        --dataset path/to/react_dataset.jsonl \
        --output adapters/flexreact \
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


REACT_SYSTEM_PROMPT = """You are a React/JSX specialist. Generate clean, functional React components with:
- Proper hooks usage (useState, useEffect, useContext, etc.)
- TypeScript type definitions
- Modern component patterns
- Accessibility best practices
Output only the code, no explanations."""


def load_dataset_from_jsonl(path: str) -> Dataset:
    """Load training data from JSONL format."""
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            data.append({
                "messages": [
                    {"role": "system", "content": REACT_SYSTEM_PROMPT},
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
                {"role": "system", "content": REACT_SYSTEM_PROMPT},
                {"role": "user", "content": "Create a button component with click handler"},
                {"role": "assistant", "content": """import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  variant = 'primary',
  disabled = false,
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 rounded font-medium transition-colors ${
        variant === 'primary'
          ? 'bg-blue-500 text-white hover:bg-blue-600'
          : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {children}
    </button>
  );
};"""},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": REACT_SYSTEM_PROMPT},
                {"role": "user", "content": "Create a counter component with useState"},
                {"role": "assistant", "content": """import React, { useState } from 'react';

interface CounterProps {
  initialValue?: number;
  step?: number;
}

export const Counter: React.FC<CounterProps> = ({
  initialValue = 0,
  step = 1,
}) => {
  const [count, setCount] = useState(initialValue);

  return (
    <div className="flex items-center gap-4">
      <button
        onClick={() => setCount(prev => prev - step)}
        className="px-3 py-1 bg-red-500 text-white rounded"
      >
        -
      </button>
      <span className="text-xl font-mono">{count}</span>
      <button
        onClick={() => setCount(prev => prev + step)}
        className="px-3 py-1 bg-green-500 text-white rounded"
      >
        +
      </button>
    </div>
  );
};"""},
            ]
        },
        {
            "messages": [
                {"role": "system", "content": REACT_SYSTEM_PROMPT},
                {"role": "user", "content": "Create a todo list component with add and toggle"},
                {"role": "assistant", "content": """import React, { useState } from 'react';

interface Todo {
  id: number;
  text: string;
  completed: boolean;
}

export const TodoList: React.FC = () => {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [input, setInput] = useState('');

  const addTodo = () => {
    if (input.trim()) {
      setTodos(prev => [...prev, { id: Date.now(), text: input, completed: false }]);
      setInput('');
    }
  };

  const toggleTodo = (id: number) => {
    setTodos(prev =>
      prev.map(todo =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      )
    );
  };

  return (
    <div>
      <div className="flex gap-2 mb-4">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          className="border rounded px-2 py-1"
          placeholder="Add todo..."
        />
        <button onClick={addTodo} className="bg-blue-500 text-white px-3 py-1 rounded">
          Add
        </button>
      </div>
      <ul>
        {todos.map(todo => (
          <li
            key={todo.id}
            onClick={() => toggleTodo(todo.id)}
            className={`cursor-pointer p-2 ${todo.completed ? 'line-through text-gray-400' : ''}`}
          >
            {todo.text}
          </li>
        ))}
      </ul>
    </div>
  );
};"""},
            ]
        },
    ]
    return Dataset.from_list(samples)


def train_flexreact(
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    dataset_path: Optional[str] = None,
    output_dir: str = "adapters/flexreact",
    epochs: int = 3,
    learning_rate: float = 2e-4,
    batch_size: int = 4,
    max_seq_length: int = 2048,
    rank: int = 8,
):
    """Train the FlexReact LoRA adapter."""
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
        use_rslora=False,
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
    parser = argparse.ArgumentParser(description="Train FlexReact LoRA adapter")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--dataset", default=None, help="JSONL dataset path")
    parser.add_argument("--output", default="adapters/flexreact")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--rank", type=int, default=8)
    
    args = parser.parse_args()
    
    train_flexreact(
        model_name=args.model,
        dataset_path=args.dataset,
        output_dir=args.output,
        epochs=args.epochs,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        rank=args.rank,
    )
