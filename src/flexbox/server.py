"""Flex Box API Server - HTTP backend for VS Code extension and Web UI."""

import json
import sys
import os
import asyncio
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from aiohttp import web

from flexbox.core.router import TaskRouter
from flexbox.core.memory import ProjectMemory
from flexbox.core.adapters import AdapterManager
from flexbox.core.engine import InferenceEngine


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8181
    model_name: str = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
    adapters_dir: str = "adapters"
    max_tokens: int = 512


class FlexBoxServer:
    """HTTP server for Flex Box inference."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.router = TaskRouter()
        self.memory = ProjectMemory()
        self.adapter_manager = AdapterManager(adapters_dir=config.adapters_dir)
        self.engine: Optional[InferenceEngine] = None
        self._start_time = time.time()

    def initialize(self):
        """Initialize the inference engine."""
        print(f"Loading model: {self.config.model_name}")
        self.engine = InferenceEngine(
            model_name=self.config.model_name,
            use_quantization=False,  # Set to True if you have enough GPU VRAM
        )
        self.engine.load_model()
        print("Model loaded successfully")

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "uptime": time.time() - self._start_time,
            "model": self.config.model_name,
            "adapters": [a.name for a in self.adapter_manager.list_adapters()],
        })

    async def handle_generate(self, request: web.Request) -> web.Response:
        """Generate code from prompt."""
        try:
            data = await request.json()
            prompt = data.get("prompt", "")
            adapter_name = data.get("adapter")
            system_prompt = data.get("system_prompt")
            max_tokens = data.get("max_tokens", self.config.max_tokens)

            if not prompt:
                return web.json_response({"error": "Missing prompt"}, status=400)

            # Auto-detect adapter if not specified
            if not adapter_name:
                result = self.router.parse(prompt)
                adapter_name = result.get("primary_adapter", "flexreact")

            # Get project context
            project_context = self.memory.get_system_context()

            # Generate
            self.engine.swap_adapter(adapter_name)
            result = self.engine.generate(
                prompt=prompt,
                system_prompt=system_prompt or project_context,
                max_new_tokens=max_tokens,
            )

            return web.json_response({
                "text": result.text,
                "adapter_used": adapter_name,
                "tokens_generated": result.tokens_generated,
                "latency_ms": result.latency_ms,
            })

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_route(self, request: web.Request) -> web.Response:
        """Route a prompt to the appropriate adapter."""
        try:
            data = await request.json()
            prompt = data.get("prompt", "")

            result = self.router.parse(prompt)

            return web.json_response({
                "primary_adapter": result.get("primary_adapter", "flexreact"),
                "subtasks": result.get("subtasks", []),
                "multi_adapter": result.get("multi_adapter", False),
            })

        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_adapters(self, request: web.Request) -> web.Response:
        """List available adapters."""
        adapters = self.adapter_manager.list_adapters()
        return web.json_response({
            "adapters": {
                a.name: {"path": str(a.path)}
                for a in adapters
            }
        })

    async def handle_context(self, request: web.Request) -> web.Response:
        """Get project context."""
        context = self.memory.get_system_prompt_context()
        return web.json_response({"context": context})

    async def handle_index(self, request: web.Request) -> web.Response:
        """Serve the Web UI."""
        index_path = Path(__file__).parent.parent.parent / "web-ui" / "index.html"
        if index_path.exists():
            html = index_path.read_text(encoding="utf-8")
            return web.Response(text=html, content_type="text/html")
        return web.Response(text="Web UI not found. Use API endpoints directly.", content_type="text/plain")

    def create_app(self) -> web.Application:
        """Create the aiohttp application."""
        app = web.Application()
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/health", self.handle_health)
        app.router.add_post("/api/v1/generate", self.handle_generate)
        app.router.add_post("/api/v1/route", self.handle_route)
        app.router.add_get("/api/v1/adapters", self.handle_adapters)
        app.router.add_get("/api/v1/context", self.handle_context)
        return app

    def run(self):
        """Run the server."""
        self.initialize()
        app = self.create_app()
        print(f"Flex Box server running on http://{self.config.host}:{self.config.port}")
        web.run_app(app, host=self.config.host, port=self.config.port)


def main():
    config = ServerConfig()
    server = FlexBoxServer(config)
    server.run()


if __name__ == "__main__":
    main()
