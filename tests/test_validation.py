import unittest
from industrial_energy.generator import IndustrialDataGenerator
from industrial_energy.validator import DataValidator

class TestValidator(unittest.TestCase):
    def test_clean_data_passes_zero_errors(self):
        gen = IndustrialDataGenerator(seed=20261022, scale="starter", inject_anomalies=False)
        clean_data = gen.generate_all()
        validator = DataValidator(clean_data)
        report = validator.validate_all()
        self.assertTrue(report["passed"])
        self.assertEqual(report["total_errors"], 0)

    def test_injected_data_flags_specific_errors(self):
        gen = IndustrialDataGenerator(seed=20261022, scale="starter", inject_anomalies=True)
        data = gen.generate_all()
        validator = DataValidator(data)
        report = validator.validate_all()
        self.assertFalse(report["passed"])
        
        rule_set = {e["rule"] for e in report["errors"]}
        self.assertIn("FOREIGN_KEY_VIOLATION", rule_set)
        self.assertIn("ARITHMETIC_RECONCILIATION_FAIL", rule_set)
        self.assertIn("INTERVAL_DUPLICATE", rule_set)

if __name__ == "__main__":
    unittest.main()
