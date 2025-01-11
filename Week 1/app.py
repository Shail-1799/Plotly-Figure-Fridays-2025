import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, dcc, callback, Input, Output
import dash
import pandas as pd
import dash_ag_grid as dag
import plotly.express as px
import io
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

app = dash.Dash(__name__)

df = pd.read_csv(r"NYC Marathon Results, 2024 - Marathon Runner Results.csv")


def convert_str_to_time(string):
    count = string.count(":")
   
    if count == 1:
        if "." in string:
            result = datetime.strptime(string, '%M:%S.%f')
        else:
            result = datetime.strptime(string, '%M:%S')
    elif count == 2:
        days_add= None
        h, m, s = string.split(':')
        if int(h)>=24:
            days_add = int(h)//24
        if days_add:
            string = '00' + string[2:]
            if "." in string:
                result = datetime.strptime(string, '%H:%M:%S.%f') + relativedelta(days=days_add)
            else:
                result = datetime.strptime(string, '%H:%M:%S') + relativedelta(days=days_add)
        elif "." in string:
            result = datetime.strptime(string, '%H:%M:%S.%f')
        else:
            result = datetime.strptime(string, '%H:%M:%S')
    midnight = result.replace(hour=0, minute=0, second=0, microsecond=0)
    time_from_midnight = result - midnight
    return round(time_from_midnight.total_seconds()/60, 2)

def get_age_group(age, start=10, end=90, step=10):
    age_groups = [
        {"group": f"{i}-{i + step}", "min_age": i, "max_age": i + step - 1}
        for i in range(start, end, step)
    ]
    age_groups.append({"group": f"{end}+", "min_age": end, "max_age": float("inf")})

    def find_group(single_age):
        for group in age_groups:
            if group["min_age"] <= single_age <= group["max_age"]:
                return group["group"]
        return "Unknown Age Group"

    if isinstance(age, list):
        return [find_group(a) for a in age]
    else:
        return find_group(age)


df["ageGroup"] = get_age_group(df["age"].values.tolist())

filter_cols = [
    "firstName",
    "age",
    "ageGroup",
    "gender",
    "city",
    "countryCode",
    "stateProvince",
    "overallPlace",
    "overallTime",
    "pace",
    "genderPlace",
    "ageGradeTime",
    "ageGradePlace",
    "ageGradePercent",
    "racesCount",
]
df = df[filter_cols]
df = df.dropna()

df['DecimalPace'] = df['pace'].apply(lambda x : convert_str_to_time(x) )

header_names = [
    "Runner Name",
    "Age",
    "Age Group",
    "Gender",
    "City",
    "Country Code",
    "State Province",
    "Overall Place",
    "Overall Time",
    "Pace",
    "Gender Place",
    "Age Grade Time",
    "Age Grade Place",
    "Age Grade Percent",
    "Total Races Run",
]
rename_dict = dict(zip(filter_cols, header_names))

total_participants = len(df)
total_nationalities = df["countryCode"].nunique()
male_participants = len(df[df["gender"] == "M"])
female_participants = len(df[df["gender"] == "W"])


def kpi_card(icon_name, title, value, icon_color, card_color="#ffffff"):
    return dmc.Card(
        shadow="sm",
        radius="md",
        style={
            "width": "24%",
            "height": "100px",
            "textAlign": "center",
            "backgroundColor": card_color,
            "padding": "10px",
        },
        children=dmc.Group(
            [
                DashIconify(
                    icon=icon_name,
                    width=60,
                    height=60,
                    color=icon_color,
                    style={
                        "width": "40%",
                    },
                ),
                dmc.Space(w=5),
                dmc.Stack(
                    [
                        dmc.Text(value, weight=700, style={"font-size": "25px"}),
                        dmc.Text(
                            title, color="grey", weight=500, style={"font-size": "18px"}
                        ),
                    ],
                    spacing=0,
                ),
            ],
        ),
    )


def get_kpi_cards_group(data={}, card_color=False):
    return dmc.Group(
        [
            kpi_card(
                "noto:person-running-facing-right-medium-light-skin-tone",
                "Runners",
                total_participants,
                icon_color="#d20303",
            ),
            kpi_card(
                "gis:search-country",
                "Nationalities",
                total_nationalities,
                icon_color="#ffa500",
            ),
            kpi_card(
                "twemoji:male-sign",
                "Men Runners",
                male_participants,
                icon_color="#119dff",
            ),
            kpi_card(
                "twemoji:female-sign",
                "Women Runners",
                female_participants,
                icon_color="#00bfff",
            ),
        ],
        spacing=20,
        position="apart",
    )


df['Country'] = df["countryCode"].apply(lambda x: 'USA' if x=='USA' else 'Abroad')
fdf = df.groupby(["age", "gender", 'Country']).size().reset_index(name="count")
fdf = fdf[fdf['gender'].isin(['M', 'W'])]

fig1 = px.scatter(
    fdf, 
    x='age', 
    y='count', 
    color='Country',  
    color_discrete_map={"Abroad": "#ef553b", "USA": "#636efa"},

    size='count',     
    facet_col="gender",
    labels={'age': 'Age', 'count': 'No. of Runners', 'Country': 'Country', 'gender':'Gender'},  
)

ddf = df.groupby(["age", "gender", 'Country'])["DecimalPace"].mean().reset_index()
ddf.rename(columns={"DecimalPace": "AvgPace"}, inplace=True)
ddf = ddf[ddf['gender'].isin(['M', 'W'])]
fig2 = px.line(
    ddf.round(2), 
    x='age', 
    y='AvgPace', 
    color='Country',   
    color_discrete_map={"Abroad": "#ef553b", "USA": "#636efa"},
    facet_col="gender",
    labels={'age': 'Age', 'AvgPace': 'Avg Duration (Minutes/Mile)', 'Country': 'Country', 'gender':'Gender'},  
)

ov_layout = html.Div(
    [
        dmc.Space(h=10),
        get_kpi_cards_group(),
        html.H3("Number of Runners Registered by Age: USA vs Abroad"),
        dcc.Graph(figure=fig1),
        html.H3("Avg Duration (Minutes/Mile) of Runners by Age: USA vs Abroad"),
        dcc.Graph(figure=fig2),

        
    ]
)

def get_age_group_chart(gender=None):
    d1_data = df.groupby(["ageGroup", "gender"]).size().reset_index(name="count")
    if gender:
        if isinstance(gender, list):
            d1_data = d1_data[d1_data["gender"].isin(gender)]
        elif isinstance(gender, str):
            d1_data = d1_data[d1_data["gender"] == gender]
    fig = px.bar(
        d1_data,
        x="ageGroup",
        y="count",
        color="gender",
        labels={"ageGroup": "Age Group", "count": "Number of Runners"},
        text="count",
        color_discrete_map={"W": "#ef553b", "M": "#636efa", "X": "#8f8f8f"},
    )
    fig.update_traces(name="Men", selector=dict(name="M"))
    fig.update_traces(name="Women", selector=dict(name="W"))
    fig.update_traces(name="Other", selector=dict(name="X"))
    fig.update_layout(
        title="<b> Runners by Age Group </b>",
        title_font=dict(color="#000000", family="Times New Roman", size=18.72),
        
    )
    # Customize layout
    fig.update_layout(
        xaxis=dict(title="Age Group"),
        yaxis=dict(title="Number of Runners"),
        template="plotly_white",
    )
    return fig
 
 
def get_country_group_chart(gender=None):
    d2_data = df.groupby(["countryCode", "gender"]).size().reset_index(name="count")
    d2_data = d2_data.sort_values(by="count", ascending=False)
    d2_data = d2_data[
        d2_data["countryCode"].isin(d2_data["countryCode"].unique()[:10])
    ].reset_index(drop=True)
    if gender:
        if isinstance(gender, list):
            d2_data = d2_data[d2_data["gender"].isin(gender)]
        elif isinstance(gender, str):
            d2_data = d2_data[d2_data["gender"] == gender]
    fig = px.bar(
        d2_data,
        y="countryCode",
        x="count",
        color="gender",
        orientation="h",
        labels={"countryCode": "Country", "count": "Number of Runners"},
        text="count",
        color_discrete_map={"W": "#ef553b", "M": "#636efa", "X": "#8f8f8f"},
    )
    fig.update_traces(name="Men", selector=dict(name="M"))
    fig.update_traces(name="Women", selector=dict(name="W"))
    fig.update_traces(name="Other", selector=dict(name="X"))
    fig.update_layout(
        title="<b> Top 10 Countries with Most Runners </b>",
        title_font=dict(color="#000000", family="Times New Roman", size=18.72),
        
    )
    # Customize layout
    fig.update_layout(
        
        yaxis=dict(title="Country", categoryorder="total ascending"),
        xaxis=dict(
            title="Number of Runners",
        ),
        template="plotly_white",
    )
    return fig
 
 
def get_avg_pace_chart(gender=None):
    d3_data = df.groupby(["ageGroup", "gender"])["DecimalPace"].mean().reset_index()
    d3_data.rename(columns={"DecimalPace": "AvgPace"}, inplace=True)
    if gender:
        if isinstance(gender, list):
            d3_data = d3_data[d3_data["gender"].isin(gender)]
        elif isinstance(gender, str):
            d3_data = d3_data[d3_data["gender"] == gender]
    fig = px.bar(
        d3_data.round(2),
        y="AvgPace",
        x="ageGroup",
        color="gender",
        labels={"AvgPace": "Avg Pace", "ageGroup": "Age Group"},
        text=f"AvgPace",
        color_discrete_map={"W": "#ef553b", "M": "#636efa", "X": "#8f8f8f"},
    )
    fig.update_traces(name="Men", selector=dict(name="M"))
    fig.update_traces(name="Women", selector=dict(name="W"))
    fig.update_traces(name="Other", selector=dict(name="X"))
    fig.update_layout(
        title="<b> Runners' Avg Pace (Minutes/Mile) by Age Group </b>",
        title_font=dict(color="#000000", family="Times New Roman", size=18.72),
        
    )
 
    # Customize layout
    fig.update_layout(
        yaxis=dict(title="Avg Pace"),
        xaxis=dict(title="Age Group"),
        template="plotly_white",
    )
    return fig
 
 
def get_race_chart(gender=None):
    d4_data = df[["firstName", "racesCount", "gender"]]
    d4_data = d4_data.sort_values(by="racesCount", ascending=True).tail(10)
    if gender:
        if isinstance(gender, list):
            d4_data = d4_data[d4_data["gender"].isin(gender)]
        elif isinstance(gender, str):
            d4_data = d4_data[d4_data["gender"] == gender]
    fig = px.bar(
        d4_data,
        y="firstName",
        x="racesCount",
        orientation="h",
        color="gender",
        labels={"firstName": "Runner Name", "racesCount": "Number of Races"},
        text="racesCount",
        color_discrete_map={"W": "#ef553b", "M": "#636efa", "X": "#8f8f8f"},
    )
    fig.update_traces(name="Men", selector=dict(name="M"))
    fig.update_traces(name="Women", selector=dict(name="W"))
    fig.update_traces(name="Other", selector=dict(name="X"))
    fig.update_layout(
        title="<b> Top 10 Runners with Most Races </b>",
        title_font=dict(color="#000000", family="Times New Roman", size=18.72)
        
    )
    # Customize layout
    fig.update_layout(
        yaxis=dict(title="Runner Name"),
        xaxis=dict(title="Number of Races"),
        template="plotly_white",
    )
    return fig

dem_layout = html.Div(
    [
        dmc.Space(h=10),
        dmc.Group(
            [
                html.H4("Select Gender: "),
                dmc.MultiSelect(
                    id="gender-select",
                    data=[
                        {"label": "Men", "value": "M"},
                        {"label": "Women", "value": "W"},
                        {"label": "Other", "value": "X"},
                    ],
                    clearable=True,
                ),
            ],
            position="center",
        ),
        dmc.Space(h=5),       
        dmc.Group(
            [dcc.Graph(id="age_group_fig"), dcc.Graph(id="country_group_fig")],
            position="apart",
        ),
        
        dmc.Group(
            [dcc.Graph(id="avg_pace_fig"), dcc.Graph(id="race_fig")],
            position="apart",
        ),
    ]
)

tabular_layout = html.Div(
    [
        dmc.Space(h=10),
        dag.AgGrid(
            rowData=df.to_dict("records"),
            columnDefs=[
                {"field": c, "headerName": rename_dict.get(c)} for c in df.columns
            ],
            defaultColDef={
                "wrapText": True,
                "cellStyle": {"wordBreak": "normal", "lineHeight": "unset"},
                "autoHeight": True,
                "wrapHeaderText": True,
                "autoHeaderHeight": True,
                "sortable": True,
                "filter": True,
                "floatingFilter": True,
                "resizable": True,
            },
            style={"height": "540px", "width": "100%"},
        ),
    ]
)


app.layout = html.Div(
    [
        dmc.Group([html.H1("Plotly Figure Friday 2025 - Exploring NYC Marathon Data"), dmc.Button('Export Data', id='export-btn')], position='apart'),
         dcc.Download(id="download-data"),
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.Tab(
                            "Overall Analysis",
                            value="ov",
                            icon=DashIconify(icon="material-symbols:analytics-outline-rounded"),
                        ),
                        dmc.Tab(
                            "Demographic Analysis",
                            value="dem",
                            icon=DashIconify(icon="foundation:results-demographics"),
                        ),
                        dmc.Tab(
                            "Tabular Data",
                            value="tabular",
                            icon=DashIconify(icon="tabler:table"),
                        ),
                    ],
                    grow=True,
                ),
                dmc.TabsPanel(ov_layout, value="ov"),
                dmc.TabsPanel(dem_layout, value="dem"),
                dmc.TabsPanel(tabular_layout, value="tabular"),
            ],
            color="red",
            value="ov",
        ),
    ],
)


@callback(
    Output("age_group_fig", "figure"),
    Output("country_group_fig", "figure"),
    Output("avg_pace_fig", "figure"),
    Output("race_fig", "figure"),
    Input("gender-select", "value"),
)
def update_gender(gender):
    if gender:
        age = get_age_group_chart(gender)
        country = get_country_group_chart(gender)
        pace = get_avg_pace_chart(gender)
        race = get_race_chart(gender)
    else:
        age = get_age_group_chart()
        country = get_country_group_chart()
        pace = get_avg_pace_chart()
        race = get_race_chart()
    return age, country, pace, race


@app.callback(
    Output("download-data", "data"),
    Input("export-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_dataframe(n_clicks):
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)      
    return dcc.send_bytes(csv_buffer.getvalue().encode(), "NYC_marathon_data.csv")

if __name__ == "__main__":
    app.run_server(debug=True)
