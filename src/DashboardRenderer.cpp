#include "DashboardRenderer.h"

#include <algorithm>
#include <iomanip>
#include <iostream>
#include <string>

namespace {

// Column widths. The Name column widens to fit the longest value so no data is
// truncated (resolved decision: widen the Name column).
constexpr int kIdWidth = 6;
constexpr int kSpeedWidth = 10;
constexpr int kBatteryWidth = 8;
constexpr int kLatitudeWidth = 11;
constexpr int kLongitudeWidth = 11;
constexpr int kUpdatedWidth = 22;

std::size_t nameColumnWidth(const std::vector<Vehicle>& vehicles) {
    std::size_t width = std::string("Name").size();
    for (const Vehicle& vehicle : vehicles) {
        width = std::max(width, vehicle.name.size());
    }
    return width;
}

}  // namespace

void DashboardRenderer::renderTable(const std::vector<Vehicle>& vehicles) {
    const int nameWidth = static_cast<int>(nameColumnWidth(vehicles));

    std::cout << std::right << std::setw(kIdWidth) << "ID" << "  " << std::left
              << std::setw(nameWidth) << "Name" << "  " << std::right
              << std::setw(kSpeedWidth) << "Speed" << "  "
              << std::setw(kBatteryWidth) << "Battery" << "  "
              << std::setw(kLatitudeWidth) << "Latitude" << "  "
              << std::setw(kLongitudeWidth) << "Longitude" << "  " << std::left
              << std::setw(kUpdatedWidth) << "Last Updated" << '\n';

    std::cout << std::fixed << std::setprecision(2);
    for (const Vehicle& vehicle : vehicles) {
        std::cout << std::right << std::setw(kIdWidth) << vehicle.id << "  "
                  << std::left << std::setw(nameWidth) << vehicle.name << "  "
                  << std::right << std::setw(kSpeedWidth) << vehicle.speed
                  << "  " << std::setw(kBatteryWidth) << vehicle.battery << "  "
                  << std::setw(kLatitudeWidth) << vehicle.latitude << "  "
                  << std::setw(kLongitudeWidth) << vehicle.longitude << "  "
                  << std::left << std::setw(kUpdatedWidth)
                  << vehicle.lastUpdated << '\n';
    }
}

void DashboardRenderer::renderSummary(const FleetSummary& summary) {
    std::cout << '\n';
    std::cout << "Fleet Summary\n";
    std::cout << "  Total vehicles: " << summary.totalVehicles << '\n';
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "  Average speed:  " << summary.averageSpeed << " km/h\n";

    // Omit the warning section entirely when there are no low-battery vehicles
    // (resolved decision: omit).
    if (!summary.lowBatteryVehicles.empty()) {
        std::cout << "  Low battery vehicles ("
                  << summary.lowBatteryVehicles.size() << "):\n";
        for (const Vehicle& vehicle : summary.lowBatteryVehicles) {
            std::cout << "    - " << vehicle.name << " (id " << vehicle.id
                      << ", battery " << vehicle.battery << "%)\n";
        }
    }
}