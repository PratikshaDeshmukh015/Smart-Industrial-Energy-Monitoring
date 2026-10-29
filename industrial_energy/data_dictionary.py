"""
Data dictionary module for Industrial Energy Intelligence.
Defines types, optionality, units, allowed values, uniqueness, and validation rules
for Plant, Meter, Machine, EnergyReading, ProductionBatch, Shift, Tariff,
WeatherObservation, MaintenanceEvent, Recommendation, and bridge entities.
"""

from typing import Dict, List, Any
import json
import csv
import io

DATA_DICTIONARY: Dict[str, Dict[str, Any]] = {
    "Plant": {
        "description": "Industrial manufacturing facility or operating site.",
        "cardinality": "Root entity (1:N with Meter, Machine, Shift, Tariff, WeatherObservation, ProductionBatch)",
        "fields": [
            {
                "field_name": "plant_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^PLT-[0-9]{3}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Non-null, globally unique plant identifier."
            },
            {
                "field_name": "name",
                "type": "string",
                "required": True,
                "allowed_values": "Free text (1-100 chars)",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Non-empty string."
            },
            {
                "field_name": "location",
                "type": "string",
                "required": True,
                "allowed_values": "City, State/Country format",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Non-empty geographic location."
            },
            {
                "field_name": "timezone",
                "type": "string",
                "required": True,
                "allowed_values": "Valid IANA timezone e.g. America/Chicago, UTC",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Valid standard timezone name."
            },
            {
                "field_name": "contracted_peak_kw",
                "type": "float",
                "required": True,
                "allowed_values": "> 0.0",
                "units": "kW",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Must be positive numeric value representing utility sanctioned maximum demand threshold."
            },
            {
                "field_name": "voltage_kv",
                "type": "float",
                "required": True,
                "allowed_values": "[0.48, 4.16, 13.8, 33.0, 69.0]",
                "units": "kV",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Nominal utility incoming grid voltage class."
            },
            {
                "field_name": "created_at",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp",
                "units": "UTC timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Valid ISO 8601 date string."
            }
        ]
    },
    "Meter": {
        "description": "Electric power meters installed at main incomers, feeder distribution boards, or machine-level disconnects.",
        "cardinality": "1:N with EnergyReading; N:1 with Plant; 1:N recursive with child Meters; N:M with Machine via MeterMachineMapping",
        "fields": [
            {
                "field_name": "meter_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^MTR-PLT-[0-9]{3}-[0-9]{3}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern MTR-<plant-id>-<seq>; immutable."
            },
            {
                "field_name": "plant_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Plant.plant_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference a valid Plant record."
            },
            {
                "field_name": "meter_name",
                "type": "string",
                "required": True,
                "allowed_values": "Descriptive name (e.g. Main Incomer, Feeder-A, Chiller Submeter)",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Non-empty string."
            },
            {
                "field_name": "meter_type",
                "type": "string",
                "required": True,
                "allowed_values": "['MAIN_INCOMER', 'SUB_FEEDER', 'MACHINE_LEVEL']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Level 1 must be MAIN_INCOMER; Level 2 SUB_FEEDER; Level 3 MACHINE_LEVEL."
            },
            {
                "field_name": "meter_level",
                "type": "integer",
                "required": True,
                "allowed_values": "[1, 2, 3]",
                "units": "hierarchy depth",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "1 for utility incomer, 2 for department feeder, 3 for asset level."
            },
            {
                "field_name": "parent_meter_id",
                "type": "string",
                "required": False,
                "allowed_values": "Null for Level 1, existing meter_id of level-1 for Level 2, level-2 for Level 3",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Self-referential hierarchy. Must not form circular reference."
            },
            {
                "field_name": "sampling_cadence_min",
                "type": "integer",
                "required": True,
                "allowed_values": "[5, 15, 30, 60]",
                "units": "minutes",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Standard sampling interval. Baseline standard is 15 minutes."
            },
            {
                "field_name": "ct_ratio",
                "type": "float",
                "required": True,
                "allowed_values": "> 0.0",
                "units": "ratio",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Current transformer multiplier (e.g. 1.0, 40.0, 100.0)."
            },
            {
                "field_name": "status",
                "type": "string",
                "required": True,
                "allowed_values": "['ACTIVE', 'INACTIVE', 'MAINTENANCE']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Operational lifecycle state."
            },
            {
                "field_name": "installed_date",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 date (YYYY-MM-DD)",
                "units": "date",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Must precede any reading timestamps."
            }
        ]
    },
    "Machine": {
        "description": "Production and auxiliary machinery consuming electrical power.",
        "cardinality": "N:1 with Plant; N:M with Meter via MeterMachineMapping; 1:N with MaintenanceEvent; 1:N with BatchMachineExecution",
        "fields": [
            {
                "field_name": "machine_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^MCH-[0-9]{3}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern MCH-<seq>; immutable."
            },
            {
                "field_name": "plant_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Plant.plant_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference parent Plant."
            },
            {
                "field_name": "name",
                "type": "string",
                "required": True,
                "allowed_values": "Free text asset tag name",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Non-empty string."
            },
            {
                "field_name": "category",
                "type": "string",
                "required": True,
                "allowed_values": "['STAMPING', 'INJECTION_MOLD', 'CNC_MILLING', 'COMPRESSOR', 'CHILLER']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Valid machine category enum."
            },
            {
                "field_name": "rated_power_kw",
                "type": "float",
                "required": True,
                "allowed_values": "> 0.0",
                "units": "kW",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Nameplate active power capacity."
            },
            {
                "field_name": "standby_power_kw",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0 and < rated_power_kw",
                "units": "kW",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Baseline power drawn when idle; strictly less than rated power."
            },
            {
                "field_name": "current_status",
                "type": "string",
                "required": True,
                "allowed_values": "['RUNNING', 'IDLE', 'MAINTENANCE', 'OFF']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Valid machine status enum."
            },
            {
                "field_name": "installed_date",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 date (YYYY-MM-DD)",
                "units": "date",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Must precede production and maintenance events."
            }
        ]
    },
    "MeterMachineMapping": {
        "description": "Bridge table mapping physical meters to one or more machines with allocation ratios and effective validity periods.",
        "cardinality": "Bridge N:M between Meter and Machine",
        "fields": [
            {
                "field_name": "mapping_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^MAP-[0-9]{5}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Unique bridge record ID."
            },
            {
                "field_name": "meter_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Meter.meter_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference valid Meter."
            },
            {
                "field_name": "machine_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Machine.machine_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference valid Machine."
            },
            {
                "field_name": "allocation_ratio",
                "type": "float",
                "required": True,
                "allowed_values": "0.0 < ratio <= 1.0",
                "units": "fraction",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Sum of allocation ratios for a meter across all machines in a timespan should be <= 1.0."
            },
            {
                "field_name": "effective_from",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Start of electrical topology assignment."
            },
            {
                "field_name": "effective_to",
                "type": "string",
                "required": False,
                "allowed_values": "Null or ISO 8601 timestamp >= effective_from",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "End date of topology mapping; null indicates currently active."
            }
        ]
    },
    "Shift": {
        "description": "Operating shift definitions for plant workers and production schedule.",
        "cardinality": "1:N with ProductionBatch; N:1 with Plant",
        "fields": [
            {
                "field_name": "shift_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^SHF-[0-9]{4}-[0-9]{3}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Unique shift record identifier."
            },
            {
                "field_name": "plant_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Plant.plant_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference parent Plant."
            },
            {
                "field_name": "shift_name",
                "type": "string",
                "required": True,
                "allowed_values": "['MORNING', 'AFTERNOON', 'NIGHT']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Standard three-shift operating model."
            },
            {
                "field_name": "start_time",
                "type": "string",
                "required": True,
                "allowed_values": "HH:MM format (24h)",
                "units": "time",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Shift commencement time."
            },
            {
                "field_name": "end_time",
                "type": "string",
                "required": True,
                "allowed_values": "HH:MM format (24h)",
                "units": "time",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Shift termination time (wraps next day if end < start)."
            },
            {
                "field_name": "active_days",
                "type": "string",
                "required": True,
                "allowed_values": "Comma-separated days e.g. 'MON,TUE,WED,THU,FRI'",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Designates production operating days."
            }
        ]
    },
    "Tariff": {
        "description": "Electric utility commercial tariff schedule specifying Time-Of-Use (TOU) energy rates and peak demand capacity charges.",
        "cardinality": "N:1 with Plant",
        "fields": [
            {
                "field_name": "tariff_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^TAR-[0-9]{4}-[0-9]{3}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern TAR-<year>-<seq>; immutable."
            },
            {
                "field_name": "plant_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Plant.plant_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference valid Plant."
            },
            {
                "field_name": "tariff_name",
                "type": "string",
                "required": True,
                "allowed_values": "Free text tariff rate code (e.g. TOU-Large-Industrial-G2)",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Non-empty string."
            },
            {
                "field_name": "effective_from",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 date (YYYY-MM-DD)",
                "units": "date",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Tariff schedule start date."
            },
            {
                "field_name": "effective_to",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 date >= effective_from",
                "units": "date",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Tariff schedule expiry date."
            },
            {
                "field_name": "rate_type",
                "type": "string",
                "required": True,
                "allowed_values": "['TOU', 'FLAT']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Pricing structure."
            },
            {
                "field_name": "peak_rate_kwh",
                "type": "float",
                "required": True,
                "allowed_values": "> 0.0 and > mid_peak_rate_kwh",
                "units": "currency/kWh",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Energy rate during high-demand peak hours."
            },
            {
                "field_name": "mid_peak_rate_kwh",
                "type": "float",
                "required": True,
                "allowed_values": "> 0.0 and > off_peak_rate_kwh",
                "units": "currency/kWh",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Energy rate during partial peak hours."
            },
            {
                "field_name": "off_peak_rate_kwh",
                "type": "float",
                "required": True,
                "allowed_values": "> 0.0",
                "units": "currency/kWh",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Energy rate during baseline/night hours."
            },
            {
                "field_name": "peak_demand_charge_kw",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "currency/kW/month",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Capacity surcharge billed on the monthly peak 15-min kW demand."
            },
            {
                "field_name": "peak_window_start",
                "type": "string",
                "required": True,
                "allowed_values": "HH:MM (e.g. '14:00')",
                "units": "time",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Start of peak billing interval."
            },
            {
                "field_name": "peak_window_end",
                "type": "string",
                "required": True,
                "allowed_values": "HH:MM (e.g. '18:00')",
                "units": "time",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "End of peak billing interval."
            },
            {
                "field_name": "mid_peak_window_start",
                "type": "string",
                "required": True,
                "allowed_values": "HH:MM (e.g. '08:00')",
                "units": "time",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Start of mid-peak billing interval."
            },
            {
                "field_name": "mid_peak_window_end",
                "type": "string",
                "required": True,
                "allowed_values": "HH:MM (e.g. '14:00')",
                "units": "time",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "End of mid-peak billing interval."
            },
            {
                "field_name": "currency",
                "type": "string",
                "required": True,
                "allowed_values": "['USD', 'EUR', 'INR', 'GBP']",
                "units": "ISO 4217 code",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Currency code."
            }
        ]
    },
    "WeatherObservation": {
        "description": "Hourly/sub-hourly meteorological readings impacting cooling, heating, and compressor efficiency.",
        "cardinality": "N:1 with Plant",
        "fields": [
            {
                "field_name": "weather_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^WTH-PLT-[0-9]{3}-[0-9]{12}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern WTH-<plant-id>-<timestamp>; unique."
            },
            {
                "field_name": "plant_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Plant.plant_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference valid Plant."
            },
            {
                "field_name": "timestamp",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Observation timestamp."
            },
            {
                "field_name": "ambient_temp_c",
                "type": "float",
                "required": True,
                "allowed_values": "-30.0 <= temp <= 55.0",
                "units": "°C",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Physical ambient dry-bulb temperature."
            },
            {
                "field_name": "relative_humidity_pct",
                "type": "float",
                "required": True,
                "allowed_values": "0.0 <= humidity <= 100.0",
                "units": "%",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Relative humidity percentage."
            },
            {
                "field_name": "dew_point_c",
                "type": "float",
                "required": True,
                "allowed_values": "<= ambient_temp_c",
                "units": "°C",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Dew point temperature cannot exceed dry bulb temperature."
            },
            {
                "field_name": "cooling_degree_hours",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "degree-hours",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Max(0.0, ambient_temp_c - 18.3)."
            }
        ]
    },
    "ProductionBatch": {
        "description": "Discrete manufacturing batch run with scheduled volumes, output, scrap, and timestamps.",
        "cardinality": "N:1 with Plant; N:1 with Shift; 1:N with BatchMachineExecution",
        "fields": [
            {
                "field_name": "batch_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^BATCH-[0-9]{4}-[0-9]{6}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern BATCH-<year>-<seq>; immutable."
            },
            {
                "field_name": "plant_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Plant.plant_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference parent Plant."
            },
            {
                "field_name": "product_sku",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^SKU-[A-Z0-9]{4,8}$",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Finished good catalog reference."
            },
            {
                "field_name": "planned_qty",
                "type": "integer",
                "required": True,
                "allowed_values": "> 0",
                "units": "pieces",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Scheduled production batch size."
            },
            {
                "field_name": "produced_qty",
                "type": "integer",
                "required": True,
                "allowed_values": ">= 0",
                "units": "pieces",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Total parts completed."
            },
            {
                "field_name": "scrap_qty",
                "type": "integer",
                "required": True,
                "allowed_values": ">= 0 and scrap_qty <= produced_qty",
                "units": "pieces",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Defective parts rejected; cannot exceed total produced."
            },
            {
                "field_name": "start_time",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Batch commencement."
            },
            {
                "field_name": "end_time",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp >= start_time",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Batch completion time; must follow start_time."
            },
            {
                "field_name": "shift_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Shift.shift_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Assigned production shift."
            },
            {
                "field_name": "status",
                "type": "string",
                "required": True,
                "allowed_values": "['PLANNED', 'IN_PROGRESS', 'COMPLETED', 'ABORTED']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Batch lifecycle status."
            }
        ]
    },
    "BatchMachineExecution": {
        "description": "Bridge table allocating machine runtime, idle time, and output pieces for a specific production batch.",
        "cardinality": "Bridge N:M between ProductionBatch and Machine",
        "fields": [
            {
                "field_name": "execution_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^EXE-[0-9]{6}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Unique execution event ID."
            },
            {
                "field_name": "batch_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing ProductionBatch.batch_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference valid Batch."
            },
            {
                "field_name": "machine_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Machine.machine_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference valid Machine."
            },
            {
                "field_name": "runtime_min",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "minutes",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Active machine manufacturing time."
            },
            {
                "field_name": "idle_min",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "minutes",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Non-productive powered idle waiting time."
            },
            {
                "field_name": "output_qty",
                "type": "integer",
                "required": True,
                "allowed_values": ">= 0",
                "units": "pieces",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Pieces processed by this specific asset."
            }
        ]
    },
    "StateChangeEvent": {
        "description": "Immutable audit log persisting entity state changes, ensuring historic traceability without overwriting records.",
        "cardinality": "N:1 with Machine, ProductionBatch, Recommendation, or Meter",
        "fields": [
            {
                "field_name": "event_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^EVT-[0-9]{4}-[0-9]{6}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern EVT-<year>-<seq>; immutable unique identifier."
            },
            {
                "field_name": "entity_type",
                "type": "string",
                "required": True,
                "allowed_values": "['Machine', 'ProductionBatch', 'Recommendation', 'Meter']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Target domain entity type undergoing lifecycle transition."
            },
            {
                "field_name": "entity_id",
                "type": "string",
                "required": True,
                "allowed_values": "Valid primary key of target entity",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference an existing entity record."
            },
            {
                "field_name": "previous_state",
                "type": "string",
                "required": False,
                "allowed_values": "Valid lifecycle state enum or None for creation",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Pre-transition lifecycle state."
            },
            {
                "field_name": "new_state",
                "type": "string",
                "required": True,
                "allowed_values": "Valid lifecycle state enum",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Post-transition lifecycle state following valid transition graph."
            },
            {
                "field_name": "transition_timestamp",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Exact chronological timestamp when transition occurred."
            },
            {
                "field_name": "triggered_by",
                "type": "string",
                "required": True,
                "allowed_values": "['SCADA_SYSTEM', 'PLANT_OPERATOR', 'PRODUCTION_PLANNER', 'MAINTENANCE_ENGINEER', 'ENERGY_INTELLIGENCE_ENGINE']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Originator system or user actor initiating state transition."
            },
            {
                "field_name": "reason",
                "type": "string",
                "required": True,
                "allowed_values": "Descriptive reason string",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Auditable business rationale for lifecycle transition."
            }
        ]
    },
    "EnergyReading": {
        "description": "Synchronous 15-minute telemetry intervals captured from electrical meters.",
        "cardinality": "N:1 with Meter",
        "fields": [
            {
                "field_name": "reading_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^ENG-MTR-PLT-[0-9]{3}-[0-9]{3}-[0-9]{12}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern ENG-<meter-id>-<timestamp>; unique."
            },
            {
                "field_name": "meter_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Meter.meter_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference existing Meter."
            },
            {
                "field_name": "timestamp",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp at 15-min boundary (:00, :15, :30, :45)",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Must align with sampling cadence."
            },
            {
                "field_name": "active_power_kw",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "kW",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Average active load demand over the 15-minute interval."
            },
            {
                "field_name": "energy_kwh",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "kWh",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Arithmetic reconciliation: energy_kwh == active_power_kw * (cadence_min / 60.0)."
            },
            {
                "field_name": "power_factor",
                "type": "float",
                "required": True,
                "allowed_values": "0.70 <= pf <= 1.0",
                "units": "ratio",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Cosine of phase angle between voltage and current."
            },
            {
                "field_name": "voltage_v",
                "type": "float",
                "required": True,
                "allowed_values": "> 0.0",
                "units": "V",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Line-to-line or line-to-neutral RMS voltage."
            },
            {
                "field_name": "current_a",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "A",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Three-phase average RMS current."
            },
            {
                "field_name": "data_source",
                "type": "string",
                "required": True,
                "allowed_values": "['SCADA', 'IOT_GATEWAY']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Data acquisition pipeline."
            }
        ]
    },
    "MaintenanceEvent": {
        "description": "Historical log of machine maintenance activities, equipment overhauls, and motor tuning.",
        "cardinality": "N:1 with Machine",
        "fields": [
            {
                "field_name": "event_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^MNT-[0-9]{4}-[0-9]{6}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern MNT-<year>-<seq>; immutable."
            },
            {
                "field_name": "machine_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Machine.machine_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference existing Machine."
            },
            {
                "field_name": "event_type",
                "type": "string",
                "required": True,
                "allowed_values": "['PREVENTIVE', 'UNPLANNED', 'OVERHAUL']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Maintenance classification."
            },
            {
                "field_name": "start_time",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Work commencement."
            },
            {
                "field_name": "end_time",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp >= start_time",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Work completion."
            },
            {
                "field_name": "description",
                "type": "string",
                "required": True,
                "allowed_values": "Free text (e.g. Bearing replacement, VFD parameter re-tuning)",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Detailed work log."
            },
            {
                "field_name": "energy_impact_kwh",
                "type": "float",
                "required": True,
                "allowed_values": "Float value (negative denotes efficiency gain, positive denotes degradation)",
                "units": "kWh/day",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Measurable shift in daily energy consumption post-event."
            }
        ]
    },
    "Recommendation": {
        "description": "Prescriptive, measurable energy saving or peak shaving actions targeted to specific plant roles.",
        "cardinality": "N:1 with Plant; optional N:1 with Machine",
        "fields": [
            {
                "field_name": "recommendation_id",
                "type": "string",
                "required": True,
                "allowed_values": "Regex ^REC-[0-9]{4}-[0-9]{6}$",
                "units": "dimensionless",
                "uniqueness": "PRIMARY_KEY",
                "validation_rule": "Pattern REC-<year>-<seq>; immutable."
            },
            {
                "field_name": "plant_id",
                "type": "string",
                "required": True,
                "allowed_values": "Existing Plant.plant_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Must reference valid Plant."
            },
            {
                "field_name": "machine_id",
                "type": "string",
                "required": False,
                "allowed_values": "Null or existing Machine.machine_id",
                "units": "dimensionless",
                "uniqueness": "FOREIGN_KEY",
                "validation_rule": "Optional asset reference for machine-specific recommendations."
            },
            {
                "field_name": "category",
                "type": "string",
                "required": True,
                "allowed_values": "['PEAK_SHAVING', 'IDLE_REDUCTION', 'LOAD_SHIFTING', 'MAINTENANCE_TUNING']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Energy efficiency category."
            },
            {
                "field_name": "title",
                "type": "string",
                "required": True,
                "allowed_values": "Concise headline (e.g. De-energize Injection Mold 02 during shift break)",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Action-oriented title."
            },
            {
                "field_name": "description",
                "type": "string",
                "required": True,
                "allowed_values": "Detailed rationale with evidence from telemetry and shift calendar",
                "units": "dimensionless",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Preserves traceability to root cause readings."
            },
            {
                "field_name": "action_actor",
                "type": "string",
                "required": True,
                "allowed_values": "['PLANT_OPERATOR', 'MAINTENANCE_ENGINEER', 'PRODUCTION_PLANNER', 'OT_IT_ADMIN']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Designated role responsible for implementing action."
            },
            {
                "field_name": "baseline_kwh",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "kWh",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Empirical historical energy baseline being measured."
            },
            {
                "field_name": "estimated_kwh_savings",
                "type": "float",
                "required": True,
                "allowed_values": "> 0.0 and <= baseline_kwh",
                "units": "kWh",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Projected energy reduction; must be <= baseline_kwh."
            },
            {
                "field_name": "estimated_cost_savings",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "currency ($)",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Financial benefit evaluated against specific TOU tariff rates."
            },
            {
                "field_name": "payback_period_days",
                "type": "float",
                "required": True,
                "allowed_values": ">= 0.0",
                "units": "days",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "0.0 for zero-cost behavioral controls, or capital payback."
            },
            {
                "field_name": "status",
                "type": "string",
                "required": True,
                "allowed_values": "['OPEN', 'ACKNOWLEDGED', 'IMPLEMENTED', 'REJECTED']",
                "units": "enum",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Workflow lifecycle state."
            },
            {
                "field_name": "generated_at",
                "type": "string",
                "required": True,
                "allowed_values": "ISO 8601 timestamp",
                "units": "timestamp",
                "uniqueness": "NON_UNIQUE",
                "validation_rule": "Timestamp of analytics engine run."
            }
        ]
    }
}

def export_data_dictionary_markdown() -> str:
    """Generates markdown documentation of the complete data dictionary."""
    lines = ["# Industrial Energy Intelligence — Master Data Dictionary\n"]
    lines.append("This document specifies the exact schema, cardinality, constraints, units, and validation rules for all 10 core entities and relational bridge tables.\n")

    for entity_name, entity_info in DATA_DICTIONARY.items():
        lines.append(f"## Entity: `{entity_name}`")
        lines.append(f"**Description**: {entity_info['description']}")
        lines.append(f"**Cardinality & Relationships**: {entity_info['cardinality']}\n")
        lines.append("| Field Name | Type | Required | Uniqueness | Units | Allowed Values | Validation Rule |")
        lines.append("|:---|:---|:---:|:---:|:---|:---|:---|")
        for f in entity_info["fields"]:
            req_str = "Yes" if f["required"] else "No"
            lines.append(f"| `{f['field_name']}` | `{f['type']}` | {req_str} | {f['uniqueness']} | {f['units']} | {f['allowed_values']} | {f['validation_rule']} |")
        lines.append("\n---\n")

    return "\n".join(lines)

def export_data_dictionary_csv() -> str:
    """Exports data dictionary flattened as CSV text."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Entity", "Field", "Type", "Required", "Uniqueness", "Units", "Allowed Values", "Validation Rule"])
    for entity_name, entity_info in DATA_DICTIONARY.items():
        for f in entity_info["fields"]:
            writer.writerow([
                entity_name,
                f["field_name"],
                f["type"],
                "YES" if f["required"] else "NO",
                f["uniqueness"],
                f["units"],
                f["allowed_values"],
                f["validation_rule"]
            ])
    return output.getvalue()
