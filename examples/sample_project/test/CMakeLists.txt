cmake_minimum_required(VERSION 3.15)
project(mockware_example_tests C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Fetch Google Test
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.15.0
)
FetchContent_MakeAvailable(googletest)

# Paths
set(MOCK_SDK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../mock-sdk")
set(PROJECT_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/..")

# Collect mock SDK sources
file(GLOB_RECURSE MOCK_SOURCES "${MOCK_SDK_DIR}/source/*.c" "${MOCK_SDK_DIR}/source/*.cpp")
file(GLOB_RECURSE PROJECT_SOURCES "${PROJECT_SRC_DIR}/main/Infra/*.cpp")

# Create test executable
add_executable(mockware_tests
    ${PROJECT_SOURCES}
    ${MOCK_SOURCES}
    TestNvsStorage.cpp
    TestTimerAdapter.cpp
    TestUtils.cpp
    TestConfigStorage.cpp
    TestWifiService.cpp
    TestNetworkService.cpp
    TestOpenThreadService.cpp
    TestTimeService.cpp
    TestSPIService.cpp
)

target_include_directories(mockware_tests PRIVATE
    "${MOCK_SDK_DIR}/include"
    "${PROJECT_SRC_DIR}/main"
    "${PROJECT_SRC_DIR}/main/App"
    "${PROJECT_SRC_DIR}/main/Infra"
)

target_link_libraries(mockware_tests PRIVATE GTest::gtest_main GTest::gmock)

# Discover tests
include(CTest)
include(GoogleTest)
gtest_discover_tests(mockware_tests)
