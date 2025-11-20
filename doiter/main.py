#!/usr/bin/env python3
"""
doiter - minimalistic macOS todo application
Main entry point
"""

import sys
import signal
import Cocoa
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory, NSApp
from src.task_manager import TaskManager
from src.overlay_window import OverlayWindow
from src.hotkey_listener import HotkeyListener
from src.status_bar import StatusBar


class DoiterApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.app = NSApplication.sharedApplication()
        self.app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        # Initialize components
        self.task_manager = TaskManager()
        self.overlay = OverlayWindow(self.task_manager)
        self.hotkey_listener = HotkeyListener(self.on_hotkey_pressed)
        self.status_bar = StatusBar(self.on_show_overlay, self.on_quit)

        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def on_hotkey_pressed(self):
        """Handle global hotkey press (Cmd+E)."""
        self.overlay.toggle()

    def on_show_overlay(self):
        """Handle show overlay from menu."""
        self.overlay.show()

    def on_quit(self):
        """Handle quit from menu."""
        print("\nQuitting doiter...")
        self.cleanup()
        NSApp().terminate_(None)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Cleanup resources."""
        self.hotkey_listener.stop()
        self.status_bar.remove()
        self.task_manager.close()

    def run(self):
        """Start the application."""
        print("doiter is starting...")
        print("Press Cmd+E to open the task overlay")
        print("Click the ✓ icon in the menu bar to quit")
        print("Or press Ctrl+C to quit")

        # Start hotkey listener
        if not self.hotkey_listener.start():
            print("ERROR: Failed to start hotkey listener.")
            print("Please grant Accessibility permissions in System Preferences > Security & Privacy > Privacy > Accessibility")
            return 1

        # Run the application
        try:
            self.app.run()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()

        return 0


def main():
    """Main entry point."""
    app = DoiterApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
