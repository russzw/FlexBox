"""Flex Box CLI - command-line interface for testing and interaction."""

import argparse
import sys
import json
from pathlib import Path

from .orchestrator import FlexBox
from .core.router import TaskRouter


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="flexbox",
        description="Flex Box: Local-first multi-agent development environment",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    route_parser = subparsers.add_parser(
        "route", 
        help="Analyze a prompt and show routing plan"
    )
    route_parser.add_argument("prompt", help="The prompt to analyze")
    
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate code from a prompt"
    )
    generate_parser.add_argument("prompt", help="The prompt to process")
    generate_parser.add_argument(
        "--model",
        default=FlexBox.DEFAULT_MODEL if hasattr(FlexBox, 'DEFAULT_MODEL') else "Qwen/Qwen2.5-Coder-7B-Instruct",
        help="Model to use"
    )
    generate_parser.add_argument(
        "--adapter",
        choices=["flexreact", "flexcss", "flexconfig"],
        help="Force a specific adapter"
    )
    generate_parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Maximum tokens to generate"
    )
    generate_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    adapters_parser = subparsers.add_parser(
        "adapters",
        help="List available adapters"
    )
    
    info_parser = subparsers.add_parser(
        "info",
        help="Show project information"
    )
    
    args = parser.parse_args()
    
    if args.command == "route":
        cmd_route(args.prompt)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "adapters":
        cmd_adapters()
    elif args.command == "info":
        cmd_info()
    else:
        parser.print_help()


def cmd_route(prompt: str):
    """Analyze and display routing plan."""
    router = TaskRouter()
    plan = router.route(prompt)
    
    print("\n=== Routing Plan ===")
    print(f"Prompt: {prompt[:80]}...")
    print(f"Primary Adapter: {plan.primary_adapter.value}")
    print(f"Needs Multi-Adapter: {plan.needs_adapter_swap}")
    print("\nSubtasks:")
    for i, subtask in enumerate(plan.subtasks, 1):
        print(f"  {i}. [{subtask.task_type.value}] {subtask.description}")
        print(f"     Priority Score: {subtask.priority}")


def cmd_generate(args):
    """Generate code from a prompt."""
    try:
        flexbox = FlexBox(model_name=args.model)
        flexbox.initialize()
        
        if args.adapter:
            result = flexbox.process_with_adapter(
                args.prompt, 
                args.adapter
            )
        else:
            result = flexbox.process(args.prompt)
        
        if args.json:
            output = {
                "text": result.text,
                "adapter_used": result.adapter_used,
                "generation_time_ms": result.generation_time_ms,
                "tokens_per_second": result.tokens_per_second,
                "subtasks": result.subtasks_completed,
            }
            print(json.dumps(output, indent=2))
        else:
            print("\n=== Generated Output ===")
            print(f"Adapter: {result.adapter_used}")
            print(f"Time: {result.generation_time_ms:.1f}ms")
            print(f"Speed: {result.tokens_per_second:.1f} tokens/s")
            print("\n--- Code ---")
            print(result.text)
            print("--- End ---")
        
        flexbox.shutdown()
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_adapters():
    """List available adapters."""
    from .core.adapters import AdapterManager
    
    manager = AdapterManager()
    adapters = manager.list_adapters()
    
    print("\n=== Available Adapters ===")
    if adapters:
        for adapter in adapters:
            status = "✓ Loaded" if adapter.loaded else "Available"
            print(f"  {adapter.name}: {status} (Rank {adapter.rank})")
    else:
        print("  No adapters found in ./adapters/")
        print("\n  Expected structure:")
        print("    adapters/")
        print("    ├── flexreact/")
        print("    ├── flexcss/")
        print("    └── flexconfig/")


def cmd_info():
    """Show project information."""
    memory = ProjectMemory(".")
    ctx = memory.initialize()
    
    print("\n=== Project Information ===")
    print(f"Root: {ctx.root_path}")
    print(f"Framework: {ctx.framework}")
    print(f"Styling: {ctx.styling}")
    print(f"Files tracked: {len(ctx.file_tree)}")
    
    if ctx.config_tokens:
        print(f"\nEnvironment Variables:")
        for key in list(ctx.config_tokens.keys())[:10]:
            print(f"  {key}")


if __name__ == "__main__":
    main()
