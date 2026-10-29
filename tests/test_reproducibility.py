import unittest
import hashlib
from industrial_energy.generator import IndustrialDataGenerator

class TestReproducibility(unittest.TestCase):
    def test_deterministic_generation_same_seed(self):
        gen1 = IndustrialDataGenerator(seed=20261022, scale="starter")
        data1 = gen1.generate_all()

        gen2 = IndustrialDataGenerator(seed=20261022, scale="starter")
        data2 = gen2.generate_all()

        # Assert identical record counts
        for k in data1.keys():
            self.assertEqual(len(data1[k]), len(data2[k]), f"Mismatch in count for entity {k}")

        # Assert identical reading values
        for r1, r2 in zip(data1["EnergyReading"], data2["EnergyReading"]):
            self.assertEqual(r1.reading_id, r2.reading_id)
            self.assertEqual(r1.active_power_kw, r2.active_power_kw)
            self.assertEqual(r1.energy_kwh, r2.energy_kwh)

    def test_different_seed_produces_different_readings(self):
        gen1 = IndustrialDataGenerator(seed=20261022, scale="starter")
        data1 = gen1.generate_all()

        gen2 = IndustrialDataGenerator(seed=99999999, scale="starter")
        data2 = gen2.generate_all()

        # At least some reading values must differ
        kw1 = [r.active_power_kw for r in data1["EnergyReading"][:20]]
        kw2 = [r.active_power_kw for r in data2["EnergyReading"][:20]]
        self.assertNotEqual(kw1, kw2)

if __name__ == "__main__":
    unittest.main()
