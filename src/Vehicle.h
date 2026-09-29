#pragma once

#include <string>

// Plain data struct for a single vehicle's telemetry snapshot.
// No behavior — construction is the VehicleBuilder's job (SWDD 5.1).
struct Vehicle {
    int id = 0;
    std::string name;
    double speed = 0.0;       // km/h
    int battery = 0;          // percent 0-100
    double latitude = 0.0;
    double longitude = 0.0;
    std::string lastUpdated;  // timestamp, formatted string
};