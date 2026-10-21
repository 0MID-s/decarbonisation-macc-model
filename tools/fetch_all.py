"""Fetch every machine-readable Phase 2 source into data_raw/<Src_ID>/.

CLI: python3 -I tools/fetch_all.py [--only Src_X]

All downloads go through tools.fetch_raw.fetch (host allowlist, suffix
allowlist, 50 MB cap, sha256 manifest). Idempotent: existing targets are
skipped. Deliberately NOT fetched (see decisions D-14, D-15, D-37, D-41-D-43):
  - EUR-Lex: WAF challenge; values are transcribed by hand (plan 02-07).
  - EEX auction archive: .zip, hand entry (D-37).
  - Damodaran waccEurope: legacy .xls; values supplied by the user (D-42).
  - NGFS: login required; user-supplied TSV (D-43).
  - US labour-statistics CPI and ECB FX APIs: D-41 supersedes D-28/D-36
    (Eurostat route; those hosts are not allowlisted).
"""
import argparse
import sys
import urllib.error
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:  # needed under `python -I`
    sys.path.insert(0, str(_ROOT))

from tools.fetch_raw import DEFAULT_ROOT, FetchError, fetch, plan_target  # noqa: E402

_ES = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
_PV = ("https://re.jrc.ec.europa.eu/api/v5_3/PVcalc?lat=51.2&lon=4.4&peakpower=1"
       "&loss=14&angle=%d&aspect=0&pvtechchoice=crystSi&raddatabase=PVGIS-SARAH3"
       "&startyear=2005&endyear=2023&outputformat=json")

FETCHES = (
    ("Src_EurostatSBS", "sbs_sc_ovw_BE_C20_C21.json",
     _ES + "sbs_sc_ovw?geo=BE&nace_r2=C20&nace_r2=C21&format=JSON&lang=EN"),
    # D-05: final consumption, energy use only (never non-energy use).
    ("Src_EurostatEnergyBalance", "nrg_bal_c_BE_FC_IND_CPC_E_TJ.json",
     _ES + "nrg_bal_c?geo=BE&nrg_bal=FC_IND_CPC_E&unit=TJ&format=JSON&lang=EN"),
    ("Src_EurostatAirAccounts", "env_ac_ainah_r2_BE_C20_C21_GHG.json",
     _ES + "env_ac_ainah_r2?geo=BE&nace_r2=C20&nace_r2=C21&airpol=GHG&format=JSON&lang=EN"),
    ("Src_EurostatElecPrice", "nrg_pc_205_BE_X_VAT.json",
     _ES + "nrg_pc_205?geo=BE&tax=X_VAT&currency=EUR&format=JSON&lang=EN"),
    ("Src_EurostatGasPrice", "nrg_pc_203_BE_X_VAT.json",
     _ES + "nrg_pc_203?geo=BE&tax=X_VAT&currency=EUR&format=JSON&lang=EN"),
    # Full series (no time filter): 2010 is needed for the D-41 NGFS conversion.
    ("Src_EurostatHICP", "prc_hicp_aind_EA_CP00.json",
     _ES + "prc_hicp_aind?geo=EA&coicop=CP00&unit=INX_A_AVG&format=JSON&lang=EN"),
    # D-41: 2010 USD per EUR annual average, expected 1.3257. If the API rejects
    # statinfo, drop it and filter at parse time.
    ("Src_EurostatFX", "ert_bil_eur_a_USD_AVG.json",
     _ES + "ert_bil_eur_a?currency=USD&statinfo=AVG&format=JSON&lang=EN"),
    ("Src_EEAGridIntensity", "eea_co2_emission_intensity_15.csv",
     "https://www.eea.europa.eu/en/analysis/maps-and-charts/co2-emission-intensity-15/@@download/file"),
    ("Src_AIBResidualMix", "aib_residual_mix_2025.xlsx",
     "https://www.aib-net.org/sites/default/files/assets/eecs/Residual%20Mix/2025_Final%20_Residual%20mix%20calculation%20results_25052026.xlsx"),
    ("Src_DESNZ2026", "ghg-conversion-factors-2026-flat-format-revised.xlsx",
     "https://assets.publishing.service.gov.uk/media/6a6c9748862aaf18d9c62ac9/ghg-conversion-factors-2026-flat-format-revised.xlsx"),
    ("Src_DEAProcessHeat", "technology_data_for_industrial_process_heat.xlsx",
     "https://ens.dk/media/7758/download"),
    ("Src_DEAElectricity", "technology_data_for_el_and_dh_alldatalong.xlsx",
     "https://ens.dk/media/8615/download"),
    ("Src_PVGIS", "pvgis_antwerp_tilt10.json", _PV % 10),
    ("Src_PVGIS", "pvgis_antwerp_tilt35.json", _PV % 35),
    ("Src_RVOEML", "rvo_eml_2023_berekeningen_v1-4.xlsx",
     "https://www.rvo.nl/sites/default/files/2025-03/Erkende%20maatregelenlijst%20%28EML%29%202023%20-%20berekeningen_v1-4.xlsx"),
    # D-31 cross-check.
    ("Src_PBLSDE2026", "pbl_ot_model_eindadvies_sde_2026.xlsx",
     "https://www.pbl.nl/downloads/pbl-2026-onrendabele-top-model-eindadvies-sde-2026-5699xlsx"),
    # Phase 3 (03-01): fuel price, heat-demand temperature split, GO market value.
    # The Oil Bulletin history file is re-issued weekly, so its hash changes.
    ("Src_EUOilBulletin", "Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx",
     "https://energy.ec.europa.eu/document/download/906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
     "?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx"),
    ("Src_JRCHeat", "ldna25381enn.pdf",
     "https://publications.jrc.ec.europa.eu/repository/bitstream/JRC70962/ldna25381enn.pdf"),
    ("Src_WalloniaMarket", "valeurs-de-marche-2026.pdf",
     "https://energie.wallonie.be/files/Soutiens%20financiers/%c3%a9lectricit%c3%a9%20verte/"
     "M%c3%a9canismes%20de%20soutiens/R%c3%a9gime%20CPMA/valeurs-de-marche-2026.pdf"),
)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch all Phase 2 raw sources (idempotent).")
    ap.add_argument("--only", help="fetch only this source id")
    a = ap.parse_args(argv)
    failed = 0
    for sid, name, url in FETCHES:
        if a.only and sid != a.only:
            continue
        try:
            try:
                plan_target(url, sid, DEFAULT_ROOT, name)
            except FetchError as exc:
                if "already exists" in str(exc):
                    print("skip %s/%s" % (sid, name))
                    continue
                raise
            print(fetch(url, sid, DEFAULT_ROOT, name))
        except (FetchError, urllib.error.URLError, OSError) as exc:
            print("fetch failed %s/%s: %s" % (sid, name, exc), file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
