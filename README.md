# doiter

A minimalistic macOS todo application that behaves like Spotlight search.

## Features

- Opens instantly with **Cmd + E** from anywhere
- Centered overlay with blur effect (macOS-native look)
- Spotlight-like design with clean input field
- Fast keyboard-driven interface - cursor auto-focuses, no mouse needed
- Real-time search and filtering
- Full undo/redo support (persists across restarts)
- Auto-starts on macOS boot
- Runs as a background agent (no dock icon)
- Menu bar icon (✓) for easy access and quitting

## Installation

### From Source

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Build the app:
```bash
./build.sh
```

3. Install to Applications:
```bash
cp -r dist/doiter.app /Applications/
```

4. Enable autostart (optional):
```bash
/Applications/doiter.app/Contents/Resources/install_autostart.sh
```

5. Grant Accessibility permissions:
   - Go to System Preferences > Security & Privacy > Privacy > Accessibility
   - Add doiter.app to the list

### From DMG (when available)

1. Run the build and create DMG:
```bash
./build.sh
./create_dmg.sh
```

2. Open the DMG and drag doiter.app to Applications
3. Run the autostart installer (optional)
4. Grant Accessibility permissions

## Usage

### Menu Bar Icon

Look for the **✓** icon in your menu bar (top right). Click it to:
- Show doiter overlay
- Quit the application

### Basic Operations

- **Cmd + E** - Open/close the overlay
- **Type immediately** - Cursor auto-focuses, no mouse needed!
- **Type text** - Search existing tasks or enter new task
- **Enter** - Add new task (when input is not empty)
- **Up/Down arrows** - Navigate through tasks
- **Backspace** - Delete selected task (when input is empty)
- **Cmd + Z** - Undo last operation
- **Cmd + Shift + Z** - Redo
- **Esc** - Close the overlay

### Data Storage

All tasks and undo/redo history are stored in:
```
~/Library/Application Support/doiter/doiter.db
```

Data persists across:
- App restarts
- macOS reboots
- Version updates

## Development

### Project Structure

```
doiter/
├── main.py                  # Application entry point
├── src/
│   ├── database.py         # SQLite database layer
│   ├── task_manager.py     # Task management logic
│   ├── overlay_window.py   # macOS overlay window UI
│   └── hotkey_listener.py  # Global hotkey listener
└── resources/
    ├── com.doiter.app.plist       # LaunchAgent configuration
    ├── install_autostart.sh       # Autostart installer
    └── uninstall_autostart.sh     # Autostart uninstaller
```

### Running from Source

```bash
cd doiter
python3 main.py
```

### Managing Autostart

Enable autostart:
```bash
/Applications/doiter.app/Contents/Resources/install_autostart.sh
```

Disable autostart:
```bash
/Applications/doiter.app/Contents/Resources/uninstall_autostart.sh
```

## Requirements

- macOS 10.13 (High Sierra) or later
- Python 3.8 or later
- Accessibility permissions (for global hotkey)

## License

MIT

## Troubleshooting

### Hotkey not working

Make sure doiter has Accessibility permissions:
1. System Preferences > Security & Privacy > Privacy > Accessibility
2. Click the lock to make changes
3. Add doiter.app or check the box next to it

### App not starting on boot

Check if the LaunchAgent is installed:
```bash
ls ~/Library/LaunchAgents/com.doiter.app.plist
```

If not found, run the install script:
```bash
/Applications/doiter.app/Contents/Resources/install_autostart.sh
```

### Reset all data

To clear all tasks and undo history:
```bash
rm ~/Library/Application\ Support/doiter/doiter.db
```
