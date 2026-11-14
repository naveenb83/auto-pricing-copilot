"""Fetch one openly licensed exterior photo per make/model from Wikimedia Commons.

Only public-domain / CC0 / CC BY / CC BY-SA images are kept; author, licence and source URL are
recorded in a manifest so the app can show attribution (required by CC BY / BY-SA).

    uv run python -m datagen.photos --out ./_media      # then uploaded to the UC volume `media`
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import time
from pathlib import Path

import requests

from datagen import catalog as C

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "auto-pricing-copilot-demo/0.1 (synthetic demo build; python-requests)"}
OK_LICENCES = re.compile(r"^(public domain|pd|cc0|cc[- ]by(-sa)?[- ]?\d(\.\d)?)", re.I)
BAD_WORDS = re.compile(
    r"interior|engine|dashboard|badge|logo|emblem|wheel|rear|heck|seat|cockpit|steering|trunk|boot|"
    r"crash|police|taxi|race|rally|concept|prototype|modified|tuned|tail|light|detail|plate|\.svg|\.png",
    re.I)
GOOD_WORDS = re.compile(r"front|\(cropped\)|1x7a|img|dsc", re.I)


def _get(url: str, **kw) -> requests.Response:
    for attempt in range(6):
        r = requests.get(url, headers=HEADERS, timeout=60, **kw)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        time.sleep(int(r.headers.get("Retry-After", 0) or 0) or 5 * (attempt + 1))
    r.raise_for_status()
    return r


def _search(query: str, limit: int = 30) -> list[str]:
    r = _get(API, params={"action": "query", "list": "search", "srsearch": f"{query} filetype:bitmap",
                                  "srnamespace": 6, "srlimit": limit, "format": "json"})
    return [h["title"] for h in r.json()["query"]["search"]]


def _info(titles: list[str]) -> list[dict]:
    r = _get(API, params={"action": "query", "titles": "|".join(titles), "prop": "imageinfo",
                                  "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1024, "format": "json"})
    out = []
    for page in r.json()["query"]["pages"].values():
        ii = (page.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        out.append({
            "title": page["title"], "width": ii.get("width", 0), "height": ii.get("height", 0),
            "mime": ii.get("mime", ""), "thumb": ii.get("thumburl"), "page": ii.get("descriptionurl"),
            "licence": html.unescape(meta.get("LicenseShortName", {}).get("value", "")),
            "licence_url": meta.get("LicenseUrl", {}).get("value", ""),
            "artist": re.sub(r"<[^>]+>", "", html.unescape(meta.get("Artist", {}).get("value", ""))).strip(),
        })
    return out


def pick(make: str, model: str, hint: str) -> dict | None:
    titles = _search(hint) or _search(f"{make} {model}")
    key = model.lower().replace("-", "").replace(" ", "")
    cands = []
    for t in titles:
        norm = t.lower().replace("-", "").replace(" ", "").replace("_", "")
        if key not in norm or BAD_WORDS.search(t):
            continue
        cands.append(t)
    if not cands:
        return None
    infos = _info(cands[:20])
    good = [i for i in infos if i["mime"] == "image/jpeg" and OK_LICENCES.match(i["licence"] or "")
            and i["width"] >= 1200 and 1.25 <= i["width"] / max(i["height"], 1) <= 2.0 and i["thumb"]]
    if not good:
        return None
    good.sort(key=lambda i: (bool(GOOD_WORDS.search(i["title"])), i["width"] * i["height"] > 2e6), reverse=True)
    order = {t: n for n, t in enumerate(cands)}
    good.sort(key=lambda i: order.get(i["title"], 99) - (5 if GOOD_WORDS.search(i["title"]) else 0))
    return good[0]


def _write(manifest: Path, rows: dict) -> None:
    with manifest.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["make", "model", "image_file", "source_title", "source_page",
                                          "author", "licence", "licence_url"])
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])


def slug(make: str, model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", f"{make}-{model}".lower()).strip("-")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./_media")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    out = Path(a.out)
    (out / "vehicles").mkdir(parents=True, exist_ok=True)
    manifest = out / "vehicle_images.csv"
    rows = {}
    if manifest.exists():
        rows = {(r["make"], r["model"]): r for r in csv.DictReader(manifest.open())}
    for make, model, *_rest in C.MODELS:
        hint = _rest[-1]
        if a.only and slug(make, model) not in a.only.split(","):
            continue
        if not a.only and (make, model) in rows and (out / rows[(make, model)]["image_file"]).exists():
            continue
        chosen = pick(make, model, hint)
        if not chosen:
            print(f"MISS  {make} {model}")
            continue
        fname = f"{slug(make, model)}.jpg"
        img = _get(chosen["thumb"])
        (out / "vehicles" / fname).write_bytes(img.content)
        rows[(make, model)] = {
            "make": make, "model": model, "image_file": f"vehicles/{fname}", "source_title": chosen["title"],
            "source_page": chosen["page"], "author": chosen["artist"][:200] or "Unknown",
            "licence": chosen["licence"], "licence_url": chosen["licence_url"],
        }
        print(f"OK    {make} {model:16s} {chosen['licence']:14s} {chosen['title']}")
        _write(manifest, rows)
        time.sleep(2.0)
    _write(manifest, rows)
    print(f"{len(rows)}/{len(C.MODELS)} models have a photo -> {manifest}")


if __name__ == "__main__":
    main()
