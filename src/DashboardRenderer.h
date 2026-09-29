#pragma once

#include <vector>

#include "TelemetryService.h"
#include "Vehicle.h"

// Presentation layer (SWDD 5.5): stateless static methods that render the
// dashboard to stdout. No side effects beyond stdout.
class DashboardRenderer {
public:
    static void renderTable(const std::vector<Vehicle>& vehicles);
    static void renderSummary(const FleetSummary& summary);
};