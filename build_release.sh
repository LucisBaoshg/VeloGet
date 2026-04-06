#!/bin/bash
set -euo pipefail

# Configuration
APP_NAME="VeloGet"
APP_ID="veloget"
PROJECT_DIR=$(pwd)
BUILD_DIR="${PROJECT_DIR}/build/macos"
DIST_DIR="${PROJECT_DIR}/dist"
VENV_ACTIVATE="${PROJECT_DIR}/venv-new/bin/activate"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting VeloGet Release Build ===${NC}"

# 1. Environment Check
if [ -f "$VENV_ACTIVATE" ]; then
    source "$VENV_ACTIVATE"
else
    echo "Warning: Virtual environment not found at $VENV_ACTIVATE, using current Python environment"
fi
VERSION=$(python -c "import tomli; print(tomli.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || grep 'version =' pyproject.toml | head -n 1 | cut -d '"' -f 2)
RAW_ARCH=$(uname -m)
if [ "$RAW_ARCH" = "arm64" ] || [ "$RAW_ARCH" = "aarch64" ]; then
    ARCH="arm64"
else
    ARCH="x64"
fi
echo -e "${GREEN}Detected Version: ${VERSION}${NC}"
echo -e "${GREEN}Detected Architecture: ${ARCH}${NC}"

# 2. Cleanup
echo -e "${BLUE}Cleaning up old builds...${NC}"
rm -rf "$BUILD_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# 3. Build .app
echo -e "${BLUE}Building macOS App Bundle...${NC}"
flet build macos \
    --yes \
    --no-rich-output \
    --project "$APP_NAME" \
    --product "$APP_NAME" \
    --org com.lucifer \
    --copyright "Copyright (c) 2026 Lucifer" \
    --exclude venv-new venv-final build dist .git .github src/ytdlpgui/_internal

# 4. Create DMG
APP_PATH="${BUILD_DIR}/${APP_NAME}.app"
DMG_NAME="${APP_ID}-${VERSION}-macos-${ARCH}.dmg"
DMG_PATH="${DIST_DIR}/${DMG_NAME}"
VOL_NAME="${APP_NAME} Installer"
IN_APP_ARCHIVE="${DIST_DIR}/${APP_ID}-${VERSION}-macos-${ARCH}.app.tar.gz"

if [ ! -d "$APP_PATH" ]; then
    ALT_APP_PATH=$(find "$BUILD_DIR" -maxdepth 3 -type d -name "${APP_NAME}.app" -print -quit || true)
    if [ -n "${ALT_APP_PATH:-}" ]; then
        APP_PATH="$ALT_APP_PATH"
        echo "Resolved app bundle path dynamically: $APP_PATH"
    else
        echo "Error: App bundle not found at $APP_PATH"
        echo "Available build outputs:"
        find "$BUILD_DIR" -maxdepth 3 -print || true
        exit 1
    fi
fi

echo -e "${BLUE}Creating DMG package...${NC}"

# Create a temporary folder for DMG content
DMG_TMP="${BUILD_DIR}/dmg_tmp"
rm -rf "$DMG_TMP"
mkdir -p "$DMG_TMP"

# Copy App to temp folder
echo "Copying app to temporary DMG folder..."
# Use rsync instead of cp to handle symlinks and cycles gracefully
rsync -a "$APP_PATH" "$DMG_TMP/"

# Create /Applications link
ln -s /Applications "$DMG_TMP/Applications"

# Generate DMG using hdiutil
echo "Generating filesystem image..."
hdiutil create \
    -volname "$VOL_NAME" \
    -srcfolder "$DMG_TMP" \
    -ov -format UDZO \
    "$DMG_PATH"

# Cleanup temp
rm -rf "$DMG_TMP"

echo -e "${BLUE}Creating in-app update archive...${NC}"
APP_PARENT_DIR=$(dirname "$APP_PATH")
tar -C "$APP_PARENT_DIR" -czf "$IN_APP_ARCHIVE" "${APP_NAME}.app"

echo -e "${GREEN}=== Build Complete! ===${NC}"
echo -e "DMG Package: ${DMG_PATH}"
echo -e "In-App Update: ${IN_APP_ARCHIVE}"
echo -e "Size: $(du -sh "$DMG_PATH" | cut -f1)"
