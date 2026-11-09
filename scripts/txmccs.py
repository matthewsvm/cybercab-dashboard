"""Page through the public TxMCCS automated-vehicle list.

No login. ``limit`` stays at the API maximum of 100. Callers pause between
pages. A short or overlapping page list that does not yield exactly ``total``
unique VINs is a failure, so the collector can fall back instead of publishing
a partial or double-counted census.
"""
import json
import time
import urllib.request

API = "https://txmccs.txdmv.gov/api/TruckStop/companies/{company_id}/automated-motor-vehicles"
UA = "cybercab-dashboard/0.1 (+https://github.com/matthewsvm/cybercab-dashboard; daily TxMCCS VIN pages, limit 100)"
PAGE_LIMIT = 100
PAGE_PAUSE_SECONDS = 0.4


def collect_vins(fetch_page, pause=0.0, sleep=time.sleep):
    """Return unique VINs, or None if the census does not match the reported total.

    ``fetch_page(offset)`` returns a dict ``{vehicles: [{vin}], total}`` or None
    on transport failure.
    """
    offset = 0
    total = None
    seen = []
    seen_set = set()
    while True:
        page = fetch_page(offset)
        if not isinstance(page, dict) or "total" not in page:
            return None
        if total is None:
            total = int(page["total"])
        vehicles = page.get("vehicles") or []
        if not vehicles:
            break
        for vehicle in vehicles:
            vin = str((vehicle or {}).get("vin") or "").strip().upper()
            if not vin or vin in seen_set:
                continue
            seen_set.add(vin)
            seen.append(vin)
        offset += len(vehicles)
        if offset >= total:
            break
        sleep(pause)
    if total is None or len(seen) != total:
        return None
    return seen


def fetch_page(company_id, offset, timeout=40):
    url = API.format(company_id=company_id) + f"?limit={PAGE_LIMIT}&offset={int(offset)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except Exception as exc:
        print(f"TxMCCS page failed for {company_id} offset {offset}: {exc}")
        return None


def fetch_vins(company_id, pause=PAGE_PAUSE_SECONDS):
    return collect_vins(lambda offset: fetch_page(company_id, offset), pause=pause)
