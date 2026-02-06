#!/bin/bash
set -e

# Configuration
APP_NAME="VeloGet"
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
if [ ! -f "$VENV_ACTIVATE" ]; then
    echo "Error: Virtual environment not found at $VENV_ACTIVATE"
    exit 1
fi

source "$VENV_ACTIVATE"
VERSION=$(python -c "import tomli; print(tomli.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>/dev/null || grep 'version =' pyproject.toml | head -n 1 | cut -d '"' -f 2)
echo -e "${GREEN}Detected Version: ${VERSION}${NC}"

# 2. Cleanup
echo -e "${BLUE}Cleaning up old builds...${NC}"
rm -rf "$BUILD_DIR"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

# 3. Build .app
echo -e "${BLUE}Building macOS App Bundle...${NC}"
flet build macos \
    --project "$APP_NAME" \
    --product "$APP_NAME" \
    --org com.lucifer \
    --copyright "Copyright (c) 2026 Lucifer" \
    --exclude venv-new venv-final build dist .git .github

# 4. Create DMG
APP_PATH="${BUILD_DIR}/${APP_NAME}.app"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
DMG_PATH="${DIST_DIR}/${DMG_NAME}"
VOL_NAME="${APP_NAME} Installer"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: App bundle not found at $APP_PATH"
    exit 1
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

echo -e "${GREEN}=== Build Complete! ===${NC}"
echo -e "DMG Package: ${DMG_PATH}"
echo -e "Size: $(du -sh "$DMG_PATH" | cut -f1)"
