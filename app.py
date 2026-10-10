import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Texas Robotaxi Fleet Tracker", page_icon="🚕", layout="wide")
st.title("🚕 Texas Robotaxi Fleet Tracker")
st.caption("Tesla Cybercab and Model Y robotaxi counts vs. other operators, from the public Texas DMV AV registry.")

@st.cache_data(ttl=3600)
def load():
    df = pd.read_csv("data/history.csv", parse_dates=["date"])
    return df

df = load()
latest_date = df["date"].max()
EVENTS = [("2026-10-21", "Tesla Q3 earnings"), ("2026-10-30", "NHTSA response due")]

def add_events(fig, xmax):
    for d, label in EVENTS:
        if pd.Timestamp(d) <= xmax + pd.Timedelta(days=30):
            fig.add_vline(x=pd.Timestamp(d).timestamp() * 1000, line_dash="dash", line_color="gray",
                          annotation_text=label, annotation_position="top left")
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
left.plotly_chart(bar, width="stretch")
if ops["date"].nunique() > 1:
    right.plotly_chart(px.line(ops, x="date", y="operator_total", color="operator", markers=True)
                       .update_layout(yaxis_title="Vehicles", xaxis_title=None), width="stretch")
else:
    right.info("Operator trend lines appear once more than one day of data is collected.")

with st.expander("Latest model breakdown / raw data"):
    st.dataframe(last[["operator", "model", "count", "operator_total"]], hide_index=True)
    st.dataframe(df.sort_values("date", ascending=False), hide_index=True)

st.divider()
st.caption("Data: [fsddb.com](https://fsddb.com/robotaxi), which tracks the public Texas DMV Automated Vehicle "
           "registry (TxDMV TxMCCS). Unofficial and not affiliated with Tesla, TxDMV or fsddb. "
           "Counts are registered vehicles, not vehicles in service.")
