# Security record (SET-01, SET-04, SET-05)

## Purpose

Records how the build environment was verified and installed, the accepted residual risks, and the rules for untrusted downloads, secrets and source domains. Lives in tracked `docs/` because `.planning/` is gitignored.

## Environment

System Python 3.9.6, end of life since October 2025. Kept as an accepted limitation (D-09); an upgrade is deferred to the user. Used only inside the project venv `.venv/` (include-system-site-packages = false). The build runs offline; the network is needed only for the install step (pypi.org, files.pythonhosted.org).

## Package verification

Verified live on 2026-10-18 from https://pypi.org/pypi/NAME/VERSION/json and https://api.osv.dev/v1/query (responses parsed as data with `python3 -I`). All wheel sha256 values match the research record.

| Package | Version | Wheel | sha256 | Author / maintainer | Licence | Source repo | requires_python | Dependencies | OSV (2026-10-18) |
|---|---|---|---|---|---|---|---|---|---|
| XlsxWriter | 3.2.9 | xlsxwriter-3.2.9-py3-none-any.whl | 9a5db42bc5dff014806c58a20b9eae7322a134abb6fce3c92c181bfb275ec5b3 | John McNamara | BSD-2-Clause | github.com/jmcnamara/XlsxWriter | >=3.8 | none | no vulnerabilities |
| openpyxl | 3.1.5 | openpyxl-3.1.5-py2.py3-none-any.whl | 5282c12b107bffeef825f4617dc029afaf41d0ea60823bbb665ef3079dc79de2 | Charlie Clark and AUTHORS | MIT | foss.heptapod.net/openpyxl/openpyxl | >=3.8 | et-xmlfile | no vulnerabilities |
| et_xmlfile | 2.0.0 | et_xmlfile-2.0.0-py3-none-any.whl | 7a91720bc756843502c3b7504c77b8fe44217c85c537d85037f0f536151b2caa | Charlie Clark and AUTHORS | MIT | foss.heptapod.net/openpyxl/et_xmlfile | >=3.8 | none | no vulnerabilities |
| pip (optional bootstrap) | 26.0.1 | pip-26.0.1-py3-none-any.whl | bdb1b08f4274833d62c1aa29e20907365a2ceb950410df15fc9521bad440122b | The pip developers (PyPA) | MIT | github.com/pypa/pip | >=3.9 | none | 4 advisories (see below) |

## pip bootstrap analysis

Bundled pip 21.2.4 has 7 distinct advisories (OSV): CVE-2025-8869, CVE-2026-1703, CVE-2023-5752, CVE-2026-3219, CVE-2026-6357, CVE-2026-8643, CVE-2026-13346.

Upgrading to pip 26.0.1 (newest pip supporting Python 3.9) clears CVE-2025-8869, CVE-2026-1703 and CVE-2023-5752. Four remain and cannot be fixed on Python 3.9: CVE-2026-3219, CVE-2026-6357, CVE-2026-8643, CVE-2026-13346. All need a malicious index or archive, or crafted console-script names.

Mitigations: `--require-hashes` (exact pins plus hash check), `--only-binary :all:` (no sdists, no setup.py), `--no-deps`, `--isolated` (ignores PIP_* env and pip.conf), `--no-cache-dir`, official PyPI only.

## Install procedure

Run from the project root (network needed only here).

```bash
python3 -m venv .venv
# Option A only (pip upgrade):
.venv/bin/python -m pip install --disable-pip-version-check --isolated --no-cache-dir \
    --require-hashes --only-binary :all: --no-deps -r requirements-bootstrap.txt
.venv/bin/python -m pip install --disable-pip-version-check --isolated --no-cache-dir \
    --require-hashes --only-binary :all: --no-deps -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -m pip list --format=freeze
```

Flags: `--isolated` ignores env vars and user config; `--require-hashes` rejects unpinned or mismatching files; `--only-binary :all:` forbids source builds; `--no-deps` stops silent extra installs; `--disable-pip-version-check` avoids a self-update call; `--no-cache-dir` avoids cached artefacts.

## Untrusted downloads policy

Downloads go only into `data_raw/` (one subdirectory per source), from allowlisted official hosts, via `tools/fetch_raw.py`. Parse as data with `python3 -I` from scripts kept outside `data_raw/`. Never open downloads in Excel, never enable or run macros. `data_raw/*` is gitignored except its README.

## Secrets policy

`.env` is never committed (gitignored). No tokens or credentials in `config/` or anywhere in the repo. No step requires credentials.

## Allowed source domains

The allowlist (`ALLOWED_DOMAINS` in `config/security.py`) is strict on purpose: it enforces the official/reputable-sources-only rule for both `Source.url` and hyperlinks.

| Domain | Justification |
|---|---|
| aib-net.org | Association of Issuing Bodies: European residual mix (market-based grid factor) |
| efrag.org | EFRAG: ESRS technical advice and standards |
| eex.com | European Energy Exchange: EU ETS auction results |
| ember-energy.org | Ember: recognised research body, EUA price data |
| ens.dk | Danish Energy Agency: technology data catalogues |
| europa.eu | EU institutions: Eurostat, EEA, JRC PVGIS, Commission, Parliament, EPRS, ECB |
| gov.uk | UK DESNZ/DEFRA: greenhouse gas conversion factors |
| iiasa.ac.at | IIASA: NGFS scenario data host |
| ifrs.org | IFRS Foundation / ISSB: IFRS S2 |
| ngfs.net | Network for Greening the Financial System: climate scenarios |
| pbl.nl | PBL Netherlands Environmental Assessment Agency: SDE++ cost basis |
| rvo.nl | Netherlands Enterprise Agency: energy-saving measure lists |
| stern.nyu.edu | NYU Stern (Damodaran): cost of capital by industry |
| theicct.org | International Council on Clean Transportation: vehicle TCO studies |

Adding a domain: a deliberate, reviewed change to `ALLOWED_DOMAINS`, made in its own commit, which must add a row with a one-line justification (publisher and why it is official or reputable) to this table. Never widen an entry to a broader suffix to make a URL pass.

## Approval log

Pending user approval

## Post-install evidence

