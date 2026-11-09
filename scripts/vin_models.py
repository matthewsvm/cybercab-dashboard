"""Decode Texas AV models from VIN prefixes, and pick one model source.

Prefixes were checked on 2026-11-09 against one live TxMCCS VIN each, using
NHTSA vPIC DecodeVINValuesBatch. The daily collector does not call NHTSA.
An unrecognized prefix is counted, not assigned a guessed model.

Model counts come from either the VIN census or fsddb's model map, never both.
"""
from model_rows import is_placeholder, norm_model

# Longer prefixes win. Every entry is 4 characters today.
PREFIX_MODELS = (
    ("5YJA", "Cybercab"),          # TESLA Cybercab
    ("7SAY", "Model Y"),           # TESLA Model Y
    ("SADH", "Jaguar I-PACE"),     # JAGUAR I-PACE
    ("L6TZ", "Zeekr RT"),          # ZEEKR RT
    ("7YAK", "Hyundai Ioniq 5"),   # HYUNDAI Ioniq 5
    ("KM8K", "Hyundai Ioniq 5"),   # HYUNDAI Ioniq 5
    ("5TDD", "Toyota Highlander"), # TOYOTA Highlander
    ("7Z00", "Zoox"),              # ZOOX Zoox
    ("7UUG", "Lucid Gravity"),     # LUCID Gravity
    ("JTDK", "Toyota Prius"),      # TOYOTA Prius
    ("5TDY", "Toyota Sienna"),     # TOYOTA Sienna
)

VIN_SOURCE = "TxDMV TxMCCS VIN prefixes; fleet_size cross-check fsddb.com/robotaxi.json"
UNRECOGNIZED = "(unrecognized VIN)"

_PREFIXES = tuple(sorted(PREFIX_MODELS, key=lambda item: len(item[0]), reverse=True))


def decode_vin(vin):
    """Return the canonical model name, or None when the prefix is not in the table."""
    text = str(vin or "").strip().upper()
    if len(text) < 11:
        return None
    for prefix, model in _PREFIXES:
        if text.startswith(prefix):
            return model
    return None


def count_vins(vins):
    """Count unique VINs by model. Duplicate VINs are ignored, not added twice."""
    counts = {}
    unrecognized = 0
    seen = set()
    duplicates = 0
    for raw in vins:
        vin = str(raw or "").strip().upper()
        if not vin:
            continue
        if vin in seen:
            duplicates += 1
            continue
        seen.add(vin)
        model = decode_vin(vin)
        if model is None:
            unrecognized += 1
        else:
            counts[model] = counts.get(model, 0) + 1
    return {
        "total": len(seen),
        "counts": counts,
        "unrecognized": unrecognized,
        "duplicates": duplicates,
    }


def choose_vin_counts(fleet_size, vin_split):
    """VIN model counts when they account for every vehicle in fleet_size.

    Returns (counts, quality) or None. None means the caller should ignore the
    VIN split. Counts are the census itself, not a mix with any other source.
    """
    if not vin_split:
        return None
    fleet_size = int(fleet_size)
    total = int(vin_split.get("total") or 0)
    counts = {}
    for model, count in (vin_split.get("counts") or {}).items():
        name = norm_model(model)
        if is_placeholder(name):
            return None
        counts[name] = counts.get(name, 0) + int(count)
    unrecognized = int(vin_split.get("unrecognized") or 0)
    if total != fleet_size or sum(counts.values()) + unrecognized != fleet_size:
        return None
    if unrecognized:
        counts[UNRECOGNIZED] = unrecognized
        return counts, "partial"
    if not counts:
        return None
    return counts, "exact"


def select_model_rows(fleet_size, fsddb_models, vin_split):
    """Choose VIN counts or fsddb counts, never their sum.

    Returns (counts, quality, origin) or None when fsddb itself has no usable
    model names. origin is ``vin`` or ``fsddb``.
    """
    chosen = choose_vin_counts(fleet_size, vin_split)
    if chosen is not None:
        counts, quality = chosen
        return counts, quality, "vin"
    usable = {}
    for model, count in (fsddb_models or {}).items():
        if is_placeholder(model):
            continue
        name = norm_model(model)
        usable[name] = usable.get(name, 0) + int(count)
    if not usable:
        return None
    return usable, "exact", "fsddb"


def texas_registered_total(rows):
    """Registered vehicles: one operator_total per operator.

    Model rows describe that total. They are not added to it.
    """
    totals = {}
    for row in rows:
        totals[row["operator"]] = int(row["operator_total"])
    return sum(totals.values())
