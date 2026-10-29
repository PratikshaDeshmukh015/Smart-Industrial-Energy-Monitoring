import unittest
import re
from industrial_energy.generator import IndustrialDataGenerator

class TestGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = IndustrialDataGenerator(seed=20261022, scale="starter")
        self.data = self.gen.generate_all()

    def test_entity_counts(self):
        self.assertEqual(len(self.data["Plant"]), 1)
        self.assertEqual(len(self.data["Meter"]), 4)
        self.assertEqual(len(self.data["Machine"]), 4)
        self.assertGreaterEqual(len(self.data["ProductionBatch"]), 40)
        self.assertGreater(len(self.data["EnergyReading"]), 2500)
        self.assertGreater(len(self.data["StateChangeEvent"]), 10)
        self.assertEqual(len(self.data["GroundTruth"]), 8)

    def test_id_nomenclature(self):
        # Meter: MTR-PLT-001-001
        meter_re = re.compile(r"^MTR-PLT-\d{3}-\d{3}$")
        for m in self.data["Meter"]:
            self.assertTrue(meter_re.match(m.meter_id), f"Invalid meter ID: {m.meter_id}")

        # Batch: BATCH-2026-000001
        batch_re = re.compile(r"^BATCH-2026-\d{6}$")
        for b in self.data["ProductionBatch"]:
            self.assertTrue(batch_re.match(b.batch_id), f"Invalid batch ID: {b.batch_id}")

        # Tariff: TAR-2026-001
        tariff_re = re.compile(r"^TAR-2026-\d{3}$")
        for t in self.data["Tariff"]:
            self.assertTrue(tariff_re.match(t.tariff_id), f"Invalid tariff ID: {t.tariff_id}")

    def test_meter_hierarchy_topology(self):
        # Root meter has no parent
        root = [m for m in self.data["Meter"] if m.meter_level == 1]
        self.assertEqual(len(root), 1)
        self.assertIsNone(root[0].parent_meter_id)

        # Children have valid parent
        children = [m for m in self.data["Meter"] if m.meter_level > 1]
        meter_ids = {m.meter_id for m in self.data["Meter"]}
        for ch in children:
            self.assertIn(ch.parent_meter_id, meter_ids)

if __name__ == "__main__":
    unittest.main()
