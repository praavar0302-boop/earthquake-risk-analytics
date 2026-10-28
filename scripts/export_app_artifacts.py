"""One-time export of the notebook's final pricing artifacts; never imported by the app.

Run from any directory: python scripts/export_app_artifacts.py
The existing notebook, data and figures are read-only inputs.
"""
from __future__ import annotations
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REVISED = ROOT / "data/processed/revised"
ASSETS = ROOT / "app_assets"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_notebook():
    for name in ["earthquake_risk_analysis.ipynb"]:
        path = ROOT / name
        if path.exists():
            notebook = json.loads(path.read_text())
            if notebook.get("metadata", {}).get("methodology_revision", {}).get("final_academic_review"):
                return path, notebook
    raise FileNotFoundError("The latest academically reviewed, executed notebook is required.")


def main():
    path, notebook = find_notebook()
    validation = json.loads((REVISED / "real_data_validation_report.json").read_text())
    expected = json.loads((REVISED / "reproduction_manifest.json").read_text())["raw_sha256"]
    raw = ROOT / "data/raw/usgs_earthquakes_1965_2025_m5.5.csv"
    if digest(raw) != expected:
        raise ValueError("Raw snapshot differs from the verified experiment. Export stopped.")
    protected = {p: digest(p) for folder in [ROOT / "data", ROOT / "figures"]
                 for p in folder.rglob("*") if p.is_file()}
    protected.update({p: digest(p) for p in ROOT.glob("*.ipynb")})
    namespace = {"Path": Path, "json": json, "REVISED_DATA_DIR": REVISED,
                 "REVISED_FIG_DIR": ROOT / "figures/revised"}
    # Load only original notebook definitions and constant assignments, never its
    # download, fitting pipelines, plotting calls or output-writing statements.
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        if cell.get("metadata", {}).get("original_cell_number") not in [52, 55, 68, 58, 72]:
            continue
        tree = ast.parse("".join(cell["source"]))
        nodes = [node for node in tree.body
                 if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))
                 or isinstance(node, ast.Assign)
                 and all(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets)]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    selected = json.loads((REVISED / "selected_features.json").read_text())
    protocol = json.loads((REVISED / "rolling_origin_protocol.json").read_text())
    params = next(p["cart_params"] for p in protocol if p["origin"] == 2016)
    with tempfile.TemporaryDirectory(prefix="quake-export-") as temporary:
        namespace["FORECAST_FILE"] = Path(temporary) / "forecast.csv"
        with contextlib.redirect_stdout(io.StringIO()):
            pricing = namespace["build_pricing_table"]({"selected_features": selected}, {"params": params})
        frame = pricing["table"].copy()
        saved = pd.read_csv(REVISED / "risk_forecast_2026.csv").set_index("cell_id")
        actual = frame.set_index("cell_id")
        assert set(actual.index) == set(saved.index)
        assert np.allclose(actual.loc[saved.index, "p_logistic"], saved.probability, rtol=1e-12)
        for city, lat, lon in [("San Francisco",37.77,-122.42), ("Tokyo",35.68,139.69),
                               ("Istanbul",41.01,28.98), ("Santiago",-33.45,-70.67),
                               ("Kathmandu",27.72,85.32)]:
            quote = namespace["quote_premium"](lat,lon,pricing,payout_eur=10_000_000,target_loss_ratio=.7)
            for model, expected_premium in validation["example_premiums_at_70_percent_target"][city].items():
                assert quote.loc["premium_eur",model] == expected_premium, (city,model)
        ASSETS.mkdir(exist_ok=True)
        frame.sort_values("cell_id").to_csv(ASSETS / "forecasts_2026.csv", index=False)
        pricing["cart_classes"].to_csv(ASSETS / "cart_classes_2026.csv", index=False)
        pd.concat([value.reset_index().assign(model=model) for model,value in pricing["factors"].items()],
                  ignore_index=True).to_csv(ASSETS / "experience_factors.csv", index=False)
    sources = [raw, path, ROOT/"data/external/plate_boundaries_pb2002.json",
               *sorted(REVISED.glob("*.csv")), *sorted(REVISED.glob("*.json")),
               *sorted((ROOT/"figures/revised").glob("*.png"))]
    manifest = {"source_notebook": path.name, "source_notebook_sha256": digest(path),
                "executed_code_cells": sum(c["cell_type"] == "code" and c.get("execution_count") is not None for c in notebook["cells"]),
                "notebook_cells": len(notebook["cells"]),
                "raw_sha256": expected, "forecast_year": 2026,
                "fit_target_years": [1975,2025], "evaluation": "exploratory; 2016–2025 previously inspected",
                "cart_parameters": params, "verified_regions": len(frame),
                "golden_quote_check": "All five locations and both models match the validation report",
                "source_hashes": {str(p.relative_to(ROOT)):digest(p) for p in sources},
                "export_hashes": {p.name:digest(p) for p in ASSETS.glob("*.csv")}}
    (ASSETS / "export_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    for p, sha in protected.items():
        assert digest(p)==sha, f"Protected input changed: {p}"
    print(f"Exported {len(frame)} regions from {path.name}; all golden quotes match.")
    print("Notebook, datasets and original/revised figures unchanged.")


if __name__ == "__main__":
    main()
