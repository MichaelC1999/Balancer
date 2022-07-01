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


def generate_line_chart(df, title, xaxis=None, yaxis="id", xaxis_zoom_start=None, xaxis_zoom_end=None, ccy=None):
    if ccy is not None:
        title += ' (' + ccy + ')'
    chart = CustomLineChart(
        chart_title=title
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

def generate_forward_unlock_bar_chart(df, title, xaxis=None, yaxis="id", ccy=None):
    chart = CustomBarChart(
        chart_title=title
    )
    if xaxis is None:
        xaxis=df.index
    else:
        xaxis=df[xaxis]

    if ccy == 'ETH' and "prices" in df:
        df[yaxis] = df[yaxis].apply(lambda x: float(x))/df["prices"]

    xaxis_data = format_xaxis(xaxis)
    chart.add_xaxis_bar_chart(xaxis_data)
    chart.DEFAULT_LEGEND_OPTS.update(
        show=False
    )
    chart.BAR_CHART.set_global_opts(
        title_opts=chart.DEFAULT_TITLE_OPTS,
        legend_opts=chart.DEFAULT_LEGEND_OPTS,
        tooltip_opts=chart.DEFAULT_TOOLTIP_OPTS,
        toolbox_opts=chart.DEFAULT_TOOLBOX_OPTS,
        xaxis_opts=chart.DEFAULT_XAXIS_OPTS,
        yaxis_opts=chart.DEFAULT_YAXIS_OPTS,
    )

    chart.add_yaxis_bar_chart(
        color="rgb(74,144,226)",
        series_name=yaxis,
        yaxis_data=df[yaxis].to_list(),
    )
    print(df[yaxis])
    return chart


def generate_combo_chart(df, title, yaxis_bar, yaxis_line, xaxis=None, xaxis_zoom_start=None, xaxis_zoom_end=None, ccy=None):
    chart = CustomBarChart(
        chart_title=title
    )
    if xaxis is None:
        xaxis=df.index
    else:
        xaxis=df[xaxis]

    xaxis_data = format_xaxis(xaxis)

    chart.add_xaxis_bar_chart(xaxis_data=xaxis_data)
    chart.add_xaxis_line_chart(xaxis_data=xaxis_data)
    
    if ccy == 'ETH' and "prices" in df:
        df[yaxis_bar] = df[yaxis_bar].apply(lambda x: float(x))/df["prices"]
        df[yaxis_line] = df[yaxis_line].apply(lambda x: float(x))/df["prices"]
    
    
    chart.add_yaxis_bar_chart(
        series_name=yaxis_bar,
        color="rgb(255,148,0)",
        yaxis_data=df[yaxis_bar].to_list(),
    )

    chart.extend_axis(name="")

    chart.add_yaxis_line_chart(
        series_name=yaxis_line,
        color="rgb(74,144,226)",
        yaxis_data=df[yaxis_line].to_list(),
    )

    if xaxis_zoom_end == None:
        xaxis_zoom_end = int(xaxis[len(xaxis)-1])
    if xaxis_zoom_start == None:
        xaxis_zoom_start = int(xaxis[0])

    slider_points = get_xaxis_zoom_range(xaxis, xaxis_zoom_start, xaxis_zoom_end)

    chart.BAR_CHART.set_global_opts(
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
    
    chart.LINE_CHART.set_global_opts(
        title_opts=chart.DEFAULT_TITLE_OPTS,
        legend_opts=chart.DEFAULT_LEGEND_OPTS,
        tooltip_opts=chart.DEFAULT_TOOLTIP_OPTS,
        toolbox_opts=chart.DEFAULT_TOOLBOX_OPTS,
        xaxis_opts=chart.DEFAULT_XAXIS_OPTS,
        yaxis_opts=chart.DEFAULT_YAXIS_OPTS,
    )

    return chart

def generate_line_chart_multiline(df, title, yaxis, xaxis=None, xaxis_zoom_start=None, xaxis_zoom_end=None, ccy=None):
    
    if len(yaxis) == 1:
        return generate_line_chart(df, title, xaxis, yaxis, xaxis_zoom_start, xaxis_zoom_end, ccy)
    
    chart = CustomLineChart(
        chart_title=title
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

    for line in yaxis:
        if line not in df:
            continue
        if ccy == 'ETH' and "prices" in df:
            df[line] = df[line].apply(lambda x: float(x))/df["prices"]
        chart.add_yaxis(
            color="rgb(74,144,226)",
            series_name=line,
            yaxis_data=df[line].to_list(),
        )
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

