#!/usr/bin/env bash
set -euo pipefail

IDF_PATH="${IDF_PATH:-/opt/esp-idf}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
YAML="${PROJECT_DIR}/known_apis.yml"
MOCK_SDK="${PROJECT_DIR}/mock-sdk"
BUILD_DIR="${PROJECT_DIR}/build"

echo "=== Step 1: Parse ESP-IDF headers into YAML ==="
mockware parse "$IDF_PATH" \
    --output "$YAML" \
    --components "esp_wifi,nvs_flash,esp_common,esp_event" \
    --verbose

echo ""
echo "=== Step 2: Generate mock SDK ==="
mockware generate \
    --project "$PROJECT_DIR" \
    --input "$YAML" \
    --output "$MOCK_SDK" \
    --verbose

echo ""
echo "=== Step 3: Build and run tests ==="
cmake -S "$PROJECT_DIR" -B "$BUILD_DIR"
cmake --build "$BUILD_DIR"
"${BUILD_DIR}/test_runner"
