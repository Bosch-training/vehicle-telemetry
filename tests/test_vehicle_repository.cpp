// Unit tests for VehicleRepository (design cases VR-*).
// Design: docs/ut-design/unit-test-design.csv
// Contract: docs/swdd.md 5.3, decisions in docs/ut-design/review-decisions.json
#include "TestHarness.h"

#include <climits>
#include <set>
#include <vector>

#include "Vehicle.h"
#include "VehicleRepository.h"

TEST_CASE("VR-POS-001", "getAll returns seeded fleet") {
    VehicleRepository repo;
    const std::vector<Vehicle>& all = repo.getAll();
    CHECK(all.size() >= 5);
    CHECK(all.size() <= 8);
    for (const Vehicle& v : all) {
        CHECK(!v.name.empty());
        CHECK(!v.lastUpdated.empty());
    }
}

TEST_CASE("VR-POS-002", "getById finds first seeded vehicle") {
    VehicleRepository repo;
    const Vehicle& first = repo.getAll().front();
    std::optional<Vehicle> found = repo.getById(first.id);
    CHECK(found.has_value());
    if (found.has_value()) {
        CHECK_EQ(found->id, first.id);
        CHECK_EQ(found->name, first.name);
        CHECK_NEAR(found->speed, first.speed, 1e-9);
        CHECK_EQ(found->battery, first.battery);
        CHECK_NEAR(found->latitude, first.latitude, 1e-9);
        CHECK_NEAR(found->longitude, first.longitude, 1e-9);
        CHECK_EQ(found->lastUpdated, first.lastUpdated);
    }
}

TEST_CASE("VR-POS-003", "getById result matches every field") {
    VehicleRepository repo;
    const std::vector<Vehicle>& all = repo.getAll();
    const Vehicle& v = all[all.size() / 2];
    std::optional<Vehicle> found = repo.getById(v.id);
    CHECK(found.has_value());
    if (found.has_value()) {
        CHECK_EQ(found->id, v.id);
        CHECK_EQ(found->name, v.name);
        CHECK_NEAR(found->speed, v.speed, 1e-9);
        CHECK_EQ(found->battery, v.battery);
        CHECK_NEAR(found->latitude, v.latitude, 1e-9);
        CHECK_NEAR(found->longitude, v.longitude, 1e-9);
        CHECK_EQ(found->lastUpdated, v.lastUpdated);
    }
}

TEST_CASE("VR-POS-004", "Seeded ids are unique") {
    VehicleRepository repo;
    std::set<int> ids;
    for (const Vehicle& v : repo.getAll()) {
        ids.insert(v.id);
    }
    CHECK_EQ(ids.size(), repo.getAll().size());
}

TEST_CASE("VR-POS-005", "Seeded values are in valid ranges") {
    VehicleRepository repo;
    for (const Vehicle& v : repo.getAll()) {
        CHECK(v.speed >= 0.0);
        CHECK(v.battery >= 0);
        CHECK(v.battery <= 100);
        CHECK(v.latitude >= -90.0);
        CHECK(v.latitude <= 90.0);
        CHECK(v.longitude >= -180.0);
        CHECK(v.longitude <= 180.0);
    }
}

TEST_CASE("VR-NEG-001", "getById unknown id") {
    VehicleRepository repo;
    CHECK(!repo.getById(9999).has_value());
}

TEST_CASE("VR-NEG-002", "getById negative id") {
    VehicleRepository repo;
    CHECK(!repo.getById(-1).has_value());
}

TEST_CASE("VR-NEG-003", "getById zero id") {
    VehicleRepository repo;
    CHECK(!repo.getById(0).has_value());
}

TEST_CASE("VR-NEG-004", "getById id just beyond last") {
    VehicleRepository repo;
    int maxId = INT_MIN;
    for (const Vehicle& v : repo.getAll()) {
        if (v.id > maxId) {
            maxId = v.id;
        }
    }
    CHECK(!repo.getById(maxId + 1).has_value());
}

TEST_CASE("VR-EDGE-001", "getById first id") {
    VehicleRepository repo;
    int minId = INT_MAX;
    for (const Vehicle& v : repo.getAll()) {
        if (v.id < minId) {
            minId = v.id;
        }
    }
    std::optional<Vehicle> found = repo.getById(minId);
    CHECK(found.has_value());
    if (found.has_value()) {
        CHECK_EQ(found->id, minId);
    }
}

TEST_CASE("VR-EDGE-002", "getById last id") {
    VehicleRepository repo;
    int maxId = INT_MIN;
    for (const Vehicle& v : repo.getAll()) {
        if (v.id > maxId) {
            maxId = v.id;
        }
    }
    std::optional<Vehicle> found = repo.getById(maxId);
    CHECK(found.has_value());
    if (found.has_value()) {
        CHECK_EQ(found->id, maxId);
    }
}

TEST_CASE("VR-EDGE-003", "Fleet size bounds") {
    VehicleRepository repo;
    const std::size_t size = repo.getAll().size();
    CHECK(size >= 5);
    CHECK(size <= 8);
}

TEST_CASE("VR-EDGE-004", "getById INT_MIN and INT_MAX") {
    VehicleRepository repo;
    CHECK(!repo.getById(INT_MIN).has_value());
    CHECK(!repo.getById(INT_MAX).has_value());
}

// TC-SKIP: VR-EDGE-005 SWDD 5.3 defines no test seam; the production constructor always seeds, so an empty repository is not constructible.
// TC-SKIP: VR-EDGE-006 SWDD 5.3 defines no test seam; a single-vehicle repository is not constructible.
// TC-SKIP: VR-EXH-002 SWDD 5.3 defines no test seam; duplicate-id construction is not possible.

TEST_CASE("VR-EXH-001", "getAll and getById agree") {
    VehicleRepository repo;
    for (const Vehicle& v : repo.getAll()) {
        std::optional<Vehicle> found = repo.getById(v.id);
        CHECK(found.has_value());
        if (found.has_value()) {
            CHECK_EQ(found->id, v.id);
            CHECK_EQ(found->name, v.name);
            CHECK_NEAR(found->speed, v.speed, 1e-9);
            CHECK_EQ(found->battery, v.battery);
            CHECK_NEAR(found->latitude, v.latitude, 1e-9);
            CHECK_NEAR(found->longitude, v.longitude, 1e-9);
            CHECK_EQ(found->lastUpdated, v.lastUpdated);
        }
    }
}

TEST_CASE("VR-EXH-003", "getAll reference stability") {
    VehicleRepository repo;
    CHECK(&repo.getAll() == &repo.getAll());
}

TEST_CASE("VR-EXH-004", "Two repositories are independent") {
    VehicleRepository a;
    VehicleRepository b;
    CHECK(&a.getAll() != &b.getAll());
    CHECK_EQ(a.getAll().size(), b.getAll().size());
    for (std::size_t i = 0; i < a.getAll().size(); ++i) {
        CHECK_EQ(a.getAll()[i].id, b.getAll()[i].id);
        CHECK_EQ(a.getAll()[i].name, b.getAll()[i].name);
    }
}

TEST_CASE("VR-EXH-005", "Lookup sweep over id range") {
    VehicleRepository repo;
    int minId = INT_MAX;
    int maxId = INT_MIN;
    std::set<int> seeded;
    for (const Vehicle& v : repo.getAll()) {
        seeded.insert(v.id);
        if (v.id < minId) {
            minId = v.id;
        }
        if (v.id > maxId) {
            maxId = v.id;
        }
    }
    for (int id = minId - 2; id <= maxId + 2; ++id) {
        const bool expected = seeded.count(id) > 0;
        CHECK_EQ(repo.getById(id).has_value(), expected);
    }
}