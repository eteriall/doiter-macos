#!/usr/bin/env python3
"""
doiter - minimalistic macOS todo application
Main entry point
"""

import sys
import signal
import Cocoa
from AppKit import NSAlert, NSApplication, NSApplicationActivationPolicyAccessory, NSApp
from PyObjCTools import AppHelper
from src.api_client import APIError, ConfigStore, DoiterAPIClient, KeychainTokenStore
from src.auth_window import AuthWindow
from src.task_manager import TaskManager
from src.overlay_window import OverlayWindow
from src.hotkey_listener import HotkeyListener
from src.settings_window import SettingsWindow
from src.status_bar import StatusBar
from src.sync_service import SyncService


class DoiterApp:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.app = NSApplication.sharedApplication()
        self.app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self._cleanup_done = False

        # Initialize components
        self.config_store = ConfigStore()
        self.token_store = KeychainTokenStore()
        self.api_client = DoiterAPIClient(self.config_store, self.token_store)
        self.task_manager = TaskManager()
        self.overlay = OverlayWindow(self.task_manager)
        self.hotkey_listener = HotkeyListener(self.on_hotkey_pressed)
        self.status_bar = StatusBar(
            self.on_show_overlay,
            self.on_quit,
            self.on_auth,
            self.on_settings,
            self.on_logout,
        )
        self.auth_window = AuthWindow(self.api_client, self.on_authenticated, self.on_auth_closed)
        self.settings_window = SettingsWindow(self.config_store)
        self.sync_service = SyncService(self.task_manager, self.api_client, self.on_sync_status)
        self.task_manager.set_sync_trigger(self.sync_service.sync_async)
        self._refresh_auth_menu()

        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def on_hotkey_pressed(self):
        """Handle global hotkey press (Cmd+E)."""
        if self.auth_window.is_visible:
            return
        self.overlay.toggle()

    def on_show_overlay(self):
        """Handle show overlay from menu."""
        if self.auth_window.is_visible:
            return
        self.overlay.show()

    def on_settings(self):
        """Handle settings from menu."""
        self.settings_window.show()

    def on_auth(self):
        """Open login/register without blocking local task usage."""
        self.overlay.hide()
        self.auth_window.show()

    def on_logout(self):
        """Log out locally and return to the auth window."""
        try:
            self.sync_service.stop()
            self.api_client.logout()
        except APIError:
            self.token_store.clear()
        self._refresh_auth_menu()
        self.overlay.show()
        self.overlay._show_toast("Logged out. Local tasks are still available.")

    def on_authenticated(self):
        """Start sync and show the task overlay after login/register."""
        self._prompt_import_local_tasks()
        self.sync_service.start()
        self._refresh_auth_menu()
        self.overlay.show()

    def on_auth_closed(self):
        """Return to the task overlay when auth is dismissed without login."""
        self.overlay.show()

    def on_sync_status(self, message: str):
        """Surface sync status without interrupting typing."""
        AppHelper.callAfter(self._show_sync_status, message)

    def _show_sync_status(self, message: str):
        """Show sync status on the AppKit main loop so toast timers fire."""
        if message == "Logged out":
            self._refresh_auth_menu()
        if self.overlay and self.overlay.is_visible:
            duration = 1.4 if message == "Synced" else 3.0
            self.overlay._show_toast(message, duration=duration)

    def _prompt_import_local_tasks(self):
        config = self.config_store.load()
        if config.get("imported_local_tasks"):
            return
        if self.task_manager.get_task_count() == 0:
            self.config_store.save({"imported_local_tasks": True})
            return

        alert = NSAlert.alloc().init()
        alert.setMessageText_("Import local tasks?")
        alert.setInformativeText_(
            "Existing tasks on this Mac can be uploaded to your doiter account."
        )
        alert.addButtonWithTitle_("Import")
        alert.addButtonWithTitle_("Skip")
        if alert.runModal() == 1000:
            self.task_manager.import_local_tasks_to_sync_queue()
        self.config_store.save({"imported_local_tasks": True})

    def _refresh_auth_menu(self):
        self.status_bar.set_authenticated(bool(self.api_client.token))

    def on_quit(self):
        """Handle quit from menu."""
        print("\nQuitting doiter...")
        self.cleanup()
        NSApp().terminate_(None)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.cleanup()
        app = NSApp()
        if app:
            app.terminate_(None)
        else:
            self.app.terminate_(None)

    def cleanup(self):
        """Cleanup resources."""
        if self._cleanup_done:
            return
        self._cleanup_done = True
        self.hotkey_listener.stop()
        self.sync_service.stop()
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

        if self.api_client.token:
            self.sync_service.start()
        self.overlay.show()

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
