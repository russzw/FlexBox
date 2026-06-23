"""Task Router - deconstructs user prompts into adapter-specific subtasks."""

import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class TaskType(Enum):
    """Types of tasks that map to specialized LoRA adapters."""
    REACT = "flexreact"
    CSS = "flexcss"
    CONFIG = "flexconfig"
    UNKNOWN = "unknown"


@dataclass
class SubTask:
    """A single atomic subtask extracted from user request."""
    task_type: TaskType
    description: str
    priority: int = 0


@dataclass
class RoutingPlan:
    """Complete execution plan for a user request."""
    original_prompt: str
    subtasks: list[SubTask]
    primary_adapter: TaskType
    
    @property
    def needs_adapter_swap(self) -> bool:
        """Check if this plan requires multiple adapter swaps."""
        adapter_types = {st.task_type for st in self.subtasks}
        return len(adapter_types - {TaskType.UNKNOWN}) > 1


class TaskRouter:
    """
    Rule-based task router that parses user prompts and determines
    which adapter(s) to invoke.
    
    Phase 1 uses regex patterns for fast classification.
    Phase 2 will upgrade to embedding-based classification.
    """

    REACT_PATTERNS = [
        r"<[A-Z][a-zA-Z]*\s*/?>",
        r"import\s+.*from\s+['\"]react['\"]",
        r"export\s+(default\s+)?(function|const)\s+\w+",
        r"use(State|Effect|Context|Reducer|Memo|Callback)",
        r"React\.createElement",
        r"\.jsx?",
        r"component",
        r"props\b",
        r"hook[s]?\b",
    ]

    CSS_PATTERNS = [
        r"\b(bg|background)(-[a-z]+)?\s*:",
        r"\b(color|text-color)\s*:",
        r"\bdisplay\s*:\s*flex",
        r"\b(grid|flexbox|flex)\b",
        r"\b(padding|margin|gap)-[0-9]+",
        r"\b(tailwind|css|style[s]?)\b",
        r"\bhover|focus|active|disabled\b.*:",
        r"@media\b",
        r"\bresponsive\b",
        r"\bshadow|border|rounded\b",
        r"\b(text|font)-(xs|sm|base|lg|xl|2xl)\b",
        r"\b(p|m|w|h|size)-\[",
    ]

    CONFIG_PATTERNS = [
        r"\.(json|yaml|yml|toml|env)\b",
        r"\bconfig\b",
        r"\benvironment\b",
        r"\bvariable[s]?\b",
        r"\bpath[s]?\b",
        r"\basset[s]?\b",
        r"\b(import|require)\s*\(",
        r"process\.env",
        r"\bNEXT_PUBLIC_",
        r"\bVITE_",
        r"\bwebpack|vite|rollup\b",
    ]

    def __init__(self):
        self._compiled_patterns = {
            TaskType.REACT: [
                re.compile(p, re.IGNORECASE) for p in self.REACT_PATTERNS
            ],
            TaskType.CSS: [
                re.compile(p, re.IGNORECASE) for p in self.CSS_PATTERNS
            ],
            TaskType.CONFIG: [
                re.compile(p, re.IGNORECASE) for p in self.CONFIG_PATTERNS
            ],
        }

    def route(self, prompt: str) -> RoutingPlan:
        """
        Analyze a user prompt and create a routing plan.
        
        Args:
            prompt: The user's natural language request
            
        Returns:
            RoutingPlan with ordered subtasks
        """
        scores = self._score_prompt(prompt)
        
        subtasks = self._extract_subtasks(prompt, scores)
        
        primary_adapter = self._determine_primary(scores)
        
        return RoutingPlan(
            original_prompt=prompt,
            subtasks=subtasks,
            primary_adapter=primary_adapter,
        )

    def _score_prompt(self, prompt: str) -> dict[TaskType, int]:
        """Score prompt against each adapter's patterns."""
        scores = {task_type: 0 for task_type in TaskType}
        
        for task_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(prompt)
                scores[task_type] += len(matches)
        
        return scores

    def _extract_subtasks(
        self, 
        prompt: str, 
        scores: dict[TaskType, int]
    ) -> list[SubTask]:
        """Extract ordered subtasks from prompt based on scores."""
        subtasks = []
        
        sorted_types = sorted(
            scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for task_type, score in sorted_types:
            if score > 0 and task_type != TaskType.UNKNOWN:
                subtasks.append(SubTask(
                    task_type=task_type,
                    description=self._generate_subtask_description(
                        prompt, task_type
                    ),
                    priority=score,
                ))
        
        if not subtasks:
            subtasks.append(SubTask(
                task_type=TaskType.UNKNOWN,
                description=prompt,
                priority=0,
            ))
        
        return subtasks

    def _determine_primary(self, scores: dict[TaskType, int]) -> TaskType:
        """Determine the primary adapter based on highest score."""
        valid_scores = {
            k: v for k, v in scores.items() 
            if k != TaskType.UNKNOWN
        }
        
        if not valid_scores or max(valid_scores.values()) == 0:
            return TaskType.REACT
        
        return max(valid_scores, key=valid_scores.get)

    def _generate_subtask_description(
        self, 
        prompt: str, 
        task_type: TaskType
    ) -> str:
        """Generate a specific description for a subtask."""
        descriptions = {
            TaskType.REACT: f"Generate React component: {prompt[:100]}",
            TaskType.CSS: f"Apply styling: {prompt[:100]}",
            TaskType.CONFIG: f"Configure: {prompt[:100]}",
            TaskType.UNKNOWN: prompt[:100],
        }
        return descriptions.get(task_type, prompt[:100])

    def suggest_adapter(self, prompt: str) -> str:
        """Quick method to get recommended adapter name."""
        plan = self.route(prompt)
        return plan.primary_adapter.value


def create_router() -> TaskRouter:
    """Factory function to create a configured TaskRouter."""
    return TaskRouter()
