import unittest
from industrial_energy.generator import IndustrialDataGenerator
from industrial_energy.correlation_engine import CorrelationEngine
from industrial_energy.recommendation_engine import RecommendationEngine

class TestCorrelation(unittest.TestCase):
    def setUp(self):
        gen = IndustrialDataGenerator(seed=20261022, scale="starter", inject_anomalies=True)
        self.data = gen.generate_all()
        self.engine = CorrelationEngine(self.data)
        self.results = self.engine.analyze_all()

    def test_idle_waste_detection(self):
        idle_waste = self.results["idle_waste"]
        self.assertGreater(len(idle_waste), 0)
        self.assertGreater(self.results["metrics"]["total_idle_waste_kwh"], 0.0)
        self.assertGreater(self.results["metrics"]["total_idle_waste_cost_usd"], 0.0)

    def test_peak_demand_detection(self):
        peak_events = self.results["peak_events"]
        breaches = [p for p in peak_events if p["is_contract_breach"]]
        self.assertGreaterEqual(len(breaches), 1)
        self.assertGreater(breaches[0]["peak_kw"], 1250.0)

    def test_sec_calculation(self):
        sec_results = self.results["sec_results"]
        self.assertEqual(len(sec_results), len(self.data["ProductionBatch"]))
        for r in sec_results:
            self.assertIn("sec_kwh_per_unit", r)
            self.assertGreaterEqual(r["sec_kwh_per_unit"], 0.0)

    def test_recommendation_generation(self):
        rec_engine = RecommendationEngine(self.data, self.results)
        recs = rec_engine.generate_recommendations()
        self.assertGreaterEqual(len(recs), 3)
        for r in recs:
            self.assertTrue(r.recommendation_id.startswith("REC-2026-"))
            self.assertGreater(r.baseline_kwh, 0.0)
            self.assertGreater(r.estimated_kwh_savings, 0.0)
    def test_exception_handling_path(self):
        exceptions = self.results.get("exceptions", [])
        self.assertGreater(len(exceptions), 0)
        gap_exc = [e for e in exceptions if e["issue_type"] == "METER_TELEMETRY_GAP"]
        self.assertGreaterEqual(len(gap_exc), 1)
        self.assertEqual(gap_exc[0]["exception_path_taken"], "LINEAR_INTERPOLATION_ESTIMATION")
        self.assertGreater(gap_exc[0]["corrected_kwh"], 0.0)

if __name__ == "__main__":
    unittest.main()
