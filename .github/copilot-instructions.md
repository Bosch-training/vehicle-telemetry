# Project Name

Vehicle Telemetry Visualization

## Description

A C++-only console prototype that ingests mock vehicle telemetry (speed, battery level, GPS coordinates) and visualizes it for fleet operators as a formatted terminal dashboard. Built as a GitHub Copilot training example demonstrating the Builder, Repository, and Singleton design patterns.

Non-goals: no GUI/web frontend, no real map rendering, no file I/O or database, no real-time looping (single-pass render only), no third-party libraries, no unit tests in initial scope.

See [docs/requirements.md](../docs/requirements.md) for full functional requirements and verification criteria.

## Tech Stack

- **Language:** C++17
- **Build system:** CMake
- **Dependencies:** None — C++ standard library only (dependency-free, offline-friendly build)

## Design Pattern

Already chosen (per [docs/requirements.md](../docs/requirements.md)):

- **Builder** — `VehicleBuilder` constructs `Vehicle` objects via fluent setters (`withId()`, `withSpeed()`, `withBattery()`, `withGps()`, `withTimestamp()`, `build()`)
- **Repository** — `VehicleRepository` owns an in-memory `std::vector<Vehicle>`; exposes `getAll()` and `getById(id)`
- **Singleton** — `TelemetryService::getInstance()` provides a single fleet-wide service instance that computes aggregations (`getFleetSummary()`)

## Language Versions & Libraries

| Component | Version/Library | Source |
|-----------|-----------------|--------|
| C++ standard | C++17 | `CMakeLists.txt` |
| Build tool | CMake | `CMakeLists.txt` |
| Compiler flags | `-Wall -Wextra` | [docs/requirements.md](../docs/requirements.md) |
| Third-party libs | None (standard library only) | [docs/requirements.md](../docs/requirements.md) |

## Coding Standards

- Compile clean with `-Wall -Wextra`, no warnings.
- One class per header/source pair (e.g. `VehicleBuilder.h`/`.cpp`).
- PascalCase for class names, camelCase for methods/variables, matching existing pattern names (`VehicleBuilder`, `getFleetSummary`).
- Keep patterns explicit and visible — this is a teaching artifact, prefer clarity over cleverness.
- No third-party dependencies; use only the C++ standard library.

## Sample Test Code

No unit tests are in the initial scope. If added later, prefer a header-only framework to keep the dependency-free build intact, e.g.:

```cpp
// tests/test_vehicle_builder.cpp (example only — not yet in scope)
#include <cassert>
#include "VehicleBuilder.h"

void test_builder_sets_fields() {
    Vehicle v = VehicleBuilder().withId(1).withSpeed(60.0).build();
    assert(v.id == 1);
    assert(v.speed == 60.0);
}
```

## Folder Structure

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

## Sensitive Data Handling

- All telemetry in this prototype is hardcoded mock data — no real vehicle, location, or personal data is used.
- No file I/O, database, or external network calls, so there is no persisted or transmitted sensitive data in this scope.
- If real data sources are integrated later: never commit `.env`/credential files (only `.env.example` is allowed), encrypt any real location/PII data at rest and in transit, and avoid logging sensitive data in plaintext.