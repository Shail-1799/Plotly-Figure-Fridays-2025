import pandas as pd
import numpy as np
import plotly.figure_factory as ff
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import dash_mantine_components as dmc
import folium
from folium import Choropleth, Circle, Marker
from folium.plugins import HeatMap, MarkerCluster
import math
import io
from collections import Counter


def top_tags(df):
    tag_counts = Counter(
        tag.strip() for tags in df["tags"].dropna() for tag in tags.split(",")
    )

    tdf = pd.DataFrame(tag_counts.items(), columns=["Tag", "Count"]).sort_values(
        by="Count", ascending=False
    )

    fig = px.bar(
        tdf.head(15),
        y="Count",
        x="Tag",
        text="Count",
    )

    fig.update_layout(
        margin=dict(b=0, t=0, r=10, l=10),
    )

    return fig


def get_product_timeline_gantt(df):
    gantt_data = []
    for _, row in df.iterrows():
        gantt_data.append(
            {
                "Task": row["product_truncated"],
                "Start": row["manufacturing_date"],
                "Finish": row["collected_on"],
                "Stage": "Manufacturing to Collection",
            }
        )
        gantt_data.append(
            {
                "Task": row["product_truncated"],
                "Start": row["collected_on"],
                "Finish": row["shipped_on"],
                "Stage": "Collection to Shipment",
            }
        )
        gantt_data.append(
            {
                "Task": row["product_truncated"],
                "Start": row["shipped_on"],
                "Finish": row["arrived_at_lab_on"],
                "Stage": "Shipment to Arrival",
            }
        )

    gantt_df = pd.DataFrame(gantt_data)

    fig_gantt = ff.create_gantt(
        gantt_df,
        title="",
        index_col="Stage",
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True,
        height=max(
            600, 40 * gantt_df["Task"].nunique()
        ),  # Dynamic height based on tasks
    )

    fig_gantt.update_layout(
        margin=dict(b=20, t=0, r=10, l=10),  
        xaxis=dict(side="top"),  
        legend=dict(
            orientation="h", yanchor="bottom", y=1.005, xanchor="center", x=0.5
        ), 
    )

    style_gantt = (
        {}
        if gantt_df["Task"].nunique() <= 15
        else {"max-height": "400px", "overflow-y": "auto"}
    )

    return fig_gantt, style_gantt


def treemap_tags_products(df):
    df["lot_no"].fillna("No Lot Data")
    df_grouped = (
        df.groupby(["tags", "product", "lot_no"])
        .size()
        .reset_index(name="count")
        .sort_values(by="count", ascending=False)
    )

    fig = px.treemap(
        df_grouped,
        path=[
            px.Constant("All"),
            "tags",
            "product",
            "lot_no",
        ],  
        values="count",  
        color="count",
        labels={
            "tags": "Tags",
            "product": "Product",
            "count": "Count",
            "lot_no": "Lot No.",
        },
        height=500,
        maxdepth=2,
    )

    return fig


def line_chart_shipment_trends(df):
    
    df_collected = (
        df.groupby(df["collected_on"].dt.date)
        .size()
        .reset_index(name="collected_count")
    )
    df_shipped = (
        df.groupby(df["shipped_on"].dt.date).size().reset_index(name="shipped_count")
    )
    df_arrived = (
        df.groupby(df["arrived_at_lab_on"].dt.date).size().reset_index(name="arrived_count")
    )

    fig = go.Figure()

    # Collected trace
    fig.add_trace(
        go.Scatter(
            x=df_collected["collected_on"],
            y=df_collected["collected_count"],
            mode="lines+markers",
            name="Collected",
            line=dict(color="red"),
        )
    )

    # Shipped trace
    fig.add_trace(
        go.Scatter(
            x=df_shipped["shipped_on"],
            y=df_shipped["shipped_count"],
            mode="lines+markers",
            name="Shipped",
            line=dict(color="blue"),
        )
    )

    # Arrived trace
    fig.add_trace(
        go.Scatter(
            x=df_arrived["arrived_at_lab_on"],
            y=df_arrived["arrived_count"],
            mode="lines+markers",
            name="Arrived",
            line=dict(color="green"),
        )
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Samples",
        margin=dict(b=40, t=40, r=0, l=0),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.005, xanchor="center", x=0.5
        ), 
    )

    return fig


def get_exp_status(d):
    if d < 0:
        return "Expired"
    if d <= 30:
        return "Critical"
    if d <= 90:
        return "Nearing Expiration"
    if d <= 180:
        return "Safe"


color_dict = {
    "Expired": "Grey",
    "Critical": "#fc3737",
    "Nearing Expiration": "#fcc521",
    "Safe": "#57ca45",
}


def exp_risk_assessment(df, status, exp_date=pd.Timestamp.today()):
    df = df.dropna(subset=["lots_truncated", "lot_no", "product_truncated"])
    df["days_to_expire"] = (df["expiration_date"] - exp_date).dt.days
    df["exp_status"] = df["days_to_expire"].apply(
        lambda x: get_exp_status(x) if x else None
    )
    df = df[df["exp_status"] == status]
    df = df.sort_values(by="days_to_expire", ascending=False)

    fig = px.bar(
        df,
        y="lots_truncated",
        x="days_to_expire",
        orientation="h",
        text=[f"{d} Days" for d in df["days_to_expire"]],
        color="exp_status",
        color_discrete_map=color_dict,
        hover_data=["product"],
        labels={
            "lots_truncated": "Lot No.",
            "days_to_expire": "Days to Expire",
            "product_truncated": "Product",
        },
        barmode="group",
        height=max(400, 40 * len(df)),
    )
    fig.update_layout(
        title=f"<b>{status}<b>",
        title_font=dict(color="#000000", family="Times New Roman", size=16),
        margin=dict(b=40, t=40, r=0, l=0),
        showlegend=False,
    )

    style_div = (
        {"width": "24%"}
        if len(df) <= 10
        else {"width": "24%", "max-height": "400px", "overflow-y": "auto"}
    )

    return fig, style_div


def bar_chart_expiring_soon_by_tags(df, exp_date=pd.Timestamp.today()):
    df["days_to_expire"] = (df["expiration_date"] - exp_date).dt.days

    df_expiring_soon = df[(df["days_to_expire"] >= 0)]
    df_expiring_soon = (
        df_expiring_soon.groupby("tags_truncated")["product_truncated"]
        .size()
        .reset_index(name="count")
    )
    df_expiring_soon = df_expiring_soon.sort_values(by="count")

    # For text lables
    df_expiring_soon["text_label"] = (
        df_expiring_soon["count"].astype("str") + " Products"
    )

    fig = px.bar(
        df_expiring_soon,
        y="tags_truncated",
        x="count",
        orientation="h",
        text="text_label",
        labels={"tags_truncated": "Tags", "count": "Count"},
        barmode="group",
        height=max(400, 40 * len(df_expiring_soon)),
    )

    style_div = {} if len(df) <= 10 else {"max-height": "400px", "overflow-y": "auto"}

    fig.update_layout(
        margin=dict(b=0, t=0, r=10, l=10),
    )

    return fig, style_div


def treemap_expired_by_tags(df, exp_date=pd.Timestamp.today()):
    df["days_to_expire"] = (df["expiration_date"] - exp_date).dt.days

    df_expiring_soon = df[df["days_to_expire"] < 0].copy()

    df_expiring_soon["lot_no"].fillna("No Data", inplace=True)

    df_grouped = (
        df_expiring_soon.groupby(["tags_truncated", "product_truncated"])["lot_no"]
        .nunique()
        .reset_index(name="lot_count")
    )

    # Get the top 10 tags based on total expired lots
    top_tags = (
        df_grouped.groupby("tags_truncated")["lot_count"].sum().nlargest(10).index
    )
    df_filtered = df_grouped[df_grouped["tags_truncated"].isin(top_tags)]

    fig = px.treemap(
        df_filtered,
        path=[
            px.Constant("All 10"),
            "tags_truncated",
            "product_truncated",
        ], 
        values="lot_count",
        labels={
            "tags_truncated": "Tags",
            "product_truncated": "Product",
            "lot_count": "Expired Lots",
            "lot_count_sum": "Total Expired Lots",
        },
        height=500,
        maxdepth=3,
    )

    fig.update_traces(
        texttemplate="%{label}<br>Expired Lots: %{value}", textinfo="label+text"
    )
    fig.update_layout(
        margin=dict(b=0, t=0, r=10, l=10),
    )

    return fig


def folium_map(df):
    cdf = df[["collected_at", "location_lat_lon", "latitude", "longitude"]]
    cdf.dropna(inplace=True)

    m_3 = folium.Map(
        location=[37.48228115, -122.23169528052277],
        tiles="cartodbpositron",
        zoom_start=4,
    )

    mc = MarkerCluster()
    for idx, row in cdf.iterrows():
        if not math.isnan(row["latitude"]) and not math.isnan(row["longitude"]):
            mc.add_child(Marker([row["latitude"], row["longitude"]]))
    m_3.add_child(mc)

    map_bytes = io.BytesIO()
    m_3.save(map_bytes, close_file=False)
    map_html = map_bytes.getvalue().decode("utf-8")  
    return map_html


def convert_str_to_int(string):
    if isinstance(string, str):
        if string.startswith("<"):
            if "LOQ" in string:
                return 0.001
            elif string[1:].isdigit():
                return int(string[1:])
        elif "." in string:
            if string.replace(".", "").isdigit():
                return float(string)
        elif string.isdigit():
            try:
                string = int(string)
            except:
                string = float(string)
            return string
        elif string == "NO RfD" or string == "NO TDI":
            return np.nan
    return string


chemicals = [
    "DEHP_equivalents",
    "DEHP",
    "DBP",
    "BBP",
    "DINP",
    "DIDP",
    "DEP",
    "DMP",
    "DIBP",
    "DNHP",
    "DCHP",
    "DNOP",
    "BPA",
    "BPS",
    "BPF",
    "DEHT",
    "DEHA",
    "DINCH",
    "DIDA",
]


def test_results(
    df, product="Whole Foods Organic Broccoli", sample_id=7091002, unit="ng_serving"
):

    df = df[(df["product"] == product) & (df["id"] == sample_id)]

    df = df[[c for c in df.columns if unit in c]]
    df.columns = [c.replace(f"_{unit}", "") for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("percentile", case=False)]

    df = df.T.reset_index()
    df.columns = ["chemical", "labels"]

    df["values"] = df["labels"].apply(lambda x: convert_str_to_int(x))

    fig = px.bar(
        df,
        x="chemical",
        y="values",
        text="labels",
        color="values",
        color_continuous_scale="RdYlGn_r",
    )

    fig.update_layout(
        xaxis_title="Chemical",
        yaxis_title=f"Concentration in {unit}",
        coloraxis_showscale=False,
        margin=dict(b=20, t=30, r=10, l=10),
    )
    return fig
