#!/bin/bash
# Build script for doiter

set -e

echo "Building doiter..."

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the app with py2app
echo "Building macOS app bundle..."
python3 setup.py py2app

echo "Build complete! App bundle is in dist/doiter.app"

# Make scripts executable
chmod +x dist/doiter.app/Contents/Resources/install_autostart.sh
chmod +x dist/doiter.app/Contents/Resources/uninstall_autostart.sh

echo ""
echo "To test the app, run:"
echo "  ./dist/doiter.app/Contents/MacOS/doiter"
echo ""
echo "To install to /Applications:"
echo "  cp -r dist/doiter.app /Applications/"
echo "  /Applications/doiter.app/Contents/Resources/install_autostart.sh"
