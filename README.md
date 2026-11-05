# Texas Robotaxi Fleet Tracker (Cybercab dashboard)

Streamlit app charting Tesla (Model Y + Cybercab) and other robotaxi operators' registered fleets in Texas.

- `app.py` – Streamlit app (entry point)
- `data/history.csv` – history. `quality` is `exact` (model split published that day), `carried_forward` (no usable model names, operator total unchanged, previous model counts reused), or `approximate` (tracker-sourced early totals)
- `scripts/collect.py` – fetches https://fsddb.com/robotaxi.json once, appends today's rows (idempotent per day)
- `scripts/model_rows.py` – shared model-name rules used by the collector and `app.py` `load()`
- `.github/workflows/daily.yml` – runs the collector daily and commits the CSV

## Data
Derived from the public Texas DMV Automated Vehicle registry via [fsddb.com](https://fsddb.com/robotaxi). Unofficial. Please be gentle with fsddb: one request per day.

`scripts/collect.py` stores `operators[].fleet_size` as `operator_total` and writes one row per usable `operators[].models` entry. Placeholder names (`Unknown model`, blank, `n/a`, `none`, `null`) are not stored as vehicles. The same rules run in `app.py` `load()`, so a placeholder row already in the CSV is not charted as a model.

When an operator has no usable model name:

- If `fleet_size` equals that operator's previous snapshot total, the previous model rows are copied onto that day with the same counts and `quality` `carried_forward`.
- If the total changed, or there is no previous snapshot, one `(all models)` row is written with `count` equal to `fleet_size`.

Only the immediately previous snapshot is consulted. After a total change, a later day that returns to an older total does not reuse the pre-change mix.

### 2026-11-05

[Run 42096654111](https://github.com/matthewsvm/cybercab-dashboard/actions/runs/42096654111) stored fsddb's placeholder: every operator was `{"Unknown model": <fleet_size>}`. Those fleet sizes matched 2026-11-04 (Waymo 1,259, Tesla Robotaxi 1,244, Avride 344, Zoox 63, Nuro 47, May Mobility 22), so the placeholder rows were replaced with that day's model counts. Tesla Robotaxi on 2026-11-05 is Model Y 671 and Cybercab 573, marked `carried_forward`. Operator totals are still the source fleet sizes.

## Deploy
1. Push these files to the repo's `main` branch.
2. On GitHub: Settings → Actions → General → Workflow permissions → allow read/write (the workflow also declares `contents: write`).
3. Run the "Daily fleet snapshot" workflow once from the Actions tab.
4. At share.streamlit.io, sign in with GitHub → New app → this repo, branch `main`, main file `app.py`.

Run locally: `pip install -r requirements.txt && streamlit run app.py`
