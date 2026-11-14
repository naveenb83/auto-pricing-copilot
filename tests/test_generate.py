"""End-to-end test of the synthetic generator: runs the full simulation into a temp dir and checks
realism bands, data-quality dirt, VIN validity, file-drop layout and that ground truth stays hidden."""

import json
from pathlib import Path

import pandas as pd
import pytest

from datagen.generate import VIN_TRANSLIT, VIN_WEIGHTS, main


@pytest.fixture(scope="module")
def out(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("landing")
    main(["--out", str(d), "--hold_last_drop", "true"])
    return d


def _read(out: Path, entity: str) -> pd.DataFrame:
    files = sorted((out / entity).rglob("*.*"))
    if files[0].suffix == ".csv":
        return pd.concat([pd.read_csv(f) for f in files])
    return pd.concat([pd.read_json(f, lines=True) for f in files])


def test_summary_realism_bands(out):
    s = json.loads((out / "_generation_summary.json").read_text())
    assert 1100 <= s["on_hand_at_as_of"] <= 2000
    aged90 = s["on_hand_90_plus"] / s["on_hand_at_as_of"]
    assert 0.10 <= aged90 <= 0.28, aged90  # a group with a real (not absurd) aging problem
    assert 20 <= s["median_days_to_retail"] <= 45
    assert s["wholesale_exits"] < 0.08 * s["retail_sales"]
    assert set(s["price_change_reasons"]) >= {"aged_45_rule", "aged_90_rule", "manager_discretion"}


def test_weekly_drop_layout_and_held_drop(out):
    drops = sorted(p.name for p in (out / "vehicles").iterdir())
    assert len(drops) >= 70 and all(d.startswith("drop_date=") for d in drops)
    held = list((out / "_held" / "vehicles").iterdir())
    assert len(held) == 1 and held[0].name not in drops  # final drop held back for the incremental demo


def test_vins_valid_check_digit(out):
    v = _read(out, "vehicles").dropna(subset=["vin"]).head(500)
    for vin in v["vin"]:
        assert len(vin) == 17 and not set(vin) & set("IOQ")
        total = sum(VIN_TRANSLIT[c] * w for c, w in zip(vin, VIN_WEIGHTS))
        assert vin[8] == ("X" if total % 11 == 10 else str(total % 11))


def test_dirt_injected_for_expectations(out):
    v = _read(out, "vehicles")
    assert v["vin"].duplicated().sum() > 0
    assert v["unit_cost"].isna().sum() > 0
    assert (v["mileage"] < 0).sum() > 0
    s = _read(out, "sales")
    assert (s["sale_price"] == 0).sum() > 0


def test_economics_plausible(out):
    v = _read(out, "vehicles").dropna(subset=["unit_cost"]).drop_duplicates("vin")
    margin = (v["initial_list_price"] - v["unit_cost"]) / v["initial_list_price"]
    assert 0.03 < margin.median() < 0.16
    s = _read(out, "sales")
    retail = s[(s["channel"] == "retail") & (s["sale_price"] > 0)]
    assert 15000 < retail["sale_price"].median() < 50000


def test_ground_truth_isolated(out):
    truth = pd.read_csv(out / "_truth" / "vehicle_truth.csv")
    assert {"appeal", "elasticity"} <= set(truth.columns)
    for entity in ["vehicles", "sales", "web_leads", "market_comps"]:
        cols = set(_read(out, entity).columns)
        assert not cols & {"appeal", "elasticity", "_appeal", "base_hazard"}, entity
