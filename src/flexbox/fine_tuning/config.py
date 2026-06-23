"""Training Configuration - defines LoRA and training hyperparameters."""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class LoRAConfig:
    """LoRA adapter configuration."""
    r: int = 8  # Rank (8 or 16 per plan)
    lora_alpha: int = 16  # Alpha scaling
    lora_dropout: float = 0.05
    target_modules: list[str] = field(default_factory=lambda: [
        "q_proj", "v_proj", "k_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


@dataclass
class TrainingConfig:
    """Full training configuration for Flex Box LoRA adapters."""
    
    # Model settings
    base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    model_dtype: str = "float16"
    use_quantization: bool = True
    quantization_bits: int = 4
    
    # LoRA settings
    lora: LoRAConfig = field(default_factory=LoRAConfig)
    
    # Training hyperparameters
    epochs: int = 3
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    lr_scheduler_type: str = "cosine"
    
    # Batch settings
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    gradient_accumulation_steps: int = 1
    
    # Sequence settings
    max_seq_length: int = 2048
    max_prompt_length: int = 1024
    
    # Output settings
    output_dir: str = "adapters"
    save_strategy: str = "epoch"
    eval_strategy: str = "epoch"
    logging_steps: int = 10
    
    # Performance settings
    fp16: bool = False
    bf16: bool = False
    gradient_checkpointing: bool = True
    
    # Data settings
    train_split: float = 0.8
    val_split: float = 0.1
    test_split: float = 0.1
    seed: int = 42
    
    def get_adapter_dir(self, adapter_name: str) -> str:
        """Get output directory for a specific adapter."""
        return str(Path(self.output_dir) / adapter_name)
    
    @classmethod
    def rank_8(cls, **kwargs) -> "TrainingConfig":
        """Create config with Rank=8 (smaller, faster)."""
        config = cls(**kwargs)
        config.lora.r = 8
        config.lora.lora_alpha = 16
        return config
    
    @classmethod
    def rank_16(cls, **kwargs) -> "TrainingConfig":
        """Create config with Rank=16 (higher quality)."""
        config = cls(**kwargs)
        config.lora.r = 16
        config.lora.lora_alpha = 32
        return config
    
    @classmethod
    def cpu_optimized(cls, **kwargs) -> "TrainingConfig":
        """Create config optimized for CPU training."""
        config = cls(**kwargs)
        config.use_quantization = False
        config.fp16 = False
        config.bf16 = False
        config.per_device_train_batch_size = 2
        config.gradient_checkpointing = False
        config.max_seq_length = 1024
        return config
