"""Flex Trainer - manages LoRA adapter training with HuggingFace PEFT and TRL."""

import json
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .config import TrainingConfig, LoRAConfig


@dataclass
class TrainingResult:
    """Result from a training run."""
    adapter_name: str
    adapter_path: str
    training_loss: float
    eval_loss: Optional[float]
    epochs: int
    training_time_s: float
    trainable_params: int
    total_params: int
    adapter_size_mb: float


class FlexTrainer:
    """
    Manages LoRA adapter training for Flex Box.
    
    Supports:
    - Rank=8 (fast, smaller adapters)
    - Rank=16 (higher quality, larger adapters)
    - Quantized training (4-bit)
    - Gradient checkpointing
    - Mixed precision (fp16/bf16)
    """

    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self._trainer = None
        self._model = None
        self._tokenizer = None

    def train(
        self,
        adapter_name: str,
        train_dataset,
        eval_dataset=None,
        system_prompt: str = "",
    ) -> TrainingResult:
        """
        Train a LoRA adapter.
        
        Args:
            adapter_name: Name for the adapter (flexreact, flexcss, flexconfig)
            train_dataset: Training dataset
            eval_dataset: Optional evaluation dataset
            system_prompt: System prompt for the adapter
            
        Returns:
            TrainingResult with metrics
        """
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
        )
        from peft import LoraConfig, get_peft_model, TaskType
        from trl import SFTTrainer, SFTConfig
        
        print(f"Training {adapter_name} adapter (Rank={self.config.lora.r})...")
        start_time = time.perf_counter()
        
        # Load model
        print(f"Loading base model: {self.config.base_model}")
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model,
            trust_remote_code=True,
        )
        
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        
        model_kwargs = {
            "trust_remote_code": True,
            "device_map": "auto",
        }
        
        if self.config.use_quantization:
            from transformers import BitsAndBytesConfig
            import torch
            
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        else:
            model_kwargs["torch_dtype"] = "float16"
        
        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model,
            **model_kwargs,
        )
        
        # Configure LoRA
        lora_config = LoraConfig(
            r=self.config.lora.r,
            lora_alpha=self.config.lora.lora_alpha,
            target_modules=self.config.lora.target_modules,
            lora_dropout=self.config.lora.lora_dropout,
            bias=self.config.lora.bias,
            task_type=TaskType.CAUSAL_LM,
        )
        
        self._model = get_peft_model(self._model, lora_config)
        self._model.print_trainable_parameters()
        
        # Training arguments
        adapter_dir = Path(self.config.output_dir) / adapter_name
        adapter_dir.mkdir(parents=True, exist_ok=True)
        
        training_args = SFTConfig(
            output_dir=str(adapter_dir),
            num_train_epochs=self.config.epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_ratio=self.config.warmup_ratio,
            lr_scheduler_type=self.config.lr_scheduler_type,
            max_seq_length=self.config.max_seq_length,
            logging_steps=self.config.logging_steps,
            save_strategy=self.config.save_strategy,
            eval_strategy=self.config.eval_strategy if eval_dataset else "no",
            fp16=self.config.fp16,
            bf16=self.config.bf16,
            gradient_checkpointing=self.config.gradient_checkpointing,
            report_to="none",
            seed=self.config.seed,
            dataset_text_field=None,
            packing=False,
        )
        
        # Create trainer
        self._trainer = SFTTrainer(
            model=self._model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            processing_class=self._tokenizer,
        )
        
        # Train
        print("Starting training...")
        train_result = self._trainer.train()
        
        # Save adapter
        print(f"Saving adapter to {adapter_dir}")
        self._model.save_pretrained(str(adapter_dir))
        self._tokenizer.save_pretrained(str(adapter_dir))
        
        # Calculate adapter size
        adapter_size = self._calculate_adapter_size(adapter_dir)
        
        # Get metrics
        trainable_params = sum(p.numel() for p in self._model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in self._model.parameters())
        
        elapsed = time.perf_counter() - start_time
        
        result = TrainingResult(
            adapter_name=adapter_name,
            adapter_path=str(adapter_dir),
            training_loss=train_result.training_loss,
            eval_loss=None,
            epochs=self.config.epochs,
            training_time_s=elapsed,
            trainable_params=trainable_params,
            total_params=total_params,
            adapter_size_mb=adapter_size,
        )
        
        print(f"Training complete in {elapsed:.1f}s")
        print(f"Adapter saved to: {adapter_dir}")
        print(f"Adapter size: {adapter_size:.2f} MB")
        
        return result

    def _calculate_adapter_size(self, adapter_dir: Path) -> float:
        """Calculate total size of adapter files in MB."""
        total_bytes = 0
        
        for file in adapter_dir.iterdir():
            if file.is_file():
                total_bytes += file.stat().st_size
        
        return total_bytes / (1024 * 1024)

    def cleanup(self):
        """Free memory after training."""
        if self._trainer is not None:
            del self._trainer
            self._trainer = None
        
        if self._model is not None:
            del self._model
            self._model = None
        
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        import gc
        gc.collect()


def train_all_adapters(
    config: Optional[TrainingConfig] = None,
    datasets: Optional[dict] = None,
) -> list[TrainingResult]:
    """
    Train all three adapters (flexreact, flexcss, flexconfig).
    
    Args:
        config: Training configuration
        datasets: Dict of {adapter_name: (train_dataset, eval_dataset)}
        
    Returns:
        List of TrainingResult for each adapter
    """
    if config is None:
        config = TrainingConfig()
    
    results = []
    
    adapter_names = ["flexreact", "flexcss", "flexconfig"]
    
    for adapter_name in adapter_names:
        trainer = FlexTrainer(config)
        
        try:
            if datasets and adapter_name in datasets:
                train_data, eval_data = datasets[adapter_name]
            else:
                # Use default sample data
                train_data = _get_default_dataset(adapter_name)
                eval_data = None
            
            result = trainer.train(
                adapter_name=adapter_name,
                train_dataset=train_data,
                eval_dataset=eval_data,
            )
            results.append(result)
            
        finally:
            trainer.cleanup()
    
    return results


def _get_default_dataset(adapter_name: str):
    """Get default dataset for an adapter."""
    from datasets import Dataset
    
    # Default prompts for each adapter type
    defaults = {
        "flexreact": [
            {"prompt": "Create a button component", "completion": "export const Button = () => <button>Click</button>"},
        ],
        "flexcss": [
            {"prompt": "Style a card with shadow", "completion": "<div className='shadow-lg rounded-lg p-4'>"},
        ],
        "flexconfig": [
            {"prompt": "Create package.json", "completion": '{"name": "app", "version": "1.0.0"}'},
        ],
    }
    
    data = defaults.get(adapter_name, defaults["flexreact"])
    return Dataset.from_list(data)
