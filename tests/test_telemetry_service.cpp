// Unit tests for TelemetryService (design cases TS-*).
// Design: docs/ut-design/unit-test-design.csv
// Contract: docs/swdd.md 5.4, decisions in docs/ut-design/review-decisions.json
#include "TestHarness.h"

#include <climits>
#include <type_traits>
#include <vector>

#include "TelemetryService.h"
#include "Vehicle.h"
#include "VehicleRepository.h"

namespace {

int minSeededBattery() {
    int minBattery = INT_MAX;
    for (const Vehicle& v : TelemetryService::getInstance().getRepository().getAll()) {
        if (v.battery < minBattery) {
            minBattery = v.battery;
        }
    }
    return minBattery;
}

int maxSeededBattery() {
    int maxBattery = INT_MIN;
    for (const Vehicle& v : TelemetryService::getInstance().getRepository().getAll()) {
        if (v.battery > maxBattery) {
            maxBattery = v.battery;
        }
    }
    return maxBattery;
}

}  // namespace

TEST_CASE("TS-POS-001", "Singleton identity") {
    CHECK(&TelemetryService::getInstance() == &TelemetryService::getInstance());
}

TEST_CASE("TS-POS-002", "Summary total count") {
    TelemetryService& svc = TelemetryService::getInstance();
    FleetSummary summary = svc.getFleetSummary();
    CHECK_EQ(summary.totalVehicles,
             static_cast<int>(svc.getRepository().getAll().size()));
}

TEST_CASE("TS-POS-003", "Summary average speed") {
    TelemetryService& svc = TelemetryService::getInstance();
    const std::vector<Vehicle>& all = svc.getRepository().getAll();
    double sum = 0.0;
    for (const Vehicle& v : all) {
        sum += v.speed;
    }
    const double expected = all.empty() ? 0.0 : sum / static_cast<double>(all.size());
    CHECK_NEAR(svc.getFleetSummary().averageSpeed, expected, 1e-9);
}

TEST_CASE("TS-POS-004", "Default low-battery threshold is 20") {
    TelemetryService& svc = TelemetryService::getInstance();
    FleetSummary withDefault = svc.getFleetSummary();
    FleetSummary withTwenty = svc.getFleetSummary(20);
    CHECK_EQ(withDefault.lowBatteryVehicles.size(), withTwenty.lowBatteryVehicles.size());
    for (std::size_t i = 0; i < withDefault.lowBatteryVehicles.size(); ++i) {
        CHECK_EQ(withDefault.lowBatteryVehicles[i].id, withTwenty.lowBatteryVehicles[i].id);
    }
    for (const Vehicle& v : withDefault.lowBatteryVehicles) {
        CHECK(v.battery < 20);
    }
}

TEST_CASE("TS-POS-005", "getRepository returns the owned repository") {
    TelemetryService& svc = TelemetryService::getInstance();
    CHECK(&svc.getRepository() == &svc.getRepository());
}

TEST_CASE("TS-POS-006", "getFleetSummary is const and repeatable") {
    TelemetryService& svc = TelemetryService::getInstance();
    FleetSummary s1 = svc.getFleetSummary();
    FleetSummary s2 = svc.getFleetSummary();
    CHECK_EQ(s1.totalVehicles, s2.totalVehicles);
    CHECK_NEAR(s1.averageSpeed, s2.averageSpeed, 1e-9);
    CHECK_EQ(s1.lowBatteryVehicles.size(), s2.lowBatteryVehicles.size());
}

TEST_CASE("TS-NEG-001", "Negative threshold") {
    FleetSummary summary = TelemetryService::getInstance().getFleetSummary(-10);
    CHECK(summary.lowBatteryVehicles.empty());
}

TEST_CASE("TS-NEG-002", "Threshold above 100") {
    TelemetryService& svc = TelemetryService::getInstance();
    FleetSummary summary = svc.getFleetSummary(150);
    CHECK_EQ(summary.lowBatteryVehicles.size(),
             static_cast<std::size_t>(summary.totalVehicles));
}

TEST_CASE("TS-NEG-003", "Copy construction is disabled") {
    static_assert(!std::is_copy_constructible_v<TelemetryService>,
                  "TelemetryService must not be copy-constructible");
    CHECK(true);
}

TEST_CASE("TS-NEG-004", "Copy assignment is disabled") {
    static_assert(!std::is_copy_assignable_v<TelemetryService>,
                  "TelemetryService must not be copy-assignable");
    CHECK(true);
}

TEST_CASE("TS-NEG-005", "Constructor is not public") {
    static_assert(!std::is_default_constructible_v<TelemetryService>,
                  "TelemetryService must not be default-constructible");
    CHECK(true);
}

TEST_CASE("TS-EDGE-001", "Threshold 0") {
    FleetSummary summary = TelemetryService::getInstance().getFleetSummary(0);
    CHECK(summary.lowBatteryVehicles.empty());
}

TEST_CASE("TS-EDGE-002", "Threshold 100") {
    TelemetryService& svc = TelemetryService::getInstance();
    FleetSummary summary = svc.getFleetSummary(100);
    std::size_t expected = 0;
    for (const Vehicle& v : svc.getRepository().getAll()) {
        if (v.battery < 100) {
            ++expected;
        }
    }
    CHECK_EQ(summary.lowBatteryVehicles.size(), expected);
    for (const Vehicle& v : summary.lowBatteryVehicles) {
        CHECK(v.battery < 100);
    }
}

TEST_CASE("TS-EDGE-003", "Threshold equals a seeded battery value") {
    TelemetryService& svc = TelemetryService::getInstance();
    const std::vector<Vehicle>& all = svc.getRepository().getAll();
    const Vehicle& target = all.front();
    const int t = target.battery;

    FleetSummary atThreshold = svc.getFleetSummary(t);
    for (const Vehicle& v : atThreshold.lowBatteryVehicles) {
        CHECK(v.id != target.id);  // strict less-than excludes the boundary vehicle
    }

    FleetSummary aboveThreshold = svc.getFleetSummary(t + 1);
    bool included = false;
    for (const Vehicle& v : aboveThreshold.lowBatteryVehicles) {
        if (v.id == target.id) {
            included = true;
        }
    }
    CHECK(included);
}

// TC-SKIP: TS-EDGE-004 SWDD 5.3 defines no test seam; an empty fleet is not constructible.
// TC-SKIP: TS-EDGE-005 SWDD 5.3 defines no test seam; a single-vehicle fleet is not constructible.
// TC-SKIP: TS-EDGE-006 SWDD 5.3 defines no test seam; an all-zero-speed fleet is not constructible.
// TC-SKIP: TS-EDGE-007 SWDD 5.3 defines no test seam; a custom battery-0 fleet is not constructible.
// TC-SKIP: TS-EXH-003 SWDD 5.3 defines no test seam; a custom battery set is not constructible.

TEST_CASE("TS-EDGE-008", "INT_MIN and INT_MAX thresholds") {
    TelemetryService& svc = TelemetryService::getInstance();
    CHECK(svc.getFleetSummary(INT_MIN).lowBatteryVehicles.empty());
    FleetSummary all = svc.getFleetSummary(INT_MAX);
    CHECK_EQ(all.lowBatteryVehicles.size(), static_cast<std::size_t>(all.totalVehicles));
}

TEST_CASE("TS-EXH-001", "All vehicles below threshold") {
    TelemetryService& svc = TelemetryService::getInstance();
    FleetSummary summary = svc.getFleetSummary(maxSeededBattery() + 1);
    const std::vector<Vehicle>& all = svc.getRepository().getAll();
    CHECK_EQ(summary.lowBatteryVehicles.size(), all.size());
    for (std::size_t i = 0; i < all.size(); ++i) {
        CHECK_EQ(summary.lowBatteryVehicles[i].id, all[i].id);
    }
}

TEST_CASE("TS-EXH-002", "No vehicles below threshold") {
    FleetSummary summary =
        TelemetryService::getInstance().getFleetSummary(minSeededBattery());
    CHECK(summary.lowBatteryVehicles.empty());
}

TEST_CASE("TS-EXH-004", "Threshold sweep") {
    TelemetryService& svc = TelemetryService::getInstance();
    std::size_t previous = 0;
    for (int t = 0; t <= 101; ++t) {
        const std::size_t count = svc.getFleetSummary(t).lowBatteryVehicles.size();
        CHECK(count >= previous);  // monotonic non-decreasing
        previous = count;
    }
    CHECK_EQ(svc.getFleetSummary(0).lowBatteryVehicles.size(), static_cast<std::size_t>(0));
    CHECK_EQ(svc.getFleetSummary(101).lowBatteryVehicles.size(),
             svc.getRepository().getAll().size());
}

TEST_CASE("TS-EXH-005", "Repeated getInstance stability") {
    const TelemetryService* a = &TelemetryService::getInstance();
    const TelemetryService* b = &TelemetryService::getInstance();
    const TelemetryService* c = &TelemetryService::getInstance();
    const TelemetryService* d = &TelemetryService::getInstance();
    const TelemetryService* e = &TelemetryService::getInstance();
    CHECK(a == b);
    CHECK(b == c);
    CHECK(c == d);
    CHECK(d == e);
}

TEST_CASE("TS-EXH-006", "Low list is a subset of the fleet") {
    TelemetryService& svc = TelemetryService::getInstance();
    FleetSummary summary = svc.getFleetSummary(50);
    for (const Vehicle& v : summary.lowBatteryVehicles) {
        std::optional<Vehicle> found = svc.getRepository().getById(v.id);
        CHECK(found.has_value());
        if (found.has_value()) {
            CHECK_EQ(found->id, v.id);
            CHECK_EQ(found->name, v.name);
            CHECK_NEAR(found->speed, v.speed, 1e-9);
            CHECK_EQ(found->battery, v.battery);
        }
    }
}