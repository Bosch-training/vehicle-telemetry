#include "VehicleRepository.h"

#include "VehicleBuilder.h"

VehicleRepository::VehicleRepository() {
    vehicles_.push_back(VehicleBuilder()
                            .withId(1)
                            .withName("Truck-A")
                            .withSpeed(72.5)
                            .withBattery(85)
                            .withGps(37.7749, -122.4194)
                            .withTimestamp("2026-09-28T10:00:00Z")
                            .build());
    vehicles_.push_back(VehicleBuilder()
                            .withId(2)
                            .withName("Van-B")
                            .withSpeed(48.0)
                            .withBattery(15)
                            .withGps(40.7128, -74.0060)
                            .withTimestamp("2026-09-28T10:01:00Z")
                            .build());
    vehicles_.push_back(VehicleBuilder()
                            .withId(3)
                            .withName("Car-C")
                            .withSpeed(60.25)
                            .withBattery(55)
                            .withGps(51.5074, -0.1278)
                            .withTimestamp("2026-09-28T10:02:00Z")
                            .build());
    vehicles_.push_back(VehicleBuilder()
                            .withId(4)
                            .withName("Bus-D")
                            .withSpeed(35.75)
                            .withBattery(8)
                            .withGps(48.8566, 2.3522)
                            .withTimestamp("2026-09-28T10:03:00Z")
                            .build());
    vehicles_.push_back(VehicleBuilder()
                            .withId(5)
                            .withName("Bike-E")
                            .withSpeed(12.5)
                            .withBattery(100)
                            .withGps(35.6762, 139.6503)
                            .withTimestamp("2026-09-28T10:04:00Z")
                            .build());
}

const std::vector<Vehicle>& VehicleRepository::getAll() const {
    return vehicles_;
}

std::optional<Vehicle> VehicleRepository::getById(int id) const {
    for (const Vehicle& vehicle : vehicles_) {
        if (vehicle.id == id) {
            return vehicle;
        }
    }
    return std::nullopt;
}