# Development Notes

## Architecture Overview

doiter is built using 100% Python with PyObjC bindings for native macOS integration.

### Core Components

1. **database.py** - SQLite-based persistence layer
   - Stores tasks with UUID, text, timestamps
   - Maintains separate undo and redo stacks
   - Persists across restarts and reboots

2. **task_manager.py** - Business logic layer
   - Manages task CRUD operations
   - Handles undo/redo operations
   - Implements observer pattern for UI updates

3. **overlay_window.py** - UI layer
   - Creates native macOS window with blur effect
   - Uses NSVisualEffectView for vibrancy
   - Implements NSTableView for task list
   - Handles all keyboard input and navigation

4. **hotkey_listener.py** - System integration
   - Uses Quartz Event Tap for global hotkey capture
   - Listens for Cmd+E system-wide
   - Requires Accessibility permissions

5. **main.py** - Application entry point
   - Initializes all components
   - Runs as NSApplicationActivationPolicyAccessory (background agent)
   - Handles graceful shutdown

## Technical Decisions

### Why PyObjC instead of alternatives?

- **Native look and feel**: Direct access to AppKit and Cocoa APIs
- **Blur effects**: NSVisualEffectView for authentic macOS appearance
- **Global hotkeys**: Quartz Event Tap for reliable system-wide shortcuts
- **Performance**: No web view overhead like Electron
- **Small footprint**: Minimal resource usage when idle

### Why SQLite for storage?

- **Reliability**: ACID compliant, battle-tested
- **Performance**: Fast local queries
- **Portability**: Single file database
- **Built-in**: No external dependencies
- **Structured undo/redo**: Separate tables for history

### Why Event Tap over pynput?

- **Reliability**: Lower-level, more direct access to events
- **Event consumption**: Can prevent event propagation
- **macOS native**: Better integration with system

## Key Implementation Details

### Undo/Redo System

The undo/redo system uses two separate stacks stored in SQLite:

- **undo_stack**: Records each action (add/delete) with full task snapshot
- **redo_stack**: Populated when undo is performed

When a new action occurs:
1. Action is recorded in undo_stack
2. redo_stack is cleared (standard undo behavior)

When undo is performed:
1. Last action from undo_stack is retrieved
2. Reverse operation is performed
3. Original action is moved to redo_stack
4. Undo entry is removed

### Global Hotkey Capture

The hotkey listener uses CGEventTapCreate to intercept keyboard events at the system level:

1. Creates an event tap for kCGEventKeyDown
2. Filters for Cmd+E (key code 14 with Command flag)
3. Returns None to consume the event (prevents propagation)
4. Returns event unchanged for all other keys

### Window Layering

The overlay window is configured to:
- Float above all other windows (NSFloatingWindowLevel)
- Join all spaces (NSWindowCollectionBehaviorCanJoinAllSpaces)
- Remain transient (NSWindowCollectionBehaviorTransient)
- Ignore window cycling (NSWindowCollectionBehaviorIgnoresCycle)

### Animation System

Animations use NSAnimationContext:
- 150ms fade-in/out (matches macOS system animations)
- Smooth alpha transitions
- Completion handlers for cleanup

## Building and Packaging

### py2app Configuration

The setup.py configures:
- LSUIElement: True (no dock icon)
- Background agent behavior
- Includes all PyObjC frameworks
- Excludes unnecessary packages (tkinter, matplotlib, etc.)

### DMG Creation

The create_dmg.sh script:
1. Creates temporary R/W DMG from app bundle
2. Mounts and adds Applications symlink
3. Sets window appearance via AppleScript
4. Converts to compressed read-only DMG

## Testing Checklist

Before release, test:

- [ ] Cmd+E opens overlay from any app
- [ ] Adding tasks works
- [ ] Search filters correctly
- [ ] Up/Down navigation works
- [ ] Backspace deletes selected task
- [ ] Cmd+Z undoes last action
- [ ] Cmd+Shift+Z redoes
- [ ] Esc closes overlay
- [ ] Tasks persist after app restart
- [ ] Tasks persist after macOS reboot
- [ ] Undo/redo history persists
- [ ] Autostart works after login
- [ ] App runs in background (no dock icon)
- [ ] Animations are smooth
- [ ] Blur effect works correctly
- [ ] Works in both light and dark mode

## Known Limitations

1. **Accessibility Permissions Required**: Must be granted manually by user
2. **Single Hotkey**: Currently hardcoded to Cmd+E (future: make configurable)
3. **No Task Completion**: Tasks can only be added/deleted (future: completion state)
4. **No Multi-line Tasks**: Single line input only
5. **No Task Priority**: All tasks are equal priority
6. **No Due Dates**: Simple task list only
7. **No Sync**: Local storage only, no cloud sync

## Future Enhancements

Potential features to add:

1. **Configurable Hotkey**: Let users choose their own shortcut
2. **Task Completion**: Mark tasks as done without deleting
3. **Task Categories/Tags**: Organize tasks
4. **Export/Import**: JSON export for backup
5. **Keyboard Shortcuts Sheet**: Show help overlay
6. **Preferences Window**: Settings UI
7. **Multi-line Tasks**: Support for longer descriptions
8. **Dark/Light Mode Toggle**: Manual theme selection
9. **Custom Themes**: Color customization
10. **Cloud Sync**: iCloud or Dropbox integration

## Performance Considerations

- **Lazy Loading**: Only load visible tasks in table view
- **Database Indexing**: Add indexes if task count grows large
- **Event Debouncing**: Debounce search input for very long task lists
- **Memory Management**: Proper cleanup of PyObjC objects

## Debugging

### Enable Verbose Logging

Add to main.py:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Database

```bash
sqlite3 ~/Library/Application\ Support/doiter/doiter.db
.tables
SELECT * FROM tasks;
SELECT * FROM undo_stack;
```

### Check LaunchAgent Status

```bash
launchctl list | grep doiter
launchctl print gui/$(id -u)/com.doiter.app
```

### Monitor System Log

```bash
log stream --predicate 'processImagePath contains "doiter"'
```

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Document complex functions with docstrings
- Keep functions focused and single-purpose
- Use descriptive variable names

## Contributing

When contributing:

1. Test thoroughly on multiple macOS versions
2. Ensure accessibility permissions work correctly
3. Verify app signing (if distributed publicly)
4. Update documentation for new features
5. Add tests for new functionality (future: add test suite)
