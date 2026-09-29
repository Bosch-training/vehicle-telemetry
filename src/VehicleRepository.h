#pragma once

#include <optional>
#include <vector>

#include "Vehicle.h"

// Repository pattern (SWDD 5.3): owns the in-memory fleet and hides storage
// details behind getAll() / getById(). The constructor seeds 5-8 mock vehicles
// via VehicleBuilder — the single source of mock data.
class VehicleRepository {
    public:
    VehicleRepository();

    const std::vector<Vehicle>& getAll() const;
    std::optional<Vehicle> getById(int id) const;

    private:
    std::vector<Vehicle> vehicles_;
};