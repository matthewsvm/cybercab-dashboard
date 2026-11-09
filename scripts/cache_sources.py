"""Download the map and California activity files used by the app.

Failures leave the previous file in place. These feeds are not fleet counts.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ca_activity import URL as CPUC_URL
from ca_activity import PATH as CPUC_PATH
from service_areas import URL as AREAS_URL
from service_areas import PATH as AREAS_PATH

UA = "cybercab-dashboard/0.1 (+https://github.com/matthewsvm/cybercab-dashboard; daily cache)"
META_PATH = Path(__file__).resolve().parent.parent / "data" / "source_meta.json"


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def _load_meta():
    if not META_PATH.exists():
        return {}
    try:
        with META_PATH.open() as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json_bytes(path, raw, accept):
    document = json.loads(raw)
    if not accept(document):
        raise ValueError(f"unexpected shape for {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw if raw.endswith(b"\n") else raw + b"\n")
    return document


def refresh():
    """Refresh cached files. Returns the meta dict. One failure does not erase the other file."""
    meta = _load_meta()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        document = _write_json_bytes(
            AREAS_PATH, _get(AREAS_URL),
            lambda doc: isinstance(doc, dict) and isinstance(doc.get("areas"), list) and doc["areas"],
        )
        meta["service_areas"] = {
            "source": AREAS_URL,
            "generated_at": document.get("generatedAt"),
            "areas": len(document.get("areas") or []),
            "fetched_at": now,
        }
        print(f"service areas: {len(document['areas'])} areas, generated {document.get('generatedAt')}")
    except Exception as exc:
        print(f"service areas unchanged: {exc}")
    try:
        document = _write_json_bytes(
            CPUC_PATH, _get(CPUC_URL),
            lambda doc: isinstance(doc, dict) and isinstance(doc.get("data"), list) and doc["data"],
        )
        meta["cpuc_activity"] = {
            "source": CPUC_URL,
            "upstream": document.get("source"),
            "dataset": document.get("dataset"),
            "rows": len(document.get("data") or []),
            "fetched_at": now,
        }
        print(f"CPUC activity: {len(document['data'])} monthly rows")
    except Exception as exc:
        print(f"CPUC activity unchanged: {exc}")
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    with META_PATH.open("w") as handle:
        json.dump(meta, handle, indent=2)
        handle.write("\n")
    return meta
