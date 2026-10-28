# Earthquake research walkthrough

A separate, read-only Streamlit application with ten guided stages. It uses the completed project's actual revised outputs; the analytical notebooks, datasets and existing figures are unchanged.

## Run

From the repository root, use Python 3.13 and a local environment:

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

Open the printed local URL (normally <http://127.0.0.1:8501>). Stop with **Ctrl+C**. Previous/Next and the sidebar share the same stage state. Technical explanations are expandable. Charts support hover, zoom and PNG download.

`requirements.txt` selects the minimal runtime with tested constraints. It does not install model-fitting or notebook dependencies. Use `requirements-analysis.txt` for notebook execution, exports and tests. The app does not need Cartopy, scikit-learn or statsmodels. Geographic displays use supplied plate boundaries on longitude–latitude axes without online map tiles. See [the project README](README.md) for full setup and publication checks.

## Walkthrough

| Stage | Content and interaction |
|---|---|
| 1. Research question | Objectives, workflow, verified headline statistics and baseline comparison |
| 2. Dataset & cleaning | Missingness chart, cleaning decisions, dictionary, sample records and provenance |
| 3. EDA | Year/magnitude/depth filters; earthquake map, distributions and annual counts; explicit map sampling |
| 4. Regional grid & target | Select a supported cell and year; examine actual regional events and its binary target |
| 5. Feature engineering | Select region/year; timeline separates preceding history from target/future; actual feature values |
| 6. Models & methodology | Chronological split, model purposes, smoothed historical baseline and validation caveats |
| 7. Evaluation & calibration | Interactive ROC/Brier charts, metrics, calibration model selection, sample counts, rolling-origin comparison and saved CART tree |
| 8. 2026 forecasts | Verified Logistic/CART probability heatmaps, risk-tier view, region selection and actual estimates |
| 9. Insurance | Region/model/payout/target controls; expected payout, premium, model comparison, optional experience adjustment and unsupported-coordinate check |
| 10. Findings & limitations | Evidence-backed conclusions, pricing reference figure, limitations and downloadable verified metrics |

The map samples at most 8,000 events deterministically for responsiveness. Counts and distribution charts always use **all** events matching the filters. Map sampling is labeled. Empty filters and unsupported regions are handled explicitly.

## Sources and one-time exports

The requested notebook was renamed before app development. The latest executed and academically reviewed source is **`earthquake_risk_analysis.ipynb`** (72 cells, 36 executed code cells after publication cleanup). The app does not rename or edit the notebook. Keep any historical copies private until their saved outputs have been reviewed.

- Read-only analytical inputs: `data/raw/`, `data/processed/revised/`, `data/external/` and `figures/revised/`.
- Dedicated exports: `app_assets/forecasts_2026.csv`, `cart_classes_2026.csv`, `experience_factors.csv` and `export_manifest.json`.
- `app_support.py`: read-only loaders, source integrity checks, plots and transparent pricing arithmetic.
- `scripts/export_app_artifacts.py`: **build-time only** export, never imported or run by the app.

The original revised CSV contains Logistic 2026 forecasts but not the final CART forecast/rules. The exporter loads only the notebook's function definitions and constants, performs the notebook's final Logistic/CART refits once, and writes app-specific artifacts. It checks Logistic probabilities against the saved forecast and all five locations' premiums for both models against the validation report. Original output-writing paths are redirected into a temporary directory. All existing analytical files are fingerprinted and checked unchanged.

Exports are already supplied. If they need regeneration after a reviewed analysis change, use the original analysis environment (or install `requirements-export.txt` in a separate environment), then run:

```bash
python scripts/export_app_artifacts.py
```

The exporter recognizes `earthquake_risk_analysis.ipynb`, requires final-review metadata and checks the raw snapshot fingerprint. Keep the full project with the app: source files are required for provenance verification. Missing or changed artifacts produce a clear error; they never trigger automatic downloads or fitting.

The app verifies fingerprints on its first data load and caches read-only frames. Restart the app after intentionally replacing analytical inputs or regenerating exports. An existing session's cached values are not a live file monitor.

## Interpretation guardrails

- Catalogue: **28,557** events, M ≥ 5.5, 1965–2025. The original saved run reported 28,558; that discrepancy remains disclosed.
- Target: at least one M ≥ 6.0 event per 5° cell-year. Final population: 722 cells, 36,822 modelling rows.
- Evaluation: 7,220 region-years, 763 positives. All 2016–2025 comparisons are exploratory; rolling origins do not create independent confirmation.
- Random Forest Brier 0.06383 versus historical rate 0.06445: about **0.96% relative improvement**, not a demonstrated significant advantage.
- Only Logistic/CART final 2026 probabilities were exported; no Random Forest forecast is invented or substituted from historical predictions.
- Annual pricing: `premium = probability × fixed payout / target loss ratio`. One qualifying annual trigger leads to one fixed payment. A 30% loading implies 76.923% target, distinct from exactly 77%.
- Region estimates are not precise city probabilities or property-loss estimates. Blank maps and unsupported coordinates do not mean zero hazard. The 30% premium/payout ceiling and credibility adjustment are illustrative assumptions. Tier experience is not a location-specific backtest.

## Validation

```bash
python -m pytest -q tests/test_streamlit_app.py
```

Tests cover all ten stages; sidebar and Previous/Next synchronization; changing EDA filters, including no matches; historical-feature controls; calibration selection; forecast model/tier/region controls; pricing and optional adjustment; invalid/unsupported coordinates; missing exports; recomputed ROC/Brier values; all golden quotes; and absence of training imports during runtime. Tests require pytest in addition to runtime dependencies.

Actual browser checks complement AppTest: chart rendering, desktop/mobile layout and real navigation. No models are fitted by the tests or application.
