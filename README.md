# Texas Robotaxi Fleet Tracker (Cybercab dashboard)

Streamlit app charting Tesla (Model Y + Cybercab) and other robotaxi operators' registered fleets in Texas.

- `app.py` – Streamlit app (entry point)
- `data/history.csv` – Texas fleet history. `quality` is `exact` (VIN census matched the fleet size, or fsddb published usable model names), `partial` (VIN census matched the fleet size and some VINs did not decode), `carried_forward` (no usable names and the operator total was unchanged), or `approximate` (early tracker totals)
- `scripts/collect.py` – daily job: fsddb totals, TxMCCS VIN pages, then cached map and California files
- `scripts/vin_models.py` – VIN prefix table and the one-source model choice
- `data/service-areas.json` – city boundaries, cached. Not a fleet count
- `data/cpuc_activity_monthly.json` – California trips and miles, cached. Not a fleet count
- `.github/workflows/daily.yml` – runs the collector daily and commits those files

## Data
Three feeds, kept apart. Texas registered vehicles stay the headline. Please be gentle with the upstream sites: the Action sleeps between TxMCCS pages and requests fsddb once.

| Feed | What it contributes |
| --- | --- |
| TxDMV TxMCCS VIN list | Per-model counts. Prefixes such as `7SAY` Model Y and `5YJA` Cybercab. |
| [fsddb.com/robotaxi.json](https://fsddb.com/robotaxi) | Operator totals (`fleet_size`). Its `models` map is currently `Unknown model`, so those names are not used. |
| [Robotaxi-Tracker service areas](https://github.com/Robotaxi-Tracker/robotaxi-service-areas) | City polygons for the map. |
| [AV Observatory CPUC monthly file](https://av-observatory.com/data/cpuc_activity_monthly.json) | California trips and vehicle miles from CPUC quarterly reports. |

A model row comes from the VIN census when the number of unique VINs equals that operator's fsddb `fleet_size`. fsddb model counts are not added on top. If TxMCCS fails or the totals disagree, names fall back as follows:

- If `fleet_size` equals that operator's previous snapshot total, the previous model rows are copied and marked `carried_forward`.
- If the total changed, or there is no previous snapshot, one `(all models)` row is written with `count` equal to `fleet_size`.

Only the immediately previous snapshot is consulted. After a total change, a later day that returns to an older total does not reuse the pre-change mix.

The same fallback runs in `app.py` `load()`. California rows and map polygons never enter `history.csv`.

### 2026-11-05

[Run 42096654111](https://github.com/matthewsvm/cybercab-dashboard/actions/runs/42096654111) stored fsddb's placeholder. Those fleet sizes matched 2026-11-04, so Tesla Robotaxi that day is Model Y 671 and Cybercab 573, marked `carried_forward`. Later days with a changed total use the VIN census when it matches.

## Deploy
1. Push these files to the repo's `main` branch.
2. On GitHub: Settings → Actions → General → Workflow permissions → allow read/write (the workflow also declares `contents: write`).
3. Run the "Daily fleet snapshot" workflow once from the Actions tab.
4. At share.streamlit.io, sign in with GitHub → New app → this repo, branch `main`, main file `app.py`.

Run locally: `pip install -r requirements.txt && streamlit run app.py`
