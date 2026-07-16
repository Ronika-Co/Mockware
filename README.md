# mockware

**Generate mock SDK layers for embedded unit testing.**

Embedded code depends on hardware (WiFi, GPIO, NVS, etc.). Unit testing
without real hardware requires faking these APIs — manually writing stubs
is tedious and brittle. `mockware` automates it in two phases:

### How it works

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  ESP-IDF     │     │  known_apis.yml   │     │  Your Project        │
│  components/ │────>│  (YAML knowledge  │<────│  #include "driver/   │
│  headers     │     │   base)           │     │         gpio.h"      │
└──────────────┘     └────────┬─────────┘     └──────────┬───────────┘
                              │                           │
                              ▼                           ▼
                     ┌─────────────────────────────────────────┐
                    │         mockware generate                │
                    └──────────────────┬──────────────────────┘
                                       ▼
              ┌──────────────────────────────────────────────┐
              │  mock-sdk/                                    │
              │  ├── include/                                 │
              │  │   ├── esp_err.h          (stub header)     │
              │  │   ├── esp_wifi.h         (stub header)     │
              │  │   ├── nvs_flash.h        (stub header)     │
              │  │   ├── esp_err_fakes.h    (extern _fp decls)│
              │  │   ├── esp_wifi_fakes.h   (extern _fp decls)│
              │  │   └── nvs_flash_fakes.h  (extern _fp decls)│
              │  ├── source/                                  │
              │  │   ├── esp_err.c          (stub impl + fp)  │
              │  │   ├── esp_wifi.c         (stub impl + fp)  │
              │  │   └── nvs_flash.c        (stub impl + fp)  │
              │  └── CMakeLists.txt         (library target)  │
              └──────────────────────────────────────────────┘
                                       │
                                       ▼
              ┌──────────────────────────────────────────────┐
              │  cmake -B build && cmake --build build        │
              │  ./build/test_runner                          │
              └──────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python >= 3.10
- `gcc` (used as the C preprocessor for header parsing)
- [`uv`](https://docs.astral.sh/uv/)

### Install

```bash
# From the repository root
uv tool install .
```

Or run directly without installing:

```bash
uv run mockware --help
```

---

## Usage

### 1. Parse — build the YAML knowledge base

```bash
mockware parse $IDF_PATH -o known_apis.yml
```

Scans all ESP-IDF component headers, extracts macros, types, enums,
structs, and function declarations, and writes them to `known_apis.yml`.

Options:
| Flag | Description |
|---|---|
| `--components esp_wifi,nvs_flash` | Only parse specific components |
| `-I /path/to/extra/includes` | Extra include paths for the preprocessor |
| `--verbose` | Detailed progress output |

### 2. Generate — create the mock SDK

```bash
mockware generate \
    --project /path/to/your/project \
    --input known_apis.yml \
    --output mock-sdk
```

Scans your project for `#include` directives referencing SDK headers,
looks them up in the YAML, and generates a complete mock SDK tree.

Options:
| Flag | Description |
|---|---|
| `--idf-path $IDF_PATH` | Auto-discover component-to-header mappings |
| `--custom-impl /path` | Directory with user-provided implementation overrides |
| `--verbose` | Detailed progress output |

### 3. Link in your test build

```cmake
# In your test CMakeLists.txt
add_subdirectory(mock-sdk)
target_link_libraries(my_test PRIVATE mock_sdk)
```

---

## Writing Tests with Custom Fakes

Every generated stub function has a corresponding function pointer
`<name>_fp` that you can reassign in your tests. Instead of hand-writing
`extern` declarations for each one, include the per-component
``<component>_fakes.h`` header that mockware generates.

### Example

**Production code** (`wifi_manager.c`):
```c
#include "esp_wifi.h"
#include "nvs_flash.h"

void start_wifi(void) {
    nvs_flash_init();
    esp_wifi_start();
}
```

**Test code** (`test_wifi_manager.c`):
```c
#include <assert.h>
#include "wifi_manager.h"
#include "esp_wifi_fakes.h"    // ← one include replaces all externs
#include "nvs_flash_fakes.h"

static esp_err_t mock_flash_init(void) { return ESP_OK; }
static esp_err_t mock_wifi_start(void) { return ESP_OK; }

int main(void) {
    // Install fakes — _fp symbols are already declared via the includes
    nvs_flash_init_fp = mock_flash_init;
    esp_wifi_start_fp = mock_wifi_start;

    // Run the code-under-test — it calls the fakes
    start_wifi();

    // If you want a function to fail:
    esp_wifi_start_fp = []() -> esp_err_t { return ESP_FAIL; };
    start_wifi();  // exercises error path

    return 0;
}
```

---

## YAML Knowledge Base Format

```yaml
headers:
  "esp_err.h":
    includes: []
    macros:
      ESP_OK: "0"
      ESP_FAIL: "-1"
    types:
      esp_err_t: "int"
    functions:
      esp_err_to_name:
        return: "const char*"
        params: ["esp_err_t err"]
        body: "return \"mock\";"

  "driver/gpio.h":
    includes:
      - "esp_err.h"
    macros:
      GPIO_NUM_0: "0"
    enums:
      gpio_mode_t:
        values:
          GPIO_MODE_INPUT: 0
          GPIO_MODE_OUTPUT: 1
    types:
      gpio_num_t: "int"
    structs:
      gpio_config_t:
        definition: |
          typedef struct {
              uint64_t pin_bit_mask;
              gpio_mode_t mode;
          } gpio_config_t;
    functions:
      gpio_set_direction:
        return: "esp_err_t"
        params:
          - "gpio_num_t gpio_num"
          - "gpio_mode_t mode"
```

---

## Example Project

See [`examples/sample_project/`](examples/sample_project/) for a complete
walkthrough:

```bash
cd examples/sample_project
bash run_test.sh
```

---

## Limitations

- **Conditional compilation**: `#ifdef` paths are resolved during parsing.
  Run `parse` with different `-D` flags for different configurations.
- **GCC extensions**: pycparser cannot handle all GCC extensions.
  The tool strips common ones (`__attribute__`, `__asm__`, etc.) before
  parsing. If you encounter unsupported constructs, please open an issue.
- **Static inline functions**: These are captured as raw text and
  reproduced verbatim in generated headers. They are **not** overridable
  via function pointers (by C language rules).

---

## Development

```bash
uv sync                     # install dependencies
uv run mockware --help  # test the CLI
uv run pytest               # run tests
```
