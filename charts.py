import altair as alt
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_echarts import st_pyecharts
from pyecharts import options as opts
import pyecharts
from CustomCharts import CustomLineChart, CustomBarChart, CustomPieChart
from utils import *
from config import *

date_axis = alt.X("Date:T", axis=alt.Axis(title=None, format="%Y-%m-%d", labelAngle=45, tickCount=20))
nearest = alt.selection(type='single', nearest=True, on='mouseover',
                        fields=['Date'], empty='none')


def generate_chart_interactive(df, title, xaxis=None, yaxis="id", xaxis_zoom_start=None, xaxis_zoom_end=None, ccy=None):
    chart = CustomLineChart(
        chart_title=title, xaxis_name="Date", yaxis_name="yaxis"
    )
    if xaxis is None:
        xaxis=df.index
    else:
        xaxis=df[xaxis]


    if xaxis_zoom_end == None:
        xaxis_zoom_end = int(xaxis[len(xaxis)-1])
    if xaxis_zoom_start == None:
        xaxis_zoom_start = int(xaxis[0])

    slider_points = get_xaxis_zoom_range(xaxis, xaxis_zoom_start, xaxis_zoom_end)
    # if ccy == "USD":

    if ccy == 'ETH' and "prices" in df:
        df[yaxis] = df[yaxis].apply(lambda x: float(x))/df["prices"]

    xaxis_data = format_xaxis(xaxis)
    chart.add_xaxis(xaxis_data)
    chart.LINE_CHART.set_global_opts(
        title_opts=chart.DEFAULT_TITLE_OPTS,
        legend_opts=chart.DEFAULT_LEGEND_OPTS,
        tooltip_opts=chart.DEFAULT_TOOLTIP_OPTS,
        toolbox_opts=chart.DEFAULT_TOOLBOX_OPTS,
        xaxis_opts=chart.DEFAULT_XAXIS_OPTS,
        yaxis_opts=chart.DEFAULT_YAXIS_OPTS,
        datazoom_opts= [
        opts.DataZoomOpts(
            range_start=slider_points["start"], 
            range_end=slider_points["end"]
        )])
    chart.add_yaxis(
        color="rgb(74,144,226)",
        series_name=yaxis,
        yaxis_data=df[yaxis].to_list(),
    )
    print(df[yaxis])
    return chart


def build_pie_chart(df, theta, color):
    base = alt.Chart(df).encode(
        theta=alt.Theta(theta+':Q', stack=True),
        color=alt.Color(color+':N', legend=None),
        tooltip=[alt.Tooltip(theta),
                 alt.Tooltip(color)]
    )
    pie = base.mark_arc(outerRadius=110)
    text = base.mark_text(radius=130, size=8).encode(text=color)
    return pie + text

def build_tvl_per_asset_pie(assets_df):
    selection = alt.selection_multi(fields=['Token'], bind='legend')
    pie_chart = alt.Chart(assets_df).mark_arc().encode(
        theta=alt.Theta(field="Total Value Locked", type="quantitative"),
        tooltip=[alt.Tooltip("Total Value Locked"), alt.Tooltip("Token")],
        color=alt.condition(selection, 'Token:N', alt.value('white'))
    ).add_selection(selection).configure_legend(
        titleFontSize=14,
        labelFontSize=10,
        columns=2
    )
    return pie_chart


def build_multi_line_rev_chart(revenue_df):
    sub_df = revenue_df[['Date','Daily Protocol Revenue','Daily Supply Revenue','timestamp']]
    sub_df = sub_df.rename(columns={'Daily Protocol Revenue': 'Protocol', 'Daily Supply Revenue': 'Supply'})
    formatted_df = sub_df.melt(id_vars=['timestamp'], var_name='Side', value_name='Revenue')
    formatted_df['timestamp'] = formatted_df['timestamp']/86400
    chart = generate_chart_interactive(formatted_df, 'Revenue',xaxis='timestamp', yaxis='Revenue')
    return chart

def build_multi_line_veBAL_chart(df):
    sub_df = df[['Date','Daily veBAL Holder Revenue','Cumulative veBAL Holder Revenue','timestamp']]
    sub_df = sub_df.rename(columns={'Daily veBAL Holder Revenue': 'Daily', 'Cumulative veBAL Holder Revenue': 'Cumulative'})
    formatted_df = sub_df.melt(id_vars=['timestamp'], var_name='Side', value_name='Revenue')
    formatted_df['timestamp'] = formatted_df['timestamp']/86400
    chart = generate_chart_interactive(formatted_df, 'Revenue',xaxis='timestamp', yaxis='Revenue')
    return chart
