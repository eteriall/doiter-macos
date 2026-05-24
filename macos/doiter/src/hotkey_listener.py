import Cocoa
import Quartz
from Quartz import CoreGraphics as CG
from typing import Callable

# Try to import ApplicationServices for accessibility check
try:
    from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    HAS_AX = True
except ImportError:
    HAS_AX = False


class HotkeyListener:
    """Global hotkey listener for macOS using Quartz Event Tap."""

    def __init__(self, callback: Callable):
        """Initialize hotkey listener with callback."""
        self.callback = callback
        self.tap = None
        self.run_loop_source = None

    def start(self):
        """Start listening for global hotkeys."""
        # Request accessibility permissions
        if HAS_AX:
            trusted = AXIsProcessTrustedWithOptions({
                kAXTrustedCheckOptionPrompt: True
            })
        else:
            print("Note: Cannot check accessibility permissions automatically.")

        # Create event tap for key down events
        self.tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown) |
            Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged),
            self._event_callback,
            None
        )

        if self.tap is None:
            print("Failed to create event tap. Accessibility permissions may be required.")
            return False

        # Create run loop source and add to current run loop
        self.run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, self.tap, 0)
        Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            self.run_loop_source,
            Quartz.kCFRunLoopCommonModes
        )

        # Enable the tap
        Quartz.CGEventTapEnable(self.tap, True)

        return True

    def _event_callback(self, proxy, event_type, event, refcon):
        """Handle global keyboard events."""
        try:
            if event_type == Quartz.kCGEventKeyDown:
                key_code = Quartz.CGEventGetIntegerValueField(
                    event, Quartz.kCGKeyboardEventKeycode
                )
                flags = Quartz.CGEventGetFlags(event)

                # Check for Cmd+E (key code 14 is 'E')
                cmd_pressed = flags & Quartz.kCGEventFlagMaskCommand

                if cmd_pressed and key_code == 14:  # E key
                    # Call the callback
                    self.callback()
                    # Consume the event to prevent it from propagating
                    return None

        except Exception as e:
            print(f"Error in event callback: {e}")

        # Pass through all other events
        return event

    def stop(self):
        """Stop listening for hotkeys."""
        if self.tap:
            Quartz.CGEventTapEnable(self.tap, False)

        if self.run_loop_source:
            Quartz.CFRunLoopRemoveSource(
                Quartz.CFRunLoopGetCurrent(),
                self.run_loop_source,
                Quartz.kCFRunLoopCommonModes
            )
            self.run_loop_source = None

        self.tap = None
