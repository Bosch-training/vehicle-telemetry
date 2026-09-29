// Unit tests for DashboardRenderer (design cases DR-*).
// Design: docs/ut-design/unit-test-design.csv
// Contract: docs/swdd.md 5.5, decisions in docs/ut-design/review-decisions.json
//
// This translation unit provides the harness main().
#define TEST_HARNESS_MAIN
#include "TestHarness.h"

#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

#include "DashboardRenderer.h"
#include "TelemetryService.h"
#include "Vehicle.h"

namespace {

template <typename Fn>
std::string captureStdout(Fn fn) {
    std::ostringstream captured;
    std::streambuf* oldBuf = std::cout.rdbuf(captured.rdbuf());
    fn();
    std::cout.rdbuf(oldBuf);
    return captured.str();
}

template <typename Fn>
std::string captureStderr(Fn fn) {
    std::ostringstream captured;
    std::streambuf* oldBuf = std::cerr.rdbuf(captured.rdbuf());
    fn();
    std::cerr.rdbuf(oldBuf);
    return captured.str();
}

// Every line of a rendered table must have the same width (aligned columns).
bool linesAreAligned(const std::string& text) {
    std::istringstream stream(text);
    std::string line;
    std::size_t width = 0;
    bool first = true;
    while (std::getline(stream, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (first) {
            width = line.size();
            first = false;
        } else if (line.size() != width) {
            return false;
        }
    }
    return !first;
}

std::size_t countLines(const std::string& text) {
    std::istringstream stream(text);
    std::string line;
    std::size_t count = 0;
    while (std::getline(stream, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (!line.empty()) {
            ++count;
        }
    }
    return count;
}

Vehicle makeVehicle(int id, const std::string& name, double speed, int battery,
                    double lat, double lon, const std::string& ts) {
    Vehicle v{};
    v.id = id;
    v.name = name;
    v.speed = speed;
    v.battery = battery;
    v.latitude = lat;
    v.longitude = lon;
    v.lastUpdated = ts;
    return v;
}

std::vector<Vehicle> typicalFleet() {
    return {
        makeVehicle(1, "Truck-A", 72.5, 85, 37.7749, -122.4194, "2026-09-28T10:00:00Z"),
        makeVehicle(2, "Van-B", 48.0, 15, 40.7128, -74.0060, "2026-09-28T10:01:00Z"),
        makeVehicle(3, "Car-C", 60.25, 55, 51.5074, -0.1278, "2026-09-28T10:02:00Z"),
        makeVehicle(4, "Bus-D", 35.75, 8, 48.8566, 2.3522, "2026-09-28T10:03:00Z"),
        makeVehicle(5, "Bike-E", 12.5, 100, 35.6762, 139.6503, "2026-09-28T10:04:00Z"),
    };
}

}  // namespace

TEST_CASE("DR-POS-001", "Table for typical fleet") {
    const std::vector<Vehicle> fleet = typicalFleet();
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(countLines(out) >= fleet.size() + 1);  // header + one row per vehicle
    CHECK(linesAreAligned(out));
    for (const Vehicle& v : fleet) {
        CHECK(out.find(v.name) != std::string::npos);
    }
}

TEST_CASE("DR-POS-002", "Table header column order") {
    const std::vector<Vehicle> fleet = {typicalFleet().front()};
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    const std::size_t id = out.find("ID");
    CHECK(id != std::string::npos);
    const std::size_t name = out.find("Name", id);
    CHECK(name != std::string::npos);
    const std::size_t speed = out.find("Speed", name);
    CHECK(speed != std::string::npos);
    const std::size_t battery = out.find("Battery", speed);
    CHECK(battery != std::string::npos);
    const std::size_t latitude = out.find("Latitude", battery);
    CHECK(latitude != std::string::npos);
    const std::size_t longitude = out.find("Longitude", latitude);
    CHECK(longitude != std::string::npos);
    const std::size_t updated = out.find("Last Updated", longitude);
    CHECK(updated != std::string::npos);
}

TEST_CASE("DR-POS-003", "Table shows every field value") {
    const Vehicle v =
        makeVehicle(1, "Truck-A", 72.5, 85, 37.7749, -122.4194, "2026-09-28T10:00:00Z");
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable({v}); });
    CHECK(out.find("Truck-A") != std::string::npos);
    CHECK(out.find("72.5") != std::string::npos);
    CHECK(out.find("85") != std::string::npos);
    CHECK(out.find("37.77") != std::string::npos);   // fixed precision of 2 decimals
    CHECK(out.find("-122.42") != std::string::npos);
    CHECK(out.find("2026-09-28T10:00:00Z") != std::string::npos);
}

TEST_CASE("DR-POS-004", "Summary for typical fleet") {
    FleetSummary summary{};
    summary.totalVehicles = 6;
    summary.averageSpeed = 55.3;
    summary.lowBatteryVehicles = {typicalFleet()[1], typicalFleet()[3]};
    const std::string out = captureStdout([&] { DashboardRenderer::renderSummary(summary); });
    CHECK(out.find("6") != std::string::npos);
    CHECK(out.find("55.3") != std::string::npos);
    CHECK(out.find("Van-B") != std::string::npos);
    CHECK(out.find("Bus-D") != std::string::npos);
}

TEST_CASE("DR-POS-005", "Summary appears below table") {
    const std::vector<Vehicle> fleet = typicalFleet();
    FleetSummary summary{};
    summary.totalVehicles = static_cast<int>(fleet.size());
    summary.averageSpeed = 55.3;
    summary.lowBatteryVehicles = {fleet[1]};

    const std::string summaryText =
        captureStdout([&] { DashboardRenderer::renderSummary(summary); });
    const std::string tableText =
        captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    const std::string combined = captureStdout([&] {
        DashboardRenderer::renderTable(fleet);
        DashboardRenderer::renderSummary(summary);
    });

    // The combined stream must start with the table and the summary must begin
    // at the point where the table output ends.
    CHECK_EQ(combined.substr(0, tableText.size()), tableText);
    const std::size_t summaryPos = combined.find(summaryText);
    CHECK(summaryPos != std::string::npos);
    if (summaryPos != std::string::npos) {
        CHECK(summaryPos >= tableText.size());
    }
    const std::size_t lastNamePos = combined.rfind(fleet.back().name);
    CHECK(lastNamePos != std::string::npos);
    if (lastNamePos != std::string::npos && summaryPos != std::string::npos) {
        CHECK(lastNamePos < summaryPos);
    }
}

TEST_CASE("DR-POS-006", "Renderer output only to stdout") {
    const std::vector<Vehicle> fleet = typicalFleet();
    FleetSummary summary{};
    summary.totalVehicles = static_cast<int>(fleet.size());
    summary.averageSpeed = 55.3;
    summary.lowBatteryVehicles = {fleet[0]};
    const std::string err = captureStderr([&] {
        captureStdout([&] {
            DashboardRenderer::renderTable(fleet);
            DashboardRenderer::renderSummary(summary);
        });
    });
    CHECK(err.empty());
}

TEST_CASE("DR-NEG-001", "Summary with no low-battery vehicles") {
    FleetSummary summary{};
    summary.totalVehicles = 6;
    summary.averageSpeed = 55.3;
    summary.lowBatteryVehicles = {};
    const std::string withEmpty = captureStdout([&] {
        DashboardRenderer::renderSummary(summary);
    });
    FleetSummary withList = summary;
    withList.lowBatteryVehicles = {typicalFleet()[1]};
    const std::string withEntry = captureStdout([&] {
        DashboardRenderer::renderSummary(withList);
    });
    CHECK(countLines(withEmpty) < countLines(withEntry));  // warning section omitted
    CHECK(withEmpty.find("55.3") != std::string::npos);
}

TEST_CASE("DR-NEG-002", "Summary with zero total") {
    FleetSummary summary{};
    summary.totalVehicles = 0;
    summary.averageSpeed = 0.0;
    summary.lowBatteryVehicles = {};
    const std::string out = captureStdout([&] { DashboardRenderer::renderSummary(summary); });
    CHECK(out.find("0") != std::string::npos);
    CHECK(out.find("0.00") != std::string::npos);
}

TEST_CASE("DR-NEG-003", "Negative speed and out-of-range battery") {
    const std::vector<Vehicle> fleet = {
        makeVehicle(1, "X", -5.0, 150, 0.0, 0.0, "t1"),
        makeVehicle(2, "Y", 10.0, -1, 0.0, 0.0, "t2"),
    };
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(out.find("-5.00") != std::string::npos);
    CHECK(out.find("150") != std::string::npos);
    CHECK(out.find("-1") != std::string::npos);
    CHECK(linesAreAligned(out));
}

TEST_CASE("DR-NEG-004", "NaN average speed") {
    FleetSummary summary{};
    summary.totalVehicles = 2;
    summary.averageSpeed = std::numeric_limits<double>::quiet_NaN();
    summary.lowBatteryVehicles = {};
    const std::string out = captureStdout([&] { DashboardRenderer::renderSummary(summary); });
    CHECK(out.find("nan") != std::string::npos);  // literal nan (decision: literal)
}

TEST_CASE("DR-EDGE-001", "Empty vehicle list") {
    const std::string out = captureStdout([&] {
        DashboardRenderer::renderTable(std::vector<Vehicle>{});
    });
    CHECK(out.find("ID") != std::string::npos);  // header row is printed
    CHECK(countLines(out) == 1);                 // header only, no data rows
}

TEST_CASE("DR-EDGE-002", "Single vehicle") {
    const std::string out = captureStdout([&] {
        DashboardRenderer::renderTable({typicalFleet().front()});
    });
    CHECK(countLines(out) == 2);  // header + one data row
    CHECK(linesAreAligned(out));
}

TEST_CASE("DR-EDGE-003", "Long vehicle name") {
    const std::vector<Vehicle> fleet = {
        makeVehicle(1, "Extremely-Long-Fleet-Vehicle-Name-001", 1.0, 50, 0.0, 0.0, "t1"),
        makeVehicle(2, "A", 2.0, 60, 0.0, 0.0, "t2"),
    };
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(out.find("Extremely-Long-Fleet-Vehicle-Name-001") != std::string::npos);
    CHECK(linesAreAligned(out));  // table widens uniformly to fit the longest name
}

TEST_CASE("DR-EDGE-004", "Multi-digit ids") {
    const std::vector<Vehicle> fleet = {
        makeVehicle(1, "A", 1.0, 10, 0.0, 0.0, "t1"),
        makeVehicle(12, "B", 2.0, 20, 0.0, 0.0, "t2"),
        makeVehicle(123456, "C", 3.0, 30, 0.0, 0.0, "t3"),
    };
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(linesAreAligned(out));
}

TEST_CASE("DR-EDGE-005", "Average speed precision") {
    FleetSummary summary{};
    summary.totalVehicles = 3;
    summary.averageSpeed = 55.333333333;
    summary.lowBatteryVehicles = {};
    const std::string out = captureStdout([&] { DashboardRenderer::renderSummary(summary); });
    CHECK(out.find("55.33") != std::string::npos);
}

TEST_CASE("DR-EDGE-006", "Zero and full battery rows") {
    const std::vector<Vehicle> fleet = {
        makeVehicle(1, "A", 1.0, 0, 0.0, 0.0, "t1"),
        makeVehicle(2, "B", 2.0, 100, 0.0, 0.0, "t2"),
    };
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(linesAreAligned(out));
}

TEST_CASE("DR-EDGE-007", "Extreme coordinates") {
    const std::vector<Vehicle> fleet = {
        makeVehicle(1, "A", 1.0, 10, -90.0, -180.0, "t1"),
        makeVehicle(2, "B", 2.0, 20, 90.0, 180.0, "t2"),
        makeVehicle(3, "C", 3.0, 30, 0.0, 0.0, "t3"),
    };
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(linesAreAligned(out));
}

TEST_CASE("DR-EDGE-008", "Empty name and timestamp") {
    const std::vector<Vehicle> fleet = {makeVehicle(1, "", 1.0, 10, 0.0, 0.0, "")};
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(linesAreAligned(out));
}

TEST_CASE("DR-EDGE-009", "Very large speed") {
    const std::vector<Vehicle> fleet = {
        makeVehicle(1, "A", 99999.9, 10, 0.0, 0.0, "t1"),
        makeVehicle(2, "B", 1.0, 20, 0.0, 0.0, "t2"),
    };
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(linesAreAligned(out));
}

TEST_CASE("DR-EXH-001", "Mixed short and long fields") {
    const std::vector<Vehicle> fleet = {
        makeVehicle(1, "A", 1.0, 1, 0.0, 0.0, "t1"),
        makeVehicle(123456, "Far-Longer-Vehicle-Name-ZZZ", 12345.75, 100, -180.0, 179.99, "t2"),
        makeVehicle(42, "Mixed", 500.5, 55, 12.34, -56.78, "t3"),
    };
    const std::string out = captureStdout([&] { DashboardRenderer::renderTable(fleet); });
    CHECK(linesAreAligned(out));
}

TEST_CASE("DR-EXH-002", "Low list size matches") {
    const std::vector<Vehicle> fleet = typicalFleet();
    FleetSummary allLow{};
    allLow.totalVehicles = static_cast<int>(fleet.size());
    allLow.averageSpeed = 55.0;
    allLow.lowBatteryVehicles = fleet;
    const std::string allOut = captureStdout([&] {
        DashboardRenderer::renderSummary(allLow);
    });
    for (const Vehicle& v : fleet) {
        CHECK(allOut.find(v.name) != std::string::npos);
    }

    FleetSummary noneLow = allLow;
    noneLow.lowBatteryVehicles = {};
    const std::string noneOut = captureStdout([&] {
        DashboardRenderer::renderSummary(noneLow);
    });
    for (const Vehicle& v : fleet) {
        CHECK(noneOut.find(v.name) == std::string::npos);
    }
}

TEST_CASE("DR-EXH-003", "Many low-battery vehicles") {
    std::vector<Vehicle> low;
    for (int i = 0; i < 50; ++i) {
        std::ostringstream name;
        name << "LOW-" << std::setw(2) << std::setfill('0') << i;
        low.push_back(makeVehicle(1000 + i, name.str(), 10.0, 5, 0.0, 0.0, "t"));
    }
    FleetSummary summary{};
    summary.totalVehicles = 50;
    summary.averageSpeed = 10.0;
    summary.lowBatteryVehicles = low;
    const std::string out = captureStdout([&] { DashboardRenderer::renderSummary(summary); });
    for (const Vehicle& v : low) {
        CHECK(out.find(v.name) != std::string::npos);
    }
}

TEST_CASE("DR-EXH-004", "Full service output end-to-end") {
    TelemetryService& svc = TelemetryService::getInstance();
    const std::vector<Vehicle>& fleet = svc.getRepository().getAll();
    FleetSummary summary = svc.getFleetSummary();
    const std::string out = captureStdout([&] {
        DashboardRenderer::renderTable(fleet);
        DashboardRenderer::renderSummary(summary);
    });
    CHECK(countLines(out) >= fleet.size() + 1);
    for (const Vehicle& v : summary.lowBatteryVehicles) {
        CHECK(out.find(v.name) != std::string::npos);
    }
    CHECK_EQ(summary.totalVehicles, static_cast<int>(fleet.size()));
}

TEST_CASE("DR-EXH-005", "Repeated rendering is deterministic") {
    const std::vector<Vehicle> fleet = typicalFleet();
    FleetSummary summary{};
    summary.totalVehicles = static_cast<int>(fleet.size());
    summary.averageSpeed = 55.3;
    summary.lowBatteryVehicles = {fleet[1]};
    const std::string first = captureStdout([&] {
        DashboardRenderer::renderTable(fleet);
        DashboardRenderer::renderSummary(summary);
    });
    const std::string second = captureStdout([&] {
        DashboardRenderer::renderTable(fleet);
        DashboardRenderer::renderSummary(summary);
    });
    CHECK_EQ(first, second);
}