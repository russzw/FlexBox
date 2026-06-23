"""Enhanced Project Memory - file watcher and system context injector."""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from fnmatch import fnmatch
from collections import defaultdict
import threading


@dataclass
class FileEntry:
    """Metadata for a tracked file."""
    path: str
    relative_path: str
    size: int
    modified_time: float
    content_hash: str = ""
    file_type: str = ""
    language: str = ""
    is_config: bool = False
    is_component: bool = False
    is_style: bool = False


@dataclass
class ProjectContext:
    """Enhanced context information about the current project."""
    root_path: Path
    framework: str = "unknown"
    styling: str = "unknown"
    language: str = "unknown"
    
    files: dict[str, FileEntry] = field(default_factory=dict)
    component_files: list[str] = field(default_factory=list)
    style_files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    
    config_tokens: dict[str, str] = field(default_factory=dict)
    gitignore_patterns: list[str] = field(default_factory=list)
    
    dependencies: dict[str, str] = field(default_factory=dict)
    dev_dependencies: dict[str, str] = field(default_factory=dict)
    
    last_scan_time: float = 0
    file_count: int = 0
    total_size: int = 0


@dataclass
class ContextInjection:
    """Context to inject into adapter prompts."""
    framework: str
    styling: str
    language: str
    key_files: list[str]
    config_summary: str
    recent_changes: list[str]
    constraints: list[str]


class EnhancedProjectMemory:
    """
    Enhanced Project Memory with file watcher and context injector.
    
    Features:
    - Active file system watching via polling
    - Dynamic workspace indexing
    - Automatic context injection for adapters
    - File change tracking
    - Dependency analysis
    """

    # File type mappings
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "react",
        ".ts": "typescript",
        ".tsx": "react",
        ".vue": "vue",
        ".svelte": "svelte",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
    }

    COMPONENT_EXTENSIONS = {".jsx", ".tsx", ".vue", ".svelte"}
    STYLE_EXTENSIONS = {".css", ".scss", ".less", ".module.css"}
    CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".env", ".config.js", ".config.ts"}

    FRAMEWORK_MARKERS = {
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
        "nuxt.config.js": "nuxt",
        "astro.config.mjs": "astro",
    }

    STYLING_MARKERS = {
        "tailwind.config.js": "tailwind",
        "tailwind.config.ts": "tailwind",
        "postcss.config.js": "postcss",
        "stitches.config.js": "stitches",
        "styled-system/config.js": "styled-system",
    }

    DEFAULT_IGNORES = [
        ".git", "node_modules", "__pycache__", ".venv", "venv",
        "dist", "build", ".next", "coverage", ".cache",
        "*.pyc", "*.pyo", ".env", ".env.local", ".env.development",
        "*.min.js", "*.min.css", "*.map",
    ]

    def __init__(self, root_path: str = ".", watch_interval: float = 5.0):
        self.root_path = Path(root_path).resolve()
        self.watch_interval = watch_interval
        
        self._context: Optional[ProjectContext] = None
        self._watching = False
        self._watch_thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        self._change_queue: list[str] = []
        self._lock = threading.Lock()

    def initialize(self) -> ProjectContext:
        """Scan project and build initial context."""
        print("Scanning project structure...")
        start = time.perf_counter()
        
        gitignore_patterns = self._parse_gitignore()
        
        self._context = ProjectContext(
            root_path=self.root_path,
            gitignore_patterns=gitignore_patterns,
        )
        
        self._scan_files()
        self._detect_framework()
        self._detect_styling()
        self._detect_language()
        self._analyze_dependencies()
        self._extract_config_tokens()
        
        self._context.last_scan_time = time.perf_counter()
        elapsed = time.perf_counter() - start
        
        print(f"Project scan complete: {self._context.file_count} files in {elapsed:.2f}s")
        
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

    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored."""
        name = Path(path).name
        
        for pattern in self._context.gitignore_patterns:
            if fnmatch(path, pattern) or fnmatch(name, pattern):
                return True
        
        return False

    def _scan_files(self):
        """Scan all files in the project."""
        def walk(directory: Path, depth: int = 0):
            if depth > 10:
                return
            
            try:
                entries = sorted(
                    directory.iterdir(),
                    key=lambda x: (not x.is_dir(), x.name.lower())
                )
            except PermissionError:
                return
            
            for entry in entries:
                if self._should_ignore(entry.name):
                    continue
                
                rel_path = str(entry.relative_to(self.root_path))
                
                if entry.is_dir():
                    walk(entry, depth + 1)
                else:
                    self._index_file(entry, rel_path)
        
        walk(self.root_path)

    def _index_file(self, file_path: Path, rel_path: str):
        """Index a single file."""
        stat = file_path.stat()
        ext = file_path.suffix.lower()
        
        content_hash = ""
        try:
            with open(file_path, "rb") as f:
                content_hash = hashlib.md5(f.read(8192)).hexdigest()
        except (PermissionError, OSError):
            pass
        
        language = self.LANGUAGE_EXTENSIONS.get(ext, "unknown")
        
        entry = FileEntry(
            path=str(file_path),
            relative_path=rel_path,
            size=stat.st_size,
            modified_time=stat.st_mtime,
            content_hash=content_hash,
            file_type=ext,
            language=language,
            is_config=ext in self.CONFIG_EXTENSIONS or "config" in file_path.name,
            is_component=ext in self.COMPONENT_EXTENSIONS,
            is_style=ext in self.STYLE_EXTENSIONS,
        )
        
        self._context.files[rel_path] = entry
        self._context.file_count += 1
        self._context.total_size += stat.st_size
        
        if entry.is_component:
            self._context.component_files.append(rel_path)
        elif entry.is_style:
            self._context.style_files.append(rel_path)
        elif entry.is_config:
            self._context.config_files.append(rel_path)

    def _detect_framework(self):
        """Detect the primary framework."""
        for marker, framework in self.FRAMEWORK_MARKERS.items():
            if (self.root_path / marker).exists():
                self._context.framework = framework
                return
        
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
                        self._context.framework = "nextjs"
                    elif "nuxt" in deps or "@nuxt" in deps:
                        self._context.framework = "nuxt"
                    elif "react" in deps:
                        self._context.framework = "react"
                    elif "vue" in deps:
                        self._context.framework = "vue"
                    elif "svelte" in deps:
                        self._context.framework = "svelte"
                    elif "@angular/core" in deps:
                        self._context.framework = "angular"
                    elif "solid-js" in deps:
                        self._context.framework = "solid"
            except (json.JSONDecodeError, KeyError):
                pass

    def _detect_styling(self):
        """Detect the styling system."""
        for marker, styling in self.STYLING_MARKERS.items():
            if (self.root_path / marker).exists():
                self._context.styling = styling
                return
        
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
                        self._context.styling = "tailwind"
                    elif "styled-components" in deps:
                        self._context.styling = "styled-components"
                    elif "@emotion/react" in deps or "@emotion/styled" in deps:
                        self._context.styling = "emotion"
                    elif "styled-jsx" in deps:
                        self._context.styling = "styled-jsx"
                    elif "sass" in deps or "node-sass" in deps:
                        self._context.styling = "sass"
            except (json.JSONDecodeError, KeyError):
                pass

    def _detect_language(self):
        """Detect primary programming language."""
        lang_counts: dict[str, int] = defaultdict(int)
        
        for entry in self._context.files.values():
            if entry.language != "unknown":
                lang_counts[entry.language] += 1
        
        if lang_counts:
            self._context.language = max(lang_counts, key=lang_counts.get)

    def _analyze_dependencies(self):
        """Extract dependencies from package manifests."""
        package_json = self.root_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                    self._context.dependencies = pkg.get("dependencies", {})
                    self._context.dev_dependencies = pkg.get("devDependencies", {})
            except (json.JSONDecodeError, KeyError):
                pass
        
        requirements = self.root_path / "requirements.txt"
        if requirements.exists():
            try:
                with open(requirements, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("-"):
                            if "==" in line:
                                name, version = line.split("==", 1)
                                self._context.dependencies[name.strip()] = version.strip()
                            else:
                                self._context.dependencies[line] = "*"
            except FileNotFoundError:
                pass

    def _extract_config_tokens(self):
        """Extract key configuration values."""
        env_files = [".env", ".env.local", ".env.development", ".env.production"]
        
        for env_file in env_files:
            env_path = self.root_path / env_file
            if env_path.exists():
                try:
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, _, value = line.partition("=")
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                
                                if key.startswith(("NEXT_PUBLIC_", "VITE_", "REACT_APP_")):
                                    self._context.config_tokens[key] = value
                except FileNotFoundError:
                    pass

    def start_watching(self, callback: Optional[Callable] = None):
        """Start file system watching."""
        if self._watching:
            return
        
        if callback:
            self._callbacks.append(callback)
        
        self._watching = True
        self._watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
        )
        self._watch_thread.start()
        print(f"File watcher started (interval: {self.watch_interval}s)")

    def stop_watching(self):
        """Stop file system watching."""
        self._watching = False
        if self._watch_thread:
            self._watch_thread.join(timeout=5)
        print("File watcher stopped")

    def _watch_loop(self):
        """Main watch loop."""
        last_scan = {path: entry.modified_time for path, entry in self._context.files.items()}
        
        while self._watching:
            time.sleep(self.watch_interval)
            
            changes = self._detect_changes(last_scan)
            
            if changes:
                with self._lock:
                    self._change_queue.extend(changes)
                
                for callback in self._callbacks:
                    try:
                        callback(changes)
                    except Exception as e:
                        print(f"Watch callback error: {e}")
            
            last_scan = {path: entry.modified_time for path, entry in self._context.files.items()}

    def _detect_changes(self, last_scan: dict[str, float]) -> list[str]:
        """Detect file changes since last scan."""
        changes = []
        
        current_files = set()
        
        def walk(directory: Path, depth: int = 0):
            if depth > 10:
                return
            
            try:
                for entry in directory.iterdir():
                    if self._should_ignore(entry.name):
                        continue
                    
                    rel_path = str(entry.relative_to(self.root_path))
                    
                    if entry.is_dir():
                        walk(entry, depth + 1)
                    else:
                        current_files.add(rel_path)
                        
                        if rel_path not in last_scan:
                            changes.append(f"added:{rel_path}")
                        elif entry.stat().st_mtime > last_scan[rel_path]:
                            changes.append(f"modified:{rel_path}")
            except PermissionError:
                pass
        
        walk(self.root_path)
        
        for path in last_scan:
            if path not in current_files:
                changes.append(f"deleted:{path}")
        
        return changes

    def get_recent_changes(self, limit: int = 10) -> list[str]:
        """Get recent file changes."""
        with self._lock:
            return self._change_queue[-limit:]

    def inject_context(self, adapter_type: str) -> ContextInjection:
        """Generate context injection for an adapter type."""
        if not self._context:
            self.initialize()
        
        key_files = []
        
        if adapter_type == "flexreact":
            key_files = self._context.component_files[:10]
        elif adapter_type == "flexcss":
            key_files = self._context.style_files[:10]
        elif adapter_type == "flexconfig":
            key_files = self._context.config_files[:10]
        
        config_summary = self._build_config_summary()
        recent = self.get_recent_changes(5)
        constraints = self._build_constraints()
        
        return ContextInjection(
            framework=self._context.framework,
            styling=self._context.styling,
            language=self._context.language,
            key_files=key_files,
            config_summary=config_summary,
            recent_changes=recent,
            constraints=constraints,
        )

    def _build_config_summary(self) -> str:
        """Build a summary of project configuration."""
        parts = []
        
        if self._context.framework != "unknown":
            parts.append(f"Framework: {self._context.framework}")
        
        if self._context.styling != "unknown":
            parts.append(f"Styling: {self._context.styling}")
        
        parts.append(f"Language: {self._context.language}")
        parts.append(f"Files: {self._context.file_count}")
        
        if self._context.dependencies:
            key_deps = list(self._context.dependencies.keys())[:5]
            parts.append(f"Key deps: {', '.join(key_deps)}")
        
        return " | ".join(parts)

    def _build_constraints(self) -> list[str]:
        """Build project-specific constraints."""
        constraints = []
        
        if self._context.framework == "nextjs":
            constraints.append("Use Next.js App Router patterns")
            constraints.append("Prefer server components when possible")
        
        if self._context.styling == "tailwind":
            constraints.append("Use Tailwind CSS utility classes")
            constraints.append("Avoid inline styles")
        
        if "typescript" in self._context.language:
            constraints.append("Use TypeScript strict mode")
            constraints.append("Define proper types")
        
        return constraints

    @property
    def context(self) -> Optional[ProjectContext]:
        return self._context

    @property
    def is_initialized(self) -> bool:
        return self._context is not None

    @property
    def is_watching(self) -> bool:
        return self._watching
