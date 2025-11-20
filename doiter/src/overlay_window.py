import Cocoa
import objc
from Foundation import NSObject, NSMakeRect, NSMakePoint, NSMakeSize, NSTimer, NSURL
from AppKit import (
    NSWindow, NSView, NSTextField, NSScrollView, NSTableView, NSTableColumn,
    NSColor, NSFont, NSBorderlessWindowMask, NSFloatingWindowLevel,
    NSWindowCollectionBehaviorCanJoinAllSpaces, NSWindowCollectionBehaviorStationary,
    NSBackingStoreBuffered, NSVisualEffectView, NSVisualEffectMaterialHUDWindow,
    NSVisualEffectBlendingModeBehindWindow, NSApplication, NSApp,
    NSTextFieldCell, NSLeftTextAlignment, NSCenterTextAlignment, NSAttributedString,
    NSWindowStyleMaskBorderless, NSWindowStyleMaskFullSizeContentView,
    NSWindowCollectionBehaviorTransient, NSWindowCollectionBehaviorIgnoresCycle,
    NSEvent, NSEventMaskKeyDown, NSPanel, NSViewWidthSizable, NSViewHeightSizable,
    NSWorkspace, NSFontAttributeName, NSForegroundColorAttributeName,
    NSUnderlineStyleAttributeName, NSPasteboard, NSPasteboardTypeString,
    NSMutableParagraphStyle
)
from typing import List, Dict, Optional, Callable

from .color_tags import COLOR_TAG_EMOJI_MAP, COLOR_TAG_KEYCODE_MAP, COLOR_TAG_NAME_MAP


class KeyableWindow(NSWindow):
    """Custom NSWindow that can become key and accept input."""

    def init(self):
        self = objc.super(KeyableWindow, self).init()
        if self is None:
            return None
        self.resize_delegate = None
        return self

    def setResizeDelegate_(self, delegate):
        """Set the resize delegate."""
        self.resize_delegate = delegate

    def setFrame_display_animate_(self, frame, display, animate):
        """Override to notify delegate on resize."""
        objc.super(KeyableWindow, self).setFrame_display_animate_(frame, display, animate)
        if self.resize_delegate and hasattr(self.resize_delegate, 'windowDidResize_'):
            self.resize_delegate.windowDidResize_(self)

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


class ClickableLabel(NSTextField):
    """Label that opens a URL when clicked."""

    def init(self):
        self = objc.super(ClickableLabel, self).init()
        if self is None:
            return None
        self.url = None
        return self

    def setURL_(self, url: str):
        self.url = url

    def mouseDown_(self, event):
        if self.url:
            nsurl = NSURL.URLWithString_(self.url)
            if nsurl:
                NSWorkspace.sharedWorkspace().openURL_(nsurl)
        else:
            objc.super(ClickableLabel, self).mouseDown_(event)


class ResizeHandle(NSView):
    """Custom view for handling window resizing from bottom-right corner."""

    def init(self):
        self = objc.super(ResizeHandle, self).init()
        if self is None:
            return None
        self.window_ref = None
        self.is_dragging = False
        self.drag_start_point = None
        self.drag_start_frame = None
        self.original_movable_state = None
        self.original_window_movable = None
        return self

    def setWindowRef_(self, window):
        self.window_ref = window

    def mouseDownCanMoveWindow(self):
        """Prevent the window from moving when the resize handle is grabbed."""
        return False

    def drawRect_(self, rect):
        """Draw the resize indicator lines."""
        objc.super(ResizeHandle, self).drawRect_(rect)

        # Draw three diagonal lines in the corner
        NSColor.tertiaryLabelColor().set()
        path = Cocoa.NSBezierPath.bezierPath()
        path.setLineWidth_(1.0)

        bounds = self.bounds()
        width = bounds.size.width
        height = bounds.size.height

        # Three parallel diagonal lines
        for i in range(3):
            offset = i * 4
            path.moveToPoint_(NSMakePoint(width - 3 - offset, 3))
            path.lineToPoint_(NSMakePoint(width - 3, 3 + offset))

        path.stroke()

    def mouseDown_(self, event):
        if not self.window_ref:
            return
        self.is_dragging = True
        self.drag_start_point = NSEvent.mouseLocation()
        self.drag_start_frame = self.window_ref.frame()

        # Disable window dragging while resizing
        self.original_movable_state = self.window_ref.isMovableByWindowBackground()
        if hasattr(self.window_ref, "isMovable") and hasattr(self.window_ref, "setMovable_"):
            self.original_window_movable = self.window_ref.isMovable()
            self.window_ref.setMovable_(False)
        self.window_ref.setMovableByWindowBackground_(False)

    def mouseDragged_(self, event):
        if not self.is_dragging or not self.window_ref:
            return

        current_point = NSEvent.mouseLocation()
        dx = current_point.x - self.drag_start_point.x
        dy = current_point.y - self.drag_start_point.y

        # Calculate new width (grows to the right)
        new_width = max(400, min(1000, self.drag_start_frame.size.width + dx))

        # Calculate new height (grows downward)
        # Since macOS origin is bottom-left, dragging down means moving mouse down (decreasing y)
        # So we need to subtract dy to increase height when dragging down
        new_height = max(300, min(800, self.drag_start_frame.size.height - dy))

        # Keep top-left corner fixed by adjusting origin.y
        # When height increases (dragging down), origin.y must decrease
        height_change = new_height - self.drag_start_frame.size.height
        new_y = self.drag_start_frame.origin.y - height_change

        new_frame = NSMakeRect(
            self.drag_start_frame.origin.x,  # Keep X fixed
            new_y,                            # Adjust Y to keep top fixed
            new_width,
            new_height
        )

        self.window_ref.setFrame_display_animate_(new_frame, True, False)

    def mouseUp_(self, event):
        self.is_dragging = False
        self.drag_start_point = None
        self.drag_start_frame = None

        # Restore window dragging state
        if self.window_ref and self.original_movable_state is not None:
            self.window_ref.setMovableByWindowBackground_(self.original_movable_state)
            self.original_movable_state = None
        if (
            self.window_ref
            and self.original_window_movable is not None
            and hasattr(self.window_ref, "setMovable_")
        ):
            self.window_ref.setMovable_(self.original_window_movable)
            self.original_window_movable = None

    def resetCursorRects(self):
        self.addCursorRect_cursor_(
            self.bounds(),
            Cocoa.NSCursor.alloc().initWithImage_hotSpot_(
                Cocoa.NSImage.imageNamed_("NSResizeNWSE"),
                NSMakePoint(8, 8)
            ) if hasattr(Cocoa.NSImage, 'imageNamed_') else Cocoa.NSCursor.arrowCursor()
        )


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
            text = task.get('text', '')
            prefix = self._color_prefix(task)
            if self.editing_task_id and task['task_id'] == self.editing_task_id:
                preview = self.editing_preview_text if self.editing_preview_text is not None else text
                preview_text = preview if preview is not None else ""
                display = f"✎ {preview_text}"
            else:
                display = text
            if prefix:
                return f"{prefix}{display}"
            return display
        return ""

    def _color_prefix(self, task: Dict) -> str:
        """Return the emoji prefix for a task's color tags."""
        tags = task.get('color_tags') or []
        icons = [COLOR_TAG_EMOJI_MAP.get(tag, "") for tag in tags]
        icons = [icon for icon in icons if icon]
        if not icons:
            return ""
        return f"{' '.join(icons)} "

    def tableViewSelectionDidChange_(self, notification):
        """Handle selection change."""
        if self.selection_callback:
            tableView = notification.object()
            selected_row = tableView.selectedRow()
            self.selection_callback(selected_row)


class ToastTimerHandler(NSObject):
    """Helper to bridge NSTimer callbacks to the overlay."""

    def init(self):
        self = objc.super(ToastTimerHandler, self).init()
        if self is None:
            return None
        self.overlay = None
        return self

    def setOverlay_(self, overlay):
        self.overlay = overlay

    def handleToastTimer_(self, timer):
        if self.overlay:
            self.overlay._toast_timer_fired()


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
        self.toast_view = None
        self.toast_label = None
        self.toast_timer = None
        self.toast_window = None
        self.status_label = None
        self.footer_label = None
        self.toast_timer_handler = ToastTimerHandler.alloc().init()
        self.toast_timer_handler.setOverlay_(self)
        self.sort_mode = "position"  # "position" or "tags"

        # Window dimensions
        self.width = 500
        self.height = 400

        self._create_window()
        self._create_ui()
        self._setup_observers()
        self._setup_event_monitor()

        # Set self as resize delegate
        self.window.setResizeDelegate_(self)

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

        # Create wrapper view that enforces rounded corners
        wrapper_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, self.width, self.height)
        )
        wrapper_view.setWantsLayer_(True)
        wrapper_layer = wrapper_view.layer()
        wrapper_layer.setCornerRadius_(12.0)
        wrapper_layer.setMasksToBounds_(True)
        wrapper_layer.setBackgroundColor_(NSColor.clearColor().CGColor())

        # Create visual effect view (blur background)
        effect_view = NSVisualEffectView.alloc().initWithFrame_(wrapper_view.bounds())
        effect_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        effect_view.setMaterial_(NSVisualEffectMaterialHUDWindow)
        effect_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        effect_view.setState_(1)  # Active state
        effect_view.setWantsLayer_(True)
        effect_view.layer().setCornerRadius_(12.0)
        effect_view.layer().setMasksToBounds_(True)

        wrapper_view.addSubview_(effect_view)
        self.window.setContentView_(wrapper_view)
        self.container = effect_view

    def _create_ui(self):
        """Create UI elements."""
        # Input text field - styled like Spotlight
        input_height = 44
        input_top = self.height - 72
        self.input_field = CustomTextField.alloc().init()
        self.input_field.setFrame_(NSMakeRect(20, input_top, self.width - 40, input_height))
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
        separator_y = input_top - 4
        self.separator = NSView.alloc().initWithFrame_(
            NSMakeRect(20, separator_y, self.width - 40, 1)
        )
        self.separator.setWantsLayer_(True)
        self.separator.layer().setBackgroundColor_(
            NSColor.separatorColor().CGColor()
        )

        status_height = 16
        status_y = separator_y - status_height - 6
        self.status_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, status_y, self.width - 40, status_height)
        )
        self.status_label.setEditable_(False)
        self.status_label.setBordered_(False)
        self.status_label.setDrawsBackground_(False)
        self.status_label.setSelectable_(False)
        self.status_label.setFont_(NSFont.systemFontOfSize_(12))
        self.status_label.setTextColor_(NSColor.secondaryLabelColor())
        self.status_label.setAlignment_(NSCenterTextAlignment)

        scroll_top = status_y - 8
        scroll_height = scroll_top - 60
        scroll_height = max(scroll_height, 80)

        # Footer label
        footer_height = 18
        footer_margin = 24
        footer_y = 20
        self.footer_label = ClickableLabel.alloc().initWithFrame_(
            NSMakeRect(0, footer_y, self.width, footer_height)
        )
        self.footer_label.setEditable_(False)
        self.footer_label.setBordered_(False)
        self.footer_label.setBezeled_(False)
        self.footer_label.setDrawsBackground_(False)
        self.footer_label.setSelectable_(False)
        self.footer_label.setFont_(NSFont.systemFontOfSize_(12))
        self.footer_label.setTextColor_(NSColor.secondaryLabelColor())
        self.footer_label.setAlignment_(NSCenterTextAlignment)
        self.footer_label.setStringValue_("doiter by rasskazchikov.de")
        self.footer_label.setURL_("https://rasskazchikov.de")

        # Create scroll view for tasks - above footer
        self.scroll_view = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, footer_y + footer_height + 8, self.width - 40, scroll_height)
        )
        self.scroll_view.setHasVerticalScroller_(True)
        self.scroll_view.setAutohidesScrollers_(True)
        self.scroll_view.setBorderType_(0)  # No border
        self.scroll_view.setDrawsBackground_(False)

        # Create table view
        self.table_view = NSTableView.alloc().initWithFrame_(self.scroll_view.bounds())
        self.table_view.setBackgroundColor_(NSColor.clearColor())
        self.table_view.setGridStyleMask_(0)  # No grid
        self.table_view.setRowHeight_(52)  # Allow larger font for rows
        self.table_view.setHeaderView_(None)
        self.table_view.setFocusRingType_(0)  # No focus ring
        self.table_view.setAllowsEmptySelection_(True)
        self.table_view.setIntercellSpacing_(NSMakeSize(0, 4))  # Spacing between rows

        # Create table column
        column = NSTableColumn.alloc().initWithIdentifier_("tasks")
        column.setWidth_(self.width - 60)
        self.table_view.addTableColumn_(column)
        data_cell = column.dataCell()
        if data_cell:
            data_cell.setFont_(NSFont.systemFontOfSize_(24))

        # Create and set delegate
        self.delegate = TaskTableDelegate.alloc().init()
        self.delegate.setSelectionCallback_(self._on_selection_changed)
        self.table_view.setDelegate_(self.delegate)
        self.table_view.setDataSource_(self.delegate)

        self.scroll_view.setDocumentView_(self.table_view)

        # Add resize handle in bottom-right corner
        resize_handle_size = 20
        self.resize_handle = ResizeHandle.alloc().initWithFrame_(
            NSMakeRect(self.width - resize_handle_size, 0, resize_handle_size, resize_handle_size)
        )
        self.resize_handle.setWindowRef_(self.window)
        self.resize_handle.setWantsLayer_(True)

        # Add views to container
        self.container.addSubview_(self.input_field)
        self.container.addSubview_(self.separator)
        if self.status_label:
            self.container.addSubview_(self.status_label)
        self.container.addSubview_(self.scroll_view)
        if self.footer_label:
            self.container.addSubview_(self.footer_label)
        self.container.addSubview_(self.resize_handle)
        self._create_toast_view()
        self._update_status_hint()
        self._update_footer_text()

    def _create_toast_view(self):
        """Create floating toast to show quick status messages."""
        toast_width = 320
        toast_height = 32

        self.toast_view = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, toast_width, toast_height)
        )
        self.toast_view.setWantsLayer_(True)
        toast_layer = self.toast_view.layer()
        toast_layer.setCornerRadius_(8.0)
        toast_layer.setMasksToBounds_(True)
        toast_layer.setBackgroundColor_(NSColor.clearColor().CGColor())

        effect_view = NSVisualEffectView.alloc().initWithFrame_(self.toast_view.bounds())
        effect_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        effect_view.setMaterial_(NSVisualEffectMaterialHUDWindow)
        effect_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        effect_view.setState_(1)
        effect_layer = effect_view.layer()
        if effect_layer:
            effect_layer.setCornerRadius_(8.0)
            effect_layer.setMasksToBounds_(True)

        self.toast_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(12, 5, toast_width - 24, toast_height - 10)
        )
        self.toast_label.setEditable_(False)
        self.toast_label.setBordered_(False)
        self.toast_label.setDrawsBackground_(False)
        self.toast_label.setBezeled_(False)
        self.toast_label.setSelectable_(False)
        self.toast_label.setFont_(NSFont.systemFontOfSize_(13))
        self.toast_label.setTextColor_(NSColor.labelColor())
        self.toast_label.setAlignment_(NSCenterTextAlignment)

        effect_view.addSubview_(self.toast_label)
        self.toast_view.addSubview_(effect_view)
        self.toast_view.setHidden_(True)
        self.toast_window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, toast_width, toast_height),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False
        )
        self.toast_window.setOpaque_(False)
        self.toast_window.setBackgroundColor_(NSColor.clearColor())
        self.toast_window.setLevel_(NSFloatingWindowLevel + 1)
        self.toast_window.setHasShadow_(True)
        self.toast_window.setHidesOnDeactivate_(False)
        self.toast_window.setIgnoresMouseEvents_(True)
        self.toast_window.setContentView_(self.toast_view)
        self.toast_window.orderOut_(None)

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

        if self.handle_key_event(event):
            return None

        # If table view (or anything else) has focus and user starts typing, refocus input
        current_responder = self.window.firstResponder()
        input_editor = self.input_field.currentEditor()
        if current_responder not in (self.input_field, input_editor):
            if self._is_text_input_event(event):
                self.window.makeFirstResponder_(self.input_field)
                self._update_status_hint()
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
        self.current_tasks = self.task_manager.get_tasks(filter_text, self.sort_mode)
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
        self._update_status_hint()

    def _on_selection_changed(self, row: int):
        """Handle selection change."""
        self.selected_index = row
        self._update_status_hint()

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
        self._update_status_hint()

    def _update_status_hint(self):
        """Update the contextual status text below the separator."""
        if not self.status_label:
            return

        input_text = self.input_field.stringValue().strip()
        has_input = len(input_text) > 0
        has_tasks = len(self.current_tasks) > 0
        table_focused = self._is_table_view_first_responder()

        if self.is_editing:
            message = "↩︎ Enter to save"
        elif table_focused and has_tasks:
            message = "↑ / ↓ to select task, ↩︎ Enter to edit"
        elif has_input and has_tasks:
            message = "↑ / ↓ to select task, ↩︎ Enter to create new task"
        elif has_input:
            message = "↩︎ Enter to create new task"
        else:
            message = "Start typing to add new task | ⌘+E or ⎋ to close"

        self.status_label.setStringValue_(message)
        self._update_footer_text()

    def _update_footer_text(self):
        """Apply underline styling to the footer link."""
        if not self.footer_label:
            return

        paragraph_style = NSMutableParagraphStyle.alloc().init()
        paragraph_style.setAlignment_(NSCenterTextAlignment)

        attributes = {
            NSFontAttributeName: NSFont.systemFontOfSize_(12),
            NSForegroundColorAttributeName: NSColor.secondaryLabelColor(),
            NSUnderlineStyleAttributeName: 1,
            Cocoa.NSParagraphStyleAttributeName: paragraph_style
        }
        attributed = NSAttributedString.alloc().initWithString_attributes_(
            "doiter by rasskazchikov.de",
            attributes
        )
        self.footer_label.setAttributedStringValue_(attributed)

    def windowDidResize_(self, window):
        """Called when the window is resized - update UI layout."""
        frame = window.frame()
        new_width = frame.size.width
        new_height = frame.size.height

        # Update stored dimensions
        self.width = new_width
        self.height = new_height

        # Recalculate positions and sizes
        input_height = 44
        input_top = new_height - 72

        # Update input field
        self.input_field.setFrame_(NSMakeRect(20, input_top, new_width - 40, input_height))

        # Update separator
        separator_y = input_top - 4
        if hasattr(self, 'separator'):
            self.separator.setFrame_(NSMakeRect(20, separator_y, new_width - 40, 1))

        # Update status label
        status_height = 16
        status_y = separator_y - status_height - 6
        if self.status_label:
            self.status_label.setFrame_(NSMakeRect(20, status_y, new_width - 40, status_height))

        # Update footer
        footer_height = 18
        footer_y = 20
        if self.footer_label:
            self.footer_label.setFrame_(NSMakeRect(0, footer_y, new_width, footer_height))

        # Update scroll view
        scroll_top = status_y - 8
        scroll_height = scroll_top - footer_y - footer_height - 8
        scroll_height = max(scroll_height, 80)
        if hasattr(self, 'scroll_view'):
            self.scroll_view.setFrame_(NSMakeRect(20, footer_y + footer_height + 8, new_width - 40, scroll_height))

        # Update table column width
        if hasattr(self, 'table_view') and self.table_view.tableColumns():
            column = self.table_view.tableColumns()[0]
            column.setWidth_(new_width - 60)

        # Update resize handle position
        resize_handle_size = 20
        if hasattr(self, 'resize_handle'):
            self.resize_handle.setFrame_(NSMakeRect(new_width - resize_handle_size, 0, resize_handle_size, resize_handle_size))

        # Update toast position if visible
        if self.toast_window and not self.toast_view.isHidden():
            self._position_toast_window()

    def _apply_color_tag(self, tag_key: str) -> bool:
        """Toggle a color tag for the selected task."""
        if self.selected_index < 0 or self.selected_index >= len(self.current_tasks):
            return False

        task = self.current_tasks[self.selected_index]
        if not task:
            return False
        had_tag = tag_key in (task.get('color_tags') or [])
        updated_task = self.task_manager.toggle_color_tag(task['task_id'], tag_key)
        if not updated_task:
            return False

        tags = updated_task.get('color_tags') or []
        has_tag_now = tag_key in tags
        if has_tag_now != had_tag:
            self._show_tag_toast(has_tag_now, tag_key)
        return True

    def _delete_selected_task(self) -> bool:
        """Delete the currently selected task if possible."""
        if self.is_editing or self.selected_index < 0:
            return False

        if self.selected_index >= len(self.current_tasks):
            return False

        task = self.current_tasks[self.selected_index]
        deleted_index = self.selected_index

        deleted_text = task.get('text', "")
        if not self.task_manager.delete_task(task['task_id']):
            return False
        self._show_task_change_toast("delete", deleted_text)

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
        self._update_status_hint()

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
        self._update_status_hint()

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
        self._update_status_hint()

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
        self._update_status_hint()

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
        self._update_status_hint()

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
                    if self.task_manager.update_task(self.editing_task_id, text):
                        self._show_task_change_toast("update", text)
                self._stop_editing()
                self._refresh_tasks()
            elif text:
                # Add new task
                created = self.task_manager.add_task(text)
                if created:
                    self._show_task_change_toast("add", created.get('text', text))
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

        if cmd_pressed and not shift_pressed and key_code in COLOR_TAG_KEYCODE_MAP:
            tag_key = COLOR_TAG_KEYCODE_MAP[key_code]
            self._apply_color_tag(tag_key)
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
            result = self.task_manager.undo()
            if result:
                self._show_action_toast("Reverted", result)
            return True

        # Cmd+Shift+Z - redo
        elif cmd_pressed and shift_pressed and key_code == 6:  # Z
            result = self.task_manager.redo()
            if result:
                self._show_action_toast("Reapplied", result)
            return True

        # Cmd+C - copy current list view
        elif cmd_pressed and not shift_pressed and key_code == 8:  # C
            if self._copy_tasks_to_clipboard():
                return True

        # Cmd+S - toggle sort mode
        elif cmd_pressed and not shift_pressed and key_code == 1:  # S
            self._toggle_sort_mode()
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
        else:
            self._update_status_hint()
        return True

    def _show_action_toast(self, verb: str, action_info: Dict):
        """Show a toast describing the undo/redo action."""
        action = action_info.get('action')
        task = action_info.get('task', {})
        desc = self._action_description(action)
        task_text = task.get('text', "") if isinstance(task, dict) else ""
        if task_text:
            task_text = self._truncate_text(task_text.strip(), 60)
            message = f"{verb} {desc}: \"{task_text}\""
        else:
            message = f"{verb} {desc}"
        icon = ""
        if verb == "Reverted":
            icon = "↩︎"
        elif verb == "Reapplied":
            icon = "↪︎"
        if icon:
            message = f"{icon} {message}"
        self._show_toast(message)

    def _action_description(self, action: Optional[str]) -> str:
        """Readable description for task actions."""
        mapping = {
            'add': 'task creation',
            'delete': 'task deletion',
            'update': 'task edit'
        }
        return mapping.get(action, 'task change')

    def _truncate_text(self, text: str, limit: int) -> str:
        """Truncate text to a safe length for the toast."""
        if len(text) <= limit:
            return text
        return text[:limit - 3] + "..."

    def _show_task_change_toast(self, action: str, text: str):
        """Show contextual toast for add/edit/delete operations."""
        verbs = {
            'add': 'Added',
            'update': 'Updated',
            'delete': 'Removed'
        }
        icons = {
            'add': '＋',
            'update': '✎',
            'delete': '－'
        }
        clean_text = (text or "").strip()
        if clean_text:
            clean_text = self._truncate_text(clean_text, 60)
            message = f"{verbs.get(action, 'Updated')} \"{clean_text}\""
        else:
            message = verbs.get(action, 'Updated') + " task"
        icon = icons.get(action)
        if icon:
            message = f"{icon} {message}"
        self._show_toast(message)

    def _show_tag_toast(self, added: bool, tag_key: str):
        """Show toast when a color tag is toggled."""
        name = COLOR_TAG_NAME_MAP.get(tag_key, tag_key.title())
        icon = COLOR_TAG_EMOJI_MAP.get(tag_key, "🏷️")
        verb = "Added" if added else "Removed"
        message = f"{icon} {verb} {name} tag"
        self._show_toast(message)

    def _color_icon_prefix(self, task: Dict) -> str:
        """Return emoji prefix for a task's color tags."""
        tags = task.get('color_tags') or []
        icons = [COLOR_TAG_EMOJI_MAP.get(tag, "") for tag in tags]
        icons = [icon for icon in icons if icon]
        if not icons:
            return ""
        return f"{' '.join(icons)} "

    def _format_task_line(self, task: Dict) -> str:
        """Format a task line for clipboard export."""
        prefix = self._color_icon_prefix(task)
        text = task.get('text', '') or ''
        if self.is_editing and task.get('task_id') == self.editing_task_id:
            preview = self.editing_preview_text if self.editing_preview_text is not None else text
            preview_text = preview if preview is not None else ""
            display = f"✎ {preview_text}"
        else:
            display = text
        content = f"{prefix}{display}" if prefix else display
        content = content.strip()
        return f"- {content}" if content else "- "

    def _copy_tasks_to_clipboard(self) -> bool:
        """Copy the current task list to the clipboard."""
        if not self.current_tasks:
            self._show_toast("No tasks to copy")
            return True

        lines = [self._format_task_line(task) for task in self.current_tasks]
        export = "\n".join(lines)

        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.declareTypes_owner_([NSPasteboardTypeString], None)
        success = pasteboard.setString_forType_(export, NSPasteboardTypeString)
        if success:
            count = len(lines)
            plural = "" if count == 1 else "s"
            self._show_toast(f"📋 Copied {count} task{plural}")
            return True

        self._show_toast("Failed to copy tasks")
        return False

    def _show_toast(self, message: str, duration: float = 3.0):
        """Display the toast message for a limited time."""
        if not self.toast_view or not self.toast_label or not self.toast_window:
            return

        self._cancel_toast_timer()
        self.toast_label.setStringValue_(message)
        self.toast_view.setHidden_(False)
        self.toast_view.setAlphaValue_(1.0)
        self._position_toast_window()
        self.toast_window.orderFront_(None)

        self.toast_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            duration,
            self.toast_timer_handler,
            "handleToastTimer:",
            None,
            False
        )

    def _cancel_toast_timer(self):
        """Invalidate the toast timer if active."""
        if self.toast_timer is not None:
            self.toast_timer.invalidate()
            self.toast_timer = None

    def _toast_timer_fired(self):
        """Called when the toast timer completes."""
        self.toast_timer = None
        if self.toast_view:
            self.toast_view.setHidden_(True)
        if self.toast_window:
            self.toast_window.orderOut_(None)

    def _hide_toast(self):
        """Immediately hide the toast."""
        self._cancel_toast_timer()
        if self.toast_view:
            self.toast_view.setHidden_(True)
        if self.toast_window:
            self.toast_window.orderOut_(None)

    def _position_toast_window(self):
        """Place the toast window centered above the overlay window."""
        if not self.toast_window or not self.window:
            return
        overlay_frame = self.window.frame()
        toast_frame = self.toast_window.frame()
        x = overlay_frame.origin.x + (overlay_frame.size.width - toast_frame.size.width) / 2
        y = overlay_frame.origin.y + overlay_frame.size.height + 12
        new_frame = NSMakeRect(x, y, toast_frame.size.width, toast_frame.size.height)
        self.toast_window.setFrame_display_(new_frame, False)

    def _toggle_sort_mode(self):
        """Toggle between sort by position and sort by tags."""
        if self.sort_mode == "position":
            self.sort_mode = "tags"
            message = "Sorting by tags (1-7)"
        else:
            self.sort_mode = "position"
            message = "Sorting by creation order"

        self._show_toast(message, duration=3.0)
        self._refresh_tasks()

    def _handle_escape(self) -> bool:
        """Centralized escape key handling."""
        if self.is_editing:
            self._stop_editing()
            self._update_status_hint()
            return True

        if self.selected_index >= 0:
            self.selected_index = -1
            self.table_view.deselectAll_(None)
            self.input_field.setStringValue_("")
            self._refresh_tasks()
            self._update_status_hint()
            return True

        if self.is_visible:
            self.hide()
            return True
        return False
