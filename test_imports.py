#!/usr/bin/env python3
"""Test if all imports work correctly."""

print("Testing imports...")

print("1. Testing Cocoa...")
import Cocoa
print("   ✓ Cocoa imported")

print("2. Testing Quartz...")
import Quartz
print("   ✓ Quartz imported")

print("3. Testing ApplicationServices...")
try:
    from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    print("   ✓ ApplicationServices imported")
except ImportError as e:
    print(f"   ✗ ApplicationServices import failed: {e}")

print("4. Testing AppKit...")
from AppKit import NSApplication
print("   ✓ AppKit imported")

print("5. Testing Foundation...")
from Foundation import NSObject
print("   ✓ Foundation imported")

print("\n6. Testing database module...")
from doiter.src.database import Database
print("   ✓ Database module imported")

print("\n7. Testing task_manager module...")
from doiter.src.task_manager import TaskManager
print("   ✓ TaskManager module imported")

print("\n8. Testing hotkey_listener module...")
from doiter.src.hotkey_listener import HotkeyListener
print("   ✓ HotkeyListener module imported")

print("\n9. Testing overlay_window module...")
from doiter.src.overlay_window import OverlayWindow
print("   ✓ OverlayWindow module imported")

print("\nAll imports successful!")
