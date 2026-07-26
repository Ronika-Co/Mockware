#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

SCRIPT_DIR="$(pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."
TEMPLATES_DIR="${PROJECT_DIR}/templates"
MOCK_SDK="${PROJECT_DIR}/mock-sdk"
BUILD_DIR="${SCRIPT_DIR}/build"

echo "=== mockware example: build and run tests ==="
echo ""

# Step 1: Generate mock SDK from all template files
echo "--- Step 1: Generate mock SDK ---"
uv run mockware generate "${TEMPLATES_DIR}" -o "${MOCK_SDK}" --verbose
echo ""

# Step 2: Build tests with CMake
echo "--- Step 2: Build tests ---"
cmake -B "${BUILD_DIR}" -S .
cmake --build "${BUILD_DIR}" -j "$(nproc)"
echo ""

# Step 3: Run tests
echo "--- Step 3: Run tests ---"
cd "${BUILD_DIR}"
ctest --output-on-failure
