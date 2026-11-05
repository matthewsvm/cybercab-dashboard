# Texas Robotaxi Fleet Tracker (Cybercab dashboard)

Streamlit app charting Tesla (Model Y + Cybercab) and other robotaxi operators' registered fleets in Texas.

- `app.py` – Streamlit app (entry point)
- `data/history.csv` – history; `quality` is `exact` (daily snapshots) or `approximate` (tracker-sourced early totals)
- `scripts/collect.py` – fetches https://fsddb.com/robotaxi.json once, appends today's rows (idempotent per day)
- `.github/workflows/daily.yml` – runs the collector daily and commits the CSV

## Data
Derived from the public Texas DMV Automated Vehicle registry via [fsddb.com](https://fsddb.com/robotaxi). Unofficial. Please be gentle with fsddb: one request per day.

`scripts/collect.py` writes one row per entry in `operators[].models` and copies `operators[].fleet_size` into `operator_total`.

### 2026-11-05 model names

That day's snapshot labels every vehicle `Unknown model`. Those labels are the strings fsddb published in `operators[].models`. [Run 42096654111](https://github.com/matthewsvm/cybercab-dashboard/actions/runs/42096654111) used the same `collect.py` as 2026-11-04 (that run wrote 10 model rows, including Tesla Model Y 671 and Cybercab 573) and logged `wrote 6 rows` — one models entry per operator.

Live `https://fsddb.com/robotaxi.json` (generated 2026-11-05T11:56:11-08:00, after that run) still has `models` as a name→count object. Each operator is `{"Unknown model": <fleet_size>}`, and `models_by_year` is `{"": <fleet_size>}`. The fsddb robotaxi page shows the same placeholder. The JSON contains none of the prior model strings (Model Y, Cybercab, Jaguar I-PACE, and the rest), so the 2026-11-05 per-model counts were left as published.

Operator totals for 2026-11-05 are the source fleet sizes and match 2026-11-04: Waymo 1,259, Tesla Robotaxi 1,244, Avride 344, Zoox 63, Nuro 47, May Mobility 22 (sum 2,979, equal to `total_active_vehicles` and to `fleet_history` for 2026-11-05). Each operator's `last_registration_at` is on or before 2026-11-01. The `count` on each `Unknown model` row equals that operator total. The dashboard's Cybercab and Model Y figures for this day have no matching rows, so they display as zero.

## Deploy
1. Push these files to the repo's `main` branch.
2. On GitHub: Settings → Actions → General → Workflow permissions → allow read/write (the workflow also declares `contents: write`).
3. Run the "Daily fleet snapshot" workflow once from the Actions tab.
4. At share.streamlit.io, sign in with GitHub → New app → this repo, branch `main`, main file `app.py`.

Run locally: `pip install -r requirements.txt && streamlit run app.py`
