from __future__ import annotations

import unittest

from evaluation.adversarial_probes.loader import load_probes
from evaluation.failure_taxonomy.taxonomy import build_failure_taxonomy
from evaluation.failure_taxonomy.validator import validate_taxonomy


class FailureTaxonomyTests(unittest.TestCase):
    def test_build_and_validate_taxonomy(self) -> None:
        probes = load_probes()
        taxonomy = build_failure_taxonomy(probes)
        validate_taxonomy(probes, taxonomy)
        self.assertIn("categories", taxonomy)
        self.assertEqual(len(taxonomy["categories"]), 10)


if __name__ == "__main__":
    unittest.main()

