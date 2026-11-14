"""Train the weekly sale-hazard model, validate it out of time, check it recovers the simulator's hidden
price elasticity, and register the pricing pyfunc (model + optimiser) in Unity Catalog as @champion.

Runs as a serverless job task:  python ml/train.py --catalog <c> --schema <s> --volume_root /Volumes/...
Prints a full text report (captured as evidence) and logs the same metrics/artifacts to MLflow.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd())

import mlflow  # noqa: E402
import sklearn  # noqa: E402
from mlflow.models import infer_signature  # noqa: E402
from mlflow.tracking import MlflowClient  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OrdinalEncoder  # noqa: E402

from pricing_core import CATEGORICAL, FEATURES, LABEL, MONOTONIC, NUMERIC, to_frame  # noqa: E402
from pyfunc_model import INPUT_COLUMNS, PricingModel  # noqa: E402

SPLIT_DATE = "2026-08-01"


def build_model() -> Pipeline:
    pre = ColumnTransformer(
        [("num", "passthrough", NUMERIC),
         ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=np.nan,
                                encoded_missing_value=np.nan), CATEGORICAL)],
        verbose_feature_names_out=False)
    hgb = HistGradientBoostingClassifier(
        learning_rate=0.06, max_iter=400, max_leaf_nodes=31, min_samples_leaf=80, l2_regularization=1.0,
        categorical_features=[False] * len(NUMERIC) + [True] * len(CATEGORICAL),
        monotonic_cst=[MONOTONIC.get(c, 0) for c in NUMERIC] + [0] * len(CATEGORICAL),
        early_stopping=True, validation_fraction=0.1, n_iter_no_change=25, random_state=7)
    return Pipeline([("pre", pre), ("hgb", hgb)])


def calibration_table(y: np.ndarray, p: np.ndarray, bins: int = 10) -> pd.DataFrame:
    q = pd.qcut(p, bins, labels=False, duplicates="drop")
    t = pd.DataFrame({"bin": q, "y": y, "p": p}).groupby("bin").agg(rows=("y", "size"), predicted=("p", "mean"),
                                                                     actual=("y", "mean"))
    return t.round(4)


def implied_elasticity(model: Pipeline, X: pd.DataFrame, body: pd.Series) -> pd.DataFrame:
    """% change in weekly sale hazard for a 1% price cut, by body class (compare with ground truth)."""
    p0 = np.clip(model.predict_proba(X)[:, 1], 1e-6, 1 - 1e-6)
    X1 = X.copy()
    X1["price_to_market"] = X1["price_to_market"] * 0.99
    p1 = np.clip(model.predict_proba(X1)[:, 1], 1e-6, 1 - 1e-6)
    h0, h1 = -np.log(1 - p0), -np.log(1 - p1)
    e = np.log(h1 / h0) / 0.01
    return pd.DataFrame({"body_class": body.to_numpy(), "e": e}).groupby("body_class")["e"].median().rename(
        "model_implied_elasticity")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--volume_root", required=True)
    a, _ = ap.parse_known_args()
    fq = f"{a.catalog}.{a.schema}"
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
    user = spark.sql("SELECT current_user()").first()[0]

    df = spark.table(f"{fq}.gold_pricing_features_weekly").where("is_complete_week").toPandas()
    df["week_start"] = pd.to_datetime(df["week_start"])
    train, test = df[df.week_start < SPLIT_DATE], df[df.week_start >= SPLIT_DATE]
    print(f"== Data: {len(df):,} vehicle-weeks | train {len(train):,} (< {SPLIT_DATE}) | "
          f"out-of-time test {len(test):,} (>= {SPLIT_DATE}) | weekly sale rate {df[LABEL].mean():.4f}")

    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(f"/Users/{user}/piag-aged-inventory-pricing")
    with mlflow.start_run(run_name="hazard_hgb_monotone") as run:
        model = build_model()
        model.fit(to_frame(train), train[LABEL].astype(int))
        Xt, yt = to_frame(test), test[LABEL].astype(int).to_numpy()
        pt = model.predict_proba(Xt)[:, 1]
        # naive benchmark: weekly sale rate by condition x age band learned on train
        band = lambda d: pd.cut(d["age_days"], [-1, 14, 30, 45, 60, 90, 120, 10_000]).astype(str) + d["condition"]
        naive_map = train.assign(b=band(train)).groupby("b")[LABEL].mean()
        pn = band(test).map(naive_map).fillna(train[LABEL].mean()).to_numpy()
        metrics = {
            "test_auc": roc_auc_score(yt, pt), "test_log_loss": log_loss(yt, pt), "test_brier": brier_score_loss(yt, pt),
            "naive_auc": roc_auc_score(yt, pn), "naive_log_loss": log_loss(yt, pn),
            "test_rows": float(len(test)), "train_rows": float(len(train)),
            "test_base_rate": float(yt.mean()), "test_mean_pred": float(pt.mean()),
            "n_iter": float(model.named_steps["hgb"].n_iter_),
        }
        mlflow.log_metrics({k: round(v, 5) for k, v in metrics.items()})
        mlflow.log_params({"model": "HistGradientBoostingClassifier", "monotone": json.dumps(MONOTONIC),
                           "features": ",".join(FEATURES), "split_date": SPLIT_DATE,
                           "sklearn": sklearn.__version__})
        print("== Out-of-time performance (higher AUC / lower loss is better)")
        print(json.dumps({k: round(v, 4) for k, v in metrics.items()}, indent=2))

        cal = calibration_table(yt, pt)
        print("== Calibration by predicted-probability decile (test)\n" + cal.to_string())

        sample = test.sample(min(6000, len(test)), random_state=1)
        pi = permutation_importance(model, to_frame(sample), sample[LABEL].astype(int), scoring="roc_auc",
                                    n_repeats=3, random_state=1)
        imp = pd.Series(pi.importances_mean, index=FEATURES).sort_values(ascending=False).round(4)
        print("== Permutation importance (AUC drop, test sample)\n" + imp.to_string())

        truth = json.load(open(os.path.join(a.volume_root, "landing", "_truth", "truth.json")))
        el = implied_elasticity(model, to_frame(sample), sample["body_class"]).to_frame()
        el["ground_truth_elasticity"] = el.index.map(truth["body_class_elasticity"])
        el["ratio_model_to_truth"] = (el["model_implied_elasticity"] / el["ground_truth_elasticity"]).round(2)
        el = el.round(2)
        print("== Price-response recovery: % hazard change per 1% price cut (model vs hidden simulator truth)\n"
              + el.to_string())
        rank_corr = el["model_implied_elasticity"].rank().corr(el["ground_truth_elasticity"].rank())
        print(f"   Spearman rank correlation model vs truth across body classes: {rank_corr:.2f}")
        mlflow.log_metric("elasticity_rank_corr", round(float(rank_corr), 4))

        # monotonicity check: lowering price never lowers sale probability
        Xs = to_frame(sample)
        grid = [1.10, 1.05, 1.00, 0.97, 0.94]
        probs = []
        for g in grid:
            Xg = Xs.copy()
            Xg["price_to_market"] = g
            probs.append(model.predict_proba(Xg)[:, 1])
        violations = int(sum((probs[i + 1] < probs[i] - 1e-9).sum() for i in range(len(grid) - 1)))
        print(f"== Monotonicity check over price_to_market grid {grid}: {violations} violations "
              f"across {len(sample):,} vehicles")
        mlflow.log_metric("monotonicity_violations", violations)

        tmp = tempfile.mkdtemp()
        for name, obj in {"calibration.csv": cal, "permutation_importance.csv": imp.to_frame("auc_drop"),
                          "elasticity_recovery.csv": el}.items():
            obj.to_csv(os.path.join(tmp, name))
            mlflow.log_artifact(os.path.join(tmp, name), "evaluation")

        # refit on all complete weeks for the served model
        final = build_model().fit(to_frame(df), df[LABEL].astype(int))
        pkl = os.path.join(tmp, "hazard_model.pkl")
        with open(pkl, "wb") as f:
            pickle.dump(final, f)

        inv = spark.table(f"{fq}.gold_inventory_current").toPandas()
        inv["as_of_date"] = inv["as_of_date"].astype(str)
        example = inv[INPUT_COLUMNS].head(3).copy()
        example["price_override"] = np.nan
        local = PricingModel(final, "candidate")
        example_out = local.predict(None, example)
        print("== Example served prediction (3 on-hand vehicles)\n"
              + example_out.drop(columns=["curve_json"]).to_string())
        here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        reg_name = f"{fq}.aged_inventory_pricing_model"
        client = MlflowClient(registry_uri="databricks-uc")
        try:  # stamp the version the registry is about to assign so served responses carry it
            next_version = max(int(v.version) for v in client.search_model_versions(f"name='{reg_name}'")) + 1
        except (ValueError, Exception):  # no versions yet / model not registered
            next_version = 1
        info = mlflow.pyfunc.log_model(
            artifact_path="pricing_model", python_model=PricingModel(None, str(next_version)),
            artifacts={"hazard_model": pkl},
            code_paths=[os.path.join(here, "pricing_core.py"), os.path.join(here, "pyfunc_model.py")],
            signature=infer_signature(example, example_out), input_example=example,
            pip_requirements=[f"scikit-learn=={sklearn.__version__}", f"pandas=={pd.__version__}",
                              f"numpy=={np.__version__}", f"mlflow=={mlflow.__version__}"],
            registered_model_name=reg_name)
        version = info.registered_model_version
        if str(version) != str(next_version):
            print(f"WARNING: registry assigned v{version}, model stamped v{next_version}")
        client.set_registered_model_alias(reg_name, "champion", version)
        client.update_registered_model(reg_name, description=(
            "Aged-inventory pricing copilot: weekly sale-hazard model (HistGradientBoosting, monotone in price-to-market) "
            "wrapped with an expected-profit optimiser over a 16-week horizon including floor-plan, lot and depreciation "
            "holding cost and auction-exit risk. Input: on-hand vehicle state. Output: recommended additional discount, "
            "sell-probability and expected-profit vs no change and vs the flat $250/$500 rule."))
        print(f"== Registered {reg_name} version {version} with alias @champion (run {run.info.run_id})")
        summary = {"registered_model": reg_name, "version": str(version), "run_id": run.info.run_id,
                   **{k: round(v, 4) for k, v in metrics.items()}, "elasticity_rank_corr": round(float(rank_corr), 3),
                   "monotonicity_violations": violations}
        print("== SUMMARY " + json.dumps(summary))


if __name__ == "__main__":
    main()
