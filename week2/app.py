import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
import dash
from dash import html, dcc, callback, Input, Output
import plotly.figure_factory as ff
import plotly.express as px
from datetime import datetime, date
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

from utils import *

pd.set_option("display.max_columns", 200)
pd.set_option("display.max_rows", 200)

df = pd.read_excel(
    r"C:\Users\DLP-I512-03\Desktop\OneDrive - UsefulBI Corporation\Artemis Test Features\Plotly Figure Friday 2025\Week 2\sample_with_coordinates.xlsx"
)
# for c in df.columns:
#     print(c)

df["collected_at_truncated"] = df["collected_at"].apply(
    lambda x: str(x)[:20] if x else x
)
df["product_truncated"] = df["product"].apply(lambda x: str(x)[:20] if x else x)
df["tags"] = df["tags"].apply(lambda x: str(x).replace("_", " ").title() if x else x)
df["tags_truncated"] = df["tags"].apply(lambda x: str(x)[:20] if x else x)
df["lots_truncated"] = df["lot_no"].apply(lambda x: str(x)[:20] if x else x)

distinct_units = ['ng_g', 'ng_serving', 'percent_tdi_14_kg_epa', 'percent_tdi_14_kg_efsa',  'percent_tdi_70_kg_epa', 'percent_tdi_70_kg_efsa', 'percentile_ng_g', 'percentile_ng_serving']


# Ensure dates are in datetime format
date_columns = [
    "manufacturing_date",
    "expiration_date",
    "collected_on",
    "shipped_on",
    "arrived_at_lab_on",
]
for col in date_columns:
    df[col] = pd.to_datetime(df[col], errors="coerce").fillna(
        method="ffill"
    )  # Example: Forward fill missing dates

df["shipping_time"] = (
    df["arrived_at_lab_on"] - df["shipped_on"]
).dt.days  # Shipping time


app = dash.Dash(__name__)

# Category Charts
fig_1_1 = dcc.Graph(figure=top_tags(df))

# Exp Charts
figs = [
    exp_risk_assessment(df, status=s)
    for s in ["Expired", "Critical", "Nearing Expiration", "Safe"]
]
children = [html.Div(dcc.Graph(figure=f[0]), style=f[1]) for f in figs]
fig_2_1 = dmc.Group(children, style={"width": "100%"})

fig_2_2 = treemap_expired_by_tags(df)
fig_2_2 = html.Div(dcc.Graph(figure=fig_2_2))
fig_2_3, style_div = bar_chart_expiring_soon_by_tags(df)
fig_2_3 = html.Div(dcc.Graph(figure=fig_2_3), style=style_div)

# SupChain Charts
fig_3_1 = html.Iframe(srcDoc=folium_map(df), width="100%", height="500px")
fig_3_2 = dcc.Graph(figure=line_chart_shipment_trends(df))
fig_3_3, style_gantt = get_product_timeline_gantt(df)
gantt_chart = html.Div(dcc.Graph(figure=fig_3_3), style=style_gantt)


app.layout = html.Div(
    [
        dmc.Group(
            [
                html.H1(
                    "Plotly Figure Friday 2025 Week 2 - Exploring Data on Plastic Chemicals in Bay Area Foods"
                ),
                dmc.Button("Export Data", id="export-btn"),
            ],
            position="apart",
        ),
        dcc.Download(id="download-data"),
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.Tab(
                            "Sample Collection & Supply Chain Analysis",
                            value="supchain",
                            icon=DashIconify(icon="mdi:truck-outline"),
                        ),
                        dmc.Tab(
                            "Product Test Analysis",
                            value="category",
                            icon=DashIconify(icon="ph:chart-line"),
                        ),
                        dmc.Tab(
                            "Expiration Risk Assessment",
                            value="expiration",
                            icon=DashIconify(icon="mdi:clock-alert-outline"),
                        ),                        
                    ],
                    grow=True,
                ),
                dmc.TabsPanel(
                    html.Div(
                        [
                            html.H3("Sample Collection Locations"),
                            fig_3_1,
                            html.H3("Collection, Shipment & Arrival Trends over Time"),
                            fig_3_2,
                            html.H3(
                                "Product Journey Timeline: Manfufacturing to Lab-Test"
                            ),
                            gantt_chart,
                        ]
                    ),
                    value="supchain",
                ),
                dmc.TabsPanel(
                    html.Div(
                        [
                            html.H3("Sample Test Results"),
                            dmc.Group(
                                [
                                    dmc.Select(
                                        id="product-dropdown",
                                        label="Select Product",
                                        data=df["product"].dropna().unique(),
                                        value="Whole Foods Organic Broccoli",
                                        searchable=True,
                                        style={"width": "40%"},
                                    ),
                                    dmc.Select(
                                        id="id-dropdown",
                                        label="Select Sample ID ",
                                        data=[],
                                        searchable=True,
                                    ),
                                    dmc.Select(
                                        id="unit-dropdown",
                                        label="Select Unit of Measurement (UoM)",
                                        data=distinct_units,
                                        value="ng_g",
                                        searchable=True,
                                        style={"width": "20%"},

                                    ),
                                ],
                                position="apart",
                            ),
                            html.Div(dcc.Graph(id='test-results-fig', figure=test_results(df))),                        
                            html.H3(
                                "Top 15 Most Common Product Tags from Collected Samples"
                            ),
                            fig_1_1,
                            ]
                    ),
                    value="category",
                ),
                dmc.TabsPanel(
                    html.Div(
                        [
                            html.H3(
                                "No. of Days to Expire for Each Product Lot as of Today"
                            ),
                            fig_2_1,
                            dmc.Space(h=30),
                            html.H3(
                                "Top 10 Tags with Most Product Lots Expired as of Today"
                            ),
                            fig_2_2,
                        ]
                    ),
                    value="expiration",
                ),
                
            ],
            color="red",
            value="supchain",
        ),
    ],
)

@callback(
    Output("id-dropdown", "data"),
    Output("id-dropdown", "value"),
    Input("product-dropdown", "value"),
)
def load_sample_id_options(product):
    if product:
        data = df[df['product'] == product]['id'].astype('str').unique()
        return data, data[0] 
    raise dash.exceptions.PreventUpdate


@callback(
    Output("test-results-fig", "figure"),
    Input("product-dropdown", "value"),
    Input("id-dropdown", "value"),
    Input("unit-dropdown", "value"),

)
def load_test_results(product, id, unit):
    if product and id and unit:        
        return test_results(df, product, int(id), unit)
    raise dash.exceptions.PreventUpdate


@app.callback(
    Output("download-data", "data"),
    Input("export-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_dataframe(n_clicks):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)      
    return dcc.send_bytes(csv_buffer.getvalue().encode(), "plasticlist_data.csv")


if __name__ == "__main__":
    app.run_server(debug=False)
