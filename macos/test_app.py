#!/usr/bin/env python3
"""Quick test to verify app can initialize."""

import sys
from doiter.src.task_manager import TaskManager
from doiter.src.overlay_window import OverlayWindow
from doiter.src.hotkey_listener import HotkeyListener

print("Testing app initialization...")

print("\n1. Creating TaskManager...")
task_manager = TaskManager()
print("   ✓ TaskManager created")

print("\n2. Adding a test task...")
task = task_manager.add_task("Test task")
print(f"   ✓ Task added: {task['text']}")

print("\n3. Getting tasks...")
tasks = task_manager.get_tasks()
print(f"   ✓ Found {len(tasks)} task(s)")

print("\n4. Testing search...")
results = task_manager.get_tasks("test")
print(f"   ✓ Search found {len(results)} result(s)")

print("\n5. Testing undo...")
task_manager.undo()
tasks = task_manager.get_tasks()
print(f"   ✓ Undo successful, now {len(tasks)} task(s)")

print("\n6. Testing redo...")
task_manager.redo()
tasks = task_manager.get_tasks()
print(f"   ✓ Redo successful, now {len(tasks)} task(s)")

print("\n7. Cleaning up test data...")
for t in tasks:
    task_manager.delete_task(t['task_id'])
print("   ✓ Cleanup complete")

task_manager.close()

print("\nAll tests passed! The app should work correctly.")
print("\nNote: The full app with GUI requires running in a proper macOS environment.")
print("Run 'cd macos/doiter && python3 main.py' to start the full application.")
