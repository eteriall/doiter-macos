import Cocoa
import objc
from Foundation import NSObject, NSMakeRect, NSMakePoint, NSMakeSize
from AppKit import (
    NSWindow, NSView, NSTextField, NSScrollView, NSTableView, NSTableColumn,
    NSColor, NSFont, NSBorderlessWindowMask, NSFloatingWindowLevel,
    NSWindowCollectionBehaviorCanJoinAllSpaces, NSWindowCollectionBehaviorStationary,
    NSBackingStoreBuffered, NSVisualEffectView, NSVisualEffectMaterialHUDWindow,
    NSVisualEffectBlendingModeBehindWindow, NSApplication, NSApp,
    NSTextFieldCell, NSLeftTextAlignment, NSAttributedString,
    NSWindowStyleMaskBorderless, NSWindowStyleMaskFullSizeContentView,
    NSWindowCollectionBehaviorTransient, NSWindowCollectionBehaviorIgnoresCycle,
    NSEvent, NSEventMaskKeyDown
)
from typing import List, Dict, Optional, Callable


class KeyableWindow(NSWindow):
    """Custom NSWindow that can become key and accept input."""

    def canBecomeKeyWindow(self) -> bool:
        """Allow window to become key."""
        return True

    def canBecomeMainWindow(self) -> bool:
        """Allow window to become main."""
        return True


class CustomTextField(NSTextField):
    """Custom text field that handles special key events."""

    def init(self):
        self = objc.super(CustomTextField, self).init()
        if self is None:
            return None
        self.key_handler = None
        self.command_delegate = None
        return self

    def setKeyHandler_(self, handler):
        """Set the key event handler."""
        self.key_handler = handler

    def setCommandDelegate_(self, delegate):
        """Set the delegate for text commands."""
        self.command_delegate = delegate

    def textView_doCommandBySelector_(self, textView, commandSelector):
        """Forward text commands to the command delegate."""
        if self.command_delegate:
            # Forward to the delegate
            method_name = 'control_textView_doCommandBySelector_'
            if hasattr(self.command_delegate, method_name):
                method = getattr(self.command_delegate, method_name)
                return method(self, textView, commandSelector)
        return False

    def keyDown_(self, event):
        """Handle key down events."""
        # Check if handler wants to intercept this key
        if self.key_handler:
            handled = self.key_handler(event)
            if handled:
                # Event was completely handled, don't pass to text field
                return

        # Let the text field handle normal text input
        objc.super(CustomTextField, self).keyDown_(event)


class TaskTableDelegate(NSObject):
    """Delegate for handling table view data source and selection."""

    def init(self):
        self = objc.super(TaskTableDelegate, self).init()
        if self is None:
            return None
        self.tasks = []
        self.selection_callback = None
        self.editing_task_id = None
        self.editing_preview_text = ""
        return self

    def setTasks_(self, tasks: List[Dict]):
        """Update the tasks list."""
        self.tasks = tasks

    def setSelectionCallback_(self, callback: Callable):
        """Set callback for selection changes."""
        self.selection_callback = callback

    def setEditingTaskId_(self, task_id: Optional[str]):
        """Set currently edited task id."""
        self.editing_task_id = task_id

    def setEditingPreviewText_(self, text: str):
        """Set preview text for edited task."""
        self.editing_preview_text = text

    def numberOfRowsInTableView_(self, tableView):
        """Return number of rows."""
        return len(self.tasks)

    def tableView_objectValueForTableColumn_row_(self, tableView, tableColumn, row):
        """Return value for cell."""
        if row < len(self.tasks):
            task = self.tasks[row]
            text = task['text']
            if self.editing_task_id and task['task_id'] == self.editing_task_id:
                preview = self.editing_preview_text if self.editing_preview_text is not None else text
                return f"✎ {preview}"
            return text
        return ""

    def tableViewSelectionDidChange_(self, notification):
        """Handle selection change."""
        if self.selection_callback:
            tableView = notification.object()
            selected_row = tableView.selectedRow()
            self.selection_callback(selected_row)


class OverlayWindow:
    """macOS overlay window with blur effect and task list."""

    def __init__(self, task_manager):
        """Initialize the overlay window."""
        self.task_manager = task_manager
        self.is_visible = False
        self.selected_index = -1
        self.current_tasks = []
        self.is_editing = False  # Track if we're editing a task
        self.editing_task_id = None  # Track which task is being edited
        self.editing_preview_text = ""
        self.key_event_monitor = None

        # Window dimensions
        self.width = 500
        self.height = 400

        self._create_window()
        self._create_ui()
        self._setup_observers()
        self._setup_event_monitor()

    def _create_window(self):
        """Create the main window with blur effect."""
        # Get screen dimensions
        screen = Cocoa.NSScreen.mainScreen()
        screen_frame = screen.frame()

        # Calculate centered position
        x = (screen_frame.size.width - self.width) / 2
        y = (screen_frame.size.height - self.height) / 2

        # Create window using our custom KeyableWindow class
        window_rect = NSMakeRect(x, y, self.width, self.height)

        self.window = KeyableWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            window_rect,
            NSWindowStyleMaskBorderless | NSWindowStyleMaskFullSizeContentView,
            NSBackingStoreBuffered,
            False
        )

        # Window properties
        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        self.window.setHasShadow_(True)
        self.window.setMovableByWindowBackground_(True)

        # Make sure window can become key and accept input
        self.window.setAcceptsMouseMovedEvents_(True)
        self.window.setIgnoresMouseEvents_(False)

        # Window behavior
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces |
            NSWindowCollectionBehaviorTransient |
            NSWindowCollectionBehaviorIgnoresCycle
        )

        # Create visual effect view (blur background)
        effect_view = NSVisualEffectView.alloc().initWithFrame_(
            NSMakeRect(0, 0, self.width, self.height)
        )
        effect_view.setMaterial_(NSVisualEffectMaterialHUDWindow)
        effect_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        effect_view.setState_(1)  # Active state
        effect_view.setWantsLayer_(True)
        effect_view.layer().setCornerRadius_(12.0)
        effect_view.layer().setMasksToBounds_(True)

        self.window.setContentView_(effect_view)
        self.container = effect_view

    def _create_ui(self):
        """Create UI elements."""
        # Input text field - styled like Spotlight
        input_top = self.height - 70
        self.input_field = CustomTextField.alloc().init()
        self.input_field.setFrame_(NSMakeRect(20, input_top, self.width - 40, 50))
        self.input_field.setPlaceholderString_("Add or search tasks...")
        self.input_field.setFont_(NSFont.systemFontOfSize_(24))
        self.input_field.setBordered_(False)
        self.input_field.setBezelStyle_(0)  # No bezel
        self.input_field.setFocusRingType_(1)  # None - no blue outline
        self.input_field.setDrawsBackground_(False)
        self.input_field.setBackgroundColor_(NSColor.clearColor())
        self.input_field.setTextColor_(NSColor.labelColor())

        # Set self as delegate for both text field and its text view
        self.input_field.setDelegate_(self)
        self.input_field.setCommandDelegate_(self)

        # Make sure text field is editable and selectable
        self.input_field.setEditable_(True)
        self.input_field.setSelectable_(True)
        self.input_field.setEnabled_(True)

        # Make input field accept first responder and allow continuous editing
        self.input_field.setRefusesFirstResponder_(False)
        self.input_field.setImportsGraphics_(False)

        # Get the text field's cell and configure it for better cursor behavior
        cell = self.input_field.cell()
        cell.setScrollable_(True)
        cell.setWraps_(False)

        # Set key handler for special keys
        self.input_field.setKeyHandler_(self.handle_key_event)

        # Add separator line below input
        separator_y = input_top - 10
        separator = NSView.alloc().initWithFrame_(
            NSMakeRect(20, separator_y, self.width - 40, 1)
        )
        separator.setWantsLayer_(True)
        separator.layer().setBackgroundColor_(
            NSColor.separatorColor().CGColor()
        )

        # Create scroll view for tasks - below separator
        scroll_view = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, 20, self.width - 40, separator_y - 30)
        )
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setAutohidesScrollers_(True)
        scroll_view.setBorderType_(0)  # No border
        scroll_view.setDrawsBackground_(False)

        # Create table view
        self.table_view = NSTableView.alloc().initWithFrame_(scroll_view.bounds())
        self.table_view.setBackgroundColor_(NSColor.clearColor())
        self.table_view.setGridStyleMask_(0)  # No grid
        self.table_view.setRowHeight_(44)  # Taller rows like Spotlight
        self.table_view.setHeaderView_(None)
        self.table_view.setFocusRingType_(0)  # No focus ring
        self.table_view.setAllowsEmptySelection_(True)
        self.table_view.setIntercellSpacing_(NSMakeSize(0, 4))  # Spacing between rows

        # Create table column
        column = NSTableColumn.alloc().initWithIdentifier_("tasks")
        column.setWidth_(self.width - 60)
        self.table_view.addTableColumn_(column)

        # Create and set delegate
        self.delegate = TaskTableDelegate.alloc().init()
        self.delegate.setSelectionCallback_(self._on_selection_changed)
        self.table_view.setDelegate_(self.delegate)
        self.table_view.setDataSource_(self.delegate)

        scroll_view.setDocumentView_(self.table_view)

        # Add views to container
        self.container.addSubview_(self.input_field)
        self.container.addSubview_(separator)
        self.container.addSubview_(scroll_view)

    def _setup_observers(self):
        """Setup task manager observers."""
        self.task_manager.add_observer(self._refresh_tasks)

    def _setup_event_monitor(self):
        """Setup global key monitor to handle focus changes."""
        if self.key_event_monitor is None:
            self.key_event_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                NSEventMaskKeyDown,
                self._handle_global_key_event
            )

    def _is_table_view_first_responder(self) -> bool:
        """Return True if the table view is currently first responder."""
        current_responder = self.window.firstResponder()
        view = current_responder
        while view is not None:
            if view == self.table_view:
                return True
            if hasattr(view, 'superview'):
                view = view.superview()
            else:
                break
        return False

    def _handle_global_key_event(self, event):
        """Handle key events even when text field isn't focused."""
        if not self.is_visible:
            return event

        key_code = event.keyCode()
        modifiers = event.modifierFlags()
        cmd_pressed = modifiers & Cocoa.NSCommandKeyMask

        if key_code == 53:  # Escape
            if self._handle_escape():
                return None

        if cmd_pressed and key_code == 12:  # Cmd+Q
            self.hide()
            return None

        if self._is_table_view_first_responder() and key_code == 51:
            if self._delete_selected_task():
                return None

        if cmd_pressed:
            return event

        # If table view (or anything else) has focus and user starts typing, refocus input
        current_responder = self.window.firstResponder()
        input_editor = self.input_field.currentEditor()
        if current_responder not in (self.input_field, input_editor):
            if self._is_text_input_event(event):
                self.window.makeFirstResponder_(self.input_field)
        return event

    def _is_text_input_event(self, event) -> bool:
        """Return True if the event represents text input."""
        chars = event.charactersIgnoringModifiers()
        if not chars:
            return False

        first_char = ord(chars[0])
        # Ignore special keys (arrows, function keys)
        if 0xF700 <= first_char <= 0xF8FF:
            return False
        if first_char < 32 or first_char == 127:
            return False
        return True

    def _refresh_tasks(self):
        """Refresh the task list."""
        filter_text = self.input_field.stringValue()
        self.current_tasks = self.task_manager.get_tasks(filter_text)
        self.delegate.setTasks_(self.current_tasks)
        self.delegate.setEditingTaskId_(self.editing_task_id)
        preview = self.editing_preview_text if self.is_editing else ""
        self.delegate.setEditingPreviewText_(preview)
        self.table_view.reloadData()

        # Maintain selection if valid
        if 0 <= self.selected_index < len(self.current_tasks):
            from Foundation import NSIndexSet
            self.table_view.selectRowIndexes_byExtendingSelection_(
                NSIndexSet.indexSetWithIndex_(self.selected_index),
                False
            )

    def _on_selection_changed(self, row: int):
        """Handle selection change."""
        self.selected_index = row

    def _reload_row(self, row: int):
        """Reload a single row in the table view."""
        if row < 0 or row >= len(self.current_tasks):
            return
        from Foundation import NSIndexSet
        row_indexes = NSIndexSet.indexSetWithIndex_(row)
        column_indexes = NSIndexSet.indexSetWithIndex_(0)
        self.table_view.reloadDataForRowIndexes_columnIndexes_(row_indexes, column_indexes)

    def _focus_task_list(self):
        """Move focus from text field to the task table."""
        editor = self.input_field.currentEditor()
        if editor:
            editor.resignFirstResponder()
        self.window.makeFirstResponder_(self.table_view)

    def _delete_selected_task(self) -> bool:
        """Delete the currently selected task if possible."""
        if self.is_editing or self.selected_index < 0:
            return False

        if self.selected_index >= len(self.current_tasks):
            return False

        task = self.current_tasks[self.selected_index]
        deleted_index = self.selected_index

        if not self.task_manager.delete_task(task['task_id']):
            return False

        self._refresh_tasks()
        if len(self.current_tasks) == 0:
            self.selected_index = -1
            return True

        new_index = min(deleted_index, len(self.current_tasks) - 1)
        self.selected_index = new_index
        from Foundation import NSIndexSet
        self.table_view.selectRowIndexes_byExtendingSelection_(
            NSIndexSet.indexSetWithIndex_(new_index),
            False
        )
        self.table_view.scrollRowToVisible_(new_index)
        return True

    def _start_editing(self):
        """Start editing the selected task."""
        if self.selected_index < 0 or self.selected_index >= len(self.current_tasks):
            return

        task = self.current_tasks[self.selected_index]
        self.is_editing = True
        self.editing_task_id = task['task_id']

        self.editing_preview_text = task['text']
        self.delegate.setEditingTaskId_(self.editing_task_id)
        self.delegate.setEditingPreviewText_(self.editing_preview_text)
        self._reload_row(self.selected_index)

        # Put task text in input field
        self.input_field.setStringValue_(task['text'])

        # Focus input field and select all text
        self.window.makeFirstResponder_(self.input_field)
        self.input_field.selectText_(None)

    def _update_editing_preview(self):
        """Update the preview text for the task currently being edited."""
        if not self.is_editing or self.selected_index < 0 or self.selected_index >= len(self.current_tasks):
            return

        preview_text = self.input_field.stringValue()
        self.editing_preview_text = preview_text
        self.delegate.setEditingPreviewText_(preview_text)
        self._reload_row(self.selected_index)

    def _stop_editing(self):
        """Stop editing and return to normal mode."""
        self.is_editing = False
        self.editing_task_id = None
        self.editing_preview_text = ""
        self.delegate.setEditingTaskId_(None)
        self.delegate.setEditingPreviewText_("")
        self._reload_row(self.selected_index)
        self.input_field.setStringValue_("")

        # Keep the task selected
        if 0 <= self.selected_index < len(self.current_tasks):
            from Foundation import NSIndexSet
            self.table_view.selectRowIndexes_byExtendingSelection_(
                NSIndexSet.indexSetWithIndex_(self.selected_index),
                False
            )

    def show(self):
        """Show the overlay with animation."""
        if self.is_visible:
            return

        self.is_visible = True
        self._refresh_tasks()

        # Reset input and selection
        self.input_field.setStringValue_("")
        self.selected_index = -1
        self.table_view.deselectAll_(None)

        # Activate app first - critical for key window status
        NSApp().activateIgnoringOtherApps_(True)

        # Show window
        self.window.setAlphaValue_(0.0)
        self.window.makeKeyAndOrderFront_(None)

        # Make window key immediately
        self.window.becomeKeyWindow()

        # Set first responder
        self.window.makeFirstResponder_(self.input_field)

        # Animate appearance
        Cocoa.NSAnimationContext.runAnimationGroup_completionHandler_(
            lambda context: self._animate_show(context),
            lambda: self._on_show_complete()
        )

    def _animate_show(self, context):
        """Animate window appearance."""
        context.setDuration_(0.15)
        self.window.animator().setAlphaValue_(1.0)

    def _on_show_complete(self):
        """Called after show animation completes."""
        # Re-activate app and window to ensure it stays key
        NSApp().activateIgnoringOtherApps_(True)
        self.window.becomeKeyWindow()

        # Make input field first responder again
        self.window.makeFirstResponder_(self.input_field)

        # Force text editing to start - this activates the cursor
        self.input_field.selectText_(self)

        # Set insertion point to beginning
        from Foundation import NSRange
        current_editor = self.input_field.currentEditor()
        if current_editor:
            current_editor.setSelectedRange_(NSRange(0, 0))

    def hide(self):
        """Hide the overlay with animation."""
        if not self.is_visible:
            return

        self.is_visible = False

        # Animate disappearance
        Cocoa.NSAnimationContext.runAnimationGroup_completionHandler_(
            lambda context: self._animate_hide(context),
            lambda: self.window.orderOut_(None)
        )

    def _animate_hide(self, context):
        """Animate window disappearance."""
        context.setDuration_(0.15)
        self.window.animator().setAlphaValue_(0.0)

    def toggle(self):
        """Toggle window visibility."""
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def controlTextDidChange_(self, notification):
        """Handle text field changes."""
        if self.is_editing:
            self._update_editing_preview()
        else:
            # Only refresh/filter when not editing a task
            self._refresh_tasks()

    def control_textView_doCommandBySelector_(self, control, textView, commandSelector):
        """Handle text view commands (like Enter key)."""
        # Convert selector to string for comparison
        selector_name = str(commandSelector)

        # Arrow navigation is delivered via selectors instead of key codes
        if 'moveUp:' in selector_name or 'moveUpAndModifySelection:' in selector_name:
            if self._move_selection(-1, focus_table=False):
                return True
        if 'moveDown:' in selector_name or 'moveDownAndModifySelection:' in selector_name:
            if self._move_selection(1, focus_table=False):
                return True

        # Check if it's the Enter/Return key
        if 'insertNewline' in selector_name:
            text = self.input_field.stringValue().strip()

            if self.is_editing:
                # Save edited task
                if text:
                    self.task_manager.update_task(self.editing_task_id, text)
                self._stop_editing()
                self._refresh_tasks()
            elif text:
                # Add new task
                self.task_manager.add_task(text)
                self.input_field.setStringValue_("")
                self._refresh_tasks()
            elif self.selected_index >= 0 and self.selected_index < len(self.current_tasks):
                # Start editing selected task
                self._start_editing()
            return True
        return False

    def handle_key_event(self, event) -> bool:
        """Handle keyboard events. Returns True if handled."""
        if not self.is_visible:
            return False

        key_code = event.keyCode()
        modifiers = event.modifierFlags()
        cmd_pressed = modifiers & Cocoa.NSCommandKeyMask
        shift_pressed = modifiers & Cocoa.NSShiftKeyMask

        # Escape key - hierarchical behavior
        if key_code == 53:  # Escape
            return self._handle_escape()

        if cmd_pressed and key_code == 12:  # Cmd+Q
            self.hide()
            return True

        # Up arrow - navigate tasks (only when not editing)
        elif key_code == 126:  # Up arrow
            if self._move_selection(-1, focus_table=True):
                return True

        # Down arrow - navigate tasks (only when not editing)
        elif key_code == 125:  # Down arrow
            if self._move_selection(1, focus_table=True):
                return True

        # Backspace - delete selected task (when not editing and input empty)
        elif key_code == 51:  # Backspace/Delete
            if not self.is_editing and self.selected_index >= 0:
                if self._is_table_view_first_responder() or not self.input_field.stringValue():
                    if self._delete_selected_task():
                        return True
            return False

        # Cmd+Z - undo
        elif cmd_pressed and not shift_pressed and key_code == 6:  # Z
            self.task_manager.undo()
            self._refresh_tasks()
            return True

        # Cmd+Shift+Z - redo
        elif cmd_pressed and shift_pressed and key_code == 6:  # Z
            self.task_manager.redo()
            self._refresh_tasks()
            return True

        return False

    def _move_selection(self, direction: int, focus_table: bool = False) -> bool:
        """Move the current task selection up or down."""
        if self.is_editing or len(self.current_tasks) == 0:
            return False

        if direction < 0:
            if self.selected_index <= 0:
                self.selected_index = 0
            else:
                self.selected_index -= 1
        elif direction > 0:
            if self.selected_index < 0:
                self.selected_index = 0
            elif self.selected_index >= len(self.current_tasks) - 1:
                self.selected_index = len(self.current_tasks) - 1
            else:
                self.selected_index += 1
        else:
            return False

        from Foundation import NSIndexSet
        self.table_view.selectRowIndexes_byExtendingSelection_(
            NSIndexSet.indexSetWithIndex_(self.selected_index),
            False
        )
        self.table_view.scrollRowToVisible_(self.selected_index)

        if focus_table:
            self._focus_task_list()
        return True

    def _handle_escape(self) -> bool:
        """Centralized escape key handling."""
        if self.is_editing:
            self._stop_editing()
            return True

        if self.selected_index >= 0:
            self.selected_index = -1
            self.table_view.deselectAll_(None)
            self.input_field.setStringValue_("")
            self._refresh_tasks()
            return True

        if self.is_visible:
            self.hide()
            return True
        return False
