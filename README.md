# Texas Robotaxi Fleet Tracker (Cybercab dashboard)

Streamlit app charting Tesla (Model Y + Cybercab) and other robotaxi operators' registered fleets in Texas.

- `app.py` – Streamlit app (entry point)
- `data/history.csv` – history; `quality` is `exact` (daily snapshots) or `approximate` (tracker-sourced early totals)
- `scripts/collect.py` – fetches https://fsddb.com/robotaxi.json once, appends today's rows (idempotent per day)
- `.github/workflows/daily.yml` – runs the collector daily and commits the CSV

## Data
Derived from the public Texas DMV Automated Vehicle registry via [fsddb.com](https://fsddb.com/robotaxi). Unofficial. Please be gentle with fsddb: one request per day.

## Deploy
1. Push these files to the repo's `main` branch.
2. On GitHub: Settings → Actions → General → Workflow permissions → allow read/write (the workflow also declares `contents: write`).
3. Run the "Daily fleet snapshot" workflow once from the Actions tab.
4. At share.streamlit.io, sign in with GitHub → New app → this repo, branch `main`, main file `app.py`.

Run locally: `pip install -r requirements.txt && streamlit run app.py`
