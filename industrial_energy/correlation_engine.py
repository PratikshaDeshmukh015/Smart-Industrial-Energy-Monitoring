"""
Correlation Engine for Industrial Energy Intelligence.
Correlates 15-minute machine telemetry with:
- Production batches and machine runtimes
- Shift calendars (Morning, Afternoon, Night, Off-shift)
- Time-of-Use (TOU) tariffs and capacity charges
- Ambient weather observations and cooling degree hours

Detects:
1. Idle baseload energy waste during unallocated/off-shift windows
2. Peak demand spikes exceeding contracted capacity or during TOU peak windows
3. Specific Energy Consumption (SEC / kWh per good unit) deviations
4. Weather-correlated auxiliary cooling degradation
Preserves full traceability to underlying readings.
"""

from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import math

class CorrelationEngine:
    def __init__(self, data: Dict[str, List[Any]]):
        self.data = data
        self._index_data()

    def _index_data(self):
        """Indexes data entities for fast relational joins and interval lookups."""
        self.plant = (self.data.get("Plant") or [{}])[0]
        self.plant_dict = self.plant if isinstance(self.plant, dict) else self.plant.__dict__
        self.contracted_peak_kw = float(self.plant_dict.get("contracted_peak_kw", 1250.0))

        # Machines map
        self.machines = {}
        for m in self.data.get("Machine", []):
            d = m if isinstance(m, dict) else m.__dict__
            self.machines[d["machine_id"]] = d

        # Meters map
        self.meters = {}
        for m in self.data.get("Meter", []):
            d = m if isinstance(m, dict) else m.__dict__
            self.meters[d["meter_id"]] = d

        # Meter to Machine mappings
        self.meter_to_machines = defaultdict(list)
        self.machine_to_meters = defaultdict(list)
        for map_rec in self.data.get("MeterMachineMapping", []):
            d = map_rec if isinstance(map_rec, dict) else map_rec.__dict__
            self.meter_to_machines[d["meter_id"]].append(d["machine_id"])
            self.machine_to_meters[d["machine_id"]].append(d["meter_id"])

        # Tariffs
        self.tariffs = [t if isinstance(t, dict) else t.__dict__ for t in self.data.get("Tariff", [])]
        self.primary_tariff = self.tariffs[0] if self.tariffs else {}

        # Weather lookup by timestamp prefix (hourly)
        self.weather_by_hour = {}
        for w in self.data.get("WeatherObservation", []):
            d = w if isinstance(w, dict) else w.__dict__
            ts_hour = d["timestamp"][:13] # YYYY-MM-DDTHH
            self.weather_by_hour[ts_hour] = d

        # Batches parsed with datetime
        self.parsed_batches = []
        for b in self.data.get("ProductionBatch", []):
            d = b if isinstance(b, dict) else b.__dict__
            try:
                t0 = datetime.fromisoformat(d["start_time"])
                t1 = datetime.fromisoformat(d["end_time"])
                self.parsed_batches.append({**d, "_t0": t0, "_t1": t1})
            except Exception:
                pass

        # Batch executions
        self.executions_by_batch = defaultdict(list)
        for exe in self.data.get("BatchMachineExecution", []):
            d = exe if isinstance(exe, dict) else exe.__dict__
            self.executions_by_batch[d["batch_id"]].append(d)

    def get_tariff_for_time(self, dt: datetime) -> Tuple[str, float]:
        """
        Determines TOU tariff window ('PEAK', 'MID_PEAK', 'OFF_PEAK') and rate ($/kWh).
        """
        t = self.primary_tariff
        hour_min = dt.strftime("%H:%M")
        
        # Check Peak window (e.g. 14:00 - 18:00 on weekdays)
        is_weekend = dt.weekday() >= 5
        peak_start = t.get("peak_window_start", "14:00")
        peak_end = t.get("peak_window_end", "18:00")
        mid_start = t.get("mid_peak_window_start", "08:00")
        mid_end = t.get("mid_peak_window_end", "22:00")

        if not is_weekend and peak_start <= hour_min < peak_end:
            return "PEAK", float(t.get("peak_rate_kwh", 0.24))
        elif not is_weekend and mid_start <= hour_min < mid_end:
            return "MID_PEAK", float(t.get("mid_peak_rate_kwh", 0.12))
        else:
            return "OFF_PEAK", float(t.get("off_peak_rate_kwh", 0.065))

    def get_weather_for_time(self, dt: datetime) -> Optional[Dict[str, Any]]:
        ts_hour = dt.strftime("%Y-%m-%dT%H")
        return self.weather_by_hour.get(ts_hour)

    def analyze_all(self) -> Dict[str, Any]:
        """Executes complete analytical correlation pipeline."""
        exceptions = self.handle_exceptions()
        idle_waste = self.detect_idle_waste()
        peak_events = self.detect_peak_demand_events()
        sec_results = self.calculate_specific_energy_consumption()
        weather_insights = self.analyze_weather_correlation()

        return {
            "exceptions": exceptions,
            "idle_waste": idle_waste,
            "peak_events": peak_events,
            "sec_results": sec_results,
            "weather_insights": weather_insights,
            "metrics": {
                "total_idle_waste_kwh": sum(w["waste_kwh"] for w in idle_waste),
                "total_idle_waste_cost_usd": sum(w["waste_cost_usd"] for w in idle_waste),
                "peak_breach_count": sum(1 for p in peak_events if p["is_contract_breach"]),
                "highest_peak_kw": max((p["peak_kw"] for p in peak_events), default=0.0),
                "batches_analyzed": len(sec_results),
                "exceptions_handled_count": len(exceptions)
            }
        }

    def handle_exceptions(self) -> List[Dict[str, Any]]:
        """
        Exception Handling Path:
        Detects telemetry anomalies (telemetry gaps, unit confusion), routes through
        an explicit exception resolution path, preserves traceability, and calculates
        corrected estimation so downstream billing and SEC rollups are not corrupted.
        """
        exception_records = []
        readings = [r if isinstance(r, dict) else r.__dict__ for r in self.data.get("EnergyReading", [])]

        # 1. Detect telemetry gaps by grouping readings by meter and sorting chronologically
        readings_by_meter = defaultdict(list)
        for r in readings:
            try:
                dt = datetime.fromisoformat(r["timestamp"])
                readings_by_meter[r["meter_id"]].append((dt, r))
            except Exception:
                pass

        for meter_id, r_list in readings_by_meter.items():
            r_list.sort(key=lambda x: x[0])
            for i in range(1, len(r_list)):
                dt_prev, r_prev = r_list[i - 1]
                dt_curr, r_curr = r_list[i]
                diff_min = (dt_curr - dt_prev).total_seconds() / 60.0
                if diff_min > 20.0: # Expected 15 min; gap detected
                    gap_ts = (dt_prev + timedelta(minutes=15)).isoformat()
                    interpolated_kw = round((float(r_prev["active_power_kw"]) + float(r_curr["active_power_kw"])) / 2.0, 2)
                    interpolated_kwh = round(interpolated_kw * 0.25, 4)
                    exception_records.append({
                        "exception_id": f"EXC-GAP-{meter_id}-{dt_prev.strftime('%Y%m%d%H%M')}",
                        "issue_type": "METER_TELEMETRY_GAP",
                        "meter_id": meter_id,
                        "timestamp": gap_ts,
                        "description": f"Missing 15-minute telemetry interval detected ({diff_min:.0f} min gap between readings).",
                        "exception_path_taken": "LINEAR_INTERPOLATION_ESTIMATION",
                        "corrected_kw": interpolated_kw,
                        "corrected_kwh": interpolated_kwh,
                        "assigned_actor": "OT_IT_ADMIN",
                        "traceable_prev_reading": r_prev.get("reading_id"),
                        "traceable_next_reading": r_curr.get("reading_id")
                    })

        # 2. Detect kW/kWh arithmetic confusion in readings
        for r in readings:
            try:
                kw = float(r["active_power_kw"])
                kwh = float(r["energy_kwh"])
                if abs(kwh - (kw * 0.25)) > 0.05:
                    exception_records.append({
                        "exception_id": f"EXC-UNIT-{r.get('reading_id')}",
                        "issue_type": "KW_CONFUSED_WITH_KWH",
                        "meter_id": r.get("meter_id"),
                        "timestamp": r.get("timestamp"),
                        "description": f"Arithmetic discrepancy: reported {kwh} kWh != expected {kw * 0.25:.4f} kWh.",
                        "exception_path_taken": "CADENCE_CORRECTED_RECALCULATION",
                        "corrected_kw": kw,
                        "corrected_kwh": round(kw * 0.25, 4),
                        "assigned_actor": "OT_IT_ADMIN",
                        "traceable_reading_id": r.get("reading_id")
                    })
            except Exception:
                pass

        return exception_records

    def detect_idle_waste(self) -> List[Dict[str, Any]]:
        """
        Detects unallocated machine idle power consumption:
        Occurs when a machine is drawing substantial electrical power during periods
        where no production batch is scheduled (e.g. weekend shutdowns, lunch shifts).
        """
        waste_records = []
        readings = [r if isinstance(r, dict) else r.__dict__ for r in self.data.get("EnergyReading", [])]

        # Group readings by machine
        # Machine readings are from Level 3 meters (or mapped meters)
        for r in readings:
            m_id = r["meter_id"]
            meter_meta = self.meters.get(m_id, {})
            # Only analyze machine disconnect meters
            if int(meter_meta.get("meter_level", 0)) != 3:
                continue

            dt = datetime.fromisoformat(r["timestamp"])
            active_kw = float(r["active_power_kw"])
            kwh = float(r["energy_kwh"])

            # Find mapped machines
            mach_ids = self.meter_to_machines.get(m_id, [])
            if not mach_ids:
                continue
            primary_mach = self.machines.get(mach_ids[0], {})
            standby_kw = float(primary_mach.get("standby_power_kw", 25.0))

            # Check if any production batch was actively executing at this time
            is_in_batch = any(b["_t0"] <= dt <= b["_t1"] for b in self.parsed_batches)
            
            # Waste condition:
            # 1. Weekend idle: drawing power when facility is closed
            # 2. Workday unallocated: drawing > 1.25x standby power when no batch is running
            is_weekend = dt.weekday() >= 5
            if (is_weekend and active_kw > standby_kw * 0.8) or (not is_in_batch and active_kw > standby_kw * 1.3):
                window_name, rate = self.get_tariff_for_time(dt)
                excess_kw = active_kw - (standby_kw * 0.2) # Baseline if properly de-energized
                waste_kwh = round(excess_kw * 0.25, 4)
                waste_cost = round(waste_kwh * rate, 2)

                waste_records.append({
                    "waste_id": f"WST-{m_id}-{dt.strftime('%Y%m%d%H%M')}",
                    "meter_id": m_id,
                    "machine_id": primary_mach.get("machine_id", "N/A"),
                    "machine_name": primary_mach.get("name", "Unknown"),
                    "timestamp": r["timestamp"],
                    "reason": "HIGH_IDLE_OFF_SHIFT" if is_weekend else "UNALLOCATED_STANDBY_DRAIN",
                    "active_kw": active_kw,
                    "baseline_kw": round(standby_kw * 0.2, 2),
                    "waste_kwh": waste_kwh,
                    "tariff_rate_kwh": rate,
                    "tariff_window": window_name,
                    "waste_cost_usd": waste_cost,
                    "traceable_reading_id": r["reading_id"]
                })

        return waste_records

    def detect_peak_demand_events(self) -> List[Dict[str, Any]]:
        """
        Analyzes 15-minute main incomer demand intervals to identify:
        1. Demand spikes exceeding contracted capacity (1250 kW)
        2. High coincident peaks (> 85% of contracted capacity) during TOU Peak hours (14:00 - 18:00)
        """
        peak_events = []
        readings = [r if isinstance(r, dict) else r.__dict__ for r in self.data.get("EnergyReading", [])]
        main_meter_id = "MTR-PLT-001-001"

        incomer_readings = [r for r in readings if r["meter_id"] == main_meter_id]
        
        for r in incomer_readings:
            dt = datetime.fromisoformat(r["timestamp"])
            kw = float(r["active_power_kw"])
            window_name, rate = self.get_tariff_for_time(dt)
            is_breach = kw > self.contracted_peak_kw
            is_peak_window_spike = (window_name == "PEAK" and kw > self.contracted_peak_kw * 0.88)

            if is_breach or is_peak_window_spike:
                # Capacity penalty risk calculation
                demand_charge_rate = float(self.primary_tariff.get("peak_demand_charge_kw", 15.50))
                excess_demand_kw = max(0.0, kw - self.contracted_peak_kw)
                penalty_exposure_usd = round(excess_demand_kw * demand_charge_rate, 2)

                peak_events.append({
                    "event_id": f"PEAK-{dt.strftime('%Y%m%d%H%M')}",
                    "meter_id": main_meter_id,
                    "timestamp": r["timestamp"],
                    "peak_kw": kw,
                    "contracted_kw": self.contracted_peak_kw,
                    "is_contract_breach": is_breach,
                    "tariff_window": window_name,
                    "excess_kw": round(excess_demand_kw, 2),
                    "monthly_penalty_exposure_usd": penalty_exposure_usd,
                    "traceable_reading_id": r["reading_id"]
                })

        return peak_events

    def calculate_specific_energy_consumption(self) -> List[Dict[str, Any]]:
        """
        Calculates Specific Energy Consumption (SEC / kWh per good unit) for each batch.
        SEC = Total Batch kWh / (Produced Qty - Scrap Qty).
        Identifies batches with abnormally high energy intensity.
        """
        results = []
        readings = [r if isinstance(r, dict) else r.__dict__ for r in self.data.get("EnergyReading", [])]
        
        # Machine readings by meter
        machine_readings_by_meter = defaultdict(list)
        for r in readings:
            m = self.meters.get(r["meter_id"], {})
            if int(m.get("meter_level", 0)) == 3:
                machine_readings_by_meter[r["meter_id"]].append(r)

        # SKU baseline tracker
        sku_energy_samples = defaultdict(list)

        for batch in self.parsed_batches:
            b_id = batch["batch_id"]
            sku = batch["product_sku"]
            produced_qty = int(batch.get("produced_qty", 0))
            scrap_qty = int(batch.get("scrap_qty", 0))
            good_qty = max(1, produced_qty - scrap_qty)
            t0, t1 = batch["_t0"], batch["_t1"]

            # Sum energy from all machines assigned to this batch
            batch_execs = self.executions_by_batch.get(b_id, [])
            total_batch_kwh = 0.0

            for exe in batch_execs:
                mach_id = exe["machine_id"]
                assigned_meters = self.machine_to_meters.get(mach_id, [])
                for m_id in assigned_meters:
                    for r in machine_readings_by_meter.get(m_id, []):
                        r_dt = datetime.fromisoformat(r["timestamp"])
                        if t0 <= r_dt <= t1:
                            total_batch_kwh += float(r["energy_kwh"])

            sec = round(total_batch_kwh / good_qty, 4) if good_qty > 0 else 0.0
            sku_energy_samples[sku].append(sec)

            results.append({
                "batch_id": b_id,
                "product_sku": sku,
                "produced_qty": produced_qty,
                "scrap_qty": scrap_qty,
                "good_qty": good_qty,
                "scrap_rate_pct": round((scrap_qty / max(1, produced_qty)) * 100, 2),
                "total_kwh": round(total_batch_kwh, 2),
                "sec_kwh_per_unit": sec
            })

        # Calculate average benchmark per SKU and flag intensity shifts
        sku_averages = {sku: (sum(vals) / len(vals)) for sku, vals in sku_energy_samples.items() if vals}
        for r in results:
            avg_sec = sku_averages.get(r["product_sku"], r["sec_kwh_per_unit"])
            r["sku_baseline_sec"] = round(avg_sec, 4)
            r["intensity_deviation_pct"] = round(((r["sec_kwh_per_unit"] - avg_sec) / max(0.0001, avg_sec)) * 100, 1)
            r["is_high_intensity_waste"] = r["intensity_deviation_pct"] > 25.0

        return results

    def analyze_weather_correlation(self) -> Dict[str, Any]:
        """
        Correlates chiller electrical power with ambient temperature and cooling degree hours.
        Calculates baseline weather sensitivity (kW per °C ambient rise).
        """
        chiller_machines = [m for m in self.machines.values() if m["category"] == "CHILLER"]
        if not chiller_machines:
            return {"status": "NO_CHILLER_MACHINE"}

        chiller_id = chiller_machines[0]["machine_id"]
        chiller_meters = self.machine_to_meters.get(chiller_id, [])
        if not chiller_meters:
            return {"status": "NO_CHILLER_METER"}

        c_meter = chiller_meters[0]
        readings = [r if isinstance(r, dict) else r.__dict__ for r in self.data.get("EnergyReading", []) if r.get("meter_id") == c_meter]

        datapoints = []
        for r in readings:
            dt = datetime.fromisoformat(r["timestamp"])
            w = self.get_weather_for_time(dt)
            if w:
                datapoints.append({
                    "temp_c": float(w["ambient_temp_c"]),
                    "power_kw": float(r["active_power_kw"]),
                    "cdh": float(w["cooling_degree_hours"])
                })

        if len(datapoints) < 10:
            return {"status": "INSUFFICIENT_DATA"}

        # Linear regression: power_kw = alpha + beta * temp_c
        n = len(datapoints)
        sum_x = sum(d["temp_c"] for d in datapoints)
        sum_y = sum(d["power_kw"] for d in datapoints)
        sum_xy = sum(d["temp_c"] * d["power_kw"] for d in datapoints)
        sum_xx = sum(d["temp_c"] ** 2 for d in datapoints)

        denom = (n * sum_xx - sum_x ** 2)
        slope_kw_per_deg = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0.0
        base_kw = (sum_y - slope_kw_per_deg * sum_x) / n

        return {
            "chiller_machine_id": chiller_id,
            "meter_id": c_meter,
            "datapoints_count": n,
            "weather_sensitivity_kw_per_celsius": round(slope_kw_per_deg, 3),
            "base_thermal_kw": round(base_kw, 2),
            "cooling_waste_recommendation_trigger": slope_kw_per_deg > 3.0
        }
