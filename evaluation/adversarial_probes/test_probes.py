from __future__ import annotations

import unittest
from collections import Counter

from evaluation.adversarial_probes.categories import CATEGORIES
from evaluation.adversarial_probes.loader import load_probes


class AdversarialProbeLibraryTests(unittest.TestCase):
    def test_probe_volume_and_categories(self) -> None:
        probes = load_probes()
        self.assertGreaterEqual(len(probes), 30)
        categories_present = {probe["category"] for probe in probes}
        self.assertEqual(categories_present, set(CATEGORIES))
        counts = Counter(probe["category"] for probe in probes)
        for category in CATEGORIES:
            self.assertGreaterEqual(counts[category], 3)

    def test_probe_fields_and_ranges(self) -> None:
        probes = load_probes()
        required_fields = {
            "probe_id",
            "category",
            "title",
            "setup",
            "expected_failure_signature",
            "observed_trigger_rate",
            "business_cost",
            "tenacious_specific",
        }
        for probe in probes:
            self.assertTrue(required_fields.issubset(probe.keys()))
            self.assertGreaterEqual(float(probe["observed_trigger_rate"]), 0.0)
            self.assertLessEqual(float(probe["observed_trigger_rate"]), 1.0)

    def test_tenacious_specific_ratio(self) -> None:
        probes = load_probes()
        tenacious_count = sum(1 for probe in probes if bool(probe["tenacious_specific"]))
        self.assertGreaterEqual(tenacious_count, int(0.4 * len(probes)))


if __name__ == "__main__":
    unittest.main()

