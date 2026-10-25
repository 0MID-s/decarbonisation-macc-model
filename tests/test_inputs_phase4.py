"""Phase 4 inputs: presence, provenance and allowlist guard."""
import unittest
from urllib.parse import urlparse

from config.inputs import INPUTS
from config.schema import Status
from config.validate import validate_provenance
from config.sources import SOURCES

IDS = {
    "Pass_CCGT_Eff": (0.56, Status.SOURCED), "Pass_PTR": (1.0, Status.ASSUMPTION),
    "Carbon_EUA_AnchorYear": (2025, Status.ASSUMPTION),
    "Carbon_ETS1_ConvYear": (2030, Status.ASSUMPTION),
    "Carbon_ETS2_ConvYear": (2030, Status.ASSUMPTION),
    "Carbon_ICP_Level": (100, Status.ASSUMPTION),
    "Carbon_DirectETS_FreeAlloc": (0, Status.ASSUMPTION),
    "Carbon_CBAM_InScope": (0, Status.SOURCED),
    "Expo_LastYear": (2035, Status.ASSUMPTION),
    "Sens_GridStep": (0.2, Status.ASSUMPTION), "Sens_RateStep": (0.01, Status.ASSUMPTION),
    "Sens_Hurdle_1": (0.06, Status.ASSUMPTION), "Sens_Hurdle_2": (0.08, Status.ASSUMPTION),
    "Sens_Hurdle_3": (0.10, Status.ASSUMPTION),
    "Sens_Torn_RateDelta": (0.02, Status.ASSUMPTION), "Sens_Torn_ElecPct": (0.2, Status.ASSUMPTION),
    "Sens_Torn_GasPct": (0.2, Status.ASSUMPTION), "Sens_Torn_CapexPct": (0.2, Status.ASSUMPTION),
    "Sens_Torn_GOPct": (0.5, Status.ASSUMPTION), "Sens_Torn_EVPct": (0.3, Status.ASSUMPTION),
    "Sens_Torn_PTRLow": (0.6, Status.ASSUMPTION), "Sens_Torn_MEFPct": (0.15, Status.ASSUMPTION),
    "Sens_ETS2_StartDelay": (1, Status.ASSUMPTION),
    "Carbon_NGFS_AltRouteFactor": (1.31, Status.ASSUMPTION),
    "Sens_Note_LifePct": (0.2, Status.ASSUMPTION), "Sens_Note_HPShareDelta": (0.1, Status.ASSUMPTION),
}


class Phase4InputTests(unittest.TestCase):
    def test_ids_values_status(self):
        by = {}
        for r in INPUTS:
            by.setdefault(r.id, []).append(r)
        for id_, (val, st) in IDS.items():
            self.assertEqual(len(by.get(id_, [])), 1, id_)
            self.assertAlmostEqual(by[id_][0].published_value, val)
            self.assertEqual(by[id_][0].status, st, id_)

    def test_provenance_validates(self):
        validate_provenance(SOURCES, INPUTS, tuple(range(2026, 2056)))

    def test_cbam_source_used_and_allowed(self):
        from config.security import host_allowed
        src = [s for s in SOURCES if s.id == "Src_CBAM"]
        self.assertEqual(len(src), 1)
        self.assertTrue(host_allowed(src[0].url))
        self.assertTrue(any(r.source_id == "Src_CBAM" for r in INPUTS))

    def test_rationales_and_hosts(self):
        by = {r.id: r for r in INPUTS}
        self.assertIn("Fabra", by["Pass_PTR"].rationale)
        self.assertIn("High-Level Commission", by["Carbon_ICP_Level"].rationale)
        for id_ in IDS:
            self.assertNotIn(by[id_].rationale[:1], ("=", "+", "-", "@"))
        for s in SOURCES:
            host = urlparse(s.url).hostname or ""
            for bad in ("aeaweb.org", "worldbank.org", "cdp.net"):
                self.assertFalse(host.endswith(bad), s.id)


if __name__ == "__main__":
    unittest.main()
