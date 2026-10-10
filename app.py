import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

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
           "per-model counts start Oct 9. Daily exact snapshots follow.")

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
    st.dataframe(last[["operator", "model", "count", "operator_total"]], hide_index=True)
    st.dataframe(df.sort_values("date", ascending=False), hide_index=True)

st.divider()
st.caption("Data: [fsddb.com](https://fsddb.com/robotaxi), which tracks the public Texas DMV Automated Vehicle "
           "registry (TxDMV TxMCCS). Unofficial and not affiliated with Tesla, TxDMV or fsddb. "
           "Counts are registered vehicles, not vehicles in service.")
