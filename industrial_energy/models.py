"""
Data models and entity definitions for Industrial Energy Intelligence.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

class MeterType(str, Enum):
    MAIN_INCOMER = "MAIN_INCOMER"
    SUB_FEEDER = "SUB_FEEDER"
    MACHINE_LEVEL = "MACHINE_LEVEL"

class MeterStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"

class MachineCategory(str, Enum):
    STAMPING = "STAMPING"
    INJECTION_MOLD = "INJECTION_MOLD"
    CNC_MILLING = "CNC_MILLING"
    COMPRESSOR = "COMPRESSOR"
    CHILLER = "CHILLER"

class MachineStatus(str, Enum):
    RUNNING = "RUNNING"
    IDLE = "IDLE"
    MAINTENANCE = "MAINTENANCE"
    OFF = "OFF"

class ShiftName(str, Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    NIGHT = "NIGHT"

class TariffRateType(str, Enum):
    TOU = "TOU"
    FLAT = "FLAT"

class BatchStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"

class MaintenanceType(str, Enum):
    PREVENTIVE = "PREVENTIVE"
    UNPLANNED = "UNPLANNED"
    OVERHAUL = "OVERHAUL"

class RecommendationCategory(str, Enum):
    PEAK_SHAVING = "PEAK_SHAVING"
    IDLE_REDUCTION = "IDLE_REDUCTION"
    LOAD_SHIFTING = "LOAD_SHIFTING"
    MAINTENANCE_TUNING = "MAINTENANCE_TUNING"

class RecommendationStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IMPLEMENTED = "IMPLEMENTED"
    REJECTED = "REJECTED"

class ActorRole(str, Enum):
    PLANT_OPERATOR = "PLANT_OPERATOR"
    MAINTENANCE_ENGINEER = "MAINTENANCE_ENGINEER"
    PRODUCTION_PLANNER = "PRODUCTION_PLANNER"
    OT_IT_ADMIN = "OT_IT_ADMIN"

@dataclass
class Plant:
    plant_id: str
    name: str
    location: str
    timezone: str
    contracted_peak_kw: float
    voltage_kv: float
    created_at: str

@dataclass
class Meter:
    meter_id: str
    plant_id: str
    meter_name: str
    meter_type: str
    meter_level: int
    parent_meter_id: Optional[str]
    sampling_cadence_min: int
    ct_ratio: float
    status: str
    installed_date: str

@dataclass
class Machine:
    machine_id: str
    plant_id: str
    name: str
    category: str
    rated_power_kw: float
    standby_power_kw: float
    current_status: str
    installed_date: str

@dataclass
class MeterMachineMapping:
    mapping_id: str
    meter_id: str
    machine_id: str
    allocation_ratio: float
    effective_from: str
    effective_to: Optional[str]

@dataclass
class Shift:
    shift_id: str
    plant_id: str
    shift_name: str
    start_time: str
    end_time: str
    active_days: str

@dataclass
class Tariff:
    tariff_id: str
    plant_id: str
    tariff_name: str
    effective_from: str
    effective_to: str
    rate_type: str
    peak_rate_kwh: float
    mid_peak_rate_kwh: float
    off_peak_rate_kwh: float
    peak_demand_charge_kw: float
    peak_window_start: str
    peak_window_end: str
    mid_peak_window_start: str
    mid_peak_window_end: str
    currency: str

@dataclass
class WeatherObservation:
    weather_id: str
    plant_id: str
    timestamp: str
    ambient_temp_c: float
    relative_humidity_pct: float
    dew_point_c: float
    cooling_degree_hours: float

@dataclass
class ProductionBatch:
    batch_id: str
    plant_id: str
    product_sku: str
    planned_qty: int
    produced_qty: int
    scrap_qty: int
    start_time: str
    end_time: str
    shift_id: str
    status: str

@dataclass
class BatchMachineExecution:
    execution_id: str
    batch_id: str
    machine_id: str
    runtime_min: float
    idle_min: float
    output_qty: int

@dataclass
class EnergyReading:
    reading_id: str
    meter_id: str
    timestamp: str
    active_power_kw: float
    energy_kwh: float
    power_factor: float
    voltage_v: float
    current_a: float
    data_source: str

@dataclass
class MaintenanceEvent:
    event_id: str
    machine_id: str
    event_type: str
    start_time: str
    end_time: str
    description: str
    energy_impact_kwh: float

@dataclass
class StateChangeEvent:
    event_id: str
    entity_type: str
    entity_id: str
    previous_state: Optional[str]
    new_state: str
    transition_timestamp: str
    triggered_by: str
    reason: str

@dataclass
class Recommendation:
    recommendation_id: str
    plant_id: str
    machine_id: Optional[str]
    category: str
    title: str
    description: str
    action_actor: str
    baseline_kwh: float
    estimated_kwh_savings: float
    estimated_cost_savings: float
    payback_period_days: float
    status: str
    generated_at: str
