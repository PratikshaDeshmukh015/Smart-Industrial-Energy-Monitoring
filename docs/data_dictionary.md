# Industrial Energy Intelligence — Master Data Dictionary

This document specifies the exact schema, cardinality, constraints, units, and validation rules for all 10 core entities and relational bridge tables.

## Entity: `Plant`
**Description**: Industrial manufacturing facility or operating site.
**Cardinality & Relationships**: Root entity (1:N with Meter, Machine, Shift, Tariff, WeatherObservation, ProductionBatch)

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `plant_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^PLT-[0-9]{3}$ | Non-null, globally unique plant identifier. |
| `name` | `string` | Yes | NON_UNIQUE | dimensionless | Free text (1-100 chars) | Non-empty string. |
| `location` | `string` | Yes | NON_UNIQUE | dimensionless | City, State/Country format | Non-empty geographic location. |
| `timezone` | `string` | Yes | NON_UNIQUE | dimensionless | Valid IANA timezone e.g. America/Chicago, UTC | Valid standard timezone name. |
| `contracted_peak_kw` | `float` | Yes | NON_UNIQUE | kW | > 0.0 | Must be positive numeric value representing utility sanctioned maximum demand threshold. |
| `voltage_kv` | `float` | Yes | NON_UNIQUE | kV | [0.48, 4.16, 13.8, 33.0, 69.0] | Nominal utility incoming grid voltage class. |
| `created_at` | `string` | Yes | NON_UNIQUE | UTC timestamp | ISO 8601 timestamp | Valid ISO 8601 date string. |

---

## Entity: `Meter`
**Description**: Electric power meters installed at main incomers, feeder distribution boards, or machine-level disconnects.
**Cardinality & Relationships**: 1:N with EnergyReading; N:1 with Plant; 1:N recursive with child Meters; N:M with Machine via MeterMachineMapping

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `meter_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^MTR-PLT-[0-9]{3}-[0-9]{3}$ | Pattern MTR-<plant-id>-<seq>; immutable. |
| `plant_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Plant.plant_id | Must reference a valid Plant record. |
| `meter_name` | `string` | Yes | NON_UNIQUE | dimensionless | Descriptive name (e.g. Main Incomer, Feeder-A, Chiller Submeter) | Non-empty string. |
| `meter_type` | `string` | Yes | NON_UNIQUE | enum | ['MAIN_INCOMER', 'SUB_FEEDER', 'MACHINE_LEVEL'] | Level 1 must be MAIN_INCOMER; Level 2 SUB_FEEDER; Level 3 MACHINE_LEVEL. |
| `meter_level` | `integer` | Yes | NON_UNIQUE | hierarchy depth | [1, 2, 3] | 1 for utility incomer, 2 for department feeder, 3 for asset level. |
| `parent_meter_id` | `string` | No | FOREIGN_KEY | dimensionless | Null for Level 1, existing meter_id of level-1 for Level 2, level-2 for Level 3 | Self-referential hierarchy. Must not form circular reference. |
| `sampling_cadence_min` | `integer` | Yes | NON_UNIQUE | minutes | [5, 15, 30, 60] | Standard sampling interval. Baseline standard is 15 minutes. |
| `ct_ratio` | `float` | Yes | NON_UNIQUE | ratio | > 0.0 | Current transformer multiplier (e.g. 1.0, 40.0, 100.0). |
| `status` | `string` | Yes | NON_UNIQUE | enum | ['ACTIVE', 'INACTIVE', 'MAINTENANCE'] | Operational lifecycle state. |
| `installed_date` | `string` | Yes | NON_UNIQUE | date | ISO 8601 date (YYYY-MM-DD) | Must precede any reading timestamps. |

---

## Entity: `Machine`
**Description**: Production and auxiliary machinery consuming electrical power.
**Cardinality & Relationships**: N:1 with Plant; N:M with Meter via MeterMachineMapping; 1:N with MaintenanceEvent; 1:N with BatchMachineExecution

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `machine_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^MCH-[0-9]{3}$ | Pattern MCH-<seq>; immutable. |
| `plant_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Plant.plant_id | Must reference parent Plant. |
| `name` | `string` | Yes | NON_UNIQUE | dimensionless | Free text asset tag name | Non-empty string. |
| `category` | `string` | Yes | NON_UNIQUE | enum | ['STAMPING', 'INJECTION_MOLD', 'CNC_MILLING', 'COMPRESSOR', 'CHILLER'] | Valid machine category enum. |
| `rated_power_kw` | `float` | Yes | NON_UNIQUE | kW | > 0.0 | Nameplate active power capacity. |
| `standby_power_kw` | `float` | Yes | NON_UNIQUE | kW | >= 0.0 and < rated_power_kw | Baseline power drawn when idle; strictly less than rated power. |
| `current_status` | `string` | Yes | NON_UNIQUE | enum | ['RUNNING', 'IDLE', 'MAINTENANCE', 'OFF'] | Valid machine status enum. |
| `installed_date` | `string` | Yes | NON_UNIQUE | date | ISO 8601 date (YYYY-MM-DD) | Must precede production and maintenance events. |

---

## Entity: `MeterMachineMapping`
**Description**: Bridge table mapping physical meters to one or more machines with allocation ratios and effective validity periods.
**Cardinality & Relationships**: Bridge N:M between Meter and Machine

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `mapping_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^MAP-[0-9]{5}$ | Unique bridge record ID. |
| `meter_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Meter.meter_id | Must reference valid Meter. |
| `machine_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Machine.machine_id | Must reference valid Machine. |
| `allocation_ratio` | `float` | Yes | NON_UNIQUE | fraction | 0.0 < ratio <= 1.0 | Sum of allocation ratios for a meter across all machines in a timespan should be <= 1.0. |
| `effective_from` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp | Start of electrical topology assignment. |
| `effective_to` | `string` | No | NON_UNIQUE | timestamp | Null or ISO 8601 timestamp >= effective_from | End date of topology mapping; null indicates currently active. |

---

## Entity: `Shift`
**Description**: Operating shift definitions for plant workers and production schedule.
**Cardinality & Relationships**: 1:N with ProductionBatch; N:1 with Plant

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `shift_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^SHF-[0-9]{4}-[0-9]{3}$ | Unique shift record identifier. |
| `plant_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Plant.plant_id | Must reference parent Plant. |
| `shift_name` | `string` | Yes | NON_UNIQUE | enum | ['MORNING', 'AFTERNOON', 'NIGHT'] | Standard three-shift operating model. |
| `start_time` | `string` | Yes | NON_UNIQUE | time | HH:MM format (24h) | Shift commencement time. |
| `end_time` | `string` | Yes | NON_UNIQUE | time | HH:MM format (24h) | Shift termination time (wraps next day if end < start). |
| `active_days` | `string` | Yes | NON_UNIQUE | dimensionless | Comma-separated days e.g. 'MON,TUE,WED,THU,FRI' | Designates production operating days. |

---

## Entity: `Tariff`
**Description**: Electric utility commercial tariff schedule specifying Time-Of-Use (TOU) energy rates and peak demand capacity charges.
**Cardinality & Relationships**: N:1 with Plant

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `tariff_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^TAR-[0-9]{4}-[0-9]{3}$ | Pattern TAR-<year>-<seq>; immutable. |
| `plant_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Plant.plant_id | Must reference valid Plant. |
| `tariff_name` | `string` | Yes | NON_UNIQUE | dimensionless | Free text tariff rate code (e.g. TOU-Large-Industrial-G2) | Non-empty string. |
| `effective_from` | `string` | Yes | NON_UNIQUE | date | ISO 8601 date (YYYY-MM-DD) | Tariff schedule start date. |
| `effective_to` | `string` | Yes | NON_UNIQUE | date | ISO 8601 date >= effective_from | Tariff schedule expiry date. |
| `rate_type` | `string` | Yes | NON_UNIQUE | enum | ['TOU', 'FLAT'] | Pricing structure. |
| `peak_rate_kwh` | `float` | Yes | NON_UNIQUE | currency/kWh | > 0.0 and > mid_peak_rate_kwh | Energy rate during high-demand peak hours. |
| `mid_peak_rate_kwh` | `float` | Yes | NON_UNIQUE | currency/kWh | > 0.0 and > off_peak_rate_kwh | Energy rate during partial peak hours. |
| `off_peak_rate_kwh` | `float` | Yes | NON_UNIQUE | currency/kWh | > 0.0 | Energy rate during baseline/night hours. |
| `peak_demand_charge_kw` | `float` | Yes | NON_UNIQUE | currency/kW/month | >= 0.0 | Capacity surcharge billed on the monthly peak 15-min kW demand. |
| `peak_window_start` | `string` | Yes | NON_UNIQUE | time | HH:MM (e.g. '14:00') | Start of peak billing interval. |
| `peak_window_end` | `string` | Yes | NON_UNIQUE | time | HH:MM (e.g. '18:00') | End of peak billing interval. |
| `mid_peak_window_start` | `string` | Yes | NON_UNIQUE | time | HH:MM (e.g. '08:00') | Start of mid-peak billing interval. |
| `mid_peak_window_end` | `string` | Yes | NON_UNIQUE | time | HH:MM (e.g. '14:00') | End of mid-peak billing interval. |
| `currency` | `string` | Yes | NON_UNIQUE | ISO 4217 code | ['USD', 'EUR', 'INR', 'GBP'] | Currency code. |

---

## Entity: `WeatherObservation`
**Description**: Hourly/sub-hourly meteorological readings impacting cooling, heating, and compressor efficiency.
**Cardinality & Relationships**: N:1 with Plant

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `weather_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^WTH-PLT-[0-9]{3}-[0-9]{12}$ | Pattern WTH-<plant-id>-<timestamp>; unique. |
| `plant_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Plant.plant_id | Must reference valid Plant. |
| `timestamp` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp | Observation timestamp. |
| `ambient_temp_c` | `float` | Yes | NON_UNIQUE | °C | -30.0 <= temp <= 55.0 | Physical ambient dry-bulb temperature. |
| `relative_humidity_pct` | `float` | Yes | NON_UNIQUE | % | 0.0 <= humidity <= 100.0 | Relative humidity percentage. |
| `dew_point_c` | `float` | Yes | NON_UNIQUE | °C | <= ambient_temp_c | Dew point temperature cannot exceed dry bulb temperature. |
| `cooling_degree_hours` | `float` | Yes | NON_UNIQUE | degree-hours | >= 0.0 | Max(0.0, ambient_temp_c - 18.3). |

---

## Entity: `ProductionBatch`
**Description**: Discrete manufacturing batch run with scheduled volumes, output, scrap, and timestamps.
**Cardinality & Relationships**: N:1 with Plant; N:1 with Shift; 1:N with BatchMachineExecution

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `batch_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^BATCH-[0-9]{4}-[0-9]{6}$ | Pattern BATCH-<year>-<seq>; immutable. |
| `plant_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Plant.plant_id | Must reference parent Plant. |
| `product_sku` | `string` | Yes | NON_UNIQUE | dimensionless | Regex ^SKU-[A-Z0-9]{4,8}$ | Finished good catalog reference. |
| `planned_qty` | `integer` | Yes | NON_UNIQUE | pieces | > 0 | Scheduled production batch size. |
| `produced_qty` | `integer` | Yes | NON_UNIQUE | pieces | >= 0 | Total parts completed. |
| `scrap_qty` | `integer` | Yes | NON_UNIQUE | pieces | >= 0 and scrap_qty <= produced_qty | Defective parts rejected; cannot exceed total produced. |
| `start_time` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp | Batch commencement. |
| `end_time` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp >= start_time | Batch completion time; must follow start_time. |
| `shift_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Shift.shift_id | Assigned production shift. |
| `status` | `string` | Yes | NON_UNIQUE | enum | ['PLANNED', 'IN_PROGRESS', 'COMPLETED', 'ABORTED'] | Batch lifecycle status. |

---

## Entity: `BatchMachineExecution`
**Description**: Bridge table allocating machine runtime, idle time, and output pieces for a specific production batch.
**Cardinality & Relationships**: Bridge N:M between ProductionBatch and Machine

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `execution_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^EXE-[0-9]{6}$ | Unique execution event ID. |
| `batch_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing ProductionBatch.batch_id | Must reference valid Batch. |
| `machine_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Machine.machine_id | Must reference valid Machine. |
| `runtime_min` | `float` | Yes | NON_UNIQUE | minutes | >= 0.0 | Active machine manufacturing time. |
| `idle_min` | `float` | Yes | NON_UNIQUE | minutes | >= 0.0 | Non-productive powered idle waiting time. |
| `output_qty` | `integer` | Yes | NON_UNIQUE | pieces | >= 0 | Pieces processed by this specific asset. |

---

## Entity: `StateChangeEvent`
**Description**: Immutable audit log persisting entity state changes, ensuring historic traceability without overwriting records.
**Cardinality & Relationships**: N:1 with Machine, ProductionBatch, Recommendation, or Meter

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `event_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^EVT-[0-9]{4}-[0-9]{6}$ | Pattern EVT-<year>-<seq>; immutable unique identifier. |
| `entity_type` | `string` | Yes | NON_UNIQUE | enum | ['Machine', 'ProductionBatch', 'Recommendation', 'Meter'] | Target domain entity type undergoing lifecycle transition. |
| `entity_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Valid primary key of target entity | Must reference an existing entity record. |
| `previous_state` | `string` | No | NON_UNIQUE | enum | Valid lifecycle state enum or None for creation | Pre-transition lifecycle state. |
| `new_state` | `string` | Yes | NON_UNIQUE | enum | Valid lifecycle state enum | Post-transition lifecycle state following valid transition graph. |
| `transition_timestamp` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp | Exact chronological timestamp when transition occurred. |
| `triggered_by` | `string` | Yes | NON_UNIQUE | enum | ['SCADA_SYSTEM', 'PLANT_OPERATOR', 'PRODUCTION_PLANNER', 'MAINTENANCE_ENGINEER', 'ENERGY_INTELLIGENCE_ENGINE'] | Originator system or user actor initiating state transition. |
| `reason` | `string` | Yes | NON_UNIQUE | dimensionless | Descriptive reason string | Auditable business rationale for lifecycle transition. |

---

## Entity: `EnergyReading`
**Description**: Synchronous 15-minute telemetry intervals captured from electrical meters.
**Cardinality & Relationships**: N:1 with Meter

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `reading_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^ENG-MTR-PLT-[0-9]{3}-[0-9]{3}-[0-9]{12}$ | Pattern ENG-<meter-id>-<timestamp>; unique. |
| `meter_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Meter.meter_id | Must reference existing Meter. |
| `timestamp` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp at 15-min boundary (:00, :15, :30, :45) | Must align with sampling cadence. |
| `active_power_kw` | `float` | Yes | NON_UNIQUE | kW | >= 0.0 | Average active load demand over the 15-minute interval. |
| `energy_kwh` | `float` | Yes | NON_UNIQUE | kWh | >= 0.0 | Arithmetic reconciliation: energy_kwh == active_power_kw * (cadence_min / 60.0). |
| `power_factor` | `float` | Yes | NON_UNIQUE | ratio | 0.70 <= pf <= 1.0 | Cosine of phase angle between voltage and current. |
| `voltage_v` | `float` | Yes | NON_UNIQUE | V | > 0.0 | Line-to-line or line-to-neutral RMS voltage. |
| `current_a` | `float` | Yes | NON_UNIQUE | A | >= 0.0 | Three-phase average RMS current. |
| `data_source` | `string` | Yes | NON_UNIQUE | enum | ['SCADA', 'IOT_GATEWAY'] | Data acquisition pipeline. |

---

## Entity: `MaintenanceEvent`
**Description**: Historical log of machine maintenance activities, equipment overhauls, and motor tuning.
**Cardinality & Relationships**: N:1 with Machine

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `event_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^MNT-[0-9]{4}-[0-9]{6}$ | Pattern MNT-<year>-<seq>; immutable. |
| `machine_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Machine.machine_id | Must reference existing Machine. |
| `event_type` | `string` | Yes | NON_UNIQUE | enum | ['PREVENTIVE', 'UNPLANNED', 'OVERHAUL'] | Maintenance classification. |
| `start_time` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp | Work commencement. |
| `end_time` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp >= start_time | Work completion. |
| `description` | `string` | Yes | NON_UNIQUE | dimensionless | Free text (e.g. Bearing replacement, VFD parameter re-tuning) | Detailed work log. |
| `energy_impact_kwh` | `float` | Yes | NON_UNIQUE | kWh/day | Float value (negative denotes efficiency gain, positive denotes degradation) | Measurable shift in daily energy consumption post-event. |

---

## Entity: `Recommendation`
**Description**: Prescriptive, measurable energy saving or peak shaving actions targeted to specific plant roles.
**Cardinality & Relationships**: N:1 with Plant; optional N:1 with Machine

| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |
|:---|:---|:---:|:---:|:---|:---|:---|
| `recommendation_id` | `string` | Yes | PRIMARY_KEY | dimensionless | Regex ^REC-[0-9]{4}-[0-9]{6}$ | Pattern REC-<year>-<seq>; immutable. |
| `plant_id` | `string` | Yes | FOREIGN_KEY | dimensionless | Existing Plant.plant_id | Must reference valid Plant. |
| `machine_id` | `string` | No | FOREIGN_KEY | dimensionless | Null or existing Machine.machine_id | Optional asset reference for machine-specific recommendations. |
| `category` | `string` | Yes | NON_UNIQUE | enum | ['PEAK_SHAVING', 'IDLE_REDUCTION', 'LOAD_SHIFTING', 'MAINTENANCE_TUNING'] | Energy efficiency category. |
| `title` | `string` | Yes | NON_UNIQUE | dimensionless | Concise headline (e.g. De-energize Injection Mold 02 during shift break) | Action-oriented title. |
| `description` | `string` | Yes | NON_UNIQUE | dimensionless | Detailed rationale with evidence from telemetry and shift calendar | Preserves traceability to root cause readings. |
| `action_actor` | `string` | Yes | NON_UNIQUE | enum | ['PLANT_OPERATOR', 'MAINTENANCE_ENGINEER', 'PRODUCTION_PLANNER', 'OT_IT_ADMIN'] | Designated role responsible for implementing action. |
| `baseline_kwh` | `float` | Yes | NON_UNIQUE | kWh | >= 0.0 | Empirical historical energy baseline being measured. |
| `estimated_kwh_savings` | `float` | Yes | NON_UNIQUE | kWh | > 0.0 and <= baseline_kwh | Projected energy reduction; must be <= baseline_kwh. |
| `estimated_cost_savings` | `float` | Yes | NON_UNIQUE | currency ($) | >= 0.0 | Financial benefit evaluated against specific TOU tariff rates. |
| `payback_period_days` | `float` | Yes | NON_UNIQUE | days | >= 0.0 | 0.0 for zero-cost behavioral controls, or capital payback. |
| `status` | `string` | Yes | NON_UNIQUE | enum | ['OPEN', 'ACKNOWLEDGED', 'IMPLEMENTED', 'REJECTED'] | Workflow lifecycle state. |
| `generated_at` | `string` | Yes | NON_UNIQUE | timestamp | ISO 8601 timestamp | Timestamp of analytics engine run. |

---
