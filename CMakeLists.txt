cmake_minimum_required(VERSION 3.16)
project(vehicle_telemetry LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Verification Criteria 1: clean compile with -Wall -Wextra, no warnings.
add_compile_options(-Wall -Wextra)

# Core library: everything except main.cpp, so the test binary can link it.
add_library(vehicle_telemetry_core STATIC
    src/VehicleBuilder.cpp
    src/VehicleRepository.cpp
    src/TelemetryService.cpp
    src/DashboardRenderer.cpp
)
target_include_directories(vehicle_telemetry_core PUBLIC src)

# Single executable target (FR5: no external runtime dependencies).
add_executable(vehicle_telemetry src/main.cpp)
target_link_libraries(vehicle_telemetry PRIVATE vehicle_telemetry_core)

# Unit tests. `include(CTest)` defines the BUILD_TESTING option (default ON).
include(CTest)
if(BUILD_TESTING)
    add_executable(vehicle_tests
        tests/test_vehicle_builder.cpp
        tests/test_vehicle_repository.cpp
        tests/test_telemetry_service.cpp
        tests/test_dashboard_renderer.cpp
    )
    target_include_directories(vehicle_tests PRIVATE tests)
    target_link_libraries(vehicle_tests PRIVATE vehicle_telemetry_core)

    add_test(NAME vehicle_tests COMMAND vehicle_tests)
endif()