#!/bin/zsh

# Stop on first error
set -e

# --- Configuration ---
APP_NAME="REAtcMARK"
BUILD_DIR="build"
APP_BUNDLE_PATH="${BUILD_DIR}/${APP_NAME}.app"

# --- Architecture Specific Naming ---
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    ARCH_SUFFIX="-AppleSilicon"
elif [ "$ARCH" = "x86_64" ]; then
    ARCH_SUFFIX="-Intel"
else
    ARCH_SUFFIX="-unknown"
fi

DMG_TEMP_DIR="${BUILD_DIR}/dmg_temp"
FINAL_DMG_PATH="${BUILD_DIR}/${APP_NAME}${ARCH_SUFFIX}.dmg"

echo "--- Starting DMG Creation for ${APP_NAME} (${ARCH}) ---"

# --- 1. Deep Sign the Application Bundle ---
# This is the crucial first step. We sign everything inside the .app
echo "--> Step 1: Applying a deep ad-hoc signature with entitlements and timestamp..."
codesign --force --deep --sign - --entitlements entitlements.plist --timestamp "${APP_BUNDLE_PATH}"
echo "--> Signature applied."

# --- 2. Prepare the DMG Folder ---
# Clean up any previous attempts and create a fresh folder.
echo "--> Step 2: Preparing temporary directory..."
rm -rf "${DMG_TEMP_DIR}" "${FINAL_DMG_PATH}"
mkdir -p "${DMG_TEMP_DIR}"
echo "--> Temporary directory created at ${DMG_TEMP_DIR}"

# --- 3. Copy Application to Temp Folder ---
echo "--> Step 3: Copying .app bundle..."
cp -R "${APP_BUNDLE_PATH}" "${DMG_TEMP_DIR}"
echo "--> App copied."

# --- 4. Add a Link to the /Applications folder ---
# This gives the user the familiar "drag to install" experience.
echo "--> Step 4: Creating link to /Applications..."
ln -s /Applications "${DMG_TEMP_DIR}/Applications"
echo "--> Link created."

# --- 5. Create the Disk Image ---
# We use hdiutil to create the DMG from our temp folder.
echo "--> Step 5: Creating the disk image..."
hdiutil create -srcfolder "${DMG_TEMP_DIR}" \
               -volname "${APP_NAME}" \
               -fs HFS+ \
               -fsargs "-c c=64,a=16,e=16" \
               -format UDZO \
               -imagekey zlib-level=9 \
               -o "${FINAL_DMG_PATH}"

echo "--> DMG created."

# --- 6. Clean Up ---
echo "--> Step 6: Cleaning up temporary files..."
rm -rf "${DMG_TEMP_DIR}"
echo "--> Cleanup complete."

echo ""
echo "--- SUCCESS! ---"
echo "Distributable disk image created at: ${FINAL_DMG_PATH}"
echo "" 