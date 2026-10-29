"""
Deterministic Synthetic Data Generator for Industrial Energy Intelligence.
Supports dual scale:
- 'starter': 4 meters, 7 days, 150 batches (fast testing & verification)
- 'full': 20 meters, 90 days, 2000 batches (production scale benchmark)
Fixed seed ensures 100% reproducible generation.
Injects labelled edge cases and records them in isolated ground_truth.
"""

import random
import math
import json
import csv
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

from .models import (
    Plant, Meter, Machine, MeterMachineMapping, Shift, Tariff,
    WeatherObservation, ProductionBatch, BatchMachineExecution,
    EnergyReading, MaintenanceEvent, Recommendation, StateChangeEvent,
    MeterType, MeterStatus, MachineCategory, MachineStatus,
    ShiftName, BatchStatus, MaintenanceType, RecommendationCategory,
    RecommendationStatus, ActorRole
)

class IndustrialDataGenerator:
    def __init__(self, seed: int = 20261022, scale: str = "starter", inject_anomalies: bool = True):
        self.seed = seed
        self.scale = scale.lower()
        self.inject_anomalies = inject_anomalies
        self.rng = random.Random(seed)
        
        # Scale configurations
        if self.scale == "full":
            self.num_meters = 20
            self.num_machines = 16
            self.days = 90
            self.num_batches = 2000
        else: # starter
            self.num_meters = 4
            self.num_machines = 4
            self.days = 7
            self.num_batches = 150

        # Base simulation start date (fixed for reproducibility)
        self.start_datetime = datetime(2026, 6, 1, 0, 0, 0)
        self.cadence_minutes = 15

        # Generated entity collections
        self.plants: List[Plant] = []
        self.meters: List[Meter] = []
        self.machines: List[Machine] = []
        self.mappings: List[MeterMachineMapping] = []
        self.shifts: List[Shift] = []
        self.tariffs: List[Tariff] = []
        self.weather_observations: List[WeatherObservation] = []
        self.batches: List[ProductionBatch] = []
        self.executions: List[BatchMachineExecution] = []
        self.readings: List[EnergyReading] = []
        self.maintenance_events: List[MaintenanceEvent] = []
        self.state_change_events: List[StateChangeEvent] = []
        self.ground_truth_anomalies: List[Dict[str, Any]] = []

    def generate_all(self) -> Dict[str, Any]:
        """Runs the entire generation pipeline in strict dependency order."""
        # Reset RNG with fixed seed for reproducibility
        self.rng = random.Random(self.seed)

        self._generate_plant()
        self._generate_shifts()
        self._generate_tariffs()
        self._generate_meter_hierarchy()
        self._generate_machines_and_mappings()
        self._generate_weather()
        self._generate_production_batches()
        self._generate_energy_readings()
        self._generate_maintenance_events()
        self._generate_lifecycle_history()
        if self.inject_anomalies:
            self._inject_labelled_edge_cases()

        return {
            "Plant": self.plants,
            "Meter": self.meters,
            "Machine": self.machines,
            "MeterMachineMapping": self.mappings,
            "Shift": self.shifts,
            "Tariff": self.tariffs,
            "WeatherObservation": self.weather_observations,
            "ProductionBatch": self.batches,
            "BatchMachineExecution": self.executions,
            "EnergyReading": self.readings,
            "MaintenanceEvent": self.maintenance_events,
            "StateChangeEvent": self.state_change_events,
            "GroundTruth": self.ground_truth_anomalies,
        }

    def _generate_plant(self):
        plant = Plant(
            plant_id="PLT-001",
            name="Apex Precision Manufacturing - Plant 1",
            location="Chicago, IL",
            timezone="America/Chicago",
            contracted_peak_kw=1250.0,
            voltage_kv=13.8,
            created_at=self.start_datetime.isoformat()
        )
        self.plants.append(plant)

    def _generate_shifts(self):
        shifts = [
            Shift(
                shift_id="SHF-2026-001",
                plant_id="PLT-001",
                shift_name=ShiftName.MORNING.value,
                start_time="06:00",
                end_time="14:00",
                active_days="MON,TUE,WED,THU,FRI"
            ),
            Shift(
                shift_id="SHF-2026-002",
                plant_id="PLT-001",
                shift_name=ShiftName.AFTERNOON.value,
                start_time="14:00",
                end_time="22:00",
                active_days="MON,TUE,WED,THU,FRI"
            ),
            Shift(
                shift_id="SHF-2026-003",
                plant_id="PLT-001",
                shift_name=ShiftName.NIGHT.value,
                start_time="22:00",
                end_time="06:00",
                active_days="MON,TUE,WED,THU,FRI"
            ),
        ]
        self.shifts.extend(shifts)

    def _generate_tariffs(self):
        end_date = self.start_datetime + timedelta(days=self.days + 30)
        tariff = Tariff(
            tariff_id="TAR-2026-001",
            plant_id="PLT-001",
            tariff_name="TOU-Large-Industrial-G2",
            effective_from=self.start_datetime.date().isoformat(),
            effective_to=end_date.date().isoformat(),
            rate_type="TOU",
            peak_rate_kwh=0.24,
            mid_peak_rate_kwh=0.12,
            off_peak_rate_kwh=0.065,
            peak_demand_charge_kw=15.50,
            peak_window_start="14:00",
            peak_window_end="18:00",
            mid_peak_window_start="08:00",
            mid_peak_window_end="22:00",
            currency="USD"
        )
        self.tariffs.append(tariff)

    def _generate_meter_hierarchy(self):
        """
        Creates hierarchical meter topology:
        Level 1: Main Incomer (MTR-PLT-001-001)
        Level 2: Sub-feeders (MTR-PLT-001-002, 003, etc.)
        Level 3: Machine-level meters
        """
        # Level 1 Main Incomer
        incomer = Meter(
            meter_id="MTR-PLT-001-001",
            plant_id="PLT-001",
            meter_name="Main Grid Incomer",
            meter_type=MeterType.MAIN_INCOMER.value,
            meter_level=1,
            parent_meter_id=None,
            sampling_cadence_min=self.cadence_minutes,
            ct_ratio=100.0,
            status=MeterStatus.ACTIVE.value,
            installed_date="2024-01-15"
        )
        self.meters.append(incomer)

        if self.scale == "starter":
            # 1 main + 1 feeder + 2 machine meters = 4 meters
            feeder = Meter(
                meter_id="MTR-PLT-001-002",
                plant_id="PLT-001",
                meter_name="Heavy Machining Sub-Feeder",
                meter_type=MeterType.SUB_FEEDER.value,
                meter_level=2,
                parent_meter_id=incomer.meter_id,
                sampling_cadence_min=self.cadence_minutes,
                ct_ratio=40.0,
                status=MeterStatus.ACTIVE.value,
                installed_date="2024-02-01"
            )
            self.meters.append(feeder)

            for i in range(1, 3):
                m_id = f"MTR-PLT-001-{i+2:03d}"
                m_meter = Meter(
                    meter_id=m_id,
                    plant_id="PLT-001",
                    meter_name=f"Machine Disconnect Meter {i}",
                    meter_type=MeterType.MACHINE_LEVEL.value,
                    meter_level=3,
                    parent_meter_id=feeder.meter_id,
                    sampling_cadence_min=self.cadence_minutes,
                    ct_ratio=10.0,
                    status=MeterStatus.ACTIVE.value,
                    installed_date="2024-03-01"
                )
                self.meters.append(m_meter)
        else:
            # Full scale: 20 meters
            # 1 Main Incomer (Level 1)
            # 4 Sub-Feeders (Level 2): Machining, Molding, Utilities, Assembly
            # 15 Machine-level meters (Level 3)
            feeder_names = ["Machining Feeder", "Molding Feeder", "Utilities Feeder", "Assembly Feeder"]
            feeder_ids = []
            for i, fname in enumerate(feeder_names):
                f_id = f"MTR-PLT-001-{i+2:03d}"
                feeder_ids.append(f_id)
                self.meters.append(Meter(
                    meter_id=f_id,
                    plant_id="PLT-001",
                    meter_name=fname,
                    meter_type=MeterType.SUB_FEEDER.value,
                    meter_level=2,
                    parent_meter_id=incomer.meter_id,
                    sampling_cadence_min=self.cadence_minutes,
                    ct_ratio=40.0,
                    status=MeterStatus.ACTIVE.value,
                    installed_date="2024-02-01"
                ))

            # 15 Machine Level Meters (6 to 20)
            for m_idx in range(6, 21):
                m_id = f"MTR-PLT-001-{m_idx:03d}"
                parent_feeder = feeder_ids[(m_idx - 6) % len(feeder_ids)]
                self.meters.append(Meter(
                    meter_id=m_id,
                    plant_id="PLT-001",
                    meter_name=f"Sub-Distribution Meter {m_idx-5}",
                    meter_type=MeterType.MACHINE_LEVEL.value,
                    meter_level=3,
                    parent_meter_id=parent_feeder,
                    sampling_cadence_min=self.cadence_minutes,
                    ct_ratio=10.0,
                    status=MeterStatus.ACTIVE.value,
                    installed_date="2024-03-01"
                ))

    def _generate_machines_and_mappings(self):
        categories = [
            (MachineCategory.STAMPING.value, 180.0, 35.0),
            (MachineCategory.INJECTION_MOLD.value, 220.0, 42.0),
            (MachineCategory.CNC_MILLING.value, 75.0, 12.0),
            (MachineCategory.COMPRESSOR.value, 110.0, 28.0),
            (MachineCategory.CHILLER.value, 160.0, 30.0),
        ]

        machine_level_meters = [m for m in self.meters if m.meter_level == 3]
        if not machine_level_meters:
            # fallback to subfeeder
            machine_level_meters = [m for m in self.meters if m.meter_level == 2]

        map_counter = 1
        for i in range(1, self.num_machines + 1):
            cat_tuple = categories[(i - 1) % len(categories)]
            m_id = f"MCH-{i:03d}"
            machine = Machine(
                machine_id=m_id,
                plant_id="PLT-001",
                name=f"{cat_tuple[0]} Machine {i}",
                category=cat_tuple[0],
                rated_power_kw=cat_tuple[1],
                standby_power_kw=cat_tuple[2],
                current_status=MachineStatus.RUNNING.value,
                installed_date="2024-01-10"
            )
            self.machines.append(machine)

            # Map machine to a meter
            meter_assigned = machine_level_meters[(i - 1) % len(machine_level_meters)]
            mapping = MeterMachineMapping(
                mapping_id=f"MAP-{map_counter:05d}",
                meter_id=meter_assigned.meter_id,
                machine_id=m_id,
                allocation_ratio=1.0,
                effective_from=self.start_datetime.isoformat(),
                effective_to=None
            )
            self.mappings.append(mapping)
            map_counter += 1

    def _generate_weather(self):
        """Generates hourly ambient weather observations over simulation days."""
        total_hours = self.days * 24
        for h in range(total_hours):
            dt = self.start_datetime + timedelta(hours=h)
            day_of_year = dt.timetuple().tm_yday
            hour_of_day = dt.hour
            
            # Diurnal temperature cycle: coolest around 5 AM, warmest around 3 PM
            daily_mean = 24.0 + 6.0 * math.sin(2 * math.pi * (day_of_year - 150) / 365)
            diurnal_swing = 7.0 * math.sin(2 * math.pi * (hour_of_day - 9) / 24)
            random_noise = self.rng.gauss(0, 1.2)
            temp_c = round(daily_mean + diurnal_swing + random_noise, 2)
            
            # Relative humidity inversely correlated with temperature
            base_rh = 70.0 - (temp_c - 18.0) * 1.5 + self.rng.gauss(0, 3.0)
            rh_pct = round(max(20.0, min(95.0, base_rh)), 1)
            
            # Magnus formula approximation for dew point
            a, b = 17.27, 237.7
            alpha = ((a * temp_c) / (b + temp_c)) + math.log(rh_pct / 100.0)
            dew_point = round((b * alpha) / (a - alpha), 2)
            dew_point = min(dew_point, temp_c) # Physical constraint

            cooling_deg_hours = round(max(0.0, temp_c - 18.3), 2)

            w_id = f"WTH-PLT-001-{dt.strftime('%Y%m%d%H%M')}"
            self.weather_observations.append(WeatherObservation(
                weather_id=w_id,
                plant_id="PLT-001",
                timestamp=dt.isoformat(),
                ambient_temp_c=temp_c,
                relative_humidity_pct=rh_pct,
                dew_point_c=dew_point,
                cooling_degree_hours=cooling_deg_hours
            ))

    def _generate_production_batches(self):
        """Generates production batches aligned with shifts, machines, and output."""
        skus = [f"SKU-ENG{k:03d}" for k in range(1, 16)]
        batch_duration_hours = [2.0, 3.0, 4.0, 5.0, 6.0]
        
        sim_end = self.start_datetime + timedelta(days=self.days)
        batch_idx = 1
        exec_idx = 1
        
        # In full scale, run multiple concurrent production cells
        num_cells = 4 if self.scale == "full" else 1
        cell_timelines = [self.start_datetime + timedelta(hours=6 + (c * 2)) for c in range(num_cells)]

        while batch_idx <= self.num_batches:
            # Pick cell with earliest current time
            c_idx = min(range(num_cells), key=lambda i: cell_timelines[i])
            current_time = cell_timelines[c_idx]

            if current_time >= sim_end:
                # Wrap or reset timeline with small jitter if target batches not yet reached
                current_time = self.start_datetime + timedelta(days=self.rng.randint(0, self.days - 2), hours=self.rng.randint(6, 20))

            duration = self.rng.choice(batch_duration_hours)
            end_time = current_time + timedelta(hours=duration)
            if end_time > sim_end:
                end_time = sim_end - timedelta(minutes=15)
            
            # Map time to shift
            start_hour = current_time.hour
            if 6 <= start_hour < 14:
                shift_id = "SHF-2026-001"
            elif 14 <= start_hour < 22:
                shift_id = "SHF-2026-002"
            else:
                shift_id = "SHF-2026-003"

            sku = self.rng.choice(skus)
            planned_qty = self.rng.randint(200, 1500)
            yield_pct = self.rng.uniform(0.92, 0.99)
            produced_qty = int(planned_qty * yield_pct)
            scrap_qty = int(produced_qty * self.rng.uniform(0.01, 0.04))

            b_id = f"BATCH-2026-{batch_idx:06d}"
            batch = ProductionBatch(
                batch_id=b_id,
                plant_id="PLT-001",
                product_sku=sku,
                planned_qty=planned_qty,
                produced_qty=produced_qty,
                scrap_qty=scrap_qty,
                start_time=current_time.isoformat(),
                end_time=end_time.isoformat(),
                shift_id=shift_id,
                status=BatchStatus.COMPLETED.value
            )
            self.batches.append(batch)

            # Assign 1 to 3 machines for this batch
            num_assigned = min(len(self.machines), self.rng.randint(1, 3))
            assigned_machines = self.rng.sample(self.machines, num_assigned)
            for m in assigned_machines:
                runtime_min = round(duration * 60.0 * self.rng.uniform(0.80, 0.95), 1)
                idle_min = round((duration * 60.0) - runtime_min, 1)
                m_output = produced_qty // num_assigned
                self.executions.append(BatchMachineExecution(
                    execution_id=f"EXE-{exec_idx:06d}",
                    batch_id=b_id,
                    machine_id=m.machine_id,
                    runtime_min=runtime_min,
                    idle_min=idle_min,
                    output_qty=m_output
                ))
                exec_idx += 1

            # Advance cell time
            cell_timelines[c_idx] = end_time + timedelta(minutes=self.rng.choice([15, 30, 45, 60]))
            batch_idx += 1

    def _generate_energy_readings(self):
        """
        Generates 15-minute readings for all meters over the simulation period.
        Maintains realistic electrical power behavior:
        - Machine active load + standby power + noise
        - Hierarchy rollup: Feeder = sum(machines) + line loss; Main = sum(feeders) + auxiliary
        - Mathematical reconciliation: energy_kwh = active_power_kw * (cadence / 60)
        """
        total_intervals = (self.days * 24 * 60) // self.cadence_minutes
        
        # Build machine fast lookup for mappings
        meter_to_machines: Dict[str, List[Machine]] = {}
        for map_rec in self.mappings:
            mach = next((m for m in self.machines if m.machine_id == map_rec.machine_id), None)
            if mach:
                meter_to_machines.setdefault(map_rec.meter_id, []).append(mach)

        # Build meter hierarchy lookup
        feeders = [m for m in self.meters if m.meter_level == 2]
        machine_meters = [m for m in self.meters if m.meter_level == 3]

        for step in range(total_intervals):
            dt = self.start_datetime + timedelta(minutes=step * self.cadence_minutes)
            hour = dt.hour
            is_weekend = dt.weekday() >= 5
            
            # Weather lookup
            weather_h = dt.hour
            temp_est = 25.0 + 5.0 * math.sin(2 * math.pi * (weather_h - 9) / 24)
            chiller_weather_factor = 1.0 + max(0.0, (temp_est - 20.0) * 0.035)

            # 1. Generate Machine Level Meters first
            feeder_kw_totals: Dict[str, float] = {f.meter_id: 0.0 for f in feeders}

            for mm in machine_meters:
                assigned_mchs = meter_to_machines.get(mm.meter_id, [])
                total_kw = 0.0
                for mch in assigned_mchs:
                    if is_weekend:
                        # Baseline idle standby or off
                        load_kw = mch.standby_power_kw * self.rng.uniform(0.7, 1.1)
                    else:
                        # Workday: check if machine active
                        if 6 <= hour < 22:
                            # Day shifts: high probability of running near rated load
                            load_kw = (mch.rated_power_kw * self.rng.uniform(0.65, 0.90) +
                                       self.rng.gauss(0, 2.0))
                        else:
                            # Night shift: reduced production
                            load_kw = (mch.rated_power_kw * self.rng.uniform(0.35, 0.60) +
                                       self.rng.gauss(0, 1.5))
                    
                    if mch.category == MachineCategory.CHILLER.value:
                        load_kw *= chiller_weather_factor

                    total_kw += max(mch.standby_power_kw * 0.5, load_kw)

                # Add small electrical noise
                total_kw = round(total_kw, 2)
                energy_kwh = round(total_kw * (self.cadence_minutes / 60.0), 4)
                pf = round(self.rng.uniform(0.88, 0.96), 3)
                v = round(480.0 + self.rng.gauss(0, 2.5), 1)
                i_amps = round((total_kw * 1000.0) / (math.sqrt(3) * v * pf), 1)

                reading_id = f"ENG-{mm.meter_id}-{dt.strftime('%Y%m%d%H%M')}"
                self.readings.append(EnergyReading(
                    reading_id=reading_id,
                    meter_id=mm.meter_id,
                    timestamp=dt.isoformat(),
                    active_power_kw=total_kw,
                    energy_kwh=energy_kwh,
                    power_factor=pf,
                    voltage_v=v,
                    current_a=i_amps,
                    data_source="IOT_GATEWAY"
                ))

                if mm.parent_meter_id and mm.parent_meter_id in feeder_kw_totals:
                    feeder_kw_totals[mm.parent_meter_id] += total_kw

            # 2. Generate Sub-Feeders
            main_incomer_kw = 0.0
            for f in feeders:
                sub_sum = feeder_kw_totals.get(f.meter_id, 0.0)
                # If starter scale where machines directly mapped to feeder
                if not machine_meters:
                    assigned_mchs = meter_to_machines.get(f.meter_id, [])
                    for mch in assigned_mchs:
                        sub_sum += mch.rated_power_kw * (0.2 if is_weekend else 0.7)
                
                # Feeder has ~3% transformer/distribution cable loss
                feeder_kw = round(sub_sum * 1.03 + self.rng.uniform(2.0, 5.0), 2)
                f_energy = round(feeder_kw * (self.cadence_minutes / 60.0), 4)
                f_pf = round(self.rng.uniform(0.90, 0.97), 3)
                f_v = round(480.0 + self.rng.gauss(0, 1.5), 1)
                f_i = round((feeder_kw * 1000.0) / (math.sqrt(3) * f_v * f_pf), 1)

                reading_id = f"ENG-{f.meter_id}-{dt.strftime('%Y%m%d%H%M')}"
                self.readings.append(EnergyReading(
                    reading_id=reading_id,
                    meter_id=f.meter_id,
                    timestamp=dt.isoformat(),
                    active_power_kw=feeder_kw,
                    energy_kwh=f_energy,
                    power_factor=f_pf,
                    voltage_v=f_v,
                    current_a=f_i,
                    data_source="SCADA"
                ))
                main_incomer_kw += feeder_kw

            # 3. Generate Main Incomer
            # Main incomer sums all feeders + facility base loads (lighting, HVAC, office, losses)
            incomer_meter = self.meters[0]
            facility_base_kw = 45.0 + (15.0 if (8 <= hour < 18) else 5.0)
            total_incomer_kw = round(main_incomer_kw + facility_base_kw, 2)
            inc_energy = round(total_incomer_kw * (self.cadence_minutes / 60.0), 4)
            inc_pf = round(self.rng.uniform(0.92, 0.98), 3)
            inc_v = round(13800.0 + self.rng.gauss(0, 30.0), 1) # 13.8 kV grid
            inc_i = round((total_incomer_kw * 1000.0) / (math.sqrt(3) * inc_v * inc_pf), 2)

            inc_id = f"ENG-{incomer_meter.meter_id}-{dt.strftime('%Y%m%d%H%M')}"
            self.readings.append(EnergyReading(
                reading_id=inc_id,
                meter_id=incomer_meter.meter_id,
                timestamp=dt.isoformat(),
                active_power_kw=total_incomer_kw,
                energy_kwh=inc_energy,
                power_factor=inc_pf,
                voltage_v=inc_v,
                current_a=inc_i,
                data_source="SCADA"
            ))

    def _generate_maintenance_events(self):
        """Generates historical maintenance events with quantified energy impacts."""
        num_events = max(4, self.days // 7)
        for i in range(1, num_events + 1):
            target_mach = self.rng.choice(self.machines)
            start_offset = timedelta(days=self.rng.randint(2, max(3, self.days - 2)), hours=self.rng.randint(1, 20))
            event_start = self.start_datetime + start_offset
            event_end = event_start + timedelta(hours=self.rng.choice([2, 4, 8, 16]))

            ev_type = self.rng.choice([
                MaintenanceType.PREVENTIVE.value,
                MaintenanceType.UNPLANNED.value,
                MaintenanceType.OVERHAUL.value
            ])
            
            if ev_type == MaintenanceType.PREVENTIVE.value:
                desc = "Scheduled motor lubrication and VFD parameter retuning"
                impact = -18.5 # 18.5 kWh/day saved
            elif ev_type == MaintenanceType.OVERHAUL.value:
                desc = "Compressor valve replacement and compressed air leak remediation"
                impact = -45.0 # 45 kWh/day saved
            else:
                desc = "Emergency repair of seized bearing assembly"
                impact = -8.0

            m_id = f"MNT-2026-{i:06d}"
            self.maintenance_events.append(MaintenanceEvent(
                event_id=m_id,
                machine_id=target_mach.machine_id,
                event_type=ev_type,
                start_time=event_start.isoformat(),
                end_time=event_end.isoformat(),
                description=desc,
                energy_impact_kwh=impact
            ))

    def _generate_lifecycle_history(self):
        """
        Rule 4: Persists state changes as explicit records/events; does not overwrite history.
        Tracks Machine and Batch state lifecycle transitions.
        """
        evt_idx = 1
        # 1. Machine deployment state events
        for m in self.machines:
            self.state_change_events.append(StateChangeEvent(
                event_id=f"EVT-2026-{evt_idx:06d}",
                entity_type="Machine",
                entity_id=m.machine_id,
                previous_state=None,
                new_state=MachineStatus.RUNNING.value,
                transition_timestamp=f"{m.installed_date}T00:00:00",
                triggered_by="PLANT_OPERATOR",
                reason="Initial commissioning and electrical line energization"
            ))
            evt_idx += 1

        # 2. Maintenance transitions
        for mnt in self.maintenance_events:
            self.state_change_events.append(StateChangeEvent(
                event_id=f"EVT-2026-{evt_idx:06d}",
                entity_type="Machine",
                entity_id=mnt.machine_id,
                previous_state=MachineStatus.RUNNING.value,
                new_state=MachineStatus.MAINTENANCE.value,
                transition_timestamp=mnt.start_time,
                triggered_by="MAINTENANCE_ENGINEER",
                reason=f"Maintenance start: {mnt.description}"
            ))
            evt_idx += 1

            self.state_change_events.append(StateChangeEvent(
                event_id=f"EVT-2026-{evt_idx:06d}",
                entity_type="Machine",
                entity_id=mnt.machine_id,
                previous_state=MachineStatus.MAINTENANCE.value,
                new_state=MachineStatus.RUNNING.value,
                transition_timestamp=mnt.end_time,
                triggered_by="MAINTENANCE_ENGINEER",
                reason=f"Maintenance completed with energy impact {mnt.energy_impact_kwh} kWh/day"
            ))
            evt_idx += 1

        # 3. Batch lifecycle state transitions (sample first 100 batches for event history)
        sample_batches = self.batches[:100]
        for b in sample_batches:
            try:
                t0 = datetime.fromisoformat(b.start_time)
                t_plan = (t0 - timedelta(minutes=30)).isoformat()
            except Exception:
                t_plan = b.start_time

            self.state_change_events.append(StateChangeEvent(
                event_id=f"EVT-2026-{evt_idx:06d}",
                entity_type="ProductionBatch",
                entity_id=b.batch_id,
                previous_state=None,
                new_state=BatchStatus.PLANNED.value,
                transition_timestamp=t_plan,
                triggered_by="PRODUCTION_PLANNER",
                reason=f"Job order scheduled for SKU {b.product_sku}"
            ))
            evt_idx += 1

            self.state_change_events.append(StateChangeEvent(
                event_id=f"EVT-2026-{evt_idx:06d}",
                entity_type="ProductionBatch",
                entity_id=b.batch_id,
                previous_state=BatchStatus.PLANNED.value,
                new_state=BatchStatus.IN_PROGRESS.value,
                transition_timestamp=b.start_time,
                triggered_by="PLANT_OPERATOR",
                reason="Work order dispatched and machines energized"
            ))
            evt_idx += 1

            self.state_change_events.append(StateChangeEvent(
                event_id=f"EVT-2026-{evt_idx:06d}",
                entity_type="ProductionBatch",
                entity_id=b.batch_id,
                previous_state=BatchStatus.IN_PROGRESS.value,
                new_state=BatchStatus.COMPLETED.value,
                transition_timestamp=b.end_time,
                triggered_by="SCADA_SYSTEM",
                reason=f"Batch complete. Output: {b.produced_qty} units, scrap: {b.scrap_qty} units"
            ))
            evt_idx += 1

    def _inject_labelled_edge_cases(self):
        """
        Step 5: Inject labelled edge cases into the dataset and record in ground_truth.
        Edge cases:
        1. Meter total disagrees with interval sums
        2. kW confused with kWh
        3. Tariff timezone mismatch
        4. Reading duplicates
        5. Energy assigned to machine outside meter hierarchy
        6. Operational waste: High idle consumption
        7. Operational waste: Peak demand spike
        """
        # Ensure we have readings to modify
        if len(self.readings) < 100:
            return

        # 1. Meter total disagrees with interval sums
        # We perturb a Main Incomer reading so it significantly disagrees with feeder sums
        incomer_readings = [r for r in self.readings if r.meter_id == "MTR-PLT-001-001"]
        if incomer_readings:
            target_r = incomer_readings[len(incomer_readings) // 4]
            old_kw = target_r.active_power_kw
            target_r.active_power_kw = round(old_kw * 0.40, 2) # Under-reports by 60%
            target_r.energy_kwh = round(target_r.active_power_kw * 0.25, 4)
            self.ground_truth_anomalies.append({
                "anomaly_id": f"ANOM-{len(self.ground_truth_anomalies)+1:04d}",
                "issue_type": "METER_TOTAL_DISAGREES_WITH_INTERVAL_SUM",
                "entity_type": "EnergyReading",
                "record_id": target_r.reading_id,
                "timestamp": target_r.timestamp,
                "meter_id": target_r.meter_id,
                "description": f"Main incomer active power dropped from {old_kw} kW to {target_r.active_power_kw} kW, causing severe negative reconciliation against sub-meters.",
                "severity": "HIGH",
                "expected_action": "Flag meter calibration fault or CT ratio telemetry failure."
            })

        # 2. kW confused with kWh (transposition / unit confusion)
        if len(self.readings) > 50:
            target_r = self.readings[50]
            # In a 15-min interval, energy_kwh should be kW * 0.25.
            # Storing kW value into kWh produces a 4x inflated energy value.
            incorrect_kwh = target_r.active_power_kw
            target_r.energy_kwh = incorrect_kwh
            self.ground_truth_anomalies.append({
                "anomaly_id": f"ANOM-{len(self.ground_truth_anomalies)+1:04d}",
                "issue_type": "KW_CONFUSED_WITH_KWH",
                "entity_type": "EnergyReading",
                "record_id": target_r.reading_id,
                "timestamp": target_r.timestamp,
                "meter_id": target_r.meter_id,
                "description": f"Telemetry unit confusion: energy_kwh set to {incorrect_kwh} instead of {round(target_r.active_power_kw*0.25, 4)} kWh (ratio 1.0 instead of 0.25).",
                "severity": "CRITICAL",
                "expected_action": "Recalculate energy_kwh using sampling interval cadence (15 min = 0.25 h)."
            })

        # 3. Tariff timezone mismatch
        # Create a tariff where peak window was defined in UTC (+5h) instead of local time
        if self.tariffs:
            misconfigured_tariff = Tariff(
                tariff_id=f"TAR-2026-{len(self.tariffs)+1:03d}",
                plant_id="PLT-001",
                tariff_name="TOU-Timezone-Misaligned-Tariff",
                effective_from=self.start_datetime.date().isoformat(),
                effective_to=(self.start_datetime + timedelta(days=30)).date().isoformat(),
                rate_type="TOU",
                peak_rate_kwh=0.28,
                mid_peak_rate_kwh=0.14,
                off_peak_rate_kwh=0.07,
                peak_demand_charge_kw=16.0,
                peak_window_start="09:00", # Shifted by 5 hours relative to local peak window 14:00
                peak_window_end="13:00",
                mid_peak_window_start="03:00",
                mid_peak_window_end="17:00",
                currency="USD"
            )
            self.tariffs.append(misconfigured_tariff)
            self.ground_truth_anomalies.append({
                "anomaly_id": f"ANOM-{len(self.ground_truth_anomalies)+1:04d}",
                "issue_type": "TARIFF_TIMEZONE_MISMATCH",
                "entity_type": "Tariff",
                "record_id": misconfigured_tariff.tariff_id,
                "timestamp": misconfigured_tariff.effective_from,
                "meter_id": "ALL",
                "description": "Tariff peak window is shifted by UTC offset (+5 hours mismatch from plant local operating window).",
                "severity": "HIGH",
                "expected_action": "Align tariff time window timezone with Plant.timezone America/Chicago."
            })

        # 4. Reading duplicates (gateway retry loops)
        if len(self.readings) > 80:
            original = self.readings[80]
            # Duplicate reading with slight timestamp or same reading_id
            duplicate_reading = EnergyReading(
                reading_id=f"{original.reading_id}-DUP",
                meter_id=original.meter_id,
                timestamp=original.timestamp,
                active_power_kw=original.active_power_kw,
                energy_kwh=original.energy_kwh,
                power_factor=original.power_factor,
                voltage_v=original.voltage_v,
                current_a=original.current_a,
                data_source="IOT_GATEWAY"
            )
            self.readings.insert(81, duplicate_reading)
            self.ground_truth_anomalies.append({
                "anomaly_id": f"ANOM-{len(self.ground_truth_anomalies)+1:04d}",
                "issue_type": "READING_DUPLICATES",
                "entity_type": "EnergyReading",
                "record_id": duplicate_reading.reading_id,
                "timestamp": duplicate_reading.timestamp,
                "meter_id": duplicate_reading.meter_id,
                "description": f"Duplicate interval reading encountered for meter {original.meter_id} at {original.timestamp}.",
                "severity": "MEDIUM",
                "expected_action": "Deduplicate interval readings by (meter_id, timestamp) composite key."
            })

        # 5. Energy assigned to machine outside meter hierarchy
        # We create a mapping linking a machine to a nonexistent or disjoint meter
        invalid_mapping = MeterMachineMapping(
            mapping_id=f"MAP-{len(self.mappings)+1:05d}",
            meter_id="MTR-PLT-001-999", # Nonexistent meter
            machine_id=self.machines[0].machine_id,
            allocation_ratio=1.0,
            effective_from=self.start_datetime.isoformat(),
            effective_to=None
        )
        self.mappings.append(invalid_mapping)
        self.ground_truth_anomalies.append({
            "anomaly_id": f"ANOM-{len(self.ground_truth_anomalies)+1:04d}",
            "issue_type": "ENERGY_ASSIGNED_OUTSIDE_HIERARCHY",
            "entity_type": "MeterMachineMapping",
            "record_id": invalid_mapping.mapping_id,
            "timestamp": invalid_mapping.effective_from,
            "meter_id": invalid_mapping.meter_id,
            "description": f"Machine {invalid_mapping.machine_id} mapped to non-existent meter MTR-PLT-001-999 outside physical plant tree.",
            "severity": "CRITICAL",
            "expected_action": "Validate foreign key existence and tree hierarchy before energy allocation."
        })

        # 6. Operational Waste: High idle consumption during weekend/off-shift
        # We pick weekend intervals for machine 1 and elevate power to 85 kW (rated 180 kW) instead of 35 kW standby
        target_meter = self.mappings[0].meter_id
        weekend_readings = [r for r in self.readings if r.meter_id == target_meter]
        if len(weekend_readings) > 30:
            waste_reading = weekend_readings[20]
            waste_reading.active_power_kw = 95.0 # High idle consumption
            waste_reading.energy_kwh = round(waste_reading.active_power_kw * 0.25, 4)
            self.ground_truth_anomalies.append({
                "anomaly_id": f"ANOM-{len(self.ground_truth_anomalies)+1:04d}",
                "issue_type": "HIGH_IDLE_CONSUMPTION",
                "entity_type": "EnergyReading",
                "record_id": waste_reading.reading_id,
                "timestamp": waste_reading.timestamp,
                "meter_id": waste_reading.meter_id,
                "description": f"Machine left energized at {waste_reading.active_power_kw} kW during scheduled plant shutdown (baseline standby is 35 kW).",
                "severity": "HIGH",
                "expected_action": "Auto de-energize hydraulic power pack during non-production shifts."
            })

        # 7. Operational Waste: Peak demand spike breaching contracted capacity
        incomer_readings = [r for r in self.readings if r.meter_id == "MTR-PLT-001-001"]
        if len(incomer_readings) > 40:
            peak_reading = incomer_readings[35]
            contracted = self.plants[0].contracted_peak_kw # 1250 kW
            peak_reading.active_power_kw = contracted + 185.0 # 1435.0 kW (breach!)
            peak_reading.energy_kwh = round(peak_reading.active_power_kw * 0.25, 4)
            self.ground_truth_anomalies.append({
                "anomaly_id": f"ANOM-{len(self.ground_truth_anomalies)+1:04d}",
                "issue_type": "PEAK_DEMAND_SPIKE",
                "entity_type": "EnergyReading",
                "record_id": peak_reading.reading_id,
                "timestamp": peak_reading.timestamp,
                "meter_id": peak_reading.meter_id,
                "description": f"Main incomer demand peaked at {peak_reading.active_power_kw} kW, exceeding contracted limit of {contracted} kW during TOU peak window.",
                "severity": "CRITICAL",
                "expected_action": "Stagger heavy stamping press startup sequence and shed auxiliary chiller loads."
            })

        # 8. Operational Telemetry Gap (dropped packet / gateway communication failure)
        feeder_readings = [r for r in self.readings if r.meter_id == "MTR-PLT-001-002"]
        if len(feeder_readings) > 20:
            dropped_reading = feeder_readings[15]
            self.readings.remove(dropped_reading)
            self.ground_truth_anomalies.append({
                "anomaly_id": f"ANOM-{len(self.ground_truth_anomalies)+1:04d}",
                "issue_type": "METER_TELEMETRY_GAP",
                "entity_type": "EnergyReading",
                "record_id": dropped_reading.reading_id,
                "timestamp": dropped_reading.timestamp,
                "meter_id": dropped_reading.meter_id,
                "description": f"Telemetry gap: Meter {dropped_reading.meter_id} dropped 15-minute interval reading at {dropped_reading.timestamp} due to IoT gateway buffer timeout.",
                "severity": "HIGH",
                "expected_action": "Execute exception handling path: interpolate missing interval and trigger OT/IT communication alert."
            })

    def export_to_directory(self, output_dir: str):
        """Exports all generated data into CSV, JSON, SQL seed, and SQLite formats."""
        import hashlib
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        data = self.generate_all()

        # 1. Export CSVs
        file_hashes = {}
        for entity_name, records in data.items():
            if not records:
                continue
            csv_file = out_path / f"{entity_name}.csv"
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                if isinstance(records[0], dict):
                    fieldnames = list(records[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(records)
                else:
                    from dataclasses import fields
                    fieldnames = [field.name for field in fields(records[0])]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in records:
                        writer.writerow(r.__dict__)
            file_hashes[csv_file.name] = hashlib.sha256(csv_file.read_bytes()).hexdigest()

        # 2. Export Ground Truth isolated JSON & CSV
        gt_path_json = out_path / "ground_truth.json"
        with open(gt_path_json, "w", encoding="utf-8") as f:
            json.dump(self.ground_truth_anomalies, f, indent=2)
        file_hashes["ground_truth.json"] = hashlib.sha256(gt_path_json.read_bytes()).hexdigest()

        # 3. Export ANSI SQL Schema DDL (schema.sql)
        sql_schema_file = out_path / "schema.sql"
        sql_statements = [
            "-- Industrial Energy Intelligence Database Schema (ANSI SQL DDL)",
            "-- Target Engines: PostgreSQL, SQLite, MySQL 8.0+",
            "CREATE TABLE IF NOT EXISTS Plant (plant_id VARCHAR(32) PRIMARY KEY, name VARCHAR(100) NOT NULL, location VARCHAR(100), timezone VARCHAR(50), contracted_peak_kw NUMERIC(10,2), voltage_kv NUMERIC(6,2), created_at TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS Meter (meter_id VARCHAR(32) PRIMARY KEY, plant_id VARCHAR(32) REFERENCES Plant(plant_id), meter_name VARCHAR(100), meter_type VARCHAR(32), meter_level INT, parent_meter_id VARCHAR(32), sampling_cadence_min INT, ct_ratio NUMERIC(8,2), status VARCHAR(20), installed_date DATE);",
            "CREATE TABLE IF NOT EXISTS Machine (machine_id VARCHAR(32) PRIMARY KEY, plant_id VARCHAR(32) REFERENCES Plant(plant_id), name VARCHAR(100), category VARCHAR(32), rated_power_kw NUMERIC(8,2), standby_power_kw NUMERIC(8,2), current_status VARCHAR(20), installed_date DATE);",
            "CREATE TABLE IF NOT EXISTS MeterMachineMapping (mapping_id VARCHAR(32) PRIMARY KEY, meter_id VARCHAR(32) REFERENCES Meter(meter_id), machine_id VARCHAR(32) REFERENCES Machine(machine_id), allocation_ratio NUMERIC(4,3), effective_from TIMESTAMP, effective_to TIMESTAMP);",
            "CREATE TABLE IF NOT EXISTS Shift (shift_id VARCHAR(32) PRIMARY KEY, plant_id VARCHAR(32) REFERENCES Plant(plant_id), shift_name VARCHAR(20), start_time VARCHAR(10), end_time VARCHAR(10), active_days VARCHAR(50));",
            "CREATE TABLE IF NOT EXISTS Tariff (tariff_id VARCHAR(32) PRIMARY KEY, plant_id VARCHAR(32) REFERENCES Plant(plant_id), tariff_name VARCHAR(100), effective_from DATE, effective_to DATE, rate_type VARCHAR(20), peak_rate_kwh NUMERIC(8,4), mid_peak_rate_kwh NUMERIC(8,4), off_peak_rate_kwh NUMERIC(8,4), peak_demand_charge_kw NUMERIC(8,2), peak_window_start VARCHAR(10), peak_window_end VARCHAR(10), mid_peak_window_start VARCHAR(10), mid_peak_window_end VARCHAR(10), currency VARCHAR(10));",
            "CREATE TABLE IF NOT EXISTS WeatherObservation (weather_id VARCHAR(64) PRIMARY KEY, plant_id VARCHAR(32) REFERENCES Plant(plant_id), timestamp TIMESTAMP, ambient_temp_c NUMERIC(5,2), relative_humidity_pct NUMERIC(5,2), dew_point_c NUMERIC(5,2), cooling_degree_hours NUMERIC(5,2));",
            "CREATE TABLE IF NOT EXISTS ProductionBatch (batch_id VARCHAR(32) PRIMARY KEY, plant_id VARCHAR(32) REFERENCES Plant(plant_id), product_sku VARCHAR(32), planned_qty INT, produced_qty INT, scrap_qty INT, start_time TIMESTAMP, end_time TIMESTAMP, shift_id VARCHAR(32) REFERENCES Shift(shift_id), status VARCHAR(20));",
            "CREATE TABLE IF NOT EXISTS BatchMachineExecution (execution_id VARCHAR(32) PRIMARY KEY, batch_id VARCHAR(32) REFERENCES ProductionBatch(batch_id), machine_id VARCHAR(32) REFERENCES Machine(machine_id), runtime_min NUMERIC(8,2), idle_min NUMERIC(8,2), output_qty INT);",
            "CREATE TABLE IF NOT EXISTS EnergyReading (reading_id VARCHAR(64) PRIMARY KEY, meter_id VARCHAR(32) REFERENCES Meter(meter_id), timestamp TIMESTAMP, active_power_kw NUMERIC(8,2), energy_kwh NUMERIC(8,4), power_factor NUMERIC(4,3), voltage_v NUMERIC(8,2), current_a NUMERIC(8,2), data_source VARCHAR(20));",
            "CREATE TABLE IF NOT EXISTS MaintenanceEvent (event_id VARCHAR(32) PRIMARY KEY, machine_id VARCHAR(32) REFERENCES Machine(machine_id), event_type VARCHAR(20), start_time TIMESTAMP, end_time TIMESTAMP, description TEXT, energy_impact_kwh NUMERIC(8,2));",
            "CREATE TABLE IF NOT EXISTS StateChangeEvent (event_id VARCHAR(32) PRIMARY KEY, entity_type VARCHAR(32), entity_id VARCHAR(32), previous_state VARCHAR(32), new_state VARCHAR(32), transition_timestamp TIMESTAMP, triggered_by VARCHAR(50), reason TEXT);",
            "CREATE TABLE IF NOT EXISTS Recommendation (recommendation_id VARCHAR(32) PRIMARY KEY, plant_id VARCHAR(32) REFERENCES Plant(plant_id), machine_id VARCHAR(32), category VARCHAR(32), title VARCHAR(150), description TEXT, action_actor VARCHAR(32), baseline_kwh NUMERIC(10,2), estimated_kwh_savings NUMERIC(10,2), estimated_cost_savings NUMERIC(10,2), payback_period_days NUMERIC(8,1), status VARCHAR(20), generated_at TIMESTAMP);"
        ]
        with open(sql_schema_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sql_statements) + "\n")
        file_hashes["schema.sql"] = hashlib.sha256(sql_schema_file.read_bytes()).hexdigest()

        # 4. Export SQL Seed Script (seed_data.sql)
        sql_seed_file = out_path / "seed_data.sql"
        with open(sql_seed_file, "w", encoding="utf-8") as f:
            f.write("-- Industrial Energy Intelligence Seed Data Script\n")
            f.write("BEGIN TRANSACTION;\n")
            for entity_name, records in data.items():
                if not records or entity_name == "GroundTruth":
                    continue
                first = records[0] if isinstance(records[0], dict) else records[0].__dict__
                cols = list(first.keys())
                col_names = ", ".join(cols)
                # Sample up to 1000 rows per table to keep seed script compact and portable
                export_sample = records[:1000] if entity_name == "EnergyReading" else records
                for r in export_sample:
                    d = r if isinstance(r, dict) else r.__dict__
                    vals = []
                    for c in cols:
                        v = d[c]
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        else:
                            clean_str = str(v).replace("'", "''")
                            vals.append(f"'{clean_str}'")
                    val_str = ", ".join(vals)
                    f.write(f"INSERT INTO {entity_name} ({col_names}) VALUES ({val_str});\n")
            f.write("COMMIT;\n")
        file_hashes["seed_data.sql"] = hashlib.sha256(sql_seed_file.read_bytes()).hexdigest()

        # 5. Export Source Manifest (source_manifest.json)
        manifest = {
            "title": "Industrial Energy Intelligence Master Dataset",
            "schema_version": "1.0.0",
            "generator": "IndustrialDataGenerator",
            "scale": self.scale,
            "seed": self.seed,
            "generator_command": f"py -3.12 cli.py generate --scale {self.scale} --seed {self.seed} --output-dir {output_dir}",
            "generated_at": datetime.now().isoformat(),
            "simulation_start": self.start_datetime.isoformat(),
            "simulation_days": self.days,
            "cadence_minutes": self.cadence_minutes,
            "provenance": {
                "source_type": "Deterministic Synthetic Physics Simulation",
                "lawful_use_statement": "100% synthetic mathematical and thermodynamic models. No private, confidential, or proprietary user data accessed.",
                "tariff_model_reference": "Public industrial TOU rate design based on ComEd Rate BES & PG&E E-19/E-20 schedules."
            },
            "row_counts": {k: len(v) for k, v in data.items()},
            "checksums_sha256": file_hashes
        }
        with open(out_path / "source_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        with open(out_path / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 6. Export SQLite DB
        import sqlite3
        db_file = out_path / "industrial_energy.db"
        if db_file.exists():
            db_file.unlink()
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        for entity_name, records in data.items():
            if not records:
                continue
            first = records[0] if isinstance(records[0], dict) else records[0].__dict__
            cols = list(first.keys())
            col_defs = ", ".join([f'"{c}" TEXT' for c in cols])
            cur.execute(f'CREATE TABLE "{entity_name}" ({col_defs})')
            
            placeholders = ", ".join(["?"] * len(cols))
            rows = []
            for r in records:
                d = r if isinstance(r, dict) else r.__dict__
                rows.append([str(d[c]) if d[c] is not None else None for c in cols])
            cur.executemany(f'INSERT INTO "{entity_name}" VALUES ({placeholders})', rows)

        conn.commit()
        conn.close()

        return manifest
