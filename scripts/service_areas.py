"""Robotaxi service-area polygons. Geometry only: no fleet counts."""
import json
from pathlib import Path

URL = "https://raw.githubusercontent.com/Robotaxi-Tracker/robotaxi-service-areas/main/dist/service-areas.json"
PATH = Path(__file__).resolve().parent.parent / "data" / "service-areas.json"


def load_document(path=PATH):
    path = Path(path)
    if not path.exists():
        return None
    with path.open() as handle:
        document = json.load(handle)
    if not isinstance(document, dict) or not isinstance(document.get("areas"), list):
        return None
    return document


def feature_collection(document):
    """Features and a city table. The table has no vehicle-count column."""
    features = []
    rows = []
    for area in document.get("areas") or []:
        geometry = ((area.get("boundary") or {}).get("geometry"))
        key = area.get("key")
        if not geometry or not key:
            continue
        provider = str(area.get("provider") or "").strip().title()
        city = str(area.get("name") or "").strip()
        features.append({
            "type": "Feature",
            "id": key,
            "properties": {"key": key, "provider": provider, "city": city},
            "geometry": geometry,
        })
        rows.append({
            "key": key,
            "provider": provider,
            "city": city,
            "test_region": bool(area.get("isTestRegion")),
        })
    rows.sort(key=lambda row: (row["city"], row["provider"]))
    return {"type": "FeatureCollection", "features": features}, rows


def generated_at(document):
    return str((document or {}).get("generatedAt") or "")
