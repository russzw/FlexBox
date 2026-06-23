"""Inference Engine - manages base model loading and LoRA inference."""

from __future__ import annotations

import time
from typing import Optional, Any
from dataclasses import dataclass

try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        PreTrainedModel,
        PreTrainedTokenizer,
    )
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    AutoModelForCausalLM = None
    AutoTokenizer = None
    BitsAndBytesConfig = None
    PreTrainedModel = None
    PreTrainedTokenizer = None
    TORCH_AVAILABLE = False

from .adapters import AdapterManager


@dataclass
class GenerationConfig:
    """Configuration for text generation."""
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    do_sample: bool = True
    repetition_penalty: float = 1.1


@dataclass
class InferenceResult:
    """Result from model inference."""
    text: str
    tokens_generated: int
    generation_time_ms: float
    adapter_used: Optional[str]
    tokens_per_second: float


class InferenceEngine:
    """
    Core inference engine managing base model and LoRA adapters.
    
    Supports:
    - Qwen2.5-Coder-7B-Instruct
    - DeepSeek-Coder-6.7B
    - Any HuggingFace causal LM with PEFT support
    """

    DEFAULT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        adapters_dir: str = "adapters",
        device: str = "auto",
        use_quantization: bool = True,
    ):
        self.model_name = model_name
        self.device = device
        
        self._model: Any = None
        self._tokenizer: Any = None
        self._adapter_manager = AdapterManager(adapters_dir)
        
        self.use_quantization = use_quantization
        self._loaded = False
        
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch and transformers are required. "
                "Install with: pip install torch transformers peft accelerate"
            )

    def load_model(self) -> None:
        """Load the base model into memory."""
        if self._loaded:
            return
            
        print(f"Loading base model: {self.model_name}")
        start_time = time.perf_counter()
        
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )
        
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token
        
        model_kwargs = {
            "trust_remote_code": True,
            "torch_dtype": torch.float16,
            "device_map": self.device,
        }
        
        if self.use_quantization:
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            **model_kwargs,
        )
        
        self._loaded = True
        elapsed = time.perf_counter() - start_time
        print(f"Model loaded in {elapsed:.2f}s")

    def load_adapter(self, adapter_name: str) -> None:
        """Load a LoRA adapter onto the base model."""
        if not self._loaded:
            raise RuntimeError("Base model not loaded. Call load_model() first.")
        
        self._adapter_manager.load_adapter(self._model, adapter_name)

    def swap_adapter(self, new_adapter_name: str) -> float:
        """
        Hot-swap adapter and return swap time in milliseconds.
        
        Target: < 50ms
        """
        if not self._loaded:
            raise RuntimeError("Base model not loaded.")
        
        start = time.perf_counter()
        self._adapter_manager.swap_adapter(self._model, new_adapter_name)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        return elapsed_ms

    def generate(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None,
        system_prompt: Optional[str] = None,
    ) -> InferenceResult:
        """
        Generate text from a prompt using the current adapter.
        
        Args:
            prompt: User input prompt
            config: Generation configuration
            system_prompt: Optional system context
            
        Returns:
            InferenceResult with generated text and metrics
        """
        if not self._loaded:
            raise RuntimeError("Base model not loaded. Call load_model() first.")
        
        if config is None:
            config = GenerationConfig()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        if hasattr(self._tokenizer, 'apply_chat_template') and self._tokenizer.chat_template:
            text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            text = ""
            for msg in messages:
                role = msg["role"].capitalize()
                text += f"{role}: {msg['content']}\n"
            text += "Assistant: "
        
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)
        
        start_time = time.perf_counter()
        
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=config.max_new_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                do_sample=config.do_sample,
                repetition_penalty=config.repetition_penalty,
            )
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        generated_ids = outputs[0][inputs["input_ids"].shape[-1]:]
        generated_text = self._tokenizer.decode(
            generated_ids, 
            skip_special_tokens=True
        )
        
        tokens_generated = len(generated_ids)
        tokens_per_second = (tokens_generated / elapsed_ms * 1000) if elapsed_ms > 0 else 0
        
        return InferenceResult(
            text=generated_text,
            tokens_generated=tokens_generated,
            generation_time_ms=elapsed_ms,
            adapter_used=self._adapter_manager.current_adapter,
            tokens_per_second=tokens_per_second,
        )

    def unload(self) -> None:
        """Unload model and free memory."""
        self._adapter_manager.unload_adapter()
        
        if self._model is not None:
            del self._model
            self._model = None
        
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def adapter_manager(self) -> AdapterManager:
        return self._adapter_manager

    @property
    def current_adapter(self) -> Optional[str]:
        return self._adapter_manager.current_adapter
