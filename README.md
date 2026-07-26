# mockware

Generate mock SDK implementations for embedded unit testing from YAML templates.

Describe your external SDK headers (ESP-IDF, FreeRTOS, OpenThread, etc.) in a YAML file and mockware produces compilable stubs with overridable function pointers for C and virtual methods for C++.

## Quick start

```bash
# Download a pre-built binary from GitHub Releases:
# https://github.com/Ronika-Co/Mockware/releases
#
# Or run directly from source:
git clone https://github.com/Ronika-Co/Mockware.git
cd Mockware

# Generate mock SDK from all templates
uv run mockware generate examples/sample_project/templates/ -o mock-sdk
```

Then compile your tests with `-I mock-sdk/include` and link `mock-sdk/source/*.c`.

## Documentation

Full documentation: https://ronika-co.github.io/Mockware/

- [YAML schema reference](https://ronika-co.github.io/Mockware/yaml-reference.html)
- [Test patterns](https://ronika-co.github.io/Mockware/test-patterns.html)

## Example

```yaml
# template.yml
headers:
  "esp_err.h":
    macros:
      ESP_OK: "0"
    types:
      esp_err_t: int

  "driver/gpio.h":
    includes: ["esp_err.h"]
    functions:
      gpio_set_level:
        return: esp_err_t
        params: ["int pin", "int level"]
```

```bash
mockware generate template.yml -o mock-sdk
```

```c
// test.c
#include "mockware/fakes.h"

void test() {
    gpio_set_level_mock = &my_stub;
    gpio_set_level(1, 1);  // calls my_stub
}
```

## Development

```bash
uv sync --group dev
uv run mockware --help
uv run pytest tests/ -v
uv run ruff check src/ tests/
```
