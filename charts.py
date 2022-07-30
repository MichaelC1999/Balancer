import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_echarts import st_pyecharts
from pyecharts import options as opts
import pyecharts
from CustomCharts import CustomLineChart, CustomBarChart, CustomPieChart
import plotly.graph_objects as go
import statistics

from utils import *
from config import *


def generate_line_chart(df, title, xaxis=None, yaxis="id", xaxis_zoom_start=None, xaxis_zoom_end=None, ccy=None):
    df = df.round(2)

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

    if ccy in ccy_options:
        df[yaxis] = df[yaxis].apply(lambda x: float(x))/df[ccy+" prices"]
        df[yaxis] = df[yaxis].apply(lambda x: round(x,2))

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
    df = df.round(2)

    chart = CustomBarChart(
        chart_title=title
    )
    if xaxis is None:
        xaxis=df.index
    else:
        xaxis=df[xaxis]

    if ccy in ccy_options:
        df[yaxis] = df[yaxis].apply(lambda x: float(x))/df[ccy+" prices"]
        df[yaxis] = df[yaxis].apply(lambda x: round(x,2))

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
    df = df.round(2)

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
    
    if ccy in ccy_options:
        df[yaxis_line] = df[yaxis_line].apply(lambda x: float(x))/df[ccy+" prices"]
        df[yaxis_line] = df[yaxis_line].apply(lambda x: round(x,2))
        df[yaxis_bar] = df[yaxis_bar].apply(lambda x: float(x))/df[ccy+" prices"]
        df[yaxis_bar] = df[yaxis_bar].apply(lambda x: round(x,2))

    
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
    df = df.round(2)

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
        if ccy in ccy_options:
            df[line] = df[line].apply(lambda x: float(x))/df[ccy+" prices"]
            df[line] = df[line].apply(lambda x: round(x,2))
        chart.add_yaxis(
            color="rgb(74,144,226)",
            series_name=line,
            yaxis_data=df[line].to_list(),
        )
    return chart

def generate_standard_table(df):
    df = df.round(2)
    html_table='<div class="table-container">' + df.to_html() + '</div>'
    style_css = """
    <style>
        div.table-container {
            width: 100%;
            overflow: scroll;
        }

        table.dataframe {
        width: 100%;
        background-color: rgb(35,58,79);
        border-collapse: collapse;
        border-width: 2px;
        border-color: rgb(17,29,40);
        border-style: solid;
        color: white;
        font-size: 14px;
        }

        table.dataframe td, table.dataframe th {
        text-align: left;
        border-top: 2px rgb(17,29,40) solid;
        border-bottom: 2px rgb(17,29,40) solid;
        padding: 3px;
        white-space:nowrap;
        }

        table.dataframe thead {
            color: rgb(215,215,215);
        background-color: rgb(17,29,40);
        }
    </style>"""
    return style_css + html_table

def generate_donut_chart(labels=[], values=[], colors=['rgb(74, 144, 226)', 'rgb(255, 148, 0)', 'rgb(255, 0, 0)','rgb(99, 210, 142)', 'rgb(6, 4, 4)']):
    return go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5, marker_colors = colors)])

def generate_histogram(df, xaxis=""):
    value_counts = df[xaxis].value_counts()
    counts = df[xaxis].tolist()
    fig = go.Figure(data=[go.Histogram(x=counts,marker_color='rgb(74,144,226)')])
    fig.update_layout(
        plot_bgcolor = "rgb(35,58,79)",
        xaxis_title=xaxis,
        yaxis_title="Frequency",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        # Annotations
        annotations=[
            dict(
                x=sum(counts) / len(counts),
                y=max(value_counts.tolist()),
                text="Mean a = " + str((sum(counts) / len(counts))),
                showarrow=True,
                arrowhead=7,
                ax=1,
                ay=1,
                font=dict(
                    family="Courier New, monospace",
                    size=12,
                    color="#ffffff"
                ),
            ),
            dict(
                x=statistics.median(counts),
                y=(max(value_counts.tolist()) * 0.84),
                text="Median a = " + str((statistics.median(counts))),
                showarrow=True,
                arrowhead=7,
                ax=1,
                ay=1,
                font=dict(
                    family="Courier New, monospace",
                    size=12,
                    color="#ffffff"
                ),
            )
        ],
        showlegend=False,
    )
    fig.add_shape(
        go.layout.Shape(
            type="line",
            xref="x",
            yref="y",
            x0=sum(counts) / len(counts),
            y0=-0.1,
            x1=sum(counts) / len(counts),
            y1=max(value_counts.tolist()),
            line=dict(color='red', width=3, dash='dot'),
        )
    )
    fig.add_shape(
        go.layout.Shape(
            type="line",
            xref="x",
            yref="y",
            x0=statistics.median(counts),
            y0=-0.1,
            x1=statistics.median(counts),
            y1=max(value_counts.tolist()),
            line=dict(color='lime', width=3, dash='dot'),
        )
    )
    return fig