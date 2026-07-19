#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
YAML="${PROJECT_DIR}/missing_apis.yml"

MOCK_DIR_NAME="mock-sdk"
BUILD_DIR_NAME="build"
MOCK_SDK="${PROJECT_DIR}/mock-sdk"
BUILD_SDK="${PROJECT_DIR}/build"

echo "=== Step 1: Auto-detect missing external dependencies ==="
if [ -f "$YAML" ]; then
    echo "  Existing YAML found — merging new items in partial mode."
    uv run mockware scan "$PROJECT_DIR" \
        --output "$YAML" \
        --existing "$YAML" \
        --mode partial \
        --include "**/*.c" --include "**/*.h" \
        --exclude "test/*" --exclude "$MOCK_DIR_NAME/*" --exclude "$BUILD_DIR_NAME/*" \
        --verbose
else
    uv run mockware scan "$PROJECT_DIR" \
        --output "$YAML" \
        --include "**/*.c" --include "**/*.h" \
        --exclude "test/*" --exclude "$MOCK_DIR_NAME/*" --exclude "$BUILD_DIR_NAME/*" \
        --verbose
fi

echo ""
echo "  >>> Review ${YAML} and add custom entries."
echo ""

echo "=== Step 2: Generate mock SDK ==="
uv run mockware generate \
    --project "$PROJECT_DIR" \
    --input "$YAML" \
    --output "$MOCK_SDK" \
    --verbose

echo ""
echo "=== Step 3: Build and run tests ==="
cmake -S "$PROJECT_DIR" -B "$BUILD_SDK"
cmake --build "$BUILD_SDK"
"${BUILD_SDK}/test_runner"
