import objc
from Foundation import NSObject
from AppKit import (
    NSStatusBar, NSMenu, NSMenuItem, NSVariableStatusItemLength,
    NSApplication, NSImage, NSFont
)
from typing import Callable


class StatusBarDelegate(NSObject):
    """Delegate for handling status bar menu actions."""

    def init(self):
        self = objc.super(StatusBarDelegate, self).init()
        if self is None:
            return None
        self.show_callback = None
        self.quit_callback = None
        return self

    def setShowCallback_(self, callback: Callable):
        """Set callback for showing overlay."""
        self.show_callback = callback

    def setQuitCallback_(self, callback: Callable):
        """Set callback for quitting app."""
        self.quit_callback = callback

    def showOverlay_(self, sender):
        """Handle show overlay menu item."""
        if self.show_callback:
            self.show_callback()

    def quitApp_(self, sender):
        """Handle quit menu item."""
        if self.quit_callback:
            self.quit_callback()


class StatusBar:
    """macOS status bar (menu bar) icon with menu."""

    def __init__(self, show_callback: Callable, quit_callback: Callable):
        """Initialize status bar icon."""
        self.show_callback = show_callback
        self.quit_callback = quit_callback

        # Create status bar item
        self.status_bar = NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(
            NSVariableStatusItemLength
        )

        # Set icon/title - use a simple checkmark or custom icon
        # For now, use a simple text indicator
        self.status_item.button().setTitle_("✓")
        self.status_item.button().setFont_(NSFont.systemFontOfSize_(14))

        # Create menu
        self.menu = NSMenu.alloc().init()

        # Create delegate
        self.delegate = StatusBarDelegate.alloc().init()
        self.delegate.setShowCallback_(show_callback)
        self.delegate.setQuitCallback_(quit_callback)

        # Add menu items
        show_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show doiter (⌘E)",
            "showOverlay:",
            ""
        )
        show_item.setTarget_(self.delegate)
        self.menu.addItem_(show_item)

        # Add separator
        self.menu.addItem_(NSMenuItem.separatorItem())

        # Add quit item
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit doiter",
            "quitApp:",
            "q"
        )
        quit_item.setTarget_(self.delegate)
        self.menu.addItem_(quit_item)

        # Set menu to status item
        self.status_item.setMenu_(self.menu)

    def remove(self):
        """Remove status bar icon."""
        self.status_bar.removeStatusItem_(self.status_item)
