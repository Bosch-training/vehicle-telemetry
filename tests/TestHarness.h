// TestHarness.h — minimal header-only test harness for the Vehicle Telemetry
// Visualization project. Standard library only; no third-party framework.
//
// Usage:
//   #include "TestHarness.h"
//
//   TEST_CASE("VB-POS-001", "Full fluent chain sets all fields") {
//       Vehicle v = VehicleBuilder().withId(1).withSpeed(60.0).build();
//       CHECK_EQ(v.id, 1);
//       CHECK_NEAR(v.speed, 60.0, 1e-9);
//   }
//
// The first TEST_CASE argument is the design case ID (from
// docs/ut-design/unit-test-design.csv). check_traceability.py scans for it, so
// keep it exactly as written in the design.
//
// A test binary needs exactly one main(); provide it with TEST_HARNESS_MAIN in
// one translation unit (or call testharness::runAll() from your own main):
//
//   #define TEST_HARNESS_MAIN
//   #include "TestHarness.h"
//
// Output contract (parsed by run_tests.py):
//   [PASS] <ID> <name>
//   [FAIL] <ID> <name>
//   TOTAL <n> PASSED <p> FAILED <f>

#pragma once

#include <cstdio>
#include <exception>
#include <functional>
#include <string>
#include <vector>

namespace testharness {

struct TestCase {
    std::string id;
    std::string name;
    std::function<void()> fn;
};

inline std::vector<TestCase>& registry() {
    static std::vector<TestCase> cases;
    return cases;
}

inline int& failureCount() {
    static int failures = 0;
    return failures;
}

struct Registrar {
    Registrar(const std::string& id, const std::string& name,
              std::function<void()> fn) {
        registry().push_back(TestCase{id, name, std::move(fn)});
    }
};

inline void reportFailure(const char* file, int line,
                          const std::string& message) {
    ++failureCount();
    std::printf("    CHECK FAILED at %s:%d: %s\n", file, line, message.c_str());
}

inline int runAll() {
    int passed = 0;
    int failed = 0;
    for (const TestCase& tc : registry()) {
        failureCount() = 0;
        try {
            tc.fn();
        } catch (const std::exception& e) {
            reportFailure("<exception>", 0, e.what());
        } catch (...) {
            reportFailure("<exception>", 0, "unknown exception");
        }
        if (failureCount() == 0) {
            std::printf("[PASS] %s %s\n", tc.id.c_str(), tc.name.c_str());
            ++passed;
        } else {
            std::printf("[FAIL] %s %s\n", tc.id.c_str(), tc.name.c_str());
            ++failed;
        }
    }
    std::printf("TOTAL %d PASSED %d FAILED %d\n", passed + failed, passed,
                failed);
    return failed == 0 ? 0 : 1;
}

}  // namespace testharness

// __LINE__ keeps the generated identifiers unique without needing the case ID
// (which contains '-' and is not a valid C++ identifier). The two-level
// concatenation is required: `##__LINE__` would paste the literal token
// "__LINE__" instead of expanding it, producing duplicate identifiers.
#define TESTHARNESS_CONCAT_(a, b) a##b
#define TESTHARNESS_CONCAT(a, b) TESTHARNESS_CONCAT_(a, b)

#define TEST_CASE(id, name)                                                    \
    static void TESTHARNESS_CONCAT(testharness_case_, __LINE__)();             \
    static ::testharness::Registrar TESTHARNESS_CONCAT(testharness_registrar_, \
                                                       __LINE__)(              \
        id, name, TESTHARNESS_CONCAT(testharness_case_, __LINE__));            \
    static void TESTHARNESS_CONCAT(testharness_case_, __LINE__)()

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            ::testharness::reportFailure(__FILE__, __LINE__, #cond);           \
        }                                                                      \
    } while (0)

#define CHECK_EQ(a, b)                                                         \
    do {                                                                       \
        if (!((a) == (b))) {                                                   \
            ::testharness::reportFailure(__FILE__, __LINE__, #a " == " #b);    \
        }                                                                      \
    } while (0)

#define CHECK_NEAR(a, b, eps)                                                  \
    do {                                                                       \
        const double testharness_da = static_cast<double>(a);                  \
        const double testharness_db = static_cast<double>(b);                  \
        const double testharness_dd = testharness_da - testharness_db;         \
        if (!(testharness_dd < (eps) && -testharness_dd < (eps))) {            \
            ::testharness::reportFailure(__FILE__, __LINE__, #a " ~= " #b);    \
        }                                                                      \
    } while (0)

#ifdef TEST_HARNESS_MAIN
int main() {
    return ::testharness::runAll();
}
#endif