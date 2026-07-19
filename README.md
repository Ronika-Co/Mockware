# mockware

**Generate mock SDK layers for embedded unit testing.**

Embedded code depends on hardware SDKs (WiFi, GPIO, NVS, FreeRTOS, etc.).
Unit testing without real hardware requires faking these APIs —
manually writing stubs is tedious and brittle. `mockware` automates it:

Scan your project → auto-detect which external headers are missing →
infer stubs, types, macros, enums, and structs from usage context →
generate compilable fakes with overridable function pointers.

---

## How it works

```
                    ┌──────────────────────────────────────┐
                    │           missing_apis.yml            │
                    │  headers:  {esp_wifi.h → includes}   │
                    │  types:    {esp_err_t → int}          │
                    │  macros:   {ESP_OK → "0"}             │
                    │  enums:    {wifi_mode_t → values}    │
                    │  structs:  {config_t → definition}   │
                    │  functions:{esp_wifi_start → params} │
                    └──────────────────┬───────────────────┘
                                      │
          ┌───────────────────────────┴───────────────────────────┐
          │                   mockware generate                   │
          └───────────────────────────┬───────────────────────────┘
                                      │
          ┌───────────────────────────┴───────────────────────────┐
          │                     mock-sdk/                          │
          │  ├── CMakeLists.txt                                   │
          │  ├── include/                                         │
          │  │   ├── esp_wifi.h          (per-header stub)        │
          │  │   ├── freertos/Freertos.h (nested-path stub)       │
          │  │   └── mockware/                                    │
          │  │       ├── types.h         (typedef defs)           │
          │  │       ├── macros.h        (#define macros)         │
          │  │       ├── enums.h         (enum defs)              │
          │  │       ├── structs.h       (struct defs)            │
          │  │       └── fakes.h         (function pointers)      │
          │  └── source/                                          │
          │      ├── esp_wifi.c          (per-header stub)        │
          │      ├── freertos/Freertos.c (nested-path impl)       │
          │      └── general.c           (untagged functions)     │
          └───────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python >= 3.10
- [`uv`](https://docs.astral.sh/uv/) (recommended)

### Install from source

```bash
cd /path/to/mockware
uv tool install .
```

Or run directly without installing:

```bash
cd /path/to/mockware
uv run mockware --help
```

---

## Usage

### 1. Scan — auto-detect missing external dependencies

```bash
mockware scan /path/to/project -o missing_apis.yml
```

Scans source files for `#include` directives and finds headers that
**don't exist** in your project tree or include paths. These are
external SDK dependencies. The inferred result is a YAML file with
six sections:

| Section      | Content |
|-------------|---------|
| `headers`   | Each missing header path and its transitive `includes` |
| `types`     | Unknown type references mapped to `int` (edit as needed) |
| `macros`    | ALL_CAPS identifiers used in expressions |
| `enums`     | `typedef enum { ... } name;` from your code |
| `structs`   | `struct { ... }` definitions from your code |
| `functions` | Inferred function names with arg counts and `header:` attribution |

**Important:** Project-internal types, enums, structs, and functions
are automatically filtered out — only external SDK symbols appear
in the YAML. The `--exclude` pattern is passed to
`scan_project_symbols()`, so generated SDK directories
(e.g. `mock-sdk/**`) can be excluded to prevent their types from
being treated as project-internal.

#### Options

| Flag | Description |
|------|-------------|
| `--mode full` | Generate complete YAML from scratch |
| `--mode partial` | Merge newly discovered deps into existing YAML (default) |
| `--existing file.yml` | Existing YAML to merge into (for `--mode partial`) |
| `-I /path/to/include` | Extra directories to check for "present" headers |
| `--include "*.c"` | Source file patterns to scan (repeatable) |
| `--exclude "mock-sdk/**"` | Glob patterns to exclude (repeatable) |
| `-v` / `--verbose` | Detailed progress output |

#### Re-scanning (merge workflow)

```bash
# First scan
mockware scan ./project -o missing_apis.yml

# Edit missing_apis.yml — add custom types, macros, etc.

# Re-scan: merges new detections, preserves your edits
mockware scan ./project \
    --existing missing_apis.yml --mode partial \
    --exclude "mock-sdk/**" --exclude "build/**"
```

The `parse` command is an alias and behaves identically.

### 2. Edit the YAML

The scanned YAML is a starting point. Common edits:

```yaml
# Fix return types
functions:
  nvs_flash_init:
    return: esp_err_t          # ← was "int"

# Add function-like macros
macros:
  pdMS_TO_TICKS: (x) ((uint64_t)x)   # → #define pdMS_TO_TICKS(x) ((uint64_t)x)

# Add header attribution for functions
  vTaskDelay:
    return: int
    params: [uint64_t arg]
    header: freertos/Freertos.h    # → lands in source/freertos/Freertos.c

# Add include dependencies
headers:
  esp_wifi.h:
    includes: [esp_err.h]          # → #include "esp_err.h" in stub
```

### 3. Generate — create the mock SDK

```bash
mockware generate \
    --project /path/to/project \
    --input missing_apis.yml \
    --output mock-sdk
```

Scans your project for `#include` directives, looks them up in the
YAML `headers` section, expands transitive includes, and writes a
complete mock SDK tree.

#### Output structure

```
mock-sdk/
├── CMakeLists.txt
├── include/
│   ├── esp_err.h              # per-header stub
│   ├── esp_wifi.h
│   ├── freertos/Freertos.h    # nested-path stub
│   ├── nvs_flash.h
│   └── mockware/
│       ├── types.h             # typedef defs
│       ├── macros.h            # #define macros (with function-like support)
│       ├── enums.h             # enum defs
│       ├── structs.h           # struct defs
│       └── fakes.h             # extern function-pointer declarations
└── source/
    ├── esp_wifi.c              # per-header implementation
    ├── freertos/Freertos.c     # nested-path implementation
    ├── general.c               # untagged function implementations
    └── nvs_flash.c
```

#### Features

**Standard type includes** — The generator scans types, function
params/returns, macro values, and struct definitions for standard
C types (`uint64_t`, `size_t`, `bool`, `FILE`, etc.) and
automatically adds the required `#include <stdint.h>`,
`#include <stddef.h>`, etc. to `mockware/types.h`. All generated
stubs and fakes include `types.h`, so standard types are always
available.

**Function-like macros** — YAML macro values starting with `(`
are emitted as `#define NAME(value)` without a space between the
name and the opening parenthesis. Example:

```yaml
# YAML
pdMS_TO_TICKS: (x) ((uint64_t)x)
```
Generates: `#define pdMS_TO_TICKS(x) ((uint64_t)x)`

#### Options

| Flag | Description |
|------|-------------|
| `--custom-impl /path` | Directory with user-provided `.c` overrides |
| `-v` / `--verbose` | Detailed progress output |

### 4. Link in your test build

```cmake
# In your test CMakeLists.txt
add_subdirectory(mock-sdk)

target_include_directories(my_test PRIVATE mock-sdk/include)
target_link_libraries(my_test PRIVATE app mock_sdk)
```

Then write tests using the generated `mockware/fakes.h`:

```c
#include <assert.h>
#include "wifi_manager.h"
#include "mockware/fakes.h"

static int mock_nvs_init(void) { return 0; }

void test_wifi(void) {
    nvs_flash_init_mock = mock_nvs_init;
    esp_wifi_start_mock = my_custom_start;
    assert(wifi_manager_start() == 0);
}
```

---

## YAML Knowledge Base Format

```yaml
headers:
  esp_wifi.h:
    includes: [esp_err.h]
  freertos/Freertos.h:
    includes: []

types:
  esp_err_t: int

macros:
  ESP_OK: "0"
  ESP_FAIL: "-1"
  pdMS_TO_TICKS: (x) ((uint64_t)x)      # function-like (no space)

enums:
  wifi_mode_t:
    values:
      WIFI_MODE_NULL: 0
      WIFI_MODE_STA: 1

structs:
  wifi_init_config_t:
    definition: |
      typedef struct { int member; } wifi_init_config_t;

functions:
  esp_wifi_init:
    return: int
    params: ["wifi_init_config_t* config"]
    header: esp_wifi.h
    body: "return 0;"
  vTaskDelay:
    return: int
    params: ["uint64_t arg"]
    header: freertos/Freertos.h
```

### Sections reference

| Section | Key format | Value format |
|---------|-----------|-------------|
| `headers` | Header path string | `{includes: [list of transitive deps]}` |
| `types` | Type name | Underlying type string (e.g. `"int"`) |
| `macros` | Macro name | Value string; if starts with `(` → function-like (no space) |
| `enums` | Enum type name | `{values: {name: int_or_str, ...}}` |
| `structs` | Struct name | `{definition: "typedef struct { ... } name;"}` |
| `functions` | Function name | `{return:, params: [str], header:, body:}` |

### Function fields

| Field | Required | Description |
|-------|----------|-------------|
| `return` | Yes | Return type string (defaults to `"void"`) |
| `params` | Yes | List of typed parameters, e.g. `["int x", "void* buf"]` |
| `header` | No | Header path for attribution. Missing → `source/general.c` |
| `body` | No | Custom stub body. Default: `return 0;` (or NULL for pointers) |
| `kind` | No | `"inline"` for static inline functions (body is the full declaration) |

---

## Writing Tests with Custom Fakes

Every generated stub function `foo` produces:

- `foo_default()` — default implementation returning 0/NULL
- `foo_mock` — overridable function pointer (declared `extern` in `fakes.h`)
- `foo()` — public function that delegates to `foo_mock`

### Example

**Production code** (`wifi_manager.c`):
```c
#include "esp_wifi.h"
#include "nvs_flash.h"

int wifi_manager_start(void) {
    esp_err_t ret;
    ret = nvs_flash_init();
    if (ret != ESP_OK) return -1;
    ret = esp_wifi_start();
    if (ret != ESP_OK) return -1;
    return 0;
}
```

**Test code** (`test_wifi_manager.c`):
```c
#include <assert.h>
#include "wifi_manager.h"
#include "mockware/fakes.h"

static int mock_nvs_init(void) { return 0; }
static int mock_wifi_ok(void) { return 0; }
static int mock_wifi_fail(void) { return -1; }

void test_start_success(void) {
    nvs_flash_init_mock = mock_nvs_init;
    esp_wifi_start_mock = mock_wifi_ok;
    assert(wifi_manager_start() == 0);
}

void test_start_wifi_fail(void) {
    nvs_flash_init_mock = mock_nvs_init;
    esp_wifi_start_mock = mock_wifi_fail;
    assert(wifi_manager_start() == -1);
}
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| `implicit declaration of function 'vTaskDelay'` | Function not attributed to a header in YAML | Add `header: freertos/Freertos.h` to the function entry |
| `unknown type name 'uint64_t'` | Standard types used in params/macros but not defined | The generator auto-adds `#include <stdint.h>` to `types.h` — ensure you re-generate |
| Generated YAML has my own types/enums | `scan_project_symbols` found them in your project headers | These are automatically filtered. If they still appear, check that `--exclude` patterns exclude generated SDK directories |
| Macros missing from YAML after editing | Your edits were overwritten by a fresh scan | Use `--existing <yaml> --mode partial` for re-scans (never a full scan over an edited YAML) |
| Function-like macro has space: `#define FOO (x)` | Macro value doesn't start with `(` | Change YAML value to start with `(` e.g. `FOO: '(x)'` |

---

## Development

```bash
uv sync                     # install dependencies
uv run mockware --help      # test the CLI
uv run pytest               # run tests (81+ tests)
```

## Sample project

```bash
cd examples/sample_project
bash run_test.sh
```
