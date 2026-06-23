"""LoRA Adapter Manager - handles loading, caching, and hot-swapping of adapters."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass

try:
    from peft import PeftModel, LoraConfig, get_peft_model
    from transformers import PreTrainedModel
    PEFT_AVAILABLE = True
except ImportError:
    PeftModel = None
    LoraConfig = None
    get_peft_model = None
    PreTrainedModel = None
    PEFT_AVAILABLE = False


@dataclass
class AdapterInfo:
    """Metadata about a loaded adapter."""
    name: str
    path: Path
    rank: int
    loaded: bool = False
    load_time_ms: float = 0.0


class AdapterManager:
    """
    Manages LoRA adapter lifecycle: loading, swapping, and unloading.
    
    Adapters are stored in the adapters/ directory with structure:
    adapters/
    ├── flexreact/
    │   ├── adapter_config.json
    │   └── adapter_model.bin
    ├── flexcss/
    │   ├── adapter_config.json
    │   └── adapter_model.bin
    └── flexconfig/
        ├── adapter_config.json
        └── adapter_model.bin
    """

    SUPPORTED_ADAPTERS = {"flexreact", "flexcss", "flexconfig"}

    def __init__(self, adapters_dir: str = "adapters"):
        self.adapters_dir = Path(adapters_dir)
        self.adapters_dir.mkdir(parents=True, exist_ok=True)
        
        self._loaded_adapter: Optional[str] = None
        self._adapter_cache: dict[str, AdapterInfo] = {}
        self._peft_model: Optional[PeftModel] = None
        
        self._scan_adapters()

    def _scan_adapters(self):
        """Scan adapters directory and register available adapters."""
        for adapter_name in self.SUPPORTED_ADAPTERS:
            adapter_path = self.adapters_dir / adapter_name
            if adapter_path.exists():
                config_path = adapter_path / "adapter_config.json"
                if config_path.exists():
                    self._adapter_cache[adapter_name] = AdapterInfo(
                        name=adapter_name,
                        path=adapter_path,
                        rank=8  
                    )

    def list_adapters(self) -> list[AdapterInfo]:
        """List all available adapters."""
        return list(self._adapter_cache.values())

    def is_adapter_available(self, name: str) -> bool:
        """Check if an adapter exists and is ready to load."""
        return name.lower() in self._adapter_cache

    def load_adapter(
        self, 
        base_model: PreTrainedModel, 
        adapter_name: str
    ) -> PeftModel:
        """
        Load a LoRA adapter onto the base model.
        
        Args:
            base_model: The base transformer model
            adapter_name: Name of adapter to load (flexreact, flexcss, flexconfig)
            
        Returns:
            PeftModel with adapter applied
            
        Raises:
            ValueError: If adapter not found
        """
        adapter_name = adapter_name.lower()
        
        if adapter_name not in self._adapter_cache:
            raise ValueError(
                f"Adapter '{adapter_name}' not found. "
                f"Available: {list(self._adapter_cache.keys())}"
            )
        
        adapter_info = self._adapter_cache[adapter_name]
        
        start_time = time.perf_counter()
        
        if self._peft_model is not None:
            self._peft_model = self._peft_model.unload()
        
        adapter_path = str(adapter_info.path)
        
        if adapter_path_exists(adapter_path):
            self._peft_model = PeftModel.from_pretrained(
                base_model, 
                adapter_path,
                adapter_name=adapter_name
            )
        else:
            lora_config = LoraConfig(
                r=adapter_info.rank,
                lora_alpha=adapter_info.rank * 2,
                target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
                lora_dropout=0.05,
                bias="none",
                task_type="CAUSAL_LM",
            )
            self._peft_model = get_peft_model(base_model, lora_config)
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        adapter_info.loaded = True
        adapter_info.load_time_ms = elapsed_ms
        
        self._loaded_adapter = adapter_name
        
        return self._peft_model

    def swap_adapter(
        self, 
        base_model: PreTrainedModel, 
        new_adapter_name: str
    ) -> PeftModel:
        """
        Hot-swap from current adapter to a new one.
        
        Target: < 50ms swap time
        """
        if self._loaded_adapter == new_adapter_name:
            return self._peft_model
        
        return self.load_adapter(base_model, new_adapter_name)

    def unload_adapter(self) -> None:
        """Unload the current adapter."""
        if self._peft_model is not None:
            self._peft_model = self._peft_model.unload()
            self._peft_model = None
        
        if self._loaded_adapter:
            self._adapter_cache[self._loaded_adapter].loaded = False
            self._loaded_adapter = None

    @property
    def current_adapter(self) -> Optional[str]:
        """Name of currently loaded adapter."""
        return self._loaded_adapter

    @property
    def peft_model(self) -> Optional[PeftModel]:
        """Currently loaded PeftModel instance."""
        return self._peft_model


def adapter_path_exists(path: str) -> bool:
    """Check if adapter path contains actual weights."""
    adapter_path = Path(path)
    return (
        adapter_path.exists() 
        and (adapter_path / "adapter_model.bin").exists() 
        or (adapter_path / "adapter_model.safetensors").exists()
    )
