# doiter

A minimalistic macOS todo application like Spotlight search.

```bash
pip3 install -r requirements.txt
./build.sh
cp -r dist/doiter.app /Applications/
/Applications/doiter.app/Contents/Resources/install_autostart.sh
```





### Basic Operations


- **Cmd + E** - Open/close the overlay
- **Type immediately** - Cursor auto-focuses, no mouse needed!
- **Cmd + /** - Show keyboard shortcuts
- **Type text** - Search existing tasks or enter new task
- **Enter** - Add new task
- **Up/Down arrows** - Navigate through tasks
- **Cmd + Up/Down arrows** - Move selected task up or down
- **Backspace** - Delete selected task
- **Cmd + Z** - Undo last operation
- **Cmd + Shift + Z** - Redo
- **Cmd + D** - Set deadline on selected task (`today`, `tomorrow`, `14:30`, `2026-05-21 14:30`)
- **Cmd + Shift + D** - Clear deadline
- **Cmd + L** - Set planned slot on selected task (`14:00-15:30`, `today 14:00-15:30`)
- **Cmd + Shift + L** - Clear planned slot
- **Cmd + P** - Copy current task list view
- **Cmd + T** - Start countdown timer on selected task (`25`, `25m`, `1h`, `1h 30m`), stop a running timer, or continue a stopped timer
- **Cmd + Shift + T** - Cancel selected task timer
- **Esc** - Close the overlay

Look for the **✓** icon in your menu bar (top right). Click it to show doiter overlay or close application.

### Requirements

- macOS 10.13 (High Sierra) or later
- Python 3.8 or later
- Accessibility permissions (for global hotkey)


### Troubleshooting

#### Hotkey not working

Make sure doiter has Accessibility permissions:
1. System Preferences > Security & Privacy > Privacy > Accessibility
2. Click the lock to make changes
3. Add doiter.app or check the box next to it

#### App not starting on boot

Check if the LaunchAgent is installed:
```bash
ls ~/Library/LaunchAgents/com.doiter.app.plist
```

If not found, run the install script:
```bash
/Applications/doiter.app/Contents/Resources/install_autostart.sh
```

#### Reset all data

To clear all tasks and undo history:
```bash
rm ~/Library/Application\ Support/doiter/doiter.db
```
