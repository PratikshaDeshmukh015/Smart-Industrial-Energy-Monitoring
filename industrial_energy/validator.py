"""
Validation Suite for Industrial Energy Intelligence.
Performs rigorous structural and business logic checks:
1. Primary key uniqueness
2. Foreign key referential integrity
3. Allowed enum validation
4. Date ordering and chronologies
5. Arithmetic reconciliation (energy = power * time, sum checks)
6. Duplicate interval checks
7. Generates structured JSON and human-readable summary reports
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional

class DataValidator:
    def __init__(self, data: Dict[str, List[Any]]):
        self.data = data
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}

    def validate_all(self) -> Dict[str, Any]:
        """Runs all validation rules and compiles findings."""
        self.errors.clear()
        self.warnings.clear()
        
        self._validate_primary_keys()
        self._validate_foreign_keys()
        self._validate_enums()
        self._validate_date_ordering()
        self._validate_arithmetic_reconciliation()
        self._validate_duplicates()
        self._validate_lifecycle_transitions()

        passed = len(self.errors) == 0
        summary = {
            "passed": passed,
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "entity_counts": {k: len(v) for k, v in self.data.items()}
        }
        return summary

    def _get_records(self, entity_name: str) -> List[Dict[str, Any]]:
        raw = self.data.get(entity_name, [])
        return [r if isinstance(r, dict) else r.__dict__ for r in raw]

    def _validate_primary_keys(self):
        pk_fields = {
            "Plant": "plant_id",
            "Meter": "meter_id",
            "Machine": "machine_id",
            "MeterMachineMapping": "mapping_id",
            "Shift": "shift_id",
            "Tariff": "tariff_id",
            "WeatherObservation": "weather_id",
            "ProductionBatch": "batch_id",
            "BatchMachineExecution": "execution_id",
            "EnergyReading": "reading_id",
            "MaintenanceEvent": "event_id",
            "StateChangeEvent": "event_id",
            "Recommendation": "recommendation_id",
        }

        for entity, pk in pk_fields.items():
            records = self._get_records(entity)
            seen = set()
            for r in records:
                val = r.get(pk)
                if val is None or val == "":
                    self.errors.append({
                        "rule": "PRIMARY_KEY_NULL",
                        "entity": entity,
                        "field": pk,
                        "message": f"Null or empty primary key in entity {entity}"
                    })
                elif val in seen:
                    self.errors.append({
                        "rule": "PRIMARY_KEY_DUPLICATE",
                        "entity": entity,
                        "field": pk,
                        "value": val,
                        "message": f"Duplicate primary key '{val}' in entity {entity}"
                    })
                else:
                    seen.add(val)

    def _validate_foreign_keys(self):
        plant_ids = {r["plant_id"] for r in self._get_records("Plant") if "plant_id" in r}
        meter_ids = {r["meter_id"] for r in self._get_records("Meter") if "meter_id" in r}
        machine_ids = {r["machine_id"] for r in self._get_records("Machine") if "machine_id" in r}
        shift_ids = {r["shift_id"] for r in self._get_records("Shift") if "shift_id" in r}
        batch_ids = {r["batch_id"] for r in self._get_records("ProductionBatch") if "batch_id" in r}

        # Meter -> Plant
        for m in self._get_records("Meter"):
            if m.get("plant_id") not in plant_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "Meter",
                    "field": "plant_id",
                    "value": m.get("plant_id"),
                    "record_id": m.get("meter_id"),
                    "message": f"Meter {m.get('meter_id')} references missing plant_id {m.get('plant_id')}"
                })
            # Parent meter
            parent = m.get("parent_meter_id")
            if parent and parent not in meter_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "Meter",
                    "field": "parent_meter_id",
                    "value": parent,
                    "record_id": m.get("meter_id"),
                    "message": f"Meter {m.get('meter_id')} references non-existent parent_meter_id {parent}"
                })

        # Machine -> Plant
        for m in self._get_records("Machine"):
            if m.get("plant_id") not in plant_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "Machine",
                    "field": "plant_id",
                    "value": m.get("plant_id"),
                    "record_id": m.get("machine_id"),
                    "message": f"Machine {m.get('machine_id')} references missing plant_id {m.get('plant_id')}"
                })

        # MeterMachineMapping -> Meter, Machine
        for map_rec in self._get_records("MeterMachineMapping"):
            if map_rec.get("meter_id") not in meter_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "MeterMachineMapping",
                    "field": "meter_id",
                    "value": map_rec.get("meter_id"),
                    "record_id": map_rec.get("mapping_id"),
                    "message": f"Mapping {map_rec.get('mapping_id')} references unknown meter {map_rec.get('meter_id')}"
                })
            if map_rec.get("machine_id") not in machine_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "MeterMachineMapping",
                    "field": "machine_id",
                    "value": map_rec.get("machine_id"),
                    "record_id": map_rec.get("mapping_id"),
                    "message": f"Mapping {map_rec.get('mapping_id')} references unknown machine {map_rec.get('machine_id')}"
                })

        # EnergyReading -> Meter
        for r in self._get_records("EnergyReading"):
            if r.get("meter_id") not in meter_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "EnergyReading",
                    "field": "meter_id",
                    "value": r.get("meter_id"),
                    "record_id": r.get("reading_id"),
                    "message": f"Reading {r.get('reading_id')} references unknown meter {r.get('meter_id')}"
                })

        # ProductionBatch -> Shift
        for b in self._get_records("ProductionBatch"):
            if b.get("shift_id") not in shift_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "ProductionBatch",
                    "field": "shift_id",
                    "value": b.get("shift_id"),
                    "record_id": b.get("batch_id"),
                    "message": f"Batch {b.get('batch_id')} references unknown shift {b.get('shift_id')}"
                })

        # BatchMachineExecution -> Batch, Machine
        for exe in self._get_records("BatchMachineExecution"):
            if exe.get("batch_id") not in batch_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "BatchMachineExecution",
                    "field": "batch_id",
                    "value": exe.get("batch_id"),
                    "record_id": exe.get("execution_id"),
                    "message": f"Execution {exe.get('execution_id')} references unknown batch {exe.get('batch_id')}"
                })
            if exe.get("machine_id") not in machine_ids:
                self.errors.append({
                    "rule": "FOREIGN_KEY_VIOLATION",
                    "entity": "BatchMachineExecution",
                    "field": "machine_id",
                    "value": exe.get("machine_id"),
                    "record_id": exe.get("execution_id"),
                    "message": f"Execution {exe.get('execution_id')} references unknown machine {exe.get('machine_id')}"
                })

    def _validate_enums(self):
        enum_specs = {
            ("Meter", "meter_type"): {"MAIN_INCOMER", "SUB_FEEDER", "MACHINE_LEVEL"},
            ("Meter", "status"): {"ACTIVE", "INACTIVE", "MAINTENANCE"},
            ("Machine", "category"): {"STAMPING", "INJECTION_MOLD", "CNC_MILLING", "COMPRESSOR", "CHILLER"},
            ("Machine", "current_status"): {"RUNNING", "IDLE", "MAINTENANCE", "OFF"},
            ("Shift", "shift_name"): {"MORNING", "AFTERNOON", "NIGHT"},
            ("Tariff", "rate_type"): {"TOU", "FLAT"},
            ("ProductionBatch", "status"): {"PLANNED", "IN_PROGRESS", "COMPLETED", "ABORTED"},
            ("EnergyReading", "data_source"): {"SCADA", "IOT_GATEWAY"},
            ("MaintenanceEvent", "event_type"): {"PREVENTIVE", "UNPLANNED", "OVERHAUL"},
        }

        for (entity, field_name), allowed in enum_specs.items():
            for r in self._get_records(entity):
                val = r.get(field_name)
                if val is not None and val not in allowed:
                    self.errors.append({
                        "rule": "INVALID_ENUM_VALUE",
                        "entity": entity,
                        "field": field_name,
                        "value": val,
                        "allowed": list(allowed),
                        "record_id": r.get(list(r.keys())[0]),
                        "message": f"Field {field_name} in {entity} has illegal enum value '{val}'"
                    })

    def _validate_date_ordering(self):
        for b in self._get_records("ProductionBatch"):
            try:
                t0 = datetime.fromisoformat(b["start_time"])
                t1 = datetime.fromisoformat(b["end_time"])
                if t1 < t0:
                    self.errors.append({
                        "rule": "CHRONOLOGY_VIOLATION",
                        "entity": "ProductionBatch",
                        "record_id": b["batch_id"],
                        "message": f"Batch end_time {b['end_time']} is before start_time {b['start_time']}"
                    })
            except Exception:
                pass

        for mnt in self._get_records("MaintenanceEvent"):
            try:
                t0 = datetime.fromisoformat(mnt["start_time"])
                t1 = datetime.fromisoformat(mnt["end_time"])
                if t1 < t0:
                    self.errors.append({
                        "rule": "CHRONOLOGY_VIOLATION",
                        "entity": "MaintenanceEvent",
                        "record_id": mnt["event_id"],
                        "message": f"Maintenance event end_time {mnt['end_time']} is before start_time {mnt['start_time']}"
                    })
            except Exception:
                pass

    def _validate_arithmetic_reconciliation(self):
        # 1. Reading energy_kwh == active_power_kw * (15/60)
        for r in self._get_records("EnergyReading"):
            try:
                kw = float(r["active_power_kw"])
                kwh = float(r["energy_kwh"])
                expected_kwh = kw * 0.25
                discrepancy = abs(kwh - expected_kwh)
                if discrepancy > 0.05: # > 0.05 kWh discrepancy
                    self.errors.append({
                        "rule": "ARITHMETIC_RECONCILIATION_FAIL",
                        "entity": "EnergyReading",
                        "record_id": r["reading_id"],
                        "meter_id": r["meter_id"],
                        "timestamp": r["timestamp"],
                        "observed_kwh": kwh,
                        "expected_kwh": round(expected_kwh, 4),
                        "message": f"Energy reading mismatch: reported {kwh} kWh != expected {expected_kwh:.4f} kWh (active_power_kw * 0.25h)"
                    })
            except Exception:
                pass

        # 2. Batch scrap_qty <= produced_qty
        for b in self._get_records("ProductionBatch"):
            try:
                prod = int(b["produced_qty"])
                scrap = int(b["scrap_qty"])
                if scrap > prod:
                    self.errors.append({
                        "rule": "ARITHMETIC_RECONCILIATION_FAIL",
                        "entity": "ProductionBatch",
                        "record_id": b["batch_id"],
                        "message": f"Scrap quantity {scrap} exceeds total produced quantity {prod}"
                    })
            except Exception:
                pass

        # 3. Weather dew point <= ambient temp
        for w in self._get_records("WeatherObservation"):
            try:
                t = float(w["ambient_temp_c"])
                dp = float(w["dew_point_c"])
                if dp > t + 0.01:
                    self.errors.append({
                        "rule": "PHYSICAL_CONSTRAINT_VIOLATION",
                        "entity": "WeatherObservation",
                        "record_id": w["weather_id"],
                        "message": f"Dew point {dp}°C exceeds dry-bulb temperature {t}°C"
                    })
            except Exception:
                pass

    def _validate_duplicates(self):
        # Check duplicate (meter_id, timestamp) in EnergyReading
        seen_reading_keys = set()
        for r in self._get_records("EnergyReading"):
            key = (r.get("meter_id"), r.get("timestamp"))
            if key in seen_reading_keys:
                self.errors.append({
                    "rule": "INTERVAL_DUPLICATE",
                    "entity": "EnergyReading",
                    "record_id": r.get("reading_id"),
                    "meter_id": r.get("meter_id"),
                    "timestamp": r.get("timestamp"),
                    "message": f"Duplicate interval reading for meter {key[0]} at timestamp {key[1]}"
                })
            else:
                seen_reading_keys.add(key)

    def _validate_lifecycle_transitions(self):
        """
        Step 8: Validates lifecycle transitions against legal state transition graphs.
        Machine: {None -> RUNNING, RUNNING -> IDLE, IDLE -> RUNNING, RUNNING -> MAINTENANCE, MAINTENANCE -> RUNNING, RUNNING -> OFF, OFF -> RUNNING}
        Batch: {None -> PLANNED, PLANNED -> IN_PROGRESS, IN_PROGRESS -> COMPLETED, IN_PROGRESS -> ABORTED}
        """
        valid_machine_transitions = {
            (None, "RUNNING"),
            ("RUNNING", "IDLE"),
            ("IDLE", "RUNNING"),
            ("RUNNING", "MAINTENANCE"),
            ("MAINTENANCE", "RUNNING"),
            ("RUNNING", "OFF"),
            ("OFF", "RUNNING"),
            ("IDLE", "OFF")
        }
        valid_batch_transitions = {
            (None, "PLANNED"),
            ("PLANNED", "IN_PROGRESS"),
            ("IN_PROGRESS", "COMPLETED"),
            ("IN_PROGRESS", "ABORTED")
        }

        for ev in self._get_records("StateChangeEvent"):
            ent_type = ev.get("entity_type")
            prev_s = ev.get("previous_state")
            if not prev_s or prev_s == "None" or prev_s == "":
                prev_s = None
            new_s = ev.get("new_state")
            pair = (prev_s, new_s)

            if ent_type == "Machine" and pair not in valid_machine_transitions:
                self.errors.append({
                    "rule": "ILLEGAL_LIFECYCLE_TRANSITION",
                    "entity": "StateChangeEvent",
                    "record_id": ev.get("event_id"),
                    "message": f"Illegal Machine lifecycle transition from '{prev_s}' to '{new_s}' for asset {ev.get('entity_id')}"
                })
            elif ent_type == "ProductionBatch" and pair not in valid_batch_transitions:
                self.errors.append({
                    "rule": "ILLEGAL_LIFECYCLE_TRANSITION",
                    "entity": "StateChangeEvent",
                    "record_id": ev.get("event_id"),
                    "message": f"Illegal ProductionBatch lifecycle transition from '{prev_s}' to '{new_s}' for batch {ev.get('entity_id')}"
                })

def generate_validation_summary_markdown(validation_report: Dict[str, Any]) -> str:
    """Formats validation report into user-facing markdown summary."""
    lines = ["# Industrial Energy Intelligence — Validation Summary Report\n"]
    status_badge = "PASS" if validation_report["passed"] else "FAIL (Edge Cases Detected)"
    lines.append(f"**Overall Status**: `{status_badge}`")
    lines.append(f"**Total Errors Detected**: `{validation_report['total_errors']}`")
    lines.append(f"**Total Warnings**: `{validation_report['total_warnings']}`\n")
    
    lines.append("## Entity Row Counts Verified")
    lines.append("| Entity | Record Count |")
    lines.append("|:---|:---:|")
    for ent, cnt in validation_report["entity_counts"].items():
        lines.append(f"| `{ent}` | {cnt:,} |")
    lines.append("\n")

    lines.append("## Validation Findings Breakdown")
    if not validation_report["errors"]:
        lines.append("All structural, relational, and arithmetic reconciliation checks passed with zero errors.\n")
    else:
        lines.append("| Severity | Rule | Entity | Record / Key | Message |")
        lines.append("|:---|:---|:---|:---|:---|")
        for err in validation_report["errors"]:
            rec_id = err.get("record_id", err.get("value", "N/A"))
            lines.append(f"| `ERROR` | `{err['rule']}` | `{err.get('entity', '-')}` | `{rec_id}` | {err['message']} |")
        lines.append("\n")

    return "\n".join(lines)
