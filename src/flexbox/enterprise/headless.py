"""Headless Runtime - allows decoupling UI from inference hardware."""

import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class RuntimeMode(Enum):
    """Runtime operation modes."""
    LOCAL = "local"           # Full local inference
    REMOTE = "remote"         # Remote inference via gateway
    HYBRID = "hybrid"         # Local + remote fallback
    AIR_GAPPED = "air_gapped"  # No network access


@dataclass
class RuntimeConfig:
    """Configuration for headless runtime."""
    mode: RuntimeMode = RuntimeMode.LOCAL
    gateway_url: Optional[str] = None
    gateway_api_key: Optional[str] = None
    local_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    remote_model: Optional[str] = None
    timeout_seconds: int = 30
    retry_attempts: int = 3
    fallback_to_local: bool = True
    enable_telemetry: bool = False
    max_concurrent_requests: int = 10


@dataclass
class RequestMetrics:
    """Metrics for inference requests."""
    request_id: str
    adapter_name: str
    prompt_length: int
    response_length: int
    latency_ms: float
    model_used: str
    mode: str
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    error_message: Optional[str] = None


class HeadlessRuntime:
    """
    Headless runtime for decoupling UI from inference.
    
    Supports:
    - Local inference mode
    - Remote inference via FlexCorp Gateway
    - Hybrid mode with local fallback
    - Air-gapped operation
    - Request metrics collection
    """

    def __init__(self, config: Optional[RuntimeConfig] = None):
        self.config = config or RuntimeConfig()
        self._metrics: list[RequestMetrics] = []
        self._request_count = 0
        self._local_engine = None
        self._remote_client = None

    def initialize(self):
        """Initialize the runtime based on mode."""
        print(f"Initializing headless runtime in {self.config.mode.value} mode...")
        
        if self.config.mode in (RuntimeMode.LOCAL, RuntimeMode.HYBRID):
            self._init_local_engine()
        
        if self.config.mode in (RuntimeMode.REMOTE, RuntimeMode.HYBRID):
            self._init_remote_client()
        
        print("Headless runtime initialized")

    def _init_local_engine(self):
        """Initialize local inference engine."""
        try:
            from ..core.engine import InferenceEngine
            self._local_engine = InferenceEngine(
                model_name=self.config.local_model,
                use_quantization=True,
            )
            self._local_engine.load_model()
            print(f"Local engine loaded: {self.config.local_model}")
        except Exception as e:
            print(f"Warning: Could not load local engine: {e}")

    def _init_remote_client(self):
        """Initialize remote gateway client."""
        if not self.config.gateway_url:
            print("Warning: No gateway URL configured for remote mode")
            return
        
        self._remote_client = GatewayClient(
            gateway_url=self.config.gateway_url,
            api_key=self.config.gateway_api_key,
            timeout=self.config.timeout_seconds,
        )
        print(f"Remote client configured: {self.config.gateway_url}")

    async def infer(
        self,
        prompt: str,
        adapter_name: str = "flexreact",
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Run inference through the configured mode.
        
        Args:
            prompt: Input prompt
            adapter_name: Adapter to use
            system_prompt: Optional system context
            
        Returns:
            Generated text
        """
        request_id = f"req_{self._request_count}"
        self._request_count += 1
        
        start_time = time.perf_counter()
        model_used = "unknown"
        success = True
        error_message = None
        response = ""
        
        try:
            if self.config.mode == RuntimeMode.LOCAL:
                response = await self._local_infer(prompt, adapter_name, system_prompt)
                model_used = self.config.local_model
                
            elif self.config.mode == RuntimeMode.REMOTE:
                response = await self._remote_infer(prompt, adapter_name, system_prompt)
                model_used = self.config.remote_model or "remote"
                
            elif self.config.mode == RuntimeMode.HYBRID:
                try:
                    response = await self._remote_infer(prompt, adapter_name, system_prompt)
                    model_used = self.config.remote_model or "remote"
                except Exception as e:
                    if self.config.fallback_to_local:
                        print(f"Remote failed, falling back to local: {e}")
                        response = await self._local_infer(prompt, adapter_name, system_prompt)
                        model_used = self.config.local_model
                    else:
                        raise
                        
            elif self.config.mode == RuntimeMode.AIR_GAPPED:
                response = await self._local_infer(prompt, adapter_name, system_prompt)
                model_used = self.config.local_model
                
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            metrics = RequestMetrics(
                request_id=request_id,
                adapter_name=adapter_name,
                prompt_length=len(prompt),
                response_length=len(response),
                latency_ms=latency_ms,
                model_used=model_used,
                mode=self.config.mode.value,
                success=success,
                error_message=error_message,
            )
            self._metrics.append(metrics)
        
        return response

    async def _local_infer(
        self,
        prompt: str,
        adapter_name: str,
        system_prompt: Optional[str],
    ) -> str:
        """Run local inference."""
        if not self._local_engine:
            raise RuntimeError("Local engine not initialized")
        
        self._local_engine.swap_adapter(adapter_name)
        
        result = self._local_engine.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )
        
        return result.text

    async def _remote_infer(
        self,
        prompt: str,
        adapter_name: str,
        system_prompt: Optional[str],
    ) -> str:
        """Run remote inference via gateway."""
        if not self._remote_client:
            raise RuntimeError("Remote client not initialized")
        
        return await self._remote_client.generate(
            prompt=prompt,
            adapter_name=adapter_name,
            system_prompt=system_prompt,
        )

    def get_metrics(self) -> list[dict]:
        """Get collected metrics."""
        return [
            {
                "request_id": m.request_id,
                "adapter_name": m.adapter_name,
                "prompt_length": m.prompt_length,
                "response_length": m.response_length,
                "latency_ms": m.latency_ms,
                "model_used": m.model_used,
                "mode": m.mode,
                "timestamp": m.timestamp,
                "success": m.success,
                "error_message": m.error_message,
            }
            for m in self._metrics
        ]

    def get_stats(self) -> dict:
        """Get aggregate statistics."""
        if not self._metrics:
            return {"total_requests": 0}
        
        successful = [m for m in self._metrics if m.success]
        failed = [m for m in self._metrics if not m.success]
        
        latencies = [m.latency_ms for m in successful]
        
        return {
            "total_requests": len(self._metrics),
            "successful": len(successful),
            "failed": len(failed),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "modes_used": list(set(m.mode for m in self._metrics)),
            "adapters_used": list(set(m.adapter_name for m in self._metrics)),
        }

    def shutdown(self):
        """Shutdown the runtime."""
        if self._local_engine:
            self._local_engine.unload()
            self._local_engine = None
        
        self._remote_client = None
        print("Headless runtime shut down")


class GatewayClient:
    """Client for communicating with FlexCorp Gateway."""

    def __init__(
        self,
        gateway_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.gateway_url = gateway_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session = None

    async def generate(
        self,
        prompt: str,
        adapter_name: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send generation request to gateway."""
        import httpx
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "prompt": prompt,
            "adapter_name": adapter_name,
            "system_prompt": system_prompt,
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.gateway_url}/api/v1/generate",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("text", "")

    async def health_check(self) -> bool:
        """Check gateway health."""
        import httpx
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.gateway_url}/health")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models on gateway."""
        import httpx
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.gateway_url}/api/v1/models",
                headers=headers,
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("models", [])
