"""Poll public sources once and append today's Texas fleet rows.

fsddb.com/robotaxi.json supplies operator totals. Per-model counts come from
the TxMCCS VIN list when that census matches the fsddb fleet size. Otherwise
the existing placeholder rules apply: carry forward the previous model mix
when the total is unchanged, or record ``(all models)`` when it changed.

The service-area file and the California activity file are cached for the app.
They are not written into history.csv.
"""
import csv
import json
import re
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from cache_sources import refresh as refresh_cached_sources
from model_rows import TOTAL_ONLY, is_placeholder, resolve_model_rows
from txmccs import fetch_vins
from vin_models import VIN_SOURCE, count_vins, select_model_rows

URL = "https://fsddb.com/robotaxi.json"
UA = "cybercab-dashboard/0.1 (+https://github.com/matthewsvm/cybercab-dashboard; daily, single fsddb request)"
CSV = Path(__file__).resolve().parent.parent / "data" / "history.csv"
FIELDS = ["date", "operator", "model", "count", "operator_total", "source", "quality"]
SOURCE = "fsddb.com/robotaxi.json (mirrors TxDMV TxMCCS)"
COMPANY_ID = re.compile(r"/companies/([0-9a-fA-F-]{36})(?:/|$)")


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def company_id(operator):
    match = COMPANY_ID.search(str(operator.get("txdmv_url") or ""))
    return match.group(1) if match else None


def vin_split_for(operator):
    """Unique VIN model counts for one operator, or None if TxMCCS cannot be used."""
    cid = company_id(operator)
    name = operator.get("name")
    if not cid:
        print(f"{name}: no TxMCCS company id; model split will fall back")
        return None
    vins = fetch_vins(cid)
    if vins is None:
        print(f"{name}: TxMCCS VIN census incomplete; model split will fall back")
        return None
    summary = count_vins(vins)
    print(
        f"{name}: {summary['total']} unique VINs, "
        f"{summary['unrecognized']} unrecognized, {summary['duplicates']} duplicates"
    )
    return summary


def snapshot_rows(data, today, vin_by_operator=None):
    """One row per model from a single source, or a placeholder when neither source has names."""
    vin_by_operator = vin_by_operator or {}
    rows = []
    for operator in data.get("operators") or []:
        name = operator.get("name")
        if not name or "fleet_size" not in operator or operator["fleet_size"] is None:
            continue
        total = int(operator["fleet_size"])
        models = operator.get("models") if isinstance(operator.get("models"), dict) else {}
        selected = select_model_rows(total, models, vin_by_operator.get(name))
        if selected is None:
            rows.append({
                "date": today, "operator": name, "model": "Unknown model", "count": total,
                "operator_total": total, "source": SOURCE, "quality": "exact",
            })
            continue
        counts, quality, origin = selected
        source = VIN_SOURCE if origin == "vin" else SOURCE
        for model, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            rows.append({
                "date": today, "operator": name, "model": model, "count": int(count),
                "operator_total": total, "source": source, "quality": quality,
            })
    return rows


def assemble(existing, data, today, vin_by_operator=None):
    """History for dates other than today, plus today's snapshot, with placeholders resolved."""
    kept = [row for row in existing if str(row["date"])[:10] != today]
    new = snapshot_rows(data, today, vin_by_operator)
    if not new and not kept:
        return []
    return resolve_model_rows(kept + new)


def check_totals(rows, data, today):
    """operator_total for today must match each source fleet_size, with no placeholder models."""
    today_rows = [row for row in rows if row["date"] == today]
    problems = []
    for operator in data.get("operators") or []:
        name = operator.get("name")
        if not name or "fleet_size" not in operator or operator["fleet_size"] is None:
            continue
        total = int(operator["fleet_size"])
        mine = [row for row in today_rows if row["operator"] == name]
        got = {int(row["operator_total"]) for row in mine}
        if got != {total}:
            problems.append(f"{name}: operator_total {sorted(got) or 'missing'} != fleet_size {total}")
        if any(is_placeholder(row["model"]) for row in mine):
            problems.append(f"{name}: placeholder model would be written")
        counted = sum(int(row["count"]) for row in mine)
        if counted != total:
            problems.append(f"{name}: model counts sum to {counted}, fleet_size is {total}")
    if problems:
        sys.exit("Refusing to write history.csv:\n" + "\n".join(problems))


def main():
    data = fetch()
    today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    vin_by_operator = {}
    for operator in data.get("operators") or []:
        name = operator.get("name")
        if not name:
            continue
        split = vin_split_for(operator)
        if split is not None:
            vin_by_operator[name] = split
    existing = list(csv.DictReader(CSV.open())) if CSV.exists() else []
    rows = assemble(existing, data, today, vin_by_operator)
    if not rows:
        sys.exit("No data returned; leaving file untouched")
    check_totals(rows, data, today)
    today_rows = [row for row in rows if row["date"] == today]
    older = len(rows) - len(today_rows)
    carried = sum(1 for row in today_rows if row["quality"] == "carried_forward")
    total_only = sum(1 for row in today_rows if row["model"] == TOTAL_ONLY)
    exact = sum(1 for row in today_rows if row["quality"] == "exact")
    partial = sum(1 for row in today_rows if row["quality"] == "partial")
    with CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"{today}: wrote {len(today_rows)} rows "
        f"({exact} exact, {partial} partial, {carried} carried forward, {total_only} total-only); "
        f"{older} older rows kept"
    )
    refresh_cached_sources()


if __name__ == "__main__":
    main()
