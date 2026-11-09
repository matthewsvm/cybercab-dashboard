"""California CPUC passenger-service activity. Trips and miles, not fleet size.

The monthly file is the AV Observatory aggregate of CPUC quarterly AV reports:
https://av-observatory.com/data/cpuc_activity_monthly.json
Upstream source, as labeled in that file: California Public Utilities Commission
AV Program quarterly deployment reports. Public agency figures; cite both.

TCP numbers are the CPUC permit identifiers (permits-issued page and the
permit PDFs): PSG0038152 Waymo LLC, PSG0039080 Cruise LLC, 0038380-P Zoox, Inc.
"""
import json
from pathlib import Path

URL = "https://av-observatory.com/data/cpuc_activity_monthly.json"
PATH = Path(__file__).resolve().parent.parent / "data" / "cpuc_activity_monthly.json"

# Confirmed from cpuc.ca.gov AV permits: TCP 38152 Waymo, TCP 39080 Cruise, TCP 38380 Zoox.
TCP_OPERATORS = {
    "PSG0038152": "Waymo",
    "PSG0039080": "Cruise",
    "0038380-P": "Zoox",
}

PROGRAM_LABELS = {
    "drivered_pilot": "Drivered pilot",
    "driverless_pilot": "Driverless pilot",
    "driverless": "Driverless deployment",
    "unspecified": "Unspecified",
}


def load_document(path=PATH):
    path = Path(path)
    if not path.exists():
        return None
    with path.open() as handle:
        document = json.load(handle)
    if not isinstance(document, dict) or not isinstance(document.get("data"), list):
        return None
    return document


def operator_name(tcp_id):
    tcp_id = str(tcp_id or "").strip()
    return TCP_OPERATORS.get(tcp_id, tcp_id or "Unknown TCP")


def activity_rows(document):
    """One row per operator, program, and month.

    Programs are separate CPUC filings. Callers may sum them for an operator
    month; that adds different services, not two copies of one filing.
    The result has trips and vmt only.
    """
    rows = []
    for raw in document.get("data") or []:
        year = int(raw["calendar_year"])
        month = int(raw["calendar_month"])
        program = str(raw.get("program") or "")
        rows.append({
            "operator": operator_name(raw.get("operator_tcpid")),
            "tcp_id": str(raw.get("operator_tcpid") or ""),
            "program": PROGRAM_LABELS.get(program, program or "Unspecified"),
            "year": year,
            "month": month,
            "period": f"{year:04d}-{month:02d}",
            "quarter": f"{year} Q{(month - 1) // 3 + 1}",
            "trips": float(raw.get("total_trips") or 0),
            "vmt": float(raw.get("total_vmt_all_periods") or 0),
        })
    rows.sort(key=lambda row: (row["period"], row["operator"], row["program"]))
    return rows


def sum_activity(rows, *keys):
    """Sum trips and VMT for the given group keys. No fleet-size field."""
    grouped = {}
    for row in rows:
        key = tuple(row[name] for name in keys)
        bucket = grouped.get(key)
        if bucket is None:
            bucket = {name: row[name] for name in keys}
            bucket["trips"] = 0.0
            bucket["vmt"] = 0.0
            grouped[key] = bucket
        bucket["trips"] += float(row["trips"])
        bucket["vmt"] += float(row["vmt"])
    return list(grouped.values())
