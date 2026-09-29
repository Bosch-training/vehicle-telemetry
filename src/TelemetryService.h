#pragma once

#include <vector>

#include "Vehicle.h"
#include "VehicleRepository.h"

// Fleet-wide aggregates computed by TelemetryService (SWDD 5.4).
struct FleetSummary {
    int totalVehicles = 0;
    double averageSpeed = 0.0;
    std::vector<Vehicle> lowBatteryVehicles;
};

// Singleton pattern (SWDD 5.4): Meyers' singleton guarantees one fleet-wide
// service instance. Copy construction/assignment are deleted; the default
// constructor is private.
class TelemetryService {
public:
    static TelemetryService& getInstance();

    const VehicleRepository& getRepository() const;
    FleetSummary getFleetSummary(int lowBatteryThreshold = 20) const;

    TelemetryService(const TelemetryService&) = delete;
    TelemetryService& operator=(const TelemetryService&) = delete;

private:
    TelemetryService() = default;

    VehicleRepository repository_;
};