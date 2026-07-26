from pathlib import Path

from mockware.yaml_reader import read_config


def test_read_basic_c(samples_dir: Path):
    config = read_config(samples_dir / "basic_c.yml")
    assert len(config.headers) == 3

    esp_err = config.headers["esp_err.h"]
    assert esp_err.language == "c"
    assert esp_err.macros["ESP_OK"].value == "0"
    assert esp_err.macros["ESP_FAIL"].value == "-1"
    assert esp_err.types["esp_err_t"].underlying == "int"

    gpio = config.headers["driver/gpio.h"]
    assert len(gpio.includes) == 1
    assert gpio.includes[0] == "esp_err.h"
    assert gpio.macros["GPIO_OUT"].value == "1"
    assert gpio.types["gpio_mode_t"].underlying == "int"

    gpio_set = gpio.functions["gpio_set_level"]
    assert gpio_set.return_type == "esp_err_t"
    assert gpio_set.params == ["int pin", "int level"]
    assert gpio_set.body == "return ESP_OK;"

    gpio_get = gpio.functions["gpio_get_level"]
    assert gpio_get.return_type == "int"
    assert gpio_get.params == ["int pin"]
    assert gpio_get.body is None

    task = config.headers["freertos/task.h"]
    assert task.macros["pdMS_TO_TICKS"].kind == "variadic"
    assert task.macros["pdMS_TO_TICKS"].body == "((x) / portTICK_PERIOD_MS)"
    vtask = task.functions["vTaskDelay"]
    assert vtask.return_type == "void"
    assert vtask.params == ["int ticks"]


def test_read_basic_cpp(samples_dir: Path):
    config = read_config(samples_dir / "basic_cpp.yml")
    assert len(config.headers) == 1

    hdr = config.headers["device/sensor.hpp"]
    assert hdr.language == "cpp"
    assert hdr.types["sensor_err_t"].underlying == "int"

    ns = hdr.namespaces["drivers"]
    assert "TemperatureSensor" in ns.classes

    cls = ns.classes["TemperatureSensor"]
    assert len(cls.constructors) == 1
    assert cls.constructors[0].params == ["int pin"]
    assert cls.constructors[0].init_list == ["pin_(pin)"]

    read_method = cls.methods["read"]
    assert read_method.return_type == "float"
    assert read_method.params == []
    assert read_method.body == "return 25.0f;"

    calibrate = cls.methods["calibrate"]
    assert calibrate.return_type == "sensor_err_t"
    assert calibrate.body is None

    static_m = cls.static_methods["get_reference_voltage"]
    assert static_m.return_type == "float"
    assert static_m.body == "return 3.3f;"

    assert cls.member_variables["pin_"] == "int"
    assert cls.member_variables["last_value_"] == "float = 0.0f"

    func = ns.functions["sensor_isr_handler"]
    assert func.return_type == "void"
    assert func.params == ["int irq", "void (*callback)(void*)"]
