# Testing Instructions for doiter

## Quick Test

Run the app:
```bash
cd doiter
python3 main.py
```

## What to Look For:

### 1. App Starts
- [ ] App prints "doiter is starting..."
- [ ] ✓ icon appears in menu bar (top right)
- [ ] No errors in console

### 2. Menu Bar Icon
- [ ] Click the ✓ icon
- [ ] Menu shows two options:
  - "Show doiter (⌘E)"
  - "Quit doiter"

### 3. Open Overlay (Cmd+E)
- [ ] Press Cmd+E
- [ ] Window appears centered on screen
- [ ] Window has blur/glass effect
- [ ] Large text input field at top
- [ ] Separator line below input
- [ ] Empty space below for tasks

### 4. Text Input (MOST IMPORTANT!)
- [ ] Cursor is blinking in the input field
- [ ] **Start typing immediately** - no mouse needed
- [ ] Text appears as you type
- [ ] Placeholder text disappears when you type
- [ ] Can use backspace to delete text

### 5. Add Task
- [ ] Type "Test task"
- [ ] Press Enter
- [ ] Input field clears
- [ ] Task appears below the input field
- [ ] Task is displayed in a separate row

### 6. Search/Filter
- [ ] Add a few more tasks
- [ ] Type part of a task name
- [ ] List filters to show only matching tasks

### 7. Navigation
- [ ] Press Down arrow
- [ ] First task gets highlighted
- [ ] Press Up/Down to navigate
- [ ] Selected task has visual indication

### 8. Delete Task
- [ ] Clear input field (make it empty)
- [ ] Select a task with arrow keys
- [ ] Press Backspace
- [ ] Task is deleted

### 9. Undo/Redo
- [ ] Press Cmd+Z
- [ ] Deleted task reappears
- [ ] Press Cmd+Shift+Z
- [ ] Task is deleted again

### 10. Close Overlay
- [ ] Press Esc
- [ ] Window closes/hides
- [ ] Press Cmd+E again
- [ ] Window reopens
- [ ] Tasks are still there (persisted)

### 11. Quit App
- [ ] Click menu bar ✓ icon
- [ ] Click "Quit doiter"
- [ ] App exits cleanly
- [ ] Or press Ctrl+C in terminal

## Common Issues and Solutions:

### "Cannot type in input field"
This was the main issue we fixed. The text field should now:
- Be automatically focused (cursor blinking)
- Accept keyboard input immediately
- Be editable, selectable, and enabled

If you still can't type:
1. Make sure the window is focused (click on it)
2. Check if Accessibility permissions are granted
3. Try clicking directly in the input field once

### "Cmd+E doesn't work"
- Grant Accessibility permissions:
  - System Preferences > Security & Privacy > Privacy > Accessibility
  - Add Terminal or Python to the list

### "No menu bar icon"
- The ✓ should appear in the top right
- If not visible, app may not have started correctly
- Check console for errors

## Expected Behavior:

**The key feature**: When you press Cmd+E, you should be able to start typing IMMEDIATELY without touching the mouse. The cursor should be blinking and ready in the input field.

Tasks should appear below the input field as separate, clearly visible elements, similar to how Spotlight shows search results.
