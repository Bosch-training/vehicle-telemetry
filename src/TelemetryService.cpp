#include "TelemetryService.h"

TelemetryService& TelemetryService::getInstance() {
    static TelemetryService instance;
    return instance;
}

const VehicleRepository& TelemetryService::getRepository() const {
    return repository_;
}

FleetSummary TelemetryService::getFleetSummary(int lowBatteryThreshold) const {
    FleetSummary summary;
    const std::vector<Vehicle>& vehicles = repository_.getAll();
    summary.totalVehicles = static_cast<int>(vehicles.size());

    double speedSum = 0.0;
    for (const Vehicle& vehicle : vehicles) {
        speedSum += vehicle.speed;
        if (vehicle.battery < lowBatteryThreshold) {
            summary.lowBatteryVehicles.push_back(vehicle);
        }
    }

    // Guard against division by zero for robustness (SWDD 7).
    summary.averageSpeed =
        summary.totalVehicles > 0 ? speedSum / summary.totalVehicles : 0.0;
    return summary;
}