"""Corporate Pipeline - automated CI/CD training data pipeline for custom adapters."""

import json
import time
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from .sanitizer import SecretSanitizer, SanitizationResult


@dataclass
class PipelineConfig:
    """Configuration for corporate adapter pipeline."""
    org_name: str
    repo_urls: list[str] = field(default_factory=list)
    repo_paths: list[str] = field(default_factory=list)
    output_dir: str = "corporate_adapters"
    adapter_name: str = "flexcorp"
    base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    lora_rank: int = 8
    max_file_size_kb: int = 100
    exclude_patterns: list[str] = field(default_factory=lambda: [
        "*.min.js", "*.min.css", "*.map",
        "node_modules", ".git", "dist", "build",
        "__pycache__", "*.pyc",
    ])
    include_extensions: list[str] = field(default_factory=lambda: [
        ".py", ".js", ".jsx", ".ts", ".tsx",
        ".json", ".yaml", ".yml",
    ])


@dataclass
class ExtractionResult:
    """Result from code extraction."""
    files_scanned: int = 0
    files_extracted: int = 0
    files_skipped: int = 0
    secrets_found: int = 0
    secrets_sanitized: int = 0
    training_examples: int = 0
    extraction_time_s: float = 0


class CorporatePipeline:
    """
    Automated CI/CD pipeline for corporate adapter training.
    
    Pipeline:
    1. Clone/pull repositories
    2. Scan and extract code patterns
    3. Sanitize secrets and PII
    4. Generate training examples
    5. Fine-tune adapter
    6. Validate and package
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._sanitizer = SecretSanitizer()
        self._output_dir = Path(config.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> ExtractionResult:
        """Run the full pipeline."""
        print(f"Starting corporate adapter pipeline for {self.config.org_name}...")
        start_time = time.perf_counter()
        
        result = ExtractionResult()
        
        # Step 1: Scan repositories
        print("[1/5] Scanning repositories...")
        all_files = self._scan_repositories()
        result.files_scanned = len(all_files)
        
        # Step 2: Extract code patterns
        print("[2/5] Extracting code patterns...")
        patterns = self._extract_patterns(all_files, result)
        
        # Step 3: Generate training examples
        print("[3/5] Generating training examples...")
        examples = self._generate_examples(patterns)
        result.training_examples = len(examples)
        
        # Step 4: Save training data
        print("[4/5] Saving training data...")
        self._save_training_data(examples)
        
        # Step 5: Generate adapter config
        print("[5/5] Generating adapter configuration...")
        self._generate_adapter_config()
        
        result.extraction_time_s = time.perf_counter() - start_time
        
        print(f"Pipeline complete in {result.extraction_time_s:.1f}s")
        print(f"  Files scanned: {result.files_scanned}")
        print(f"  Files extracted: {result.files_extracted}")
        print(f"  Secrets sanitized: {result.secrets_sanitized}")
        print(f"  Training examples: {result.training_examples}")
        
        return result

    def _scan_repositories(self) -> list[Path]:
        """Scan all configured repositories."""
        all_files = []
        
        # Scan local paths
        for repo_path in self.config.repo_paths:
            path = Path(repo_path)
            if path.exists():
                all_files.extend(self._scan_directory(path))
        
        return all_files

    def _scan_directory(self, directory: Path) -> list[Path]:
        """Scan a directory for source files."""
        files = []
        
        for item in directory.rglob("*"):
            if not item.is_file():
                continue
            
            # Check exclude patterns
            if any(item.match(p) for p in self.config.exclude_patterns):
                continue
            
            # Check include extensions
            if item.suffix not in self.config.include_extensions:
                continue
            
            # Check file size
            if item.stat().st_size > self.config.max_file_size_kb * 1024:
                continue
            
            files.append(item)
        
        return files

    def _extract_patterns(self, files: list[Path], result: ExtractionResult) -> list[dict]:
        """Extract code patterns from files."""
        patterns = []
        
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                # Sanitize content
                sanitized, sanitize_result = self._sanitizer.sanitize_code(
                    content,
                    language=file_path.suffix.lstrip("."),
                )
                
                result.secrets_found += sanitize_result.secrets_found
                result.secrets_sanitized += sanitize_result.secrets_removed
                
                if sanitize_result.secrets_found > 0:
                    result.files_skipped += 1
                    continue
                
                result.files_extracted += 1
                
                # Extract patterns
                file_patterns = self._extract_file_patterns(
                    file_path,
                    sanitized,
                )
                patterns.extend(file_patterns)
                
            except Exception as e:
                print(f"  Warning: Could not process {file_path}: {e}")
                result.files_skipped += 1
        
        return patterns

    def _extract_file_patterns(self, file_path: Path, content: str) -> list[dict]:
        """Extract patterns from a single file."""
        patterns = []
        lines = content.split("\n")
        
        # Extract function/class definitions
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # JavaScript/TypeScript functions
            if any(kw in stripped for kw in ["export function", "export const", "export default", "export class"]):
                # Get context (function + first few lines)
                start = max(0, i - 1)
                end = min(len(lines), i + 10)
                context = "\n".join(lines[start:end])
                
                patterns.append({
                    "type": "function",
                    "language": file_path.suffix.lstrip("."),
                    "file": str(file_path),
                    "content": context,
                    "line": i + 1,
                })
            
            # Python functions/classes
            elif stripped.startswith("def ") or stripped.startswith("class "):
                start = max(0, i - 1)
                end = min(len(lines), i + 10)
                context = "\n".join(lines[start:end])
                
                patterns.append({
                    "type": "function" if stripped.startswith("def ") else "class",
                    "language": "python",
                    "file": str(file_path),
                    "content": context,
                    "line": i + 1,
                })
        
        return patterns

    def _generate_examples(self, patterns: list[dict]) -> list[dict]:
        """Generate training examples from patterns."""
        examples = []
        
        for pattern in patterns:
            # Create prompt-completion pairs
            example = {
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a {self.config.org_name} code specialist. Generate code following the organization's patterns and conventions.",
                    },
                    {
                        "role": "user",
                        "content": f"Create a {pattern['type']} similar to the one in {Path(pattern['file']).name}",
                    },
                    {
                        "role": "assistant",
                        "content": pattern["content"],
                    },
                ],
                "metadata": {
                    "source": "corporate",
                    "org": self.config.org_name,
                    "language": pattern["language"],
                    "file": pattern["file"],
                },
            }
            examples.append(example)
        
        return examples

    def _save_training_data(self, examples: list[dict]):
        """Save training examples to JSONL file."""
        output_file = self._output_dir / f"{self.config.adapter_name}_training.jsonl"
        
        with open(output_file, "w", encoding="utf-8") as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")
        
        print(f"  Saved {len(examples)} examples to {output_file}")

    def _generate_adapter_config(self):
        """Generate adapter configuration file."""
        config = {
            "peft_type": "LORA",
            "task_type": "CAUSAL_LM",
            "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
            "r": self.config.lora_rank,
            "lora_alpha": self.config.lora_rank * 2,
            "lora_dropout": 0.05,
            "bias": "none",
            "inference_mode": False,
            "base_model_name_or_path": self.config.base_model,
        }
        
        adapter_dir = self._output_dir / self.config.adapter_name
        adapter_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = adapter_dir / "adapter_config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        
        print(f"  Adapter config saved to {config_file}")

    def generate_report(self) -> dict:
        """Generate pipeline execution report."""
        return {
            "org_name": self.config.org_name,
            "adapter_name": self.config.adapter_name,
            "base_model": self.config.base_model,
            "lora_rank": self.config.lora_rank,
            "output_dir": str(self._output_dir),
        }
