import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from ca_activity import activity_rows, load_document as load_cpuc, sum_activity
from model_rows import resolve_model_rows
from service_areas import feature_collection, generated_at, load_document as load_areas

RED = "#E31937"
BG = "#0B0B0D"
CARD = "#16161A"
TEXT = "#F2F2F2"
MUTED = "#9A9AA3"
PALETTE = [RED, "#F2F2F2", "#4DA3FF", "#F5A623", "#7ED957", "#B388FF"]

pio.templates["cybercab_dark"] = go.layout.Template(layout=dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT), colorway=PALETTE,
    xaxis=dict(showgrid=False, zeroline=False, linecolor="#2A2A30", tickcolor=MUTED),
    yaxis=dict(showgrid=False, zeroline=False, linecolor="#2A2A30", tickcolor=MUTED),
    legend=dict(font=dict(color=TEXT)),
))
pio.templates.default = "cybercab_dark"

st.set_page_config(page_title="Texas Robotaxi Fleet Tracker", page_icon="assets/favicon.png", layout="wide")

st.html(f"""
<style>
div[data-testid="stMetric"] {{background:{CARD}; border:1px solid #26262C; border-left:4px solid {RED};
  border-radius:12px; padding:20px 24px;}}
div[data-testid="stMetricValue"] {{font-size:2.8rem; font-weight:700;}}
div[data-testid="stMetricLabel"] p {{font-size:1rem; color:{MUTED}; text-transform:uppercase; letter-spacing:.06em;}}
h1, h2, h3 {{letter-spacing:-.01em;}}
.cc-title {{display:flex; align-items:center; gap:16px; margin:0 0 .25rem;}}
.cc-title h1 {{margin:0; padding:0;}}
</style>
""")

CYBERCAB_SVG = """<svg width="96" height="48" viewBox="0 0 96 48" xmlns="http://www.w3.org/2000/svg" aria-label="Futuristic two-door robotaxi">
<path d="M4 33 L12 22 L38 12 L66 13 L90 27 L92 33 Z" fill="#F2F2F2"/>
<path d="M17 24 L39 15 L60 15 L78 26 Z" fill="#0B0B0D"/>
<path d="M39 15 L39 26 M17 24 L78 26" stroke="#F2F2F2" stroke-width="1" fill="none" opacity=".5"/>
<path d="M30 14 L44 6 L62 9 L58 14 Z" fill="#E31937" opacity=".9"/>
<rect x="4" y="33" width="88" height="4" fill="#E31937"/>
<circle cx="25" cy="37" r="8" fill="#1E1E22" stroke="#F2F2F2" stroke-width="2.5"/>
<circle cx="75" cy="37" r="8" fill="#1E1E22" stroke="#F2F2F2" stroke-width="2.5"/>
<circle cx="25" cy="37" r="2.5" fill="#E31937"/><circle cx="75" cy="37" r="2.5" fill="#E31937"/>
</svg>"""
st.html('<div class="cc-title">' + CYBERCAB_SVG.replace(chr(10), ' ') + '<h1>Texas Robotaxi Fleet Tracker</h1></div>')
st.caption("Tesla Cybercab and Model Y robotaxi counts vs. other operators, from the public Texas DMV AV registry.")

@st.cache_data(ttl=3600)
def load():
    df = pd.read_csv("data/history.csv", parse_dates=["date"])
    # Canonicalize model names, drop placeholder labels, and reuse the previous
    # snapshot's counts when the operator total is unchanged.
    df = pd.DataFrame(resolve_model_rows(df.to_dict("records")))
    df["date"] = pd.to_datetime(df["date"])
    df["count"] = pd.to_numeric(df["count"])
    df["operator_total"] = pd.to_numeric(df["operator_total"])
    df = (df.groupby(["date", "operator", "model"], as_index=False, sort=False)
            .agg({"count": "sum", "operator_total": "first", "source": "first", "quality": "first"}))
    return df

df = load()
latest_date = df["date"].max()
EVENTS = [("2026-10-21", "Tesla Q3 earnings"), ("2026-10-30", "NHTSA response due")]

def add_events(fig, xmax):
    for i, (d, label) in enumerate(EVENTS):
        if pd.Timestamp(d) <= xmax + pd.Timedelta(days=30):
            fig.add_vline(x=pd.Timestamp(d).timestamp() * 1000, line_dash="dash", line_color=MUTED,
                          annotation_text=label, annotation_position="top left" if i == 0 else "top right")
    return fig

# Latest metrics
last = df[df["date"] == latest_date]
tesla = last[last["operator"] == "Tesla Robotaxi"]
ops_total = last.groupby("operator")["operator_total"].first()
c = st.columns(4)
c[0].metric("Tesla total", int(ops_total.get("Tesla Robotaxi", 0)))
c[1].metric("Cybercab", int(tesla.loc[tesla["model"] == "Cybercab", "count"].sum()))
c[2].metric("Model Y", int(tesla.loc[tesla["model"] == "Model Y", "count"].sum()))
c[3].metric("All operators", int(ops_total.sum()))
st.caption(f"Latest data: {latest_date:%b %d, %Y}")
if (last["quality"] == "carried_forward").any():
    st.caption("Model counts marked carried forward are the previous snapshot's counts. "
               "The source had no usable model names that day, and the operator total was unchanged.")

# Tesla over time
st.subheader("Tesla fleet over time")
t = df[df["operator"] == "Tesla Robotaxi"]
tot = t.groupby("date", as_index=False)["operator_total"].first().rename(columns={"operator_total": "count"})
tot["series"] = "Tesla total"
models = t[t["model"].isin(["Model Y", "Cybercab"])][["date", "model", "count"]].rename(columns={"model": "series"})
ts = pd.concat([tot, models]).sort_values("date")
fig = px.line(ts, x="date", y="count", color="series", markers=True)
fig.update_layout(yaxis_title="Registered vehicles", xaxis_title=None, legend_title=None)
fig.update_yaxes(showgrid=False)
fig.update_xaxes(showgrid=False)
add_events(fig, latest_date)
st.plotly_chart(fig, width="stretch")
st.caption("Early points (Jul 30 – Oct 7) are approximate totals from third-party trackers; "
           "per-model counts start Oct 9. If a later snapshot has no usable model names and the "
           "operator total is unchanged, that day's model counts are the previous snapshot's.")

# Operators
st.subheader("Operator comparison")
ops = df.groupby(["date", "operator"], as_index=False)["operator_total"].first()
ops = ops[ops["operator"].isin(["Tesla Robotaxi", "Waymo", "Avride", "Zoox", "Nuro", "May Mobility"])]
left, right = st.columns(2)
bar = px.bar(ops[ops["date"] == latest_date].sort_values("operator_total"), x="operator_total", y="operator",
             orientation="h", text="operator_total")
bar.update_layout(xaxis_title="Vehicles", yaxis_title=None)
bar.update_traces(marker_color=RED, textfont_color=TEXT)
bar.update_yaxes(showgrid=False)
bar.update_xaxes(showgrid=False)
left.plotly_chart(bar, width="stretch")
if ops["date"].nunique() > 1:
    ofig = px.line(ops, x="date", y="operator_total", color="operator", markers=True)
    ofig.update_layout(yaxis_title="Vehicles", xaxis_title=None)
    ofig.update_yaxes(showgrid=False)
    ofig.update_xaxes(showgrid=False)
    right.plotly_chart(ofig, width="stretch")
else:
    right.info("Operator trend lines appear once more than one day of data is collected.")

with st.expander("Latest model breakdown / raw data"):
    st.dataframe(last[["operator", "model", "count", "operator_total", "quality"]], hide_index=True)
    st.dataframe(df.sort_values("date", ascending=False), hide_index=True)

if last["source"].astype(str).str.contains("TxMCCS VIN").any():
    st.caption("Per-model counts are VIN prefix counts from the TxDMV TxMCCS registry. "
               "Each operator total is the fsddb fleet size, which matched that VIN census.")

def load_meta():
    path = Path("data/source_meta.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}

meta = load_meta()

st.divider()
st.subheader("Service areas")
st.caption("Cities where Waymo, Tesla, and Zoox publish a service boundary. "
           "These shapes are context for where vehicles operate. They are not vehicle counts "
           "and are separate from the Texas registry totals above.")
areas_doc = load_areas()
if not areas_doc:
    st.info("Service-area file is not available yet. The daily collector stores data/service-areas.json.")
else:
    geojson, area_rows = feature_collection(areas_doc)
    area_frame = pd.DataFrame(area_rows)
    map_args = dict(
        geojson=geojson, locations="key", featureidkey="properties.key", color="provider",
        hover_name="city", hover_data={"provider": True, "key": False, "test_region": False},
        color_discrete_map={"Waymo": "#4DA3FF", "Tesla": RED, "Zoox": "#B388FF"},
        opacity=0.62, zoom=3.1, center={"lat": 36.2, "lon": -96.5},
    )
    try:
        if hasattr(px, "choropleth_map"):
            area_fig = px.choropleth_map(area_frame, map_style="carto-darkmatter", **map_args)
        else:
            area_fig = px.choropleth_mapbox(area_frame, mapbox_style="carto-darkmatter", **map_args)
        area_fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=560, legend_title=None,
                               paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(area_fig, width="stretch")
    except Exception as exc:
        st.info(f"Service-area map could not be drawn ({exc}).")
    st.dataframe(area_frame[["city", "provider"]], hide_index=True)
    areas_meta = meta.get("service_areas") or {}
    stamped = areas_meta.get("generated_at") or generated_at(areas_doc) or "unknown"
    fetched = areas_meta.get("fetched_at") or "not recorded"
    st.caption(f"Source: [Robotaxi-Tracker service-areas.json](https://github.com/Robotaxi-Tracker/robotaxi-service-areas). "
               f"File generated {stamped}. Cached by the daily collector {fetched}.")

st.divider()
st.subheader("California activity")
st.caption("Quarterly CPUC passenger-service reports, shown by month. "
           "Trips and vehicle miles are activity, lagged to the filing, not a fleet size. "
           "They are not added to the Texas vehicle totals.")
cpuc_doc = load_cpuc()
if not cpuc_doc:
    st.info("California activity file is not available yet. The daily collector stores data/cpuc_activity_monthly.json.")
else:
    monthly = pd.DataFrame(sum_activity(activity_rows(cpuc_doc), "period", "operator"))
    quarterly = pd.DataFrame(sum_activity(activity_rows(cpuc_doc), "quarter", "operator"))
    monthly["period"] = pd.to_datetime(monthly["period"])
    monthly = monthly.sort_values(["period", "operator"])
    quarterly = quarterly.sort_values(["quarter", "operator"])
    latest_quarter = quarterly["quarter"].max()
    quarter_rows = quarterly[quarterly["quarter"] == latest_quarter].sort_values("trips", ascending=False)
    cols = st.columns(max(1, len(quarter_rows)))
    for column, record in zip(cols, quarter_rows.itertuples()):
        column.metric(f"{record.operator} trips", f"{int(round(record.trips)):,}",
                      help="Passenger trips in this quarter. Not a vehicle count.")
    st.caption(f"{latest_quarter}. Separate CPUC programs for the same operator are summed. "
               "That adds drivered and driverless filings, which are different services.")
    left, right = st.columns(2)
    trips = px.line(monthly, x="period", y="trips", color="operator", markers=True)
    trips.update_layout(yaxis_title="Trips", xaxis_title=None, legend_title=None)
    trips.update_yaxes(showgrid=False)
    trips.update_xaxes(showgrid=False)
    left.plotly_chart(trips, width="stretch")
    miles = px.line(monthly, x="period", y="vmt", color="operator", markers=True)
    miles.update_layout(yaxis_title="Vehicle miles", xaxis_title=None, legend_title=None)
    miles.update_yaxes(showgrid=False)
    miles.update_xaxes(showgrid=False)
    right.plotly_chart(miles, width="stretch")
    table = quarterly.sort_values(["quarter", "operator"], ascending=[False, True]).copy()
    table["trips"] = table["trips"].round(0).astype(int)
    table["vmt"] = table["vmt"].round(0).astype(int)
    st.dataframe(table, hide_index=True)
    cpuc_meta = meta.get("cpuc_activity") or {}
    fetched = cpuc_meta.get("fetched_at") or "not recorded"
    st.caption("Source: California Public Utilities Commission AV Program quarterly deployment reports, "
               "monthly aggregate from [AV Observatory](https://av-observatory.com/data/cpuc_activity_monthly.json) "
               f"(public agency data, cited here). Cached by the daily collector {fetched}.")

st.divider()
st.caption("Texas counts are registered vehicles from the TxDMV TxMCCS list, with operator totals cross-checked "
           "against [fsddb.com](https://fsddb.com/robotaxi). Unofficial and not affiliated with Tesla, TxDMV, "
           "fsddb, the CPUC, or AV Observatory. Service areas and California trips are separate feeds.")
