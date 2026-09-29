# Vehicle Telemetry Visualization — Requirements

## Overview
A C++-only console prototype that ingests mock vehicle telemetry (speed, battery level, GPS coordinates) and visualizes it for fleet operators as a formatted terminal dashboard. Built as a GitHub Copilot training example demonstrating Builder, Repository, and Singleton design patterns.

## Goals
- Demonstrate a clean, layered C++ architecture using well-known design patterns
- Provide a fast (1-2 hour), dependency-free build that works in locked-down/offline environments
- Serve as a teaching artifact for a GitHub Copilot training course

## Non-Goals
- No GUI (Qt, SFML, Dear ImGui) or web frontend
- No real map/GPS rendering — latitude/longitude shown as plain numeric columns
- No file I/O, database, or external data ingestion
- No real-time/looping telemetry simulation (single-pass render only; looping is an optional stretch goal)
- No third-party libraries — C++ standard library only
- No unit tests in initial scope

## Functional Requirements
1. System holds a fleet of 5-8 mock vehicles, each with: id, name, speed (km/h), battery level (%), latitude, longitude, last-updated timestamp
2. System computes fleet-wide aggregates: total vehicle count, average speed, list of vehicles with low battery (threshold configurable, e.g. <20%)
3. System renders a fixed-width ASCII table of all vehicles with aligned columns: ID | Name | Speed | Battery | Latitude | Longitude | Last Updated
4. System renders a fleet summary section below the table showing count, average speed, and a low-battery warning list
5. Program builds and runs as a single executable with no external runtime dependencies

## Architecture / Design Patterns
- **Builder pattern** — `VehicleBuilder` constructs `Vehicle` objects via fluent setters (`withId()`, `withSpeed()`, `withBattery()`, `withGps()`, `withTimestamp()`, `build()`)
- **Repository pattern** — `VehicleRepository` owns an in-memory `std::vector<Vehicle>`; exposes `getAll()` and `getById(id)`; hides storage details from consumers
- **Singleton pattern** — `TelemetryService::getInstance()` provides a single fleet-wide service instance that owns the repository and computes aggregations (`getFleetSummary()`)

## Project Structure
```
vehicle-telemetry-visualization/
├── CMakeLists.txt                  # C++17, single executable target, -Wall -Wextra
├── README.md                       # Architecture, patterns, build/run instructions, Copilot teaching notes
└── src/
    ├── main.cpp                    # Entry point: fetch service instance, render dashboard
    ├── Vehicle.h                   # Vehicle data struct (id, name, speed, battery, lat, long, lastUpdated)
    ├── VehicleBuilder.h/.cpp       # Builder pattern
    ├── VehicleRepository.h/.cpp    # Repository pattern (in-memory mock data)
    ├── TelemetryService.h/.cpp     # Singleton (fleet aggregation logic)
    └── DashboardRenderer.h/.cpp    # ASCII table + fleet summary rendering
```

## Build & Run
```
cmake -S . -B build
cmake --build build
./build/vehicle_telemetry
```

## Verification Criteria
1. Clean compile with `-Wall -Wextra`, no warnings
2. Binary output shows a correctly aligned ASCII table for all mock vehicles
3. Fleet average speed and low-battery count match manual calculation from hardcoded data
4. `TelemetryService::getInstance()` returns the same instance across multiple calls
5. README accurately documents the architecture and pattern placement

## Stretch Goals (optional, out of initial scope)
- Real-time loop simulating telemetry updates every N seconds (clear + redraw console)
- ANSI escape-code coloring for low-battery warning rows
