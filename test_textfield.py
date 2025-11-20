#!/usr/bin/env python3
"""Test text field input in a simple window."""

import sys
from AppKit import NSApplication, NSWindow, NSTextField, NSMakeRect, NSBackingStoreBuffered
from Foundation import NSObject
import Cocoa

app = NSApplication.sharedApplication()

# Create a simple window
window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
    NSMakeRect(100, 100, 400, 200),
    15,  # Titled, closable, miniaturizable, resizable
    NSBackingStoreBuffered,
    False
)
window.setTitle_("Text Field Test")

# Create a text field
text_field = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 100, 360, 40))
text_field.setPlaceholderString_("Type here to test...")
text_field.setEditable_(True)
text_field.setSelectable_(True)

# Add to window
window.contentView().addSubview_(text_field)

# Show window
window.makeKeyAndOrderFront_(None)
window.makeFirstResponder_(text_field)

print("Test window opened. Try typing in the text field.")
print("Close the window to exit.")

# Run
app.run()
