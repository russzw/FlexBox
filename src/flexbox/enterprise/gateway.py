"""FlexCorp Gateway - centralized server for enterprise inference."""

import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GatewayStatus(Enum):
    """Gateway operational status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


@dataclass
class GatewayConfig:
    """Configuration for FlexCorp Gateway."""
    host: str = "0.0.0.0"
    port: int = 8080
    workers: int = 4
    model_dir: str = "models"
    adapter_dir: str = "adapters"
    max_concurrent: int = 100
    request_timeout: int = 60
    enable_auth: bool = True
    api_key: Optional[str] = None
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    log_level: str = "info"


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    name: str
    adapter_count: int
    loaded_adapters: list[str]
    vram_usage_mb: float
    last_used: float
    request_count: int = 0


class FlexCorpGateway:
    """
    Centralized inference gateway for enterprise deployment.
    
    Features:
    - Multi-model support
    - LoRA adapter hot-swapping
    - Request queuing and load balancing
    - Health monitoring
    - API key authentication
    - Metrics collection
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()
        self._status = GatewayStatus.HEALTHY
        self._models: dict[str, ModelInfo] = {}
        self._request_queue: asyncio.Queue = None
        self._metrics: list[dict] = []
        self._running = False

    async def start(self):
        """Start the gateway server."""
        logger.info(f"Starting FlexCorp Gateway on {self.config.host}:{self.config.port}")
        
        self._request_queue = asyncio.Queue(maxsize=self.config.max_concurrent)
        self._running = True
        
        # Load models
        await self._load_models()
        
        # Start worker tasks
        workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.config.workers)
        ]
        
        logger.info(f"Gateway started with {self.config.workers} workers")
        
        # Run server
        try:
            await self._run_server()
        except KeyboardInterrupt:
            logger.info("Shutting down gateway...")
        finally:
            self._running = False
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    async def _run_server(self):
        """Run the HTTP server."""
        from aiohttp import web
        
        app = web.Application()
        
        # Routes
        app.router.add_get("/health", self._handle_health)
        app.router.add_get("/api/v1/models", self._handle_list_models)
        app.router.add_post("/api/v1/generate", self._handle_generate)
        app.router.add_get("/api/v1/metrics", self._handle_metrics)
        app.router.add_post("/api/v1/adapters/load", self._handle_load_adapter)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, self.config.host, self.config.port)
        await site.start()
        
        logger.info(f"Server listening on http://{self.config.host}:{self.config.port}")
        
        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def _load_models(self):
        """Load configured models."""
        model_dir = Path(self.config.model_dir)
        adapter_dir = Path(self.config.adapter_dir)
        
        if model_dir.exists():
            for model_path in model_dir.iterdir():
                if model_path.is_dir():
                    name = model_path.name
                    self._models[name] = ModelInfo(
                        name=name,
                        adapter_count=0,
                        loaded_adapters=[],
                        vram_usage_mb=0,
                        last_used=time.time(),
                    )
                    logger.info(f"Registered model: {name}")
        
        # Register adapters
        if adapter_dir.exists():
            for adapter_path in adapter_dir.iterdir():
                if adapter_path.is_dir() and (adapter_path / "adapter_config.json").exists():
                    # Associate with first model
                    if self._models:
                        model_name = next(iter(self._models))
                        self._models[model_name].adapter_count += 1
                        self._models[model_name].loaded_adapters.append(adapter_path.name)
                        logger.info(f"Registered adapter: {adapter_path.name}")

    async def _worker(self, worker_id: int):
        """Background worker for processing requests."""
        while self._running:
            try:
                request = await asyncio.wait_for(
                    self._request_queue.get(),
                    timeout=1.0,
                )
                
                result = await self._process_request(request)
                request["future"].set_result(result)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

    async def _process_request(self, request: dict) -> dict:
        """Process an inference request."""
        start_time = time.perf_counter()
        
        prompt = request["prompt"]
        adapter_name = request.get("adapter_name", "flexreact")
        system_prompt = request.get("system_prompt")
        
        # In production, this would call the actual inference engine
        # For now, return a simulated response
        await asyncio.sleep(0.1)  # Simulate processing
        
        result = {
            "text": f"[Gateway] Generated response for adapter '{adapter_name}'",
            "adapter_used": adapter_name,
            "latency_ms": (time.perf_counter() - start_time) * 1000,
        }
        
        # Record metrics
        self._metrics.append({
            "adapter_name": adapter_name,
            "latency_ms": result["latency_ms"],
            "prompt_length": len(prompt),
            "response_length": len(result["text"]),
            "timestamp": time.time(),
        })
        
        return result

    async def _handle_health(self, request):
        """Handle health check request."""
        from aiohttp import web
        
        return web.json_response({
            "status": self._status.value,
            "models": len(self._models),
            "queue_size": self._request_queue.qsize() if self._request_queue else 0,
        })

    async def _handle_list_models(self, request):
        """Handle list models request."""
        from aiohttp import web
        
        models = [
            {
                "name": m.name,
                "adapter_count": m.adapter_count,
                "loaded_adapters": m.loaded_adapters,
                "request_count": m.request_count,
            }
            for m in self._models.values()
        ]
        
        return web.json_response({"models": models})

    async def _handle_generate(self, request):
        """Handle generation request."""
        from aiohttp import web
        
        # Check auth
        if self.config.enable_auth:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            token = auth_header[7:]
            if self.config.api_key and token != self.config.api_key:
                return web.json_response({"error": "Invalid API key"}, status=403)
        
        # Parse request
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        
        prompt = data.get("prompt")
        if not prompt:
            return web.json_response({"error": "Missing prompt"}, status=400)
        
        # Queue request
        future = asyncio.Future()
        await self._request_queue.put({
            "prompt": prompt,
            "adapter_name": data.get("adapter_name", "flexreact"),
            "system_prompt": data.get("system_prompt"),
            "future": future,
        })
        
        try:
            result = await asyncio.wait_for(future, timeout=self.config.request_timeout)
            return web.json_response(result)
        except asyncio.TimeoutError:
            return web.json_response({"error": "Request timeout"}, status=504)

    async def _handle_metrics(self, request):
        """Handle metrics request."""
        from aiohttp import web
        
        return web.json_response({
            "total_requests": len(self._metrics),
            "metrics": self._metrics[-100:],  # Last 100 requests
        })

    async def _handle_load_adapter(self, request):
        """Handle adapter loading request."""
        from aiohttp import web
        
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Invalid JSON"}, status=400)
        
        adapter_name = data.get("adapter_name")
        if not adapter_name:
            return web.json_response({"error": "Missing adapter_name"}, status=400)
        
        # In production, this would hot-swap the adapter
        logger.info(f"Loading adapter: {adapter_name}")
        
        return web.json_response({
            "status": "loaded",
            "adapter_name": adapter_name,
        })

    def get_status(self) -> dict:
        """Get gateway status."""
        return {
            "status": self._status.value,
            "models": len(self._models),
            "queue_size": self._request_queue.qsize() if self._request_queue else 0,
            "total_requests": len(self._metrics),
        }
