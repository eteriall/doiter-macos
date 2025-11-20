#!/bin/bash
# Uninstall LaunchAgent for autostart

PLIST_NAME="com.doiter.app.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

# Unload the agent if it's loaded
if [ -f "$PLIST_DEST" ]; then
    launchctl unload "$PLIST_DEST" 2>/dev/null
    rm "$PLIST_DEST"
    echo "doiter autostart disabled and removed"
else
    echo "LaunchAgent not found"
fi
