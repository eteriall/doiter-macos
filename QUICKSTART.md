# Quick Start Guide

## Building and Running doiter

### 1. Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Test Run from Source

```bash
cd doiter
python3 main.py
```

Press **Cmd+E** to open the overlay. If you see a permissions dialog, grant Accessibility permissions.

### 3. Build the App Bundle

```bash
./build.sh
```

This creates `dist/doiter.app`

### 4. Test the Built App

```bash
./dist/doiter.app/Contents/MacOS/doiter
```

### 5. Install to Applications

```bash
cp -r dist/doiter.app /Applications/
```

### 6. Enable Autostart (Optional)

```bash
/Applications/doiter.app/Contents/Resources/install_autostart.sh
```

### 7. Create DMG Installer (Optional)

```bash
./create_dmg.sh
```

This creates `doiter-1.0.0.dmg`

## First Time Setup

After installation:

1. **Grant Accessibility Permissions**
   - Open System Preferences
   - Go to Security & Privacy > Privacy > Accessibility
   - Click the lock icon to make changes
   - Click '+' and add doiter.app
   - OR check the box next to doiter if it's already listed

2. **Test the Hotkey**
   - Press **Cmd+E** anywhere on macOS
   - The overlay should appear
   - Type something and press Enter to add a task

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Cmd + E | Open/close overlay |
| Enter | Add task |
| Up/Down | Navigate tasks |
| Backspace | Delete selected task |
| Cmd + Z | Undo |
| Cmd + Shift + Z | Redo |
| Esc | Close overlay |

## Troubleshooting

### "doiter" cannot be opened because the developer cannot be verified

This happens on macOS Catalina and later. To fix:

```bash
xattr -cr /Applications/doiter.app
```

Then try opening again.

### Hotkey doesn't work

Make sure Accessibility permissions are granted (see step 1 above).

### Want to disable autostart?

```bash
/Applications/doiter.app/Contents/Resources/uninstall_autostart.sh
```

### Reset all data

```bash
rm ~/Library/Application\ Support/doiter/doiter.db
```
