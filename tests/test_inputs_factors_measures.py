"""Value, unit and provenance tests for Emission factors and Measures sections."""
import unittest

from config.inputs import INPUTS
from config.schema import Status

BY_ID = {r.id: r for r in INPUTS}
EF = [r for r in INPUTS if r.section == "Emission factors"]
MEAS = [r for r in INPUTS if r.section == "Measures"]

EF_IDS = ["EF_GridLB", "EF_GridLB_Change", "EF_ResidualMB",
          "EF_ResidualMB_Change", "EF_Gas_NCV", "EF_Gas_GCV", "EF_LPG_NCV",
          "EF_Naphtha_NCV", "EF_GasOil_NCV", "EF_Diesel_NCV", "EF_Diesel_l",
          "EF_HeatProxy"]


class FactorTests(unittest.TestCase):
    def test_order(self):
        self.assertEqual([r.id for r in EF], EF_IDS)

    def test_grid_and_residual(self):
        r = BY_ID["EF_GridLB"]
        self.assertEqual((r.published_value, r.published_unit, r.model_unit,
                          r.source_id), (154, "gCO2e/kWh", "tCO2e/MWh",
                                         "Src_EEAGridIntensity"))
        r = BY_ID["EF_ResidualMB"]
        self.assertEqual((r.published_value, r.published_unit, r.model_unit,
                          r.source_id), (171.01, "gCO2/kWh", "tCO2/MWh",
                                         "Src_AIBResidualMix"))

    def test_flat_paths_are_assumptions(self):
        for i in ("EF_GridLB_Change", "EF_ResidualMB_Change"):
            r = BY_ID[i]
            self.assertEqual(r.published_value, 0.0)
            self.assertEqual((r.status, r.model_unit), (Status.ASSUMPTION, "%"))
        self.assertIn("D-38", BY_ID["EF_GridLB_Change"].rationale
                      + BY_ID["EF_GridLB_Change"].note)

    def test_desnz(self):
        exp = {"EF_Gas_NCV": 0.20199, "EF_Gas_GCV": 0.18231,
               "EF_LPG_NCV": 0.23032, "EF_Naphtha_NCV": 0.24891,
               "EF_GasOil_NCV": 0.27288, "EF_Diesel_NCV": 0.26071,
               "EF_HeatProxy": 0.17529}
        for i, v in exp.items():
            r = BY_ID[i]
            self.assertEqual(r.published_value, v, i)
            self.assertEqual((r.published_unit, r.model_unit,
                              r.conversion_ref),
                             ("kgCO2e/kWh", "tCO2e/MWh", "Const_None"), i)
            self.assertEqual(r.source_id, "Src_DESNZ2026")
        r = BY_ID["EF_Diesel_l"]
        self.assertEqual((r.published_value, r.model_unit), (2.58354, "kgCO2e/l"))
        self.assertEqual(BY_ID["EF_HeatProxy"].status, Status.ASSUMPTION)


class MeasureTests(unittest.TestCase):
    def test_values(self):
        exp = {"Meas_HP_COP_Trad": 5.28, "Meas_HP_COP_80C": 3.30,
               "Meas_HP_COP_HT": 2.70, "Meas_HP_Capex_Trad": 0.95,
               "Meas_HP_Capex_80C": 0.95, "Meas_HP_Capex_HT": 1.20,
               "Meas_HP_IndirectCapex_Trad": 0.19,
               "Meas_HP_IndirectCapex_HT": 0.23, "Meas_HP_FixOM_Trad": 2127,
               "Meas_HP_FixOM_HT": 2494, "Meas_HP_VarOM_Trad": 3.07,
               "Meas_HP_VarOM_HT": 3.60, "Meas_HP_Life_Trad": 25,
               "Meas_HP_Life_HT": 20, "Meas_Boiler_Eff": 0.939,
               "Meas_Boiler_Capex": 0.09, "Meas_Boiler_FixOM": 2000,
               "Meas_Boiler_VarOM": 1.23, "Meas_Boiler_Life": 25,
               "Meas_PV_FixOMDEA": 2190, "Meas_PV_Life": 40,
               "Meas_PV_InverterLife": 15, "Meas_PV_Degradation": 0.3,
               "Meas_PV_YieldTilt10": 942.09, "Meas_PV_YieldTilt35": 1038.15,
               "Meas_LED_HalogenCapex": 6.79296,
               "Meas_LED_HalogenSaving": 118.625,
               "Meas_VSD_Capex": 4361.60, "Meas_VSD_Saving": 15360,
               "Meas_PV_CapexPBL": 531, "Meas_HP_CapexPBL": 1476}
        for i, v in exp.items():
            self.assertEqual(BY_ID[i].published_value, v, i)
        self.assertAlmostEqual(BY_ID["Meas_PV_CapexDEA"].published_value,
                               0.6365, 4)

    def test_conversions_and_basis(self):
        r = BY_ID["Meas_HP_Capex_Trad"]
        self.assertEqual((r.conversion_ref, r.model_unit, r.price_basis.label),
                         ("Const_Mega_per_kilo", "EUR/kW", "EUR 2025 real"))
        self.assertEqual(BY_ID["Meas_PV_CapexDEA"].price_basis.label,
                         "EUR 2020 real")
        self.assertEqual(BY_ID["Meas_VSD_Capex"].price_basis.label,
                         "EUR 2023 nominal")

    def test_lifetimes_present(self):
        for i in ("Meas_HP_Life_Trad", "Meas_HP_Life_HT", "Meas_Boiler_Life",
                  "Meas_PV_Life", "Meas_LED_Life", "Meas_VSD_Life",
                  "Meas_Fleet_Life"):
            self.assertEqual(BY_ID[i].model_unit, "years", i)

    def test_led_vsd_lifetime_fallback(self):
        for i in ("Meas_LED_Life", "Meas_VSD_Life"):
            r = BY_ID[i]
            self.assertEqual((r.status, r.source_id, r.published_value),
                             (Status.ASSUMPTION, None, 15))

    def test_fleet_assumptions(self):
        fleet = [r for r in MEAS if r.id.startswith("Meas_Fleet_")]
        self.assertEqual(len(fleet), 3)
        for r in fleet:
            self.assertEqual(r.status, Status.ASSUMPTION)
            self.assertIn("no numeric ICCT anchor", r.note)
        self.assertEqual(BY_ID["Meas_Fleet_EVPremium"].published_value, 15000)
        self.assertEqual(BY_ID["Meas_Fleet_EVkWhPerKm"].published_value, 0.25)
        self.assertEqual(BY_ID["Meas_Fleet_Life"].published_value, 8)


if __name__ == "__main__":
    unittest.main()
