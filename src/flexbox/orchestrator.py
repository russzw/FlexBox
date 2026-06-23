"""Flex Box Core - main orchestrator that coordinates all components."""

from typing import Optional
from dataclasses import dataclass

from .core.router import TaskRouter, RoutingPlan, TaskType, SubTask
from .core.memory import ProjectMemory

try:
    from .core.engine import InferenceEngine, GenerationConfig, InferenceResult
    INFERENCE_AVAILABLE = True
except ImportError:
    INFERENCE_AVAILABLE = False


@dataclass
class FlexBoxResponse:
    """Response from Flex Box processing."""
    text: str
    adapter_used: str
    subtasks_completed: list[str]
    generation_time_ms: float
    tokens_per_second: float


class FlexBox:
    """
    Main Flex Box orchestrator.
    
    Coordinates:
    - Project Memory (context)
    - Task Router (planning)
    - Inference Engine (execution)
    - Adapter Manager (LoRA swapping)
    """

    def __init__(
        self,
        model_name: str = InferenceEngine.DEFAULT_MODEL,
        project_root: str = ".",
        adapters_dir: str = "adapters",
    ):
        self.project_memory = ProjectMemory(project_root)
        self.task_router = TaskRouter()
        self.inference_engine = InferenceEngine(
            model_name=model_name,
            adapters_dir=adapters_dir,
        )
        
        self._initialized = False

    def initialize(self) -> None:
        """Initialize all components."""
        print("Initializing Flex Box...")
        
        print("Scanning project structure...")
        self.project_memory.initialize()
        
        print("Loading base model...")
        self.inference_engine.load_model()
        
        self._initialized = True
        print("Flex Box ready.")

    def process(self, prompt: str) -> FlexBoxResponse:
        """
        Process a user prompt through the full pipeline.
        
        1. Route to appropriate adapter(s)
        2. Load/swap adapter
        3. Generate response with context
        """
        if not self._initialized:
            raise RuntimeError("FlexBox not initialized. Call initialize() first.")
        
        routing_plan = self.task_router.route(prompt)
        
        system_context = self.project_memory.get_system_prompt_context()
        system_prompt = self._build_system_prompt(routing_plan, system_context)
        
        adapter_name = routing_plan.primary_adapter.value
        
        swap_time = self.inference_engine.swap_adapter(adapter_name)
        
        result = self.inference_engine.generate(
            prompt=prompt,
            system_prompt=system_prompt,
        )
        
        return FlexBoxResponse(
            text=result.text,
            adapter_used=adapter_name,
            subtasks_completed=[
                st.description for st in routing_plan.subtasks
            ],
            generation_time_ms=result.generation_time_ms,
            tokens_per_second=result.tokens_per_second,
        )

    def _build_system_prompt(
        self, 
        plan: RoutingPlan, 
        context: str
    ) -> str:
        """Build system prompt with project context and task instructions."""
        adapter_instructions = {
            TaskType.REACT: (
                "You are a React/JSX specialist. Generate clean, functional "
                "React components with proper hooks usage and TypeScript types."
            ),
            TaskType.CSS: (
                "You are a CSS/Tailwind specialist. Generate responsive, "
                "modern styling using utility classes or semantic CSS."
            ),
            TaskType.CONFIG: (
                "You are a configuration specialist. Generate valid, properly "
                "formatted configuration files and environment setups."
            ),
            TaskType.UNKNOWN: (
                "You are a helpful coding assistant. Generate clean, "
                "well-structured code."
            ),
        }
        
        primary_instruction = adapter_instructions.get(
            plan.primary_adapter, 
            adapter_instructions[TaskType.UNKNOWN]
        )
        
        parts = [
            primary_instruction,
            f"Project Context: {context}",
            "",
            "Rules:",
            "- Output only the requested code or changes",
            "- Follow existing project conventions",
            "- Use modern best practices",
        ]
        
        if plan.needs_adapter_swap:
            parts.append("- Coordinate with other specialists if needed")
        
        return "\n".join(parts)

    def suggest_adapter(self, prompt: str) -> str:
        """Quick adapter suggestion without full processing."""
        return self.task_router.suggest_adapter(prompt)

    def get_routing_plan(self, prompt: str) -> RoutingPlan:
        """Get the routing plan for a prompt without executing."""
        return self.task_router.route(prompt)

    def shutdown(self) -> None:
        """Clean shutdown and memory release."""
        self.inference_engine.unload()
        self._initialized = False
