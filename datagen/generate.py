"""Synthetic dealer-group simulator for the aged-inventory pricing copilot.

Simulates 18 months of a 6-rooftop dealer group day by day:
  * vehicles arrive (new + used), get a list price and a floor-plan-financed unit cost
  * each day a vehicle on the lot sells with a hazard driven by GROUND TRUTH:
        h = base(class) * popularity * colour * season * appeal * exp(-elasticity(class) * price_gap) * staleness
    where price_gap = (current price - market value) / market value
  * managers discount using the historic flat rule ($250 at 45 days, $500 at 90) with imperfect
    compliance PLUS noisy discretionary cuts -> identifiable price response for the model
  * used units unsold past ~120 days are wholesaled at a loss
Outputs weekly "dealer management system" file drops (CSV / JSON lines) with realistic dirt
(duplicates, nulls, bad values) for Lakeflow expectations to catch, plus a hidden _truth folder.

Run locally:      uv run python -m datagen.generate --out ./_out
Run on Databricks: spark_python_task with --out /Volumes/<cat>/<schema>/landing
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from datagen import catalog as C

START = date(2025, 5, 12)  # Monday
AS_OF = date(2026, 11, 13)  # Friday -> "today" in the demo
LOT_COST_PER_DAY = 6.0  # insurance, lot, detailing
FI_GROSS_MEAN = 1350.0  # back-end (finance & insurance) gross per retail sale
VIN_CHARS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
VIN_TRANSLIT = {**{str(d): d for d in range(10)}, **dict(zip("ABCDEFGH", range(1, 9))),
                **dict(zip("JKLMN", range(1, 6))), "P": 7, "R": 9,
                **dict(zip("STUVWXYZ", range(2, 10)))}
VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
WMI = {"Toyota": "JTD", "Honda": "1HG", "Hyundai": "KMH", "Kia": "KNA", "Ford": "1FT",
       "Chevrolet": "1GC", "Mazda": "JM1", "Subaru": "JF2"}
MY_CODE = {2017: "H", 2018: "J", 2019: "K", 2020: "L", 2021: "M", 2022: "N", 2023: "P",
           2024: "R", 2025: "S", 2026: "T", 2027: "V"}


@dataclass
class Config:
    out: str
    seed: int = 42
    start: date = START
    as_of: date = AS_OF
    initial_stock: int = 1650
    daily_arrivals: float = 15.5
    hold_last_drop: bool = False
    dirty: bool = True


def season(d: date) -> float:
    return {1: 0.85, 2: 0.90, 3: 1.10, 4: 1.12, 5: 1.08, 6: 1.02, 7: 1.00, 8: 1.00,
            9: 0.94, 10: 0.97, 11: 1.03, 12: 1.15}[d.month]


def floorplan_apr(d: date) -> float:
    """Floor-plan APR drifting down with rate cuts over the window."""
    months = (d.year - START.year) * 12 + d.month - START.month
    return round(0.0790 - 0.00045 * months, 4)


def vin_for(rng: np.random.Generator, make: str, model_year: int) -> str:
    body = WMI[make] + "".join(rng.choice(list(VIN_CHARS), 5)) + "0" + MY_CODE[model_year] \
        + rng.choice(list("ABCDEFGHJKLMNPRSTUVWXYZ")) + "".join(rng.choice(list("0123456789"), 6))
    total = sum(VIN_TRANSLIT[ch] * w for ch, w in zip(body, VIN_WEIGHTS))
    check = total % 11
    return body[:8] + ("X" if check == 10 else str(check)) + body[9:]


def colour_factor(colour: str) -> float:
    return {"White": 1.0, "Black": 1.0, "Silver": 0.98, "Grey": 1.0, "Blue": 0.95, "Red": 0.93,
            "Green": 0.82, "Orange": 0.78, "Brown": 0.75}[colour]


def round_price(p: float, used: bool) -> float:
    if used:
        return float(max(1995, math.floor(p / 100.0) * 100 - 5))  # 24,995 style
    return float(round(p / 5.0) * 5)


class Simulator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.models = pd.DataFrame(C.MODELS, columns=["make", "model", "body_class", "base_msrp",
                                                      "popularity", "photo_hint"])
        self.vehicles: list[dict] = []
        self.price_changes: list[dict] = []
        self.sales: list[dict] = []
        self.weekly_leads: list[dict] = []
        self.weekly_comps: list[dict] = []
        self.customers = self._make_customers()
        self._cust_by_seg = {s: g["customer_id"].to_numpy() for s, g in self.customers.groupby("segment")}

    # ------------------------------------------------------------------ customers
    def _make_customers(self, n: int = 25000) -> pd.DataFrame:
        rng = self.rng
        segs = rng.choice(list(C.SEGMENT_MIX), n, p=list(C.SEGMENT_MIX.values()))
        signup_days = (self.cfg.as_of - (self.cfg.start - timedelta(days=900))).days
        offsets = np.sort(rng.integers(0, signup_days, n))
        first = rng.choice(C.FIRST_NAMES, n)
        last = rng.choice(C.LAST_NAMES, n)
        age_band = [
            {"first_time_buyer": rng.choice(["18-24", "25-34"], p=[0.6, 0.4]),
             "young_family": rng.choice(["25-34", "35-44"], p=[0.5, 0.5]),
             "active_lifestyle": rng.choice(["25-34", "35-44", "45-54"], p=[0.4, 0.4, 0.2]),
             "trades_and_fleet": rng.choice(["25-34", "35-44", "45-54", "55-64"]),
             "value_retiree": rng.choice(["55-64", "65+"], p=[0.4, 0.6])}[s] for s in segs]
        return pd.DataFrame({
            "customer_id": [f"C{100000 + i}" for i in range(n)],
            "first_name": first,
            "last_name": last,
            "email": [f"{f.lower()}.{l.lower()}{i % 997}@example.com" for i, (f, l) in enumerate(zip(first, last))],
            "phone": [f"(555) {rng.integers(200, 999)}-{rng.integers(1000, 9999)}" for _ in range(n)],
            "region": rng.choice(C.REGIONS, n),
            "age_band": age_band,
            "segment": segs,
            "signup_date": [(self.cfg.start - timedelta(days=900) + timedelta(days=int(o))).isoformat() for o in offsets],
        })

    # ------------------------------------------------------------------ vehicles
    def _new_vehicle(self, arrival: date, initial_age: int = 0) -> dict:
        rng = self.rng
        used = rng.random() < 0.45
        if used:
            rooftop = "R06" if rng.random() < 0.40 else rng.choice(["R01", "R02", "R03", "R04", "R05"])
            m = self.models.sample(1, weights=self.models["popularity"], random_state=rng.integers(1 << 31)).iloc[0]
        else:
            rt = C.ROOFTOPS[int(rng.integers(0, 5))]
            rooftop = rt[0]
            cand = self.models[self.models["make"].isin(rt[2])]
            m = cand.sample(1, weights=cand["popularity"], random_state=rng.integers(1 << 31)).iloc[0]
        acq = arrival - timedelta(days=initial_age)
        if used:
            model_year = int(acq.year - rng.integers(1, 8))
            model_year = max(model_year, 2018)
        else:
            model_year = 2027 if (acq >= date(2026, 8, 1) and rng.random() < 0.7) else 2026
            if acq < date(2025, 8, 1):
                model_year = 2025 if rng.random() < 0.6 else 2026
        model_year = min(model_year, 2027)
        trim, trim_up = C.TRIMS[m.body_class][int(rng.choice(3, p=[0.45, 0.35, 0.20]))]
        colour = rng.choice([c for c, _ in C.COLOURS], p=[w for _, w in C.COLOURS])
        msrp = m.base_msrp * (1 + trim_up) * (1.02 ** (model_year - 2026))
        age_years = max(0.0, (acq - date(model_year - 1, 10, 1)).days / 365.25)
        if used:
            mileage = int(max(800, age_years * 12000 * rng.normal(1.0, 0.25)))
            dep = 0.84 * (0.885 ** max(0.0, age_years - 1)) - (mileage - age_years * 12000) * 0.000002
            market0 = msrp * dep * (0.97 + 0.04 * m.popularity) * rng.normal(1.0, 0.03)
            unit_cost = market0 * rng.uniform(0.80, 0.88) + rng.uniform(600, 2800)
            list_price = round_price(market0 * (1 + rng.normal(0.045, 0.025)), True)
            drift = -0.00050 * rng.uniform(0.8, 1.2)
        else:
            mileage = int(rng.integers(5, 60))
            market0 = msrp * (0.955 + 0.035 * min(m.popularity, 1.3)) * rng.normal(1.0, 0.008)
            unit_cost = msrp * rng.uniform(0.905, 0.94)
            list_price = round_price(msrp * (1 + rng.normal(0.0, 0.008)), False)
            drift = -0.00010
        elasticity, base_h = C.BODY_CLASSES[m.body_class]
        appeal = float(rng.lognormal(0.0, 0.28))
        v = {
            "vin": vin_for(rng, m.make, model_year),
            "rooftop_id": rooftop,
            "stock_number": f"{rooftop}-{len(self.vehicles) + 10001}",
            "condition": "used" if used else "new",
            "make": m.make, "model": m.model, "trim": trim, "body_class": m.body_class,
            "model_year": model_year, "exterior_colour": colour, "mileage": mileage,
            "msrp": round(msrp, 0), "unit_cost": round(unit_cost, 2), "initial_list_price": list_price,
            "acquisition_date": acq,
            "acquisition_source": (rng.choice(["trade_in", "auction", "lease_return", "street_purchase"],
                                              p=[0.5, 0.3, 0.15, 0.05]) if used else "factory_allocation"),
            # simulation state (not exported except via _truth)
            "_market0": market0, "_drift": drift, "_appeal": appeal, "_elasticity": elasticity,
            "_base_h": base_h * 1.2 * m.popularity, "_pop": m.popularity, "_price": list_price,
            "_rule45": False, "_rule90": False, "_sold": None, "_photo_hint": m.photo_hint,
        }
        self.vehicles.append(v)
        return v

    def market_value(self, v: dict, d: date) -> float:
        age = (d - v["acquisition_date"]).days
        drift = v["_drift"]
        if v["condition"] == "new" and v["model_year"] < (2027 if d >= date(2026, 8, 1) else 2026):
            drift -= 0.00035  # prior model year after rollover loses value faster
        return v["_market0"] * (1 + drift) ** age

    def holding_cost_per_day(self, v: dict, d: date) -> float:
        interest = v["unit_cost"] * floorplan_apr(d) / 365.0
        dep = -v["_drift"] * self.market_value(v, d) if v["condition"] == "used" else 0.0
        return interest + LOT_COST_PER_DAY + dep

    def _change_price(self, v: dict, d: date, new_price: float, reason: str) -> None:
        new_price = round_price(new_price, v["condition"] == "used")
        if new_price >= v["_price"] or new_price < 1000:
            return
        self.price_changes.append({
            "vin": v["vin"], "change_date": d.isoformat(), "old_price": v["_price"], "new_price": new_price,
            "reason": reason, "changed_by": f"M{v['rooftop_id'][1:]}{int(self.rng.integers(1, 4))}",
        })
        v["_price"] = new_price

    # ------------------------------------------------------------------ simulation
    def run(self) -> None:
        rng, cfg = self.rng, self.cfg
        on_lot: list[dict] = [self._new_vehicle(cfg.start, int(a)) for a in
                              np.clip(rng.exponential(42, cfg.initial_stock), 0, 200)]
        d = cfg.start
        while d <= cfg.as_of:
            # arrivals: replace sales, with a mild pull toward ~1,800 units
            target = 1800 * (1.05 if d.month in (3, 4, 11, 12) else 1.0)
            lam = max(2.0, cfg.daily_arrivals + 0.04 * (target - len(on_lot)))
            if d.weekday() == 6:
                lam *= 0.3
            for _ in range(rng.poisson(lam)):
                on_lot.append(self._new_vehicle(d))
            still: list[dict] = []
            for v in on_lot:
                age = (d - v["acquisition_date"]).days
                mv = self.market_value(v, d)
                # --- historic pricing behaviour (the flat rule + noisy discretion)
                discount = v["initial_list_price"] - v["_price"]
                if age >= 45 and not v["_rule45"]:
                    v["_rule45"] = True
                    if rng.random() < 0.75 and discount < 250:
                        self._change_price(v, d, v["initial_list_price"] - 250, "aged_45_rule")
                if age >= 90 and not v["_rule90"]:
                    v["_rule90"] = True
                    if rng.random() < 0.75 and discount < 500:
                        self._change_price(v, d, v["initial_list_price"] - 500, "aged_90_rule")
                gap_now = (v["_price"] - mv) / mv
                p_disc = 0.0035 + 0.00004 * min(age, 200) + 0.06 * max(0.0, gap_now - 0.03)
                if age > 10 and rng.random() < p_disc:
                    amt = float(rng.choice([250, 500, 750, 1000, 1500, 2000, 2500],
                                           p=[0.22, 0.24, 0.16, 0.16, 0.10, 0.07, 0.05]))
                    self._change_price(v, d, v["_price"] - amt, "manager_discretion")
                if v["condition"] == "used" and d.weekday() == 0 and age > 14 and rng.random() < 0.18:
                    if v["_price"] > mv * 1.03:
                        self._change_price(v, d, mv * (1 + rng.normal(0.02, 0.012)), "market_adjustment")
                if v["condition"] == "new" and d.weekday() == 0 and age > 60 and gap_now > 0.04 and rng.random() < 0.12:
                    self._change_price(v, d, mv * (1 + rng.normal(0.015, 0.01)), "market_adjustment")
                # --- ground-truth sale hazard
                gap = (v["_price"] - mv) / mv
                h = (v["_base_h"] * colour_factor(v["exterior_colour"]) * season(d) * v["_appeal"]
                     * math.exp(-v["_elasticity"] * gap) * math.exp(-0.0020 * min(age, 240))
                     * (1.10 if v["condition"] == "used" else 1.0) * (0.55 if d.weekday() == 6 else 1.05))
                h = min(h, 0.30)
                if rng.random() < 1 - math.exp(-h):
                    self._sell(v, d, "retail")
                    continue
                if v["condition"] == "used" and age >= 120 and rng.random() < 0.035:
                    self._sell(v, d, "wholesale")
                    continue
                if v["condition"] == "new" and age >= 240 and rng.random() < 0.012:
                    self._sell(v, d, "dealer_trade")
                    continue
                still.append(v)
            on_lot = still
            if d.weekday() == 6:  # Sunday: close the week -> weekly feeds
                self._weekly_feeds(on_lot, d)
            d += timedelta(days=1)
        self._weekly_feeds(on_lot, cfg.as_of)  # partial final week up to as-of
        self.on_lot_at_end = on_lot

    def _sell(self, v: dict, d: date, channel: str) -> None:
        rng = self.rng
        mv = self.market_value(v, d)
        if channel == "retail":
            price = round(v["_price"] * (1 - max(0.0, rng.normal(0.006, 0.006))), 0)
            weights = np.array([C.SEGMENTS[s].get(v["body_class"], 0.4) * C.SEGMENT_MIX[s] for s in C.SEGMENTS])
            seg = rng.choice(list(C.SEGMENTS), p=weights / weights.sum())
            cust = str(rng.choice(self._cust_by_seg[seg]))
            fi = round(max(0.0, rng.normal(FI_GROSS_MEAN, 450)), 0)
            pay = rng.choice(["finance", "cash", "lease"], p=[0.62, 0.23, 0.15])
        elif channel == "dealer_trade":
            price, cust, fi, pay, seg = round(v["unit_cost"] * rng.uniform(0.97, 1.0), 0), None, 0.0, "dealer_trade", None
        else:
            price, cust, fi, pay, seg = round(mv * rng.uniform(0.86, 0.93), 0), None, 0.0, "auction", None
        days = (d - v["acquisition_date"]).days
        v["_sold"] = d
        self.sales.append({
            "deal_id": f"D{700000 + len(self.sales)}", "vin": v["vin"], "rooftop_id": v["rooftop_id"],
            "sale_date": d.isoformat(), "channel": channel, "sale_price": price,
            "list_price_at_sale": v["_price"], "customer_id": cust, "payment_type": pay,
            "fi_gross": fi, "days_in_stock": days,
            "salesperson_id": f"S{v['rooftop_id'][1:]}{int(rng.integers(1, 9)):02d}" if channel == "retail" else None,
        })

    def _weekly_feeds(self, on_lot: list[dict], week_end: date) -> None:
        rng = self.rng
        week_start = week_end - timedelta(days=week_end.weekday())  # Monday
        days = (week_end - week_start).days + 1
        for v in on_lot + [x for x in self.vehicles if x["_sold"] and week_start <= x["_sold"] <= week_end]:
            first = max(week_start, v["acquisition_date"])
            last = min(week_end, v["_sold"] or week_end)
            n_days = (last - first).days + 1
            if n_days <= 0:
                continue
            age = (last - v["acquisition_date"]).days
            mv = self.market_value(v, last)
            gap = (v["_price"] - mv) / mv
            views_rate = 9.0 * v["_pop"] * colour_factor(v["exterior_colour"]) * v["_appeal"] ** 0.8 * math.exp(-0.004 * age)
            views = int(rng.poisson(views_rate * n_days))
            leads = int(rng.binomial(views, min(0.2, 0.035 * math.exp(-5.0 * gap)))) if views else 0
            tds = int(rng.binomial(leads, 0.35)) if leads else 0
            self.weekly_leads.append({"vin": v["vin"], "week_start": week_start.isoformat(),
                                      "vdp_views": views, "leads": leads, "test_drives": tds,
                                      "days_listed": n_days})
            supply = max(12.0, 70.0 / (v["_pop"] * season(last)) * rng.normal(1.0, 0.12))
            self.weekly_comps.append({"vin": v["vin"], "snapshot_date": last.isoformat(),
                                      "market_avg_price": round(mv * rng.normal(1.0, 0.012), 0),
                                      "comp_count": int(rng.integers(4, 40)),
                                      "market_days_supply": round(supply, 0)})
        _ = days

    # ------------------------------------------------------------------ promotions
    def promotions(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        rng = self.rng
        camps, resp = [], []
        d = self.cfg.start + timedelta(days=10)
        cid = 0
        classes = list(C.BODY_CLASSES)
        while d < self.cfg.as_of - timedelta(days=7):
            body = rng.choice(classes)
            offer = int(rng.choice([250, 500, 750, 1000, 1500]))
            channel = rng.choice(["email", "sms", "paid_social"], p=[0.6, 0.25, 0.15])
            camp_id = f"P{2000 + cid}"
            camps.append({"campaign_id": camp_id, "launch_date": d.isoformat(), "target_body_class": body,
                          "offer_amount": offer, "channel": channel,
                          "name": f"{body.replace('_', ' ').title()} ${offer} offer"})
            n = int(rng.integers(900, 1600))
            recips = self.customers.sample(n, random_state=int(rng.integers(1 << 31)))
            for c in recips.itertuples():
                aff = C.SEGMENTS[c.segment].get(body, 0.4)
                sens = C.SEGMENT_DISCOUNT_SENSITIVITY[c.segment]
                p_open = 0.32 if channel == "email" else (0.85 if channel == "sms" else 0.6)
                p_click = min(0.6, 0.05 * math.sqrt(aff) * (1 + 0.55 * sens * offer / 1000.0))
                opened = rng.random() < p_open
                clicked = opened and rng.random() < p_click
                lead = clicked and rng.random() < 0.22 * math.sqrt(aff)
                purchased = lead and rng.random() < min(0.6, 0.12 * (1 + 0.45 * sens * offer / 1000.0))
                resp.append({"campaign_id": camp_id, "customer_id": c.customer_id,
                             "sent_date": d.isoformat(), "opened": bool(opened), "clicked": bool(clicked),
                             "lead_created": bool(lead), "purchased_within_30d": bool(purchased)})
            cid += 1
            d += timedelta(days=int(rng.integers(8, 16)))
        return pd.DataFrame(camps), pd.DataFrame(resp)


# ---------------------------------------------------------------------- output
def _week_drop(d: str | date) -> str:
    dd = date.fromisoformat(d) if isinstance(d, str) else d
    monday_next = dd + timedelta(days=7 - dd.weekday())
    return min(monday_next, AS_OF).isoformat()


def _dirty(df: pd.DataFrame, rng: np.random.Generator, dup: float = 0.0, null_cols: dict | None = None,
           bad: dict | None = None) -> pd.DataFrame:
    out = df.copy()
    if dup and len(out):
        out = pd.concat([out, out.sample(frac=dup, random_state=int(rng.integers(1 << 31)))])
        out = out.reset_index(drop=True)  # unique labels so nulls/bad values hit single rows, not dup pairs
    for col, frac in (null_cols or {}).items():
        idx = out.sample(frac=frac, random_state=int(rng.integers(1 << 31))).index
        out.loc[idx, col] = None
    for col, (frac, value) in (bad or {}).items():
        idx = out.sample(frac=frac, random_state=int(rng.integers(1 << 31))).index
        out.loc[idx, col] = value
    return out.reset_index(drop=True)


def write_outputs(sim: Simulator, cfg: Config) -> dict:
    rng = np.random.default_rng(cfg.seed + 1)
    out = cfg.out
    if os.path.exists(out):
        for sub in os.listdir(out):
            shutil.rmtree(os.path.join(out, sub), ignore_errors=True)
    if not out.startswith("/Volumes/"):  # a UC volume root already exists and cannot be mkdir'd
        os.makedirs(out, exist_ok=True)
    pub_cols = ["vin", "rooftop_id", "stock_number", "condition", "make", "model", "trim", "body_class",
                "model_year", "exterior_colour", "mileage", "msrp", "unit_cost", "initial_list_price",
                "acquisition_date", "acquisition_source"]
    veh = pd.DataFrame(sim.vehicles)
    veh_pub = veh[pub_cols].copy()
    veh_pub["acquisition_date"] = veh_pub["acquisition_date"].map(lambda x: x.isoformat())
    # initial stock acquired before the window arrives in the first drop
    veh_pub["_drop"] = veh_pub["acquisition_date"].map(lambda s: _week_drop(max(date.fromisoformat(s), cfg.start)))
    cust = sim.customers.copy()
    cust["_drop"] = cust["signup_date"].map(lambda s: _week_drop(max(date.fromisoformat(s), cfg.start)))
    pcs = pd.DataFrame(sim.price_changes)
    pcs["_drop"] = pcs["change_date"].map(_week_drop)
    sales = pd.DataFrame(sim.sales)
    sales["_drop"] = sales["sale_date"].map(_week_drop)
    leads = pd.DataFrame(sim.weekly_leads)
    leads["_drop"] = leads["week_start"].map(_week_drop)
    comps = pd.DataFrame(sim.weekly_comps)
    comps["_drop"] = comps["snapshot_date"].map(_week_drop)
    camps, resp = sim.promotions()
    camps["_drop"] = camps["launch_date"].map(_week_drop)
    resp["_drop"] = resp["sent_date"].map(_week_drop)

    if cfg.dirty:
        veh_pub = _dirty(veh_pub, rng, dup=0.004, null_cols={"unit_cost": 0.002}, bad={"mileage": (0.001, -1)})
        sales = _dirty(sales, rng, dup=0.002, bad={"sale_price": (0.002, 0.0)})
        leads = _dirty(leads, rng, null_cols={"vin": 0.002})
        pcs = _dirty(pcs, rng, dup=0.003)

    drops = sorted(set(veh_pub["_drop"]) | set(sales["_drop"]) | set(leads["_drop"]))
    last_drop = drops[-1]
    feeds = {  # entity -> (frame, format)
        "vehicles": (veh_pub, "csv"), "customers": (cust, "csv"), "price_changes": (pcs, "csv"),
        "sales": (sales, "csv"), "web_leads": (leads, "json"), "market_comps": (comps, "csv"),
        "campaigns": (camps, "csv"), "campaign_responses": (resp, "json"),
    }
    counts: dict = {}
    for entity, (df, fmt) in feeds.items():
        for drop, g in df.groupby("_drop"):
            root = os.path.join(out, "_held") if (cfg.hold_last_drop and drop == last_drop) else out
            folder = os.path.join(root, entity, f"drop_date={drop}")
            os.makedirs(folder, exist_ok=True)
            body = g.drop(columns=["_drop"])
            path = os.path.join(folder, f"{entity}_{drop.replace('-', '')}.{fmt}")
            if fmt == "csv":
                body.to_csv(path, index=False)
            else:
                body.to_json(path, orient="records", lines=True, date_format="iso")
        counts[entity] = int(len(df))

    ref = os.path.join(out, "reference")
    os.makedirs(ref, exist_ok=True)
    pd.DataFrame([{"rooftop_id": r[0], "rooftop_name": r[1], "franchises": "|".join(r[2]) or "pre-owned",
                   "lot_capacity": r[3]} for r in C.ROOFTOPS]).to_csv(os.path.join(ref, "rooftops.csv"), index=False)
    sim.models.drop(columns=["popularity"]).to_csv(os.path.join(ref, "models.csv"), index=False)
    months = pd.date_range(cfg.start.replace(day=1), cfg.as_of, freq="MS")
    pd.DataFrame([{"month": m.date().isoformat(), "lender": "Island Floorplan Finance",
                   "apr": floorplan_apr(m.date()), "lot_cost_per_day": LOT_COST_PER_DAY} for m in months]
                 ).to_csv(os.path.join(ref, "floorplan_rates.csv"), index=False)

    # hidden ground truth (never ingested by the pipeline) for model validation
    truth = os.path.join(out, "_truth")
    os.makedirs(truth, exist_ok=True)
    tv = veh[["vin", "condition", "body_class", "_appeal", "_elasticity", "_base_h", "_drift", "_market0", "_sold"]].copy()
    tv.columns = ["vin", "condition", "body_class", "appeal", "elasticity", "base_hazard", "daily_market_drift",
                  "market_value_at_acquisition", "disposed_date"]
    tv["disposed_date"] = tv["disposed_date"].map(lambda x: x.isoformat() if x else None)
    tv.to_csv(os.path.join(truth, "vehicle_truth.csv"), index=False)
    json.dump({"body_class_elasticity": {k: v[0] for k, v in C.BODY_CLASSES.items()},
               "segment_discount_sensitivity": C.SEGMENT_DISCOUNT_SENSITIVITY,
               "segment_body_affinity": C.SEGMENTS, "as_of": cfg.as_of.isoformat(), "seed": cfg.seed},
              open(os.path.join(truth, "truth.json"), "w"), indent=2)

    on_hand = len(sim.on_lot_at_end)
    ages = np.array([(cfg.as_of - v["acquisition_date"]).days for v in sim.on_lot_at_end])
    s = pd.DataFrame(sim.sales)
    summary = {
        "as_of": cfg.as_of.isoformat(), "drops": len(drops), "held_drop": last_drop if cfg.hold_last_drop else None,
        "rows": counts, "vehicles_simulated": len(sim.vehicles), "on_hand_at_as_of": on_hand,
        "on_hand_45_plus": int((ages >= 45).sum()), "on_hand_90_plus": int((ages >= 90).sum()),
        "retail_sales": int((s["channel"] == "retail").sum()), "wholesale_exits": int((s["channel"] == "wholesale").sum()),
        "median_days_to_retail": float(s.loc[s["channel"] == "retail", "days_in_stock"].median()),
        "price_change_reasons": pd.DataFrame(sim.price_changes)["reason"].value_counts().to_dict(),
    }
    json.dump(summary, open(os.path.join(out, "_generation_summary.json"), "w"), indent=2)
    return summary


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--hold_last_drop", default="false")
    a, _ = p.parse_known_args(argv)
    cfg = Config(out=a.out, seed=a.seed, hold_last_drop=str(a.hold_last_drop).lower() == "true")
    sim = Simulator(cfg)
    sim.run()
    summary = write_outputs(sim, cfg)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
