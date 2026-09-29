# Unit test design review

Cases reviewed: 94

## Summary

- High: 0
- Medium: 0
- Low: 3

## Coverage matrix

| Requirement | Description | Covering cases |
|---|---|---|
| FR1 | Fleet of 5-8 mock vehicles with the full field set | VB-POS-001, VB-POS-002, VB-NEG-004, VB-NEG-005, VB-EDGE-005, VB-EXH-001, VB-EXH-005, VR-POS-001, VR-POS-002, VR-POS-003, VR-POS-004, VR-POS-005, VR-NEG-001, VR-NEG-003, VR-NEG-004, VR-EDGE-001, VR-EDGE-002, VR-EDGE-003, VR-EXH-005 |
| FR2 | Fleet aggregates: count, average speed, low-battery list | TS-POS-002, TS-POS-003, TS-POS-004, TS-POS-006, TS-NEG-001, TS-NEG-002, TS-EDGE-001, TS-EDGE-002, TS-EDGE-003, TS-EDGE-004, TS-EDGE-005, TS-EDGE-006, TS-EDGE-007, TS-EDGE-008, TS-EXH-001, TS-EXH-002, TS-EXH-003, TS-EXH-004, TS-EXH-006 |
| FR3 | Fixed-width ASCII table with aligned columns | DR-POS-001, DR-POS-002, DR-POS-003, DR-POS-005, DR-NEG-003, DR-EDGE-001, DR-EDGE-002, DR-EDGE-003, DR-EDGE-004, DR-EDGE-006, DR-EDGE-007, DR-EDGE-008, DR-EDGE-009, DR-EXH-001, DR-EXH-004 |
| FR4 | Fleet summary section below the table | DR-POS-004, DR-POS-005, DR-NEG-001, DR-NEG-002, DR-EXH-002, DR-EXH-003, DR-EXH-004 |
| FR5 | Single executable, no external runtime dependencies | n/a (build) |
| VC1 | Clean compile with -Wall -Wextra, no warnings | n/a (build) |
| VC2 | Binary output shows a correctly aligned ASCII table | DR-POS-001, DR-POS-002, DR-POS-003, DR-POS-005, DR-NEG-003, DR-EDGE-001, DR-EDGE-002, DR-EDGE-003, DR-EDGE-004, DR-EDGE-006, DR-EDGE-007, DR-EDGE-008, DR-EDGE-009, DR-EXH-001, DR-EXH-004 |
| VC3 | Average speed and low-battery count match manual calculation | TS-POS-003, TS-POS-004, TS-POS-006, TS-NEG-001, TS-NEG-002, TS-EDGE-001, TS-EDGE-002, TS-EDGE-003, TS-EDGE-004, TS-EDGE-005, TS-EDGE-006, TS-EDGE-007, TS-EXH-001, TS-EXH-002, TS-EXH-003, TS-EXH-006 |
| VC4 | getInstance() returns the same instance across calls | TS-POS-001, TS-POS-004, TS-POS-005, TS-NEG-003, TS-NEG-004, TS-EXH-005 |
| VC5 | README documents architecture and pattern placement | n/a (doc) |

## Category balance

| Component | Positive | Negative | Edge | Exhaustive |
|---|---|---|---|---|
| VB | 5 | 6 | 9 | 5 |
| VR | 5 | 4 | 6 | 5 |
| TS | 6 | 5 | 8 | 6 |
| DR | 6 | 4 | 9 | 5 |

## Findings by severity

### High

None.

### Medium

None.

### Low

- **Coverage Gap** [-] (FR5): FR5 (Single executable, no external runtime dependencies) is not verifiable by unit cases
  - Evidence: build-level criterion
  - Recommendation: Verify via the CMake build and a clean -Wall -Wextra compile, not the CSV.
- **Coverage Gap** [-] (VC1): VC1 (Clean compile with -Wall -Wextra, no warnings) is not verifiable by unit cases
  - Evidence: build-level criterion
  - Recommendation: Verify via the CMake build and a clean -Wall -Wextra compile, not the CSV.
- **Coverage Gap** [-] (VC5): VC5 (README documents architecture and pattern placement) is a documentation deliverable
  - Evidence: doc-level criterion
  - Recommendation: Verify by reading README.md; no unit case applies.

## Open questions

None raised by the design.

## Proposed cases

Add cases for each High/Medium coverage gap above, using the existing ID scheme.
