#include "VehicleBuilder.h"

VehicleBuilder& VehicleBuilder::withId(int id) {
    vehicle_.id = id;
    return *this;
}

VehicleBuilder& VehicleBuilder::withName(const std::string& name) {
    vehicle_.name = name;
    return *this;
}

VehicleBuilder& VehicleBuilder::withSpeed(double speed) {
    vehicle_.speed = speed;
    return *this;
}

VehicleBuilder& VehicleBuilder::withBattery(int battery) {
    vehicle_.battery = battery;
    return *this;
}

VehicleBuilder& VehicleBuilder::withGps(double lat, double lon) {
    vehicle_.latitude = lat;
    vehicle_.longitude = lon;
    return *this;
}

VehicleBuilder& VehicleBuilder::withTimestamp(const std::string& ts) {
    vehicle_.lastUpdated = ts;
    return *this;
}

Vehicle VehicleBuilder::build() const {
    return vehicle_;
}