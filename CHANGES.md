# Recent Changes

## Version 1.1 - UI Improvements

### Fixed Issues:
1. **Auto-focus on input field** - The input field now automatically receives focus when overlay opens, cursor is ready to type immediately
2. **Import error fixed** - Added proper ApplicationServices framework import

### New Features:
1. **Menu Bar Icon** - Added a ✓ icon to the macOS menu bar (top right)
   - Click to access menu
   - Menu options: "Show doiter (⌘E)" and "Quit doiter"
   - Easy way to quit the app without using terminal

### UI Improvements:
1. **Spotlight-like design**
   - Larger input field (24pt font, was 18pt)
   - Input field positioned at top with more prominence
   - Separator line between input and tasks
   - Tasks displayed below input as separate elements
   - Taller task rows (44px, was 32px)
   - Better spacing between tasks (4px gap)
   - Cleaner, more polished appearance

2. **Better focus handling**
   - Input field refuses to lose focus
   - App activates ignoring other apps when opened
   - Focus is re-enforced after animation completes

## Testing

To test these changes:

```bash
cd doiter
python3 main.py
```

1. Look for the ✓ icon in your menu bar (top right)
2. Press Cmd+E to open overlay
3. Start typing immediately (no mouse needed!)
4. Tasks appear below the input field
5. Use arrow keys to navigate
6. Click the menu bar icon to quit

## Breaking Changes

None - all existing functionality preserved.
