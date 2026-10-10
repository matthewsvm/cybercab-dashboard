"""Poll fsddb.com's public JSON once and append today's per-operator/model rows
to data/history.csv. Idempotent per day (existing rows for today are replaced)."""
import csv, json, sys, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

URL = "https://fsddb.com/robotaxi.json"
UA = "cybercab-dashboard/0.1 (+https://github.com/matthewsvm/cybercab-dashboard; daily, single request)"
CSV = Path(__file__).resolve().parent.parent / "data" / "history.csv"
FIELDS = ["date", "operator", "model", "count", "operator_total", "source", "quality"]
SOURCE = "fsddb.com/robotaxi.json (mirrors TxDMV TxMCCS)"

def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    data = fetch()
    today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    new = []
    for op in data["operators"]:
        for model, n in op["models"].items():
            new.append({"date": today, "operator": op["name"], "model": model, "count": n,
                        "operator_total": op["fleet_size"], "source": SOURCE, "quality": "exact"})
    if not new:
        sys.exit("No data returned; leaving file untouched")
    existing = list(csv.DictReader(CSV.open())) if CSV.exists() else []
    kept = [r for r in existing if r["date"] != today]
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, FIELDS); w.writeheader(); w.writerows(kept + new)
    print(f"{today}: wrote {len(new)} rows ({len(kept)} older rows kept)")

if __name__ == "__main__":
    main()
