"""Dataset Curator - orchestrates dataset collection, validation, and formatting."""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class TrainingExample:
    """Single training example for LoRA fine-tuning."""
    prompt: str
    completion: str
    system_prompt: str = ""
    metadata: dict = field(default_factory=dict)

    def to_messages(self) -> list[dict]:
        """Convert to chat message format."""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": self.prompt})
        messages.append({"role": "assistant", "content": self.completion})
        return messages


class DatasetCurator:
    """
    Orchestrates dataset curation for LoRA fine-tuning.
    
    Pipeline:
    1. Collect raw examples from generators
    2. Validate code quality (syntax, imports, patterns)
    3. Deduplicate and balance
    4. Format for training (JSONL, chat format)
    5. Split into train/val/test
    """

    def __init__(self, output_dir: str = "datasets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._examples: list[TrainingExample] = []
        self._generator_results: dict[str, int] = {}

    def add_examples(self, examples: list[TrainingExample], source: str = "unknown"):
        """Add examples from a generator."""
        self._examples.extend(examples)
        self._generator_results[source] = len(examples)

    def validate_examples(self) -> tuple[list[TrainingExample], list[TrainingExample]]:
        """Validate examples and return (valid, invalid) split."""
        valid = []
        invalid = []
        
        for example in self._examples:
            errors = self._validate_example(example)
            if not errors:
                valid.append(example)
            else:
                example.metadata["validation_errors"] = errors
                invalid.append(example)
        
        return valid, invalid

    def _validate_example(self, example: TrainingExample) -> list[str]:
        """Validate a single training example."""
        errors = []
        
        if not example.prompt.strip():
            errors.append("Empty prompt")
        
        if not example.completion.strip():
            errors.append("Empty completion")
        
        if len(example.prompt) > 4096:
            errors.append(f"Prompt too long: {len(example.prompt)} chars")
        
        if len(example.completion) > 4096:
            errors.append(f"Completion too long: {len(example.completion)} chars")
        
        if example.prompt == example.completion:
            errors.append("Prompt equals completion")
        
        return errors

    def deduplicate(self) -> int:
        """Remove duplicate examples. Returns count removed."""
        seen = set()
        unique = []
        
        for example in self._examples:
            key = (example.prompt.strip(), example.completion.strip())
            if key not in seen:
                seen.add(key)
                unique.append(example)
        
        removed = len(self._examples) - len(unique)
        self._examples = unique
        return removed

    def balance_dataset(self, max_per_source: Optional[int] = None) -> None:
        """Balance examples across sources."""
        if not max_per_source:
            return
        
        source_counts: dict[str, list[TrainingExample]] = {}
        for example in self._examples:
            source = example.metadata.get("source", "unknown")
            if source not in source_counts:
                source_counts[source] = []
            source_counts[source].append(example)
        
        balanced = []
        for source, examples in source_counts.items():
            balanced.extend(examples[:max_per_source])
        
        self._examples = balanced

    def format_for_training(
        self, 
        system_prompt: str,
        format: str = "jsonl"
    ) -> list[dict]:
        """Format examples for training."""
        formatted = []
        
        for example in self._examples:
            if not example.system_prompt:
                example.system_prompt = system_prompt
            
            if format == "jsonl":
                formatted.append({
                    "messages": example.to_messages(),
                    "metadata": example.metadata,
                })
        
        return formatted

    def save_dataset(
        self, 
        filename: str,
        format: str = "jsonl"
    ) -> Path:
        """Save formatted dataset to file."""
        output_path = self.output_dir / filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            for example in self._examples:
                record = {
                    "messages": example.to_messages(),
                    "metadata": example.metadata,
                }
                f.write(json.dumps(record) + "\n")
        
        return output_path

    def split_dataset(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> tuple[list[TrainingExample], list[TrainingExample], list[TrainingExample]]:
        """Split dataset into train/val/test."""
        import random
        
        random.seed(seed)
        shuffled = self._examples.copy()
        random.shuffle(shuffled)
        
        n = len(shuffled)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        return (
            shuffled[:train_end],
            shuffled[train_end:val_end],
            shuffled[val_end:],
        )

    def get_stats(self) -> dict:
        """Get dataset statistics."""
        source_counts: dict[str, int] = {}
        for example in self._examples:
            source = example.metadata.get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        
        prompt_lengths = [len(e.prompt) for e in self._examples]
        completion_lengths = [len(e.completion) for e in self._examples]
        
        return {
            "total_examples": len(self._examples),
            "by_source": source_counts,
            "avg_prompt_length": sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0,
            "avg_completion_length": sum(completion_lengths) / len(completion_lengths) if completion_lengths else 0,
            "generator_results": self._generator_results,
        }

    def clear(self):
        """Clear all examples."""
        self._examples.clear()
        self._generator_results.clear()
