import altair as alt
import pandas as pd
import streamlit as st

date_axis = alt.X("Date:T", axis=alt.Axis(title=None, format="%Y-%m-%d", labelAngle=45, tickCount=20))
nearest = alt.selection(type='single', nearest=True, on='mouseover',
                        fields=['Date'], empty='none')

def build_financial_chart(df, column, title=None, y_axis_format='$,.2f',color=None):
    # st.markdown(df.columns.tolist())
    title = column if not title else title
    y_axis = alt.Y(column+":Q", axis=alt.Axis(format=y_axis_format)) if y_axis_format else alt.Y(column+":Q")
    line = alt.Chart(df).mark_line().encode(x=date_axis, y=y_axis, tooltip=[alt.Tooltip("Date")])
    if color:
        line = alt.Chart(df).mark_line().encode(x=date_axis, y=y_axis, tooltip=[alt.Tooltip("Date")],color=color)
    selectors = alt.Chart(df).mark_point().encode(x=date_axis, opacity=alt.value(0),).add_selection(nearest)
    points = line.mark_point().encode(opacity=alt.condition(nearest, alt.value(1), alt.value(0)))
    text = line.mark_text(align='left', dx=5, dy=-5, color='black').encode(text=alt.condition(nearest, column+":Q", alt.value(' ')))
    rules = alt.Chart(df).mark_rule(color='gray').encode(x=date_axis,).transform_filter(nearest)
    line_chart = alt.layer(line, selectors, points, rules, text).interactive().properties(title=title)
    return line_chart


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
    sub_df = revenue_df[['Date','Daily Protocol Revenue','Daily Supply Revenue']]
    sub_df = sub_df.rename(columns={'Daily Protocol Revenue': 'Protocol', 'Daily Supply Revenue': 'Supply'})
    formatted_df = sub_df.melt(id_vars=['Date'], var_name='Side', value_name='Revenue')
    chart = build_financial_chart(formatted_df,  'Revenue', 'Daily Revenue', color='Side')
    return chart

def build_multi_line_veBAL_chart(df):
    sub_df = df[['Date','Daily veBAL Holder Revenue','Cumulative veBAL Holder Revenue']]
    sub_df = sub_df.rename(columns={'Daily veBAL Holder Revenue': 'Daily', 'Cumulative veBAL Holder Revenue': 'Cumulative'})
    formatted_df = sub_df.melt(id_vars=['Date'], var_name='Side', value_name='Revenue')
    chart = build_financial_chart(formatted_df, 'Revenue', 'Daily Revenue', color='Side')
    return chart
