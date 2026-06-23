"""Project Memory - manages workspace context, file trees, and conventions."""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from fnmatch import fnmatch


@dataclass
class ProjectContext:
    """Context information about the current project."""
    root_path: Path
    framework: str = "unknown"
    styling: str = "unknown"
    file_tree: list[str] = field(default_factory=list)
    config_tokens: dict[str, str] = field(default_factory=dict)
    gitignore_patterns: list[str] = field(default_factory=list)


class ProjectMemory:
    """
    Maintains active workspace state and context.
    
    Parses:
    - .gitignore for exclusion patterns
    - package.json / pyproject.toml for framework detection
    - Style files for styling system detection
    - File tree for context injection
    """

    FRAMEWORK_MARKERS = {
        "package.json": "node",
        "next.config.js": "nextjs",
        "next.config.mjs": "nextjs",
        "next.config.ts": "nextjs",
        "vite.config.js": "vite",
        "vite.config.ts": "vite",
        "vue.config.js": "vue",
        "angular.json": "angular",
        "svelte.config.js": "svelte",
        "remix.config.js": "remix",
        "gatsby-config.js": "gatsby",
        "pyproject.toml": "python",
        "setup.py": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
    }

    STYLING_MARKERS = {
        "tailwind.config.js": "tailwind",
        "tailwind.config.ts": "tailwind",
        "postcss.config.js": "postcss",
        "styled-components": "styled-components",
        "emotion.config.js": "emotion",
        "styled-jsx": "styled-jsx",
        "globals.css": "css",
        "app.css": "css",
    }

    DEFAULT_IGNORES = [
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        "coverage",
        "*.pyc",
        "*.pyo",
        ".env",
        ".env.local",
    ]

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self._context: Optional[ProjectContext] = None

    def initialize(self) -> ProjectContext:
        """Scan project and build context."""
        gitignore_patterns = self._parse_gitignore()
        file_tree = self._build_file_tree(gitignore_patterns)
        framework = self._detect_framework()
        styling = self._detect_styling()
        config_tokens = self._extract_config_tokens()
        
        self._context = ProjectContext(
            root_path=self.root_path,
            framework=framework,
            styling=styling,
            file_tree=file_tree,
            config_tokens=config_tokens,
            gitignore_patterns=gitignore_patterns,
        )
        
        return self._context

    def _parse_gitignore(self) -> list[str]:
        """Parse .gitignore file for exclusion patterns."""
        patterns = list(self.DEFAULT_IGNORES)
        
        gitignore_path = self.root_path / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        
        return patterns

    def _build_file_tree(
        self, 
        ignore_patterns: list[str],
        max_depth: int = 3,
        max_files: int = 200
    ) -> list[str]:
        """Build a compressed file tree representation."""
        files = []
        
        def _should_ignore(path: str) -> bool:
            for pattern in ignore_patterns:
                if fnmatch(path, pattern) or fnmatch(Path(path).name, pattern):
                    return True
            return False
        
        def _walk(directory: Path, depth: int):
            if depth > max_depth or len(files) >= max_files:
                return
            
            try:
                entries = sorted(
                    directory.iterdir(),
                    key=lambda x: (not x.is_dir(), x.name.lower())
                )
            except PermissionError:
                return
            
            for entry in entries:
                if _should_ignore(entry.name):
                    continue
                
                rel_path = entry.relative_to(self.root_path)
                files.append(str(rel_path))
                
                if entry.is_dir():
                    _walk(entry, depth + 1)
        
        _walk(self.root_path, 0)
        return files

    def _detect_framework(self) -> str:
        """Detect the primary framework from project files."""
        for marker, framework in self.FRAMEWORK_MARKERS.items():
            if (self.root_path / marker).exists():
                return framework
        
        package_json = self.root_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                    deps = {
                        **pkg.get("dependencies", {}),
                        **pkg.get("devDependencies", {}),
                    }
                    
                    if "next" in deps:
                        return "nextjs"
                    if "react" in deps:
                        return "react"
                    if "vue" in deps:
                        return "vue"
                    if "svelte" in deps:
                        return "svelte"
                    if "angular" in deps:
                        return "angular"
            except (json.JSONDecodeError, KeyError):
                pass
        
        return "unknown"

    def _detect_styling(self) -> str:
        """Detect the styling system from project files."""
        for marker, styling in self.STYLING_MARKERS.items():
            if (self.root_path / marker).exists():
                return styling
        
        package_json = self.root_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                    deps = {
                        **pkg.get("dependencies", {}),
                        **pkg.get("devDependencies", {}),
                    }
                    
                    if "tailwindcss" in deps:
                        return "tailwind"
                    if "styled-components" in deps:
                        return "styled-components"
                    if "@emotion/react" in deps or "@emotion/styled" in deps:
                        return "emotion"
            except (json.JSONDecodeError, KeyError):
                pass
        
        return "unknown"

    def _extract_config_tokens(self) -> dict[str, str]:
        """Extract key configuration values."""
        tokens = {}
        
        env_files = [".env", ".env.local", ".env.development"]
        for env_file in env_files:
            env_path = self.root_path / env_file
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            tokens[key.strip()] = value.strip().strip('"').strip("'")
        
        return tokens

    def get_system_prompt_context(self) -> str:
        """Generate a context string for system prompts."""
        if self._context is None:
            self.initialize()
        
        ctx = self._context
        
        context_parts = [
            f"Framework: {ctx.framework}",
            f"Styling: {ctx.styling}",
            f"Root: {ctx.root_path.name}",
        ]
        
        if ctx.config_tokens:
            key_configs = [
                k for k in ctx.config_tokens.keys() 
                if k.startswith(("NEXT_PUBLIC_", "VITE_", "REACT_APP_"))
            ][:5]
            if key_configs:
                context_parts.append(f"Env vars: {', '.join(key_configs)}")
        
        return " | ".join(context_parts)

    @property
    def context(self) -> Optional[ProjectContext]:
        return self._context

    @property
    def is_initialized(self) -> bool:
        return self._context is not None
