"""Turn raw snapshot rows into history rows without inventing model counts.

Usable ``operators[].models`` entries are kept as published. Placeholder names
(``Unknown model``, blank, ``n/a``, and similar) are not stored as vehicles.

When a day has no usable model name:

- If ``operator_total`` equals the immediately previous snapshot for that
  operator, copy that snapshot's model counts and mark them
  ``carried_forward``. The counts are reused, not recomputed.
- Otherwise write one ``(all models)`` row whose count is the operator total.

A total change blocks the older mix. The next day consults that total-only
snapshot, so a total that later returns to an earlier number does not
resurrect the pre-change split.
"""
from collections import defaultdict

CANON = {"cybercab": "Cybercab", "model y": "Model Y", "modey y": "Model Y"}
PLACEHOLDERS = {
    "",
    "unknown",
    "unknown model",
    "n/a",
    "na",
    "none",
    "null",
    "undefined",
    "nan",
    "-",
    "—",
}
TOTAL_ONLY = "(all models)"


def as_date(value):
    if hasattr(value, "strftime") and not isinstance(value, str):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def norm_model(model):
    if model is None:
        return ""
    try:
        if model != model:  # NaN
            return ""
    except TypeError:
        pass
    text = str(model).strip()
    return CANON.get(text.lower(), text)


def is_placeholder(model):
    return norm_model(model).strip().lower() in PLACEHOLDERS


def merge(rows):
    """Merge rows with the same date/operator/model (case-insensitive), summing counts."""
    out = {}
    for raw in rows:
        row = dict(raw)
        row["date"] = as_date(row["date"])
        row["model"] = norm_model(row["model"])
        row["count"] = int(row["count"])
        row["operator_total"] = int(row["operator_total"])
        key = (row["date"], row["operator"], row["model"].lower())
        if key in out:
            out[key]["count"] += row["count"]
        else:
            out[key] = row
    return list(out.values())


def _carried_quality(prev_rows):
    qualities = {str(r.get("quality") or "") for r in prev_rows}
    if qualities == {"approximate"}:
        return "approximate"
    return "carried_forward"


def resolve_model_rows(rows):
    """Replace placeholder model rows. Counts are copied or set to the operator total."""
    merged = merge(rows)
    by_key = defaultdict(list)
    order = []
    dates_by_op = defaultdict(list)
    for row in merged:
        key = (row["date"], row["operator"])
        if key not in by_key:
            order.append(key)
            dates_by_op[row["operator"]].append(row["date"])
        by_key[key].append(row)

    resolved = {}
    for operator, dates in dates_by_op.items():
        prev = None
        for date in sorted(set(dates)):
            day = by_key[(date, operator)]
            total = int(day[0]["operator_total"])
            usable = [r for r in day if not is_placeholder(r["model"])]
            if usable:
                resolved_day = usable
            elif prev is not None and int(prev[0]["operator_total"]) == total:
                quality = _carried_quality(prev)
                resolved_day = [{
                    "date": date,
                    "operator": operator,
                    "model": r["model"],
                    "count": int(r["count"]),
                    "operator_total": total,
                    "source": day[0]["source"],
                    "quality": quality,
                } for r in prev]
            else:
                quality = "approximate" if str(day[0].get("quality") or "") == "approximate" else "exact"
                resolved_day = [{
                    "date": date,
                    "operator": operator,
                    "model": TOTAL_ONLY,
                    "count": total,
                    "operator_total": total,
                    "source": day[0]["source"],
                    "quality": quality,
                }]
            resolved[(date, operator)] = resolved_day
            prev = resolved_day

    out = []
    for key in order:
        out.extend(resolved[key])
    return out
