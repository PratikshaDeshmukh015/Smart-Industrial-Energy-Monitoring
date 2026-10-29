<<<<<<< HEAD
# Industrial Energy Intelligence

An end-to-end industrial software system that correlates machine telemetry (15-minute kW/kWh readings), production output (discrete batches, yields, scrap), Time-of-Use (TOU) utility tariffs, and meteorological observations to detect energy waste, shave peak demand surcharges, and generate prioritized, measurable recommendations.

---

## 1. Business Context & Problem Statement

Modern manufacturing facilities struggle with rising electricity costs, capacity surcharges, and volatile carbon intensity. Plant operators often lack real-time visibility into machine idle power draw, while production planners schedule heavy batch runs during peak utility tariff windows without understanding the penalty implications. Furthermore, auxiliary systems (central chillers and air compressors) silently degrade due to fouling and seasonal temperature swings.

This system provides:
- **Hierarchical Telemetry Ingestion**: Multi-level meter tree (Main Grid Incomer $\rightarrow$ Department Sub-Feeders $\rightarrow$ Machine-Level Disconnects).
- **Multi-Source Context Correlation**: Aligns 15-minute telemetry intervals with shift calendars, discrete production batches, TOU tariffs, and ambient wet/dry bulb weather conditions.
- **Root-Cause Waste Identification**: Separates productive active power from idle baseload drain and weather-induced thermal degradation.
- **Peak Demand Risk Management**: Anticipates and mitigates 15-minute kW demand threshold breaches that trigger massive utility capacity penalties.
- **Traceable Recommendations**: Generates role-targeted recommendations citing empirical baselines, expected kWh and dollar savings, and payback periods.
- **Rigorous Data Quality Validation & Isolated Ground Truth**: Injects labelled negative scenarios and validates them without leaking ground-truth labels into input features.

---

## 2. Primary Actors & Systems

| Actor / Persona | Role & Core Workflow Responsibilities |
|:---|:---|
| **Plant Operator** | Monitors real-time floor telemetry; executes procedural machine shutdown sequences; prevents idle power bleed during breaks and weekend shutdowns. |
| **Production Planner** | Balances job order schedules against Time-of-Use (TOU) tariff windows; sequences batch startups to prevent coincident peak demand spikes. |
| **Maintenance Engineer** | Monitors equipment specific energy consumption (SEC) and tool wear; performs motor tuning, compressed air leak remediation, and chiller coil descaling. |
| **OT / IT Administrator** | Configures meter hierarchies, CT ratios, IoT gateway telemetry pipelines, deduplication filters, and timezone synchronization. |

---

## 3. Meter & Asset Hierarchy Topology

```
PLT-001 (Apex Precision Manufacturing - 13.8 kV Grid Incomer)
│
└── [L1] MTR-PLT-001-001 (Main Grid Incomer Meter, CT 100:1, 15-min cadence)
    │
    ├── [L2] MTR-PLT-001-002 (Heavy Machining Feeder)
    │   ├── [L3] MTR-PLT-001-006 ──> MCH-001 (Stamping Press 1 - 180 kW)
    │   ├── [L3] MTR-PLT-001-007 ──> MCH-002 (CNC Milling Cell 1 - 75 kW)
    │   └── [L3] MTR-PLT-001-008 ──> MCH-003 (Stamping Press 2 - 180 kW)
    │
    ├── [L2] MTR-PLT-001-003 (Molding Department Feeder)
    │   ├── [L3] MTR-PLT-001-009 ──> MCH-004 (Injection Mold 1 - 220 kW)
    │   ├── [L3] MTR-PLT-001-010 ──> MCH-005 (Injection Mold 2 - 220 kW)
    │   └── [L3] MTR-PLT-001-011 ──> MCH-006 (Injection Mold 3 - 220 kW)
    │
    ├── [L2] MTR-PLT-001-004 (Utilities & Facility Feeder)
    │   ├── [L3] MTR-PLT-001-012 ──> MCH-007 (Screw Air Compressor - 110 kW)
    │   └── [L3] MTR-PLT-001-013 ──> MCH-008 (Central Water Chiller - 160 kW)
    │
    └── [L2] MTR-PLT-001-005 (Assembly Feeder & Finishing Lines)
        └── [L3] MTR-PLT-001-014 to 020 ──> MCH-009 to MCH-016
```

---

## 4. Master Schema & Relational Model (10 Entities + Bridges)

1. **`Plant`**: Facility root entity; defines physical location, timezone (`America/Chicago`), nominal voltage (`13.8 kV`), and contracted peak capacity threshold (`1,250 kW`).
2. **`Meter`**: Hierarchical power meter nodes; tracks meter type (`MAIN_INCOMER`, `SUB_FEEDER`, `MACHINE_LEVEL`), hierarchy depth level (1, 2, 3), CT ratio, and sampling cadence (`15 min`).
3. **`Machine`**: Electrical assets consuming energy; nameplate rated power (kW), standby idle power (kW), category, and operational state.
4. **`MeterMachineMapping`**: Relational bridge table allocating meters to machines with allocation ratios and effective date intervals.
5. **`Shift`**: Standard operating calendar: Morning (`06:00 - 14:00`), Afternoon (`14:00 - 22:00`), Night (`22:00 - 06:00`).
6. **`Tariff`**: Time-Of-Use schedule:
   - **Off-Peak** (`22:00 - 08:00` weekdays & all weekend): `$0.065 / kWh`
   - **Mid-Peak** (`08:00 - 14:00` & `18:00 - 22:00`): `$0.120 / kWh`
   - **On-Peak** (`14:00 - 18:00` weekdays): `$0.240 / kWh`
   - **Peak Demand Capacity Charge**: `$15.50 / kW / month` billed on peak 15-minute demand.
7. **`WeatherObservation`**: Hourly ambient dry-bulb temperature (°C), relative humidity (%), calculated dew point (°C), and cooling degree hours (CDH).
8. **`ProductionBatch`**: Discrete manufacturing batches; product SKU, planned vs produced quantity, scrap quantity, start and end timestamps.
9. **`BatchMachineExecution`**: Relational bridge recording machine-level runtime (min), idle time (min), and piece output per batch.
10. **`EnergyReading`**: 15-minute telemetry intervals ($kW$, derived $kWh = kW \times 0.25$, power factor, RMS voltage, phase current).
11. **`MaintenanceEvent`**: Equipment servicing records, valve overhauls, motor lubrication, and quantified daily energy shift ($kWh/\text{day}$).
12. **`StateChangeEvent`**: Immutable audit log persisting entity state changes (Machine and Batch lifecycles), ensuring historic traceability without overwriting history (Rule 4).
13. **`Recommendation`**: Prioritized efficiency actions targeting designated actors with baseline kWh, projected savings, and payback period.

---

## 5. Deterministic Generation & Coverage

The generator supports dual scales using fixed seed `20261022`:
- **Starter Scale** (`--scale starter`): 4 meters, 7 days, 4 machines, 150 batches, 312 state change events, 2,688 telemetry readings.
- **Full Production Benchmark** (`--scale full`): 20 meters, 90 days, 16 machines, 2,000 production batches, 3,996 machine execution allocations, 340 state change events, 2,160 hourly weather observations, and **172,800 15-minute energy readings**.

### Injected Negative Edge Cases & Isolated Ground Truth
As mandated by Step 5 and Step 7, edge cases are injected into the telemetry and transactional tables, and explicitly cataloged in `ground_truth.json` / `ground_truth.csv` without leaking labels into pipeline inputs:
1. **Meter Total Disagrees with Interval Sums**: Main grid incomer reading perturbed to under-report by 60%, violating sub-feeder rollup balance.
2. **kW Confused with kWh**: Telemetry field transposition where active demand (kW) was logged directly into the interval energy (kWh) column (producing an arithmetic 4x discrepancy for a 15-min cadence).
3. **Tariff Timezone Mismatch**: Secondary tariff schedule defined in UTC rather than plant local time (`America/Chicago`), causing a 5-hour phase shift in peak windows.
4. **Reading Duplicates**: IoT gateway retry loop generating duplicate interval readings for the same meter and timestamp.
5. **Energy Assigned Outside Hierarchy**: Machine mapped to a non-existent meter `MTR-PLT-001-999` outside the physical electrical plant tree.
6. **Operational Waste: High Idle Draw**: Machine left energized at 95 kW during non-scheduled shutdown windows (baseline standby is 35 kW).
7. **Operational Waste: Peak Demand Spike**: Simultaneous startups during high-tariff window resulting in 1,435 kW load breaching the 1,250 kW contracted limit.
8. **Operational Telemetry Gap**: Dropped 15-minute readings due to IoT gateway communication timeout, triggering the explicit exception recovery path.

---

## 6. Validation Suite & Acceptance Criteria

The system validates data integrity using multi-point assertion checks:
- **Primary Key Uniqueness**: Strict validation of zero nulls and zero duplicate keys across all entities.
- **Foreign Key Integrity**: Traverses all relationships (`Meter.parent_meter_id`, `MeterMachineMapping`, `Shift`, `Tariff`, `ProductionBatch`, `EnergyReading`, `StateChangeEvent`).
- **Allowed Enums**: Asserts enum bounds for meter types, machine categories, shift names, batch statuses, and maintenance types.
- **Date Ordering**: Verifies $t_{\text{end}} \ge t_{\text{start}}$ across production batches, maintenance intervals, and tariff validities.
- **Arithmetic Reconciliation**: Validates $kWh = kW \times (\text{cadence} / 60)$ within $\pm 0.05\text{ kWh}$; verifies scrap pieces $\le$ produced pieces; verifies dew point $\le$ ambient temperature.
- **Duplicate Checks**: Detects duplicate telemetry intervals on composite key `(meter_id, timestamp)`.
- **Lifecycle Transition Checks**: Validates directed state transition graph for Machine (`RUNNING` $\leftrightarrow$ `IDLE` $\leftrightarrow$ `MAINTENANCE` $\leftrightarrow$ `OFF`) and Batch (`PLANNED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `COMPLETED`).

---

## 7. Correlation & Analytics Engine

The correlation engine integrates four disparate industrial data streams and includes an explicit exception path:
1. **Exception Handling Path**:
   - Detects missing telemetry intervals and arithmetic unit transpositions.
   - Applies deterministic linear interpolation and cadence-corrected recalculation.
   - Logs auditable exception records for OT/IT administrators without corrupting downstream billing rollups.
2. **Idle Baseload Waste Detector**:
   - Compares machine telemetry against active production batch executions and shift calendars.
   - Detects unallocated idle draw where machines remain powered during non-operational periods.
   - Computes wasted energy ($kWh$) and financial loss evaluated against the specific TOU tariff rate active at that timestamp.
3. **Peak Demand & Capacity Surcharge Engine**:
   - Tracks 15-minute rolling facility demand against the 1,250 kW contracted capacity limit.
   - Flags coincident peaks during the high-tariff 14:00 - 18:00 window.
   - Computes monthly capacity surcharge exposure ($excess\_kW \times \$15.50/kW$).
4. **Specific Energy Consumption (SEC / Energy Intensity)**:
   - Computes $SEC = \frac{\sum kWh_{\text{batch}}}{\text{Produced Qty} - \text{Scrap Qty}}$ (kWh per good unit).
   - Establishes statistical SKU baselines and flags batches with $>25\%$ intensity deviation driven by process scrap.
5. **Weather-Correlated Cooling Analysis**:
   - Performs regression between ambient dry-bulb temperature, cooling degree hours, and chiller electrical load.
   - Quantifies thermal sensitivity ($kW / ^\circ C$) and identifies heat exchanger fouling.

---

## 8. Benchmark Evaluation & Results

Evaluated against the isolated `ground_truth.json`:

| Metric | Result | Target Benchmark |
|:---|:---:|:---:|
| **Ground Truth Injected Anomalies** | **8** | 8 |
| **True Positives (TP)** | **8** | $\ge 7$ |
| **False Positives (FP)** | **0** | 0 |
| **False Negatives (FN)** | **0** | 0 |
| **Precision** | **100.0%** | $\ge 95.0\%$ |
| **Recall** | **100.0%** | $\ge 95.0\%$ |
| **F1 Score** | **100.0%** | $\ge 95.0\%$ |

---

## 9. Quickstart CLI Guide

All operations are executable via `cli.py`:

### Step 1: Export Data Dictionary Documentation
```bash
py -3.12 cli.py export-dict --output-dir docs
```
*Outputs `docs/data_dictionary.md` and `docs/data_dictionary.csv`.*

### Step 2: Generate Synthetic Dataset
```bash
# Starter scale (rapid testing)
py -3.12 cli.py generate --scale starter --output-dir data/starter

# Full production benchmark (20 meters, 90 days, 2000 batches, 172,801 readings)
py -3.12 cli.py generate --scale full --output-dir data/full
```

### Step 3: Run Data Quality Validation Suite
```bash
py -3.12 cli.py validate --data-dir data/full --export-report docs/validation_report.md
```

### Step 4: Run Energy Correlation & Waste Detection Engine
```bash
py -3.12 cli.py correlate --data-dir data/full
```

### Step 5: Benchmark against Isolated Ground Truth
```bash
py -3.12 cli.py evaluate --data-dir data/full --export-report docs/evaluation_report.md
```

### Step 6: Generate Operations Dashboard
```bash
# Generate standalone HTML dashboard
py -3.12 cli.py dashboard --data-dir data/full --output dashboard.html

# Optionally launch local preview server
py -3.12 cli.py dashboard --data-dir data/full --output dashboard.html --serve --port 8080
```

### Step 7: Verify 100% Deterministic Reproducibility
```bash
py -3.12 cli.py reproduce --scale starter --seed 20261022
```
*Generates the dataset twice in independent temporary directories and compares SHA256 checksums across all tables to prove byte-for-byte reproducibility.*

### Step 8: Run Automated Unit Tests
```bash
py -3.12 -m unittest discover -s tests -v
```

---

## 10. Lawful Provenance & Public Data Statement

This system uses 100% synthetic data generated deterministically using standard thermodynamic, electrical, and industrial scheduling formulations. No proprietary, confidential, or private personal data was accessed or harvested. Electrical tariff structures are modeled on public Time-Of-Use industrial rate tariffs (such as Commonwealth Edison Rate BES and California PG&E E-19/E-20 schedules).
=======
# Smart-Industrial-Energy-Monitoring
Industrial energy monitoring system for detecting energy waste, analyzing peak demand, optimizing electricity costs, and improving energy efficiency.
>>>>>>> 8497ea96c81072bca6c6ed3f5ecbbfb245bf029b
