# Recursively collect all .c source files
file(GLOB_RECURSE SOURCES
        "Main.cpp"
        "App/*.cpp"
        "Infra/*.cpp"
        "Infra/*.c"
)

# Recursively collect all directories that contain .h files
file(GLOB_RECURSE HEADER_PATHS RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} "App/*.h" "Infra/*.h")

# Get the list of directories from header paths
set(INCLUDE_PATHS ".")
foreach (header ${HEADER_PATHS})
    get_filename_component(dir "${header}" DIRECTORY)
    message("Processing header: ${header} in directory: ${dir}")
    list(APPEND INCLUDE_PATHS "${CMAKE_CURRENT_SOURCE_DIR}/${dir}")
endforeach ()

# Remove duplicate directories
list(REMOVE_DUPLICATES INCLUDE_PATHS)

# Register the component
idf_component_register(
        SRCS ${SOURCES}
        INCLUDE_DIRS ${INCLUDE_PATHS}
        REQUIRES nvs_flash esp_driver_gpio esp_event vfs esp_timer bt json openthread mqtt esp_https_ota app_update fatfs
)
