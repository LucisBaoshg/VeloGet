# Windows Build Script for VeloGet
$ErrorActionPreference = "Stop"

$APP_NAME = "VeloGet"
$PROJECT_DIR = Get-Location
$BUILD_DIR = Join-Path $PROJECT_DIR "build"
$DIST_DIR = Join-Path $PROJECT_DIR "dist"
$VENV_ACTIVATE = Join-Path $PROJECT_DIR "venv-new\Scripts\Activate.ps1"

Write-Host "=== Starting VeloGet Release Build (Windows) ===" -ForegroundColor Cyan

# 1. Environment Check
if (-not (Test-Path $VENV_ACTIVATE)) {
    Write-Error "Virtual environment not found at $VENV_ACTIVATE"
}

# Activate Venv
. $VENV_ACTIVATE

# Get Version
$VERSION = python -c "import tomli; print(tomli.load(open('pyproject.toml', 'rb'))['project']['version'])" 2>$null
if (-not $VERSION) {
    # Fallback grep-like
    $VERSION = (Get-Content pyproject.toml | Select-String 'version = "').ToString().Split('"')[1]
}
Write-Host "Detected Version: $VERSION" -ForegroundColor Green

# 2. Cleanup
Write-Host "Cleaning up old builds..." -ForegroundColor Cyan
if (Test-Path $BUILD_DIR) { Remove-Item -Recurse -Force $BUILD_DIR }
if (Test-Path $DIST_DIR) { Remove-Item -Recurse -Force $DIST_DIR }
New-Item -ItemType Directory -Force -Path $DIST_DIR | Out-Null

# 3. Check/Prepare Binaries
# Ensure ffmpeg.exe is in src/ytdlpgui/_internal
$INTERNAL_DIR = Join-Path $PROJECT_DIR "src\ytdlpgui\_internal"
$FFMPEG_EXE = Join-Path $INTERNAL_DIR "ffmpeg.exe"

if (-not (Test-Path $FFMPEG_EXE)) {
    Write-Warning "ffmpeg.exe not found in $INTERNAL_DIR"
    Write-Warning "Build will proceed, but user must install FFmpeg manually or via App."
} else {
    Write-Host "Found bundled ffmpeg.exe" -ForegroundColor Green
}

# 4. Build
Write-Host "Building Windows App..." -ForegroundColor Cyan
# exclude venv and build artifacts
flet build windows `
    --project "$APP_NAME" `
    --product "$APP_NAME" `
    --org "com.lucifer" `
    --copyright "Copyright (c) 2026 Lucifer" `
    --exclude venv-new venv-final build dist .git .github

# 5. Package (Zip)
$TARGET_BUILD = Join-Path $BUILD_DIR "windows"
if (Test-Path $TARGET_BUILD) {
    $ZIP_NAME = "$APP_NAME-Windows-$VERSION.zip"
    $ZIP_PATH = Join-Path $DIST_DIR $ZIP_NAME
    
    Write-Host "Creating Zip Package: $ZIP_PATH" -ForegroundColor Cyan
    Compress-Archive -Path "$TARGET_BUILD\*" -DestinationPath $ZIP_PATH -Force
    
    Write-Host "=== Build Complete! ===" -ForegroundColor Green
    Write-Host "Output: $ZIP_PATH"
} else {
    Write-Error "Build failed? Output directory not found."
}
