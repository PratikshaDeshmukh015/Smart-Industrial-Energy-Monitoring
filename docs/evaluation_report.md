# Industrial Energy Intelligence — Evaluation & Benchmark Report

| Metric | Value |
|:---|:---:|
| **Ground Truth Injected Anomalies** | `8` |
| **True Positives (TP)** | `8` |
| **False Positives (FP)** | `0` |
| **False Negatives (FN)** | `0` |
| **Precision** | `100.0%` |
| **Recall** | `100.0%` |
| **F1 Score** | `100.0%` |


## Detailed Ground Truth Detection Traceability
| Anomaly ID | Issue Type | Classification | Detection Engine Component | Ground Truth Description |
|:---|:---|:---:|:---|:---|
| `ANOM-0001` | `METER_TOTAL_DISAGREES_WITH_INTERVAL_SUM` | 🟢 TP | `CorrelationEngine.HierarchyReconciliation` | Main incomer active power dropped from 2053.92 kW to 821.57 kW, causing severe negative reconciliation against sub-meters. |
| `ANOM-0002` | `KW_CONFUSED_WITH_KWH` | 🟢 TP | `ValidationSuite.ARITHMETIC_RECONCILIATION_FAIL` | Telemetry unit confusion: energy_kwh set to 82.39 instead of 20.5975 kWh (ratio 1.0 instead of 0.25). |
| `ANOM-0003` | `TARIFF_TIMEZONE_MISMATCH` | 🟢 TP | `CorrelationEngine.TariffAlignment` | Tariff peak window is shifted by UTC offset (+5 hours mismatch from plant local operating window). |
| `ANOM-0004` | `READING_DUPLICATES` | 🟢 TP | `ValidationSuite.INTERVAL_DUPLICATE` | Duplicate interval reading encountered for meter MTR-PLT-001-006 at 2026-06-01T01:00:00. |
| `ANOM-0005` | `ENERGY_ASSIGNED_OUTSIDE_HIERARCHY` | 🟢 TP | `ValidationSuite.FOREIGN_KEY_VIOLATION` | Machine MCH-001 mapped to non-existent meter MTR-PLT-001-999 outside physical plant tree. |
| `ANOM-0006` | `HIGH_IDLE_CONSUMPTION` | 🟢 TP | `CorrelationEngine.IdleWasteDetector` | Machine left energized at 95.0 kW during scheduled plant shutdown (baseline standby is 35 kW). |
| `ANOM-0007` | `PEAK_DEMAND_SPIKE` | 🟢 TP | `CorrelationEngine.PeakDemandDetector` | Main incomer demand peaked at 1435.0 kW, exceeding contracted limit of 1250.0 kW during TOU peak window. |
| `ANOM-0008` | `METER_TELEMETRY_GAP` | 🟢 TP | `CorrelationEngine.ExceptionRouter (LINEAR_INTERPOLATION_ESTIMATION)` | Telemetry gap: Meter MTR-PLT-001-002 dropped 15-minute interval reading at 2026-06-01T03:45:00 due to IoT gateway buffer timeout. |

