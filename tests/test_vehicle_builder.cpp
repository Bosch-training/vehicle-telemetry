// Unit tests for VehicleBuilder (design cases VB-*).
// Design: docs/ut-design/unit-test-design.csv
// Contract: docs/swdd.md 5.2, decisions in docs/ut-design/review-decisions.json
#include "TestHarness.h"

#include <climits>
#include <limits>
#include <string>

#include "Vehicle.h"
#include "VehicleBuilder.h"

TEST_CASE("VB-POS-001", "Full fluent chain sets all fields") {
    Vehicle v = VehicleBuilder()
                    .withId(1)
                    .withName("Truck-A")
                    .withSpeed(72.5)
                    .withBattery(85)
                    .withGps(37.7749, -122.4194)
                    .withTimestamp("2026-09-28T10:00:00Z")
                    .build();
    CHECK_EQ(v.id, 1);
    CHECK_EQ(v.name, std::string("Truck-A"));
    CHECK_NEAR(v.speed, 72.5, 1e-9);
    CHECK_EQ(v.battery, 85);
    CHECK_NEAR(v.latitude, 37.7749, 1e-9);
    CHECK_NEAR(v.longitude, -122.4194, 1e-9);
    CHECK_EQ(v.lastUpdated, std::string("2026-09-28T10:00:00Z"));
}

TEST_CASE("VB-POS-002", "withGps sets both coordinates") {
    Vehicle v = VehicleBuilder().withGps(40.7128, -74.0060).build();
    CHECK_NEAR(v.latitude, 40.7128, 1e-9);
    CHECK_NEAR(v.longitude, -74.0060, 1e-9);
    CHECK_EQ(v.id, 0);
    CHECK_NEAR(v.speed, 0.0, 1e-9);
    CHECK_EQ(v.battery, 0);
    CHECK_EQ(v.name, std::string(""));
    CHECK_EQ(v.lastUpdated, std::string(""));
}

TEST_CASE("VB-POS-003", "Setter order does not matter") {
    Vehicle v = VehicleBuilder()
                    .withBattery(50)
                    .withSpeed(30.0)
                    .withId(2)
                    .withTimestamp("2026-09-28T11:00:00Z")
                    .withName("Van-B")
                    .withGps(1.0, 2.0)
                    .build();
    CHECK_EQ(v.id, 2);
    CHECK_EQ(v.name, std::string("Van-B"));
    CHECK_NEAR(v.speed, 30.0, 1e-9);
    CHECK_EQ(v.battery, 50);
    CHECK_NEAR(v.latitude, 1.0, 1e-9);
    CHECK_NEAR(v.longitude, 2.0, 1e-9);
    CHECK_EQ(v.lastUpdated, std::string("2026-09-28T11:00:00Z"));
}

TEST_CASE("VB-POS-004", "Setters return the same builder") {
    VehicleBuilder b;
    CHECK(&b.withId(1) == &b);
    CHECK(&b.withName("x") == &b);
    CHECK(&b.withSpeed(1.0) == &b);
    CHECK(&b.withBattery(1) == &b);
    CHECK(&b.withGps(0.0, 0.0) == &b);
    CHECK(&b.withTimestamp("t") == &b);
}

TEST_CASE("VB-POS-005", "build() is const and returns a copy") {
    const VehicleBuilder b =
        VehicleBuilder().withId(9).withSpeed(42.0).withName("Const-B");
    Vehicle v = b.build();
    CHECK_EQ(v.id, 9);
    CHECK_NEAR(v.speed, 42.0, 1e-9);
    v.speed = 999.0;  // mutating the copy must not affect the builder
    Vehicle again = b.build();
    CHECK_NEAR(again.speed, 42.0, 1e-9);
}

TEST_CASE("VB-NEG-001", "Negative speed") {
    Vehicle v = VehicleBuilder().withSpeed(-10.0).build();
    CHECK_NEAR(v.speed, -10.0, 1e-9);
}

TEST_CASE("VB-NEG-002", "Battery above 100") {
    Vehicle v = VehicleBuilder().withBattery(150).build();
    CHECK_EQ(v.battery, 150);
}

TEST_CASE("VB-NEG-003", "Battery below 0") {
    Vehicle v = VehicleBuilder().withBattery(-5).build();
    CHECK_EQ(v.battery, -5);
}

TEST_CASE("VB-NEG-004", "Latitude out of range") {
    Vehicle v = VehicleBuilder().withGps(200.0, 10.0).build();
    CHECK_NEAR(v.latitude, 200.0, 1e-9);
}

TEST_CASE("VB-NEG-005", "Longitude out of range") {
    Vehicle v = VehicleBuilder().withGps(10.0, -500.0).build();
    CHECK_NEAR(v.longitude, -500.0, 1e-9);
}

TEST_CASE("VB-NEG-006", "NaN speed") {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    Vehicle v = VehicleBuilder().withSpeed(nan).build();
    CHECK(v.speed != v.speed);  // NaN is not equal to itself
}

TEST_CASE("VB-EDGE-001", "Battery lower bound") {
    Vehicle v = VehicleBuilder().withBattery(0).build();
    CHECK_EQ(v.battery, 0);
}

TEST_CASE("VB-EDGE-002", "Battery upper bound") {
    Vehicle v = VehicleBuilder().withBattery(100).build();
    CHECK_EQ(v.battery, 100);
}

TEST_CASE("VB-EDGE-003", "Zero speed") {
    Vehicle v = VehicleBuilder().withSpeed(0.0).build();
    CHECK_NEAR(v.speed, 0.0, 1e-9);
}

TEST_CASE("VB-EDGE-004", "No setters called") {
    Vehicle v = VehicleBuilder().build();
    CHECK_EQ(v.id, 0);
    CHECK_EQ(v.name, std::string(""));
    CHECK_NEAR(v.speed, 0.0, 1e-9);
    CHECK_EQ(v.battery, 0);
    CHECK_NEAR(v.latitude, 0.0, 1e-9);
    CHECK_NEAR(v.longitude, 0.0, 1e-9);
    CHECK_EQ(v.lastUpdated, std::string(""));
}

TEST_CASE("VB-EDGE-005", "Only id set") {
    Vehicle v = VehicleBuilder().withId(3).build();
    CHECK_EQ(v.id, 3);
    CHECK_EQ(v.name, std::string(""));
    CHECK_NEAR(v.speed, 0.0, 1e-9);
    CHECK_EQ(v.battery, 0);
    CHECK_NEAR(v.latitude, 0.0, 1e-9);
    CHECK_NEAR(v.longitude, 0.0, 1e-9);
    CHECK_EQ(v.lastUpdated, std::string(""));
}

TEST_CASE("VB-EDGE-006", "GPS extreme valid corners") {
    Vehicle ne = VehicleBuilder().withGps(90.0, 180.0).build();
    CHECK_NEAR(ne.latitude, 90.0, 1e-9);
    CHECK_NEAR(ne.longitude, 180.0, 1e-9);
    Vehicle sw = VehicleBuilder().withGps(-90.0, -180.0).build();
    CHECK_NEAR(sw.latitude, -90.0, 1e-9);
    CHECK_NEAR(sw.longitude, -180.0, 1e-9);
}

TEST_CASE("VB-EDGE-007", "Empty name and timestamp") {
    Vehicle v = VehicleBuilder().withName("").withTimestamp("").build();
    CHECK_EQ(v.name, std::string(""));
    CHECK_EQ(v.lastUpdated, std::string(""));
}

TEST_CASE("VB-EDGE-008", "Very long name") {
    Vehicle v = VehicleBuilder().withName(std::string(1000, 'A')).build();
    CHECK_EQ(v.name.size(), static_cast<std::size_t>(1000));
}

TEST_CASE("VB-EDGE-009", "Id extremes") {
    CHECK_EQ(VehicleBuilder().withId(INT_MIN).build().id, INT_MIN);
    CHECK_EQ(VehicleBuilder().withId(-1).build().id, -1);
    CHECK_EQ(VehicleBuilder().withId(0).build().id, 0);
    CHECK_EQ(VehicleBuilder().withId(INT_MAX).build().id, INT_MAX);
}

TEST_CASE("VB-EXH-001", "All numeric fields invalid together") {
    Vehicle v = VehicleBuilder()
                    .withSpeed(-50.0)
                    .withBattery(999)
                    .withGps(-999.0, 999.0)
                    .build();
    CHECK_NEAR(v.speed, -50.0, 1e-9);
    CHECK_EQ(v.battery, 999);
    CHECK_NEAR(v.latitude, -999.0, 1e-9);
    CHECK_NEAR(v.longitude, 999.0, 1e-9);
}

TEST_CASE("VB-EXH-002", "Builder reuse after build") {
    VehicleBuilder b;
    b.withId(1).withSpeed(10.0);
    Vehicle v1 = b.build();
    b.withSpeed(20.0);
    Vehicle v2 = b.build();
    CHECK_NEAR(v1.speed, 10.0, 1e-9);
    CHECK_NEAR(v2.speed, 20.0, 1e-9);
    CHECK_EQ(v1.id, 1);
    CHECK_EQ(v2.id, 1);
}

TEST_CASE("VB-EXH-003", "Repeated setter keeps last value") {
    Vehicle v = VehicleBuilder()
                    .withBattery(30)
                    .withBattery(70)
                    .withSpeed(1.0)
                    .withSpeed(2.5)
                    .build();
    CHECK_EQ(v.battery, 70);
    CHECK_NEAR(v.speed, 2.5, 1e-9);
}

TEST_CASE("VB-EXH-004", "Two builders are independent") {
    VehicleBuilder a;
    VehicleBuilder b;
    a.withId(1);
    b.withId(2);
    Vehicle va = a.build();
    Vehicle vb = b.build();
    CHECK_EQ(va.id, 1);
    CHECK_EQ(vb.id, 2);
}

TEST_CASE("VB-EXH-005", "Boundary battery x speed x GPS grid") {
    const int batteries[] = {0, 100};
    const double speeds[] = {0.0, 200.0};
    const double lats[] = {0.0, 90.0};
    const double lons[] = {0.0, 180.0};
    for (int battery : batteries) {
        for (double speed : speeds) {
            for (double lat : lats) {
                for (double lon : lons) {
                    Vehicle v = VehicleBuilder()
                                    .withBattery(battery)
                                    .withSpeed(speed)
                                    .withGps(lat, lon)
                                    .build();
                    CHECK_EQ(v.battery, battery);
                    CHECK_NEAR(v.speed, speed, 1e-9);
                    CHECK_NEAR(v.latitude, lat, 1e-9);
                    CHECK_NEAR(v.longitude, lon, 1e-9);
                }
            }
        }
    }
}