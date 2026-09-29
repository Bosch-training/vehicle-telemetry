#pragma once

#include <string>

#include "Vehicle.h"

// Builder pattern (SWDD 5.2): fluent, step-by-step construction of Vehicle
// objects. Each with* method stores the value verbatim and returns *this by
// reference to enable chaining; build() returns a copy.
class VehicleBuilder {
public:
    VehicleBuilder& withId(int id);
    VehicleBuilder& withName(const std::string& name);
    VehicleBuilder& withSpeed(double speed);
    VehicleBuilder& withBattery(int battery);
    VehicleBuilder& withGps(double lat, double lon);
    VehicleBuilder& withTimestamp(const std::string& ts);
    Vehicle build() const;

private:
    Vehicle vehicle_{};
};