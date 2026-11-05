"""Poll fsddb.com's public JSON once and append today's per-operator/model rows
to data/history.csv. Idempotent per day (existing rows for today are replaced).

Placeholder model names are not written as vehicles. When fleet_size matches
the previous snapshot's operator total, that snapshot's model counts are
reused. When the total changed and the source has no usable split, the
operator total is stored as "(all models)".
"""
import csv, json, sys, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from model_rows import TOTAL_ONLY, is_placeholder, resolve_model_rows

URL = "https://fsddb.com/robotaxi.json"
UA = "cybercab-dashboard/0.1 (+https://github.com/matthewsvm/cybercab-dashboard; daily, single request)"
CSV = Path(__file__).resolve().parent.parent / "data" / "history.csv"
FIELDS = ["date", "operator", "model", "count", "operator_total", "source", "quality"]
SOURCE = "fsddb.com/robotaxi.json (mirrors TxDMV TxMCCS)"


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def snapshot_rows(data, today):
    """One row per usable model. Operators with no usable names get a placeholder marker.

    The marker is replaced by resolve_model_rows before anything is written.
    Its count is fleet_size and is not kept as a model count.
    """
    rows = []
    for op in data.get("operators") or []:
        name = op.get("name")
        if not name or "fleet_size" not in op or op["fleet_size"] is None:
            continue
        total = int(op["fleet_size"])
        models = op.get("models") if isinstance(op.get("models"), dict) else {}
        usable = [(model, count) for model, count in models.items() if not is_placeholder(model)]
        if usable:
            for model, count in usable:
                rows.append({
                    "date": today, "operator": name, "model": model, "count": int(count),
                    "operator_total": total, "source": SOURCE, "quality": "exact",
                })
        else:
            rows.append({
                "date": today, "operator": name, "model": "Unknown model", "count": total,
                "operator_total": total, "source": SOURCE, "quality": "exact",
            })
    return rows


def assemble(existing, data, today):
    """History for dates other than today, plus today's source snapshot, with placeholders resolved."""
    kept = [r for r in existing if str(r["date"])[:10] != today]
    new = snapshot_rows(data, today)
    if not new and not kept:
        return []
    return resolve_model_rows(kept + new)


def check_totals(rows, data, today):
    """operator_total for today must match each source fleet_size, with no placeholder models."""
    today_rows = [r for r in rows if r["date"] == today]
    problems = []
    for op in data.get("operators") or []:
        name = op.get("name")
        if not name or "fleet_size" not in op or op["fleet_size"] is None:
            continue
        total = int(op["fleet_size"])
        mine = [r for r in today_rows if r["operator"] == name]
        got = {int(r["operator_total"]) for r in mine}
        if got != {total}:
            problems.append(f"{name}: operator_total {sorted(got) or 'missing'} != fleet_size {total}")
        if any(is_placeholder(r["model"]) for r in mine):
            problems.append(f"{name}: placeholder model would be written")
    if problems:
        sys.exit("Refusing to write history.csv:\n" + "\n".join(problems))


def main():
    data = fetch()
    today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    existing = list(csv.DictReader(CSV.open())) if CSV.exists() else []
    rows = assemble(existing, data, today)
    if not rows:
        sys.exit("No data returned; leaving file untouched")
    check_totals(rows, data, today)
    today_rows = [r for r in rows if r["date"] == today]
    older = len(rows) - len(today_rows)
    carried = sum(1 for r in today_rows if r["quality"] == "carried_forward")
    total_only = sum(1 for r in today_rows if r["model"] == TOTAL_ONLY)
    exact = sum(1 for r in today_rows if r["quality"] == "exact")
    with CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"{today}: wrote {len(today_rows)} rows "
        f"({exact} exact, {carried} carried forward, {total_only} total-only); "
        f"{older} older rows kept"
    )


if __name__ == "__main__":
    main()
