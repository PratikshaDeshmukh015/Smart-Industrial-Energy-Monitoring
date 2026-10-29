# Industrial Energy Intelligence — Validation Summary Report

**Overall Status**: `FAIL (Edge Cases Detected)`
**Total Errors Detected**: `3`
**Total Warnings**: `0`

## Entity Row Counts Verified
| Entity | Record Count |
|:---|:---:|
| `BatchMachineExecution` | 3,996 |
| `EnergyReading` | 172,800 |
| `GroundTruth` | 8 |
| `Machine` | 16 |
| `MaintenanceEvent` | 12 |
| `Meter` | 20 |
| `MeterMachineMapping` | 17 |
| `Plant` | 1 |
| `ProductionBatch` | 2,000 |
| `Shift` | 3 |
| `StateChangeEvent` | 340 |
| `Tariff` | 2 |
| `WeatherObservation` | 2,160 |


## Validation Findings Breakdown
| Severity | Rule | Entity | Record / Key | Message |
|:---|:---|:---|:---|:---|
| `ERROR` | `FOREIGN_KEY_VIOLATION` | `MeterMachineMapping` | `MAP-00017` | Mapping MAP-00017 references unknown meter MTR-PLT-001-999 |
| `ERROR` | `ARITHMETIC_RECONCILIATION_FAIL` | `EnergyReading` | `ENG-MTR-PLT-001-016-202606010030` | Energy reading mismatch: reported 82.39 kWh != expected 20.5975 kWh (active_power_kw * 0.25h) |
| `ERROR` | `INTERVAL_DUPLICATE` | `EnergyReading` | `ENG-MTR-PLT-001-006-202606010100-DUP` | Duplicate interval reading for meter MTR-PLT-001-006 at timestamp 2026-06-01T01:00:00 |

