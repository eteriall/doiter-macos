#!/bin/bash
# Install LaunchAgent for autostart

PLIST_NAME="com.doiter.app.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_SOURCE="/Applications/doiter.app/Contents/Resources/$PLIST_NAME"
PLIST_DEST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Copy plist file
if [ -f "$PLIST_SOURCE" ]; then
    cp "$PLIST_SOURCE" "$PLIST_DEST"
    echo "LaunchAgent installed to $PLIST_DEST"

    # Load the agent
    launchctl load "$PLIST_DEST"
    echo "doiter autostart enabled"
else
    echo "Error: Could not find $PLIST_SOURCE"
    exit 1
fi
