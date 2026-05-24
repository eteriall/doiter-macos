#!/bin/bash
# Create DMG installer for doiter

set -e

APP_NAME="doiter"
VERSION="1.0.0"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
DMG_TMP_NAME="${APP_NAME}-tmp.dmg"
VOLUME_NAME="${APP_NAME}"
SOURCE_FOLDER="dist"
APP_PATH="${SOURCE_FOLDER}/${APP_NAME}.app"

echo "Creating DMG installer for ${APP_NAME}..."

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: App bundle not found at $APP_PATH"
    echo "Please run ./build.sh first"
    exit 1
fi

# Clean old DMG files
rm -f "$DMG_NAME" "$DMG_TMP_NAME"

# Create temporary DMG
echo "Creating temporary DMG..."
hdiutil create -srcfolder "$APP_PATH" \
    -volname "$VOLUME_NAME" \
    -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" \
    -format UDRW \
    -size 100m \
    "$DMG_TMP_NAME"

# Mount the temporary DMG
echo "Mounting temporary DMG..."
MOUNT_DIR=$(hdiutil attach -readwrite -noverify -noautoopen "$DMG_TMP_NAME" | grep -E '^/dev/' | sed 1q | awk '{print $3}')

echo "Mounted at: $MOUNT_DIR"

# Create Applications symlink
echo "Creating Applications symlink..."
ln -s /Applications "$MOUNT_DIR/Applications"

# Set up the DMG window appearance
echo "Setting DMG appearance..."
echo '
   tell application "Finder"
     tell disk "'$VOLUME_NAME'"
           open
           set current view of container window to icon view
           set toolbar visible of container window to false
           set statusbar visible of container window to false
           set the bounds of container window to {100, 100, 600, 400}
           set viewOptions to the icon view options of container window
           set arrangement of viewOptions to not arranged
           set icon size of viewOptions to 72
           delay 1
           close
     end tell
   end tell
' | osascript || true

# Give Finder time to complete
sync

# Unmount
echo "Unmounting temporary DMG..."
hdiutil detach "$MOUNT_DIR" || true

# Convert to final compressed DMG
echo "Converting to final DMG..."
hdiutil convert "$DMG_TMP_NAME" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "$DMG_NAME"

# Clean up temporary DMG
rm -f "$DMG_TMP_NAME"

echo ""
echo "DMG created successfully: $DMG_NAME"
echo ""
echo "To install:"
echo "  1. Open $DMG_NAME"
echo "  2. Drag doiter.app to Applications folder"
echo "  3. Run: /Applications/doiter.app/Contents/Resources/install_autostart.sh"
