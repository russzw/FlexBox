"""Phase 1 Validation Tests for Flex Box."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flexbox.core.router import TaskRouter, TaskType
from flexbox.core.memory import ProjectMemory
from flexbox.core.adapters import AdapterManager


def test_task_router():
    """Test the rule-based task router."""
    print("\n=== Testing Task Router ===")
    
    router = TaskRouter()
    
    test_cases = [
        (
            "Create a React component with useState and useEffect hooks",
            TaskType.REACT,
        ),
        (
            "Add bg-blue-500 text-white p-4 rounded-lg shadow-md",
            TaskType.CSS,
        ),
        (
            "Update the .env.local file with NEXT_PUBLIC_API_URL",
            TaskType.CONFIG,
        ),
        (
            "Build a responsive hero section component with a cat image background",
            TaskType.REACT,
        ),
        (
            "Add hover:bg-blue-600 transition-colors duration-200",
            TaskType.CSS,
        ),
        (
            "Configure webpack to handle SVG imports",
            TaskType.CONFIG,
        ),
    ]
    
    passed = 0
    failed = 0
    
    for prompt, expected_adapter in test_cases:
        plan = router.route(prompt)
        
        if plan.primary_adapter == expected_adapter:
            status = "[PASS]"
            passed += 1
        else:
            status = f"[FAIL] (expected {expected_adapter.value})"
            failed += 1
        
        print(f"\n  {status}")
        print(f"  Prompt: {prompt[:60]}...")
        print(f"  Detected: {plan.primary_adapter.value}")
        print(f"  Subtasks: {len(plan.subtasks)}")
    
    print(f"\n  Results: {passed}/{passed + failed} passed")
    return failed == 0


def test_project_memory():
    """Test project memory initialization."""
    print("\n=== Testing Project Memory ===")
    
    memory = ProjectMemory(".")
    ctx = memory.initialize()
    
    print(f"  Root: {ctx.root_path}")
    print(f"  Framework: {ctx.framework}")
    print(f"  Styling: {ctx.styling}")
    print(f"  Files: {len(ctx.file_tree)}")
    
    system_prompt = memory.get_system_prompt_context()
    print(f"  System Context: {system_prompt[:80]}...")
    
    return True


def test_adapter_manager():
    """Test adapter manager."""
    print("\n=== Testing Adapter Manager ===")
    
    manager = AdapterManager()
    adapters = manager.list_adapters()
    
    print(f"  Adapters found: {len(adapters)}")
    
    if adapters:
        for adapter in adapters:
            print(f"    - {adapter.name}: {adapter.path}")
    else:
        print("  No adapters (expected for fresh project)")
        print("  Run 'flexbox adapters' to see expected structure")
    
    return True


def test_routing_plan_multi_adapter():
    """Test multi-adapter routing."""
    print("\n=== Testing Multi-Adapter Routing ===")
    
    router = TaskRouter()
    
    complex_prompt = (
        "Create a React hero component with a cat background image, "
        "add tailwind styling with bg-gradient-to-r from-purple-500 to-blue-500, "
        "and update the config to point to /public/images/hero-cat.jpg"
    )
    
    plan = router.route(complex_prompt)
    
    print(f"  Prompt: {complex_prompt[:60]}...")
    print(f"  Primary: {plan.primary_adapter.value}")
    print(f"  Multi-adapter: {plan.needs_adapter_swap}")
    print(f"  Subtasks: {len(plan.subtasks)}")
    
    for i, st in enumerate(plan.subtasks, 1):
        print(f"    {i}. [{st.task_type.value}] Priority: {st.priority}")
    
    return True


def run_all_tests():
    """Run all Phase 1 validation tests."""
    print("=" * 60)
    print("Flex Box Phase 1 Validation Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("Task Router", test_task_router()))
    results.append(("Project Memory", test_project_memory()))
    results.append(("Adapter Manager", test_adapter_manager()))
    results.append(("Multi-Adapter Routing", test_routing_plan_multi_adapter()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\nPhase 1 Core Components: VALIDATED")
        print("Next: Set up adapters and test with model inference")
    else:
        print("\nSome tests failed. Review output above.")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
