#include "DashboardRenderer.h"
#include "TelemetryService.h"

// Entry point: fetch the singleton service, render the table, then the summary.
int main() {
    auto& service = TelemetryService::getInstance();
    DashboardRenderer::renderTable(service.getRepository().getAll());
    DashboardRenderer::renderSummary(service.getFleetSummary());
    return 0;
}