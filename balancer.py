from utilities.coingecko import get_market_data, get_coin_market_chart
from subgrounds.subgrounds import Subgrounds
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
from datetime import datetime
import requests
import streamlit as st
import altair as alt
import pandas as pd
import json
import datafields
import charts
import quarterTable
from web3 import Web3
from streamlit_echarts import st_pyecharts
from utils import *
from config import *
from pyecharts import options as opts
import math

pd.options.display.float_format = '{:.2f}'.format

with open('./treasuryTokens.json', 'r') as f:
  treasuryTokens = json.load(f)

TREASURY_ADDR = '0x10A19e7eE7d7F8a52822f6817de8ea18204F2e4f'

w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.alchemyapi.io/v2/WYmSY_d_bqG0HEb68q7V322WOVc8rELO'))

# Refresh every 60 seconds
REFRESH_INTERVAL_SEC = 600

# Initialize Subgrounds
sg = Subgrounds()

MAINNET_SUBGRAPH_URL = 'https://api.thegraph.com/subgraphs/name/messari/balancer-v2-ethereum' # messari/balancerV2-ethereum
balancerV2_mainnet = sg.load_subgraph(MAINNET_SUBGRAPH_URL)

MATIC_SUBGRAPH_URL = 'https://api.thegraph.com/subgraphs/name/messari/balancer-v2-ethereum' # messari/balancerV2-polygon
balancerV2_matic = sg.load_subgraph(MATIC_SUBGRAPH_URL)

ARBITRUM_SUBGRAPH_URL = 'https://api.thegraph.com/subgraphs/name/messari/balancer-v2-arbitrum' # messari/balancerV2-arbitrum
balancerV2_arbitrum = sg.load_subgraph(ARBITRUM_SUBGRAPH_URL)


VOTE_BAL_SUBGRAPH_URL = 'https://api.thegraph.com/subgraphs/name/balancer-labs/balancer-gauges'
veBAL_Subgraph = sg.load_subgraph(VOTE_BAL_SUBGRAPH_URL)
#  python3.10 -m streamlit run protocols/balancerV2.py 

#####################
##### Streamlit #####
#####################

st.set_page_config(layout='wide')

def time_window_input(key, state_val):
    # Need to format for timezones? State update works however changed input display SHOWS one day before
    window_input = st.container()
    start_val = datetime.datetime.fromtimestamp(int(state_val['window_start'])*86400)
    end_val = datetime.datetime.fromtimestamp(int(state_val['window_end'])*86400)
    now = datetime.datetime.now()
    creation = datetime.datetime(2021, 4, 19)
    with window_input:
        st.date_input('Start', value=start_val, min_value=creation, max_value=now, key=key+'start', on_change=format_calendar_input, args=(key, state_val, 'start'))
        st.date_input('End', value=end_val, min_value=creation, max_value=now, key=key+'end', on_change=format_calendar_input, args=(key, state_val, 'end'))
    return window_input

def format_calendar_input(key, state_val, changed_window):
    new_val=st.session_state[key+changed_window]
    changed_window = 'window_' + changed_window
    state_val[changed_window] = (datetime.datetime.combine(new_val, datetime.datetime.max.time()).timestamp()-43200)/86400
    if state_val['window_start'] > state_val['window_end']:
        end = state_val['window_end']
        state_val['window_end'] = state_val['window_start']
        state_val['window_start'] = end
    set_chart_window(key, state_val['window_start'], state_val['window_end'])
    
def chart_window_input(key, state_val):
    buttons = st.container()
    window_options = ['1D','1W','1M','1Y']
    window_options_index = 0
    window_start=state_val['window_start']
    window_end=state_val['window_end']
    if state_val['window_start'] >= state_val['window_end'] - 1:
        window_options_index = 0
    if state_val['window_start'] >= state_val['window_end'] - 7:
        window_options_index = 1
    if state_val['window_start'] >= state_val['window_end'] - 30:
        window_options_index = 2
    if state_val['window_start'] >= state_val['window_end'] - 365:
        window_options_index = 3

    with buttons:
        st.selectbox("Time Window", window_options, index=window_options_index, key='window'+key, on_change=(lambda: route_chart_window_select(key)))
        time_window_input(key, state_val)
    return buttons

def ccy_selection(state_type, element, state_val):
    current_ccy = state_val['ccy']
    index = ccy_options.index(current_ccy)
    buttons = st.container()
    with buttons:
        st.selectbox("Currency", ccy_options, index=index, key='set_ccy'+state_type+element, on_change=(lambda: set_ccy(state_type,element)))
    return buttons

# Chart states manages the window of time set to look at and the currency denomination
# Window range values are number of days since epoch
# This dictionary is organized like: key: {window_start: 19348, window_end: 19476, ccy: USD}
if 'chart_states' not in st.session_state:
    st.session_state['chart_states'] = {}

if 'table_states' not in st.session_state:
    st.session_state['table_states'] = {}


def set_table_rank_col(table, col):
    state_val = st.session_state['table_states'][table]
    st.session_state['table_states'][table] = {'rank_col': col, 'ccy': state_val['ccy']}

def route_chart_window_select(chart):
    state_val = st.session_state['chart_states'][chart]
    start = state_val['window_start']
    if st.session_state['window' + chart] == '1D':
        start = state_val['window_end'] - 1
    if st.session_state['window' + chart] == '1W':
        start = state_val['window_end'] - 7
    if st.session_state['window' + chart] == '1M':
        start = state_val['window_end'] - 30
    if st.session_state['window' + chart] == '1Y':
        start = state_val['window_end'] - 365
    st.session_state['chart_states'][chart]['window_start'] = start

def set_chart_window(chart, start, end):
    state_val = st.session_state['chart_states'][chart]
    st.session_state['chart_states'][chart] = {'window_start': start, 'window_end': end, 'ccy': state_val['ccy']}

def set_ccy(state_type, element):
    st.session_state[state_type + '_states'][element]['ccy'] = st.session_state['set_ccy'+state_type+element]

def set_agg(key, frame):
    st.session_state['chart_states'][key]['agg'] = frame

def change_tab(tab):
    st.session_state['tab'] = tab

tabs = ['Main', 'Liquidity Providers', 'Traders', 'Treasury', 'veBAL', 'By Pool', 'By Chain', 'By Product']
if 'tab' not in st.session_state:
    st.session_state['tab'] = 'Main'

col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
with col1:
    st.button('Main', on_click=change_tab, args=('Main', ))
with col2:
    st.button('Liquidity Providers', on_click=change_tab, args=('Liquidity Providers', ))
with col3:
    st.button('Traders', on_click=change_tab, args=('Traders', ))
with col4:
    st.button('Treasury', on_click=change_tab, args=('Treasury', ))
with col5:
    st.button('veBAL', on_click=change_tab, args=('veBAL', ))
with col6:
    st.button('By Pool', on_click=change_tab, args=('By Pool', ))
with col7:
    st.button('By Chain', on_click=change_tab, args=('By Chain', ))
with col8:
    st.button('By Product', on_click=change_tab, args=('By Product', ))


networks = ['mainnet', 'polygon', 'arbitrum']
if 'network' not in st.session_state:
    st.session_state['network'] = networks[0]

ticker = st_autorefresh(interval=REFRESH_INTERVAL_SEC * 1000, key='ticker')
st.title('balancerV2 Analytics')

st.markdown('CURRENT TAB: ' + str(st.session_state['tab']))

data_loading = st.text(f'[Every {REFRESH_INTERVAL_SEC} seconds] Loading data...')

def format_currency(x):
    return '${:.1f}K'.format(x/1000)

def get_asset_tvl(liquidityPools_df):
    assets_df = liquidityPools_df.copy()
    for i, row in assets_df.iterrows():
        if row['liquidityPools_inputTokens_name'] == 'Uniswap V2':
            assets_df.loc[i, 'liquidityPools_inputTokens_symbol'] = row['liquidityPools_name'].split('-')[0]
    assets_df = assets_df.groupby(['liquidityPools_inputTokens_id', 'liquidityPools_inputTokens_symbol'])['liquidityPools_totalValueLockedUSD'].sum().reset_index()
    assets_df = assets_df[assets_df['liquidityPools_totalValueLockedUSD'] >= 1.0]
    assets_df = assets_df.rename(columns={'liquidityPools_totalValueLockedUSD': 'Total Value Locked', 'liquidityPools_inputTokens_symbol': 'Token'})
    return assets_df

def get_financial_statement_df(df):
    financial_df = df[['Date']]
    return financial_df

def get_stable_ratio(assets_df):
    stablecoins = ['TUSD','GUSD','USDC','PAX','USDT']
    stable_ratio = assets_df[assets_df['Token'].isin(stablecoins)]['Total Value Locked'].sum() / assets_df['Total Value Locked'].sum()
    stable_ratio_df = pd.DataFrame({'ratio': [stable_ratio, 1-stable_ratio], 'Collateral Type': ['STABLE', 'NON-STABLE']})
    return stable_ratio_df

market_data = get_market_data('balancer')

def has_percent(val):
    return True if '%' in val else False

def format_percent_to_float(val):
    return float(val.strip('%'))

def which_color(val):
    if isinstance(val, str):
        val = format_percent_to_float(val) if has_percent(val) else val
    return 'green' if val > 0 else 'red'

def get_colored_text(val):
    text = '<span id="bottom-right" class="is-display-inline-block is-text-align-right" style="font-family:sans-serif; color:{}; font-size: 18px;">{}</span>'.format(which_color(val),val)
    return text

def annualize_value(val_list):
    num_vals = len(val_list)
    annual_val = (sum(val_list) / num_vals) * 365
    return annual_val

data_loading.text(f'[Every {REFRESH_INTERVAL_SEC} seconds] Loading data... done!')

# veBAL_df = None
veBAL_locked_df = None
veBAL_unlocks_df = None

merge_fin = []
merge_usage = []

mainnet_financial_df = datafields.get_financial_snapshots(balancerV2_mainnet, sg)
mainnet_usage_df = datafields.get_usage_metrics_df(balancerV2_mainnet, sg)
merge_fin.append(mainnet_financial_df)
merge_usage.append(mainnet_usage_df)

matic_financial_df = datafields.get_financial_snapshots(balancerV2_matic, sg) 
matic_usage_df = datafields.get_usage_metrics_df(balancerV2_matic, sg)
merge_fin.append(matic_financial_df)
merge_usage.append(matic_usage_df)

arbitrum_financial_df = datafields.get_financial_snapshots(balancerV2_arbitrum, sg)
arbitrum_usage_df = datafields.get_usage_metrics_df(balancerV2_arbitrum, sg)
merge_fin.append(arbitrum_financial_df)
merge_usage.append(arbitrum_usage_df)

financial_df = datafields.merge_financials_dfs(merge_fin)
usage_df = datafields.merge_usage_dfs(merge_usage)

revenue_df = datafields.get_revenue_df(financial_df)
# veBAL_df = charts.get_veBAL_df(veBAL_Subgraph)
veBAL_locked_df = datafields.get_veBAL_locked_df(veBAL_Subgraph, sg)
veBAL_unlocks_df = datafields.get_veBAL_unlocks_df(veBAL_Subgraph, sg)

mainnet_liquidityPools_df = datafields.get_pools_df(balancerV2_mainnet, sg, 'mainnet')
matic_liquidityPools_df = datafields.get_pools_df(balancerV2_matic, sg, 'matic')
arbitrum_liquidityPools_df = datafields.get_pools_df(balancerV2_arbitrum, sg, 'arbitrum')

liquidityPools_df = datafields.merge_dfs([mainnet_liquidityPools_df, matic_liquidityPools_df, arbitrum_liquidityPools_df], 'Total Value Locked') 

if st.session_state['tab'] == 'Main':

    st.header('Protocol Snapshot')
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.subheader(market_data['price'])
        st.markdown('24h: {}'.format(get_colored_text(market_data['24hr_change'])) + '$~~~~~$ 7d: {}'.format(get_colored_text(market_data['7d_change'])), unsafe_allow_html=True)
        st.markdown('30d: {}'.format(get_colored_text(market_data['30d_change'])) + '$~~~~~$ 1y: {}'.format(get_colored_text(market_data['1y_change'])), unsafe_allow_html=True)

    with col2:
        st.header('')
        text = '<span style="color:gray;">Circulating market cap:</span><br><span style="color:black;">{}</span>'.format(market_data['circ_market_cap'])
        st.markdown(text, unsafe_allow_html=True)
        text = '<span style="color:gray;">Fully-diluted market cap:</span><br><span style="color:black;">{}</span>'.format(market_data['fdv_market_cap'])
        st.markdown(text, unsafe_allow_html=True)

    with col3:
        st.header('')
        rate_change_rev = (sum(financial_df['Daily Total Revenue'][:30])-sum(financial_df['Daily Total Revenue'][31:60]))/sum(financial_df['Daily Total Revenue'][:30])
        text = '<span style="color:gray;">Total revenue 30d:</span><br>' \
            '<span style="color:black;">{}</span>' \
            '<span style="color:{};"> ({})</span>'.format('${:,.2f}'.format(sum(financial_df['Daily Total Revenue'][:30])),which_color(rate_change_rev), '{:.2%}'.format(rate_change_rev))
        st.markdown(text, unsafe_allow_html=True)
        rate_change_rev = (sum(financial_df['Daily Protocol Revenue'][:30])-sum(financial_df['Daily Protocol Revenue'][31:60]))/sum(financial_df['Daily Protocol Revenue'][:30])
        text = '<span style="color:gray;">Total protocol revenue 30d:</span><br>' \
            '<span style="color:black;">{}</span>' \
            '<span style="color:{};"> ({})</span>'.format('${:,.2f}'.format(sum(financial_df['Daily Protocol Revenue'][:30])),which_color(rate_change_rev), '{:.2%}'.format(rate_change_rev))
        st.markdown(text, unsafe_allow_html=True)

    with col4:
        st.header('')
        text = '<span style="color:gray;">Annualized total revenue:</span><br><span style="color:black;">{}</span>'.format('${:,.2f}'.format(annualize_value(financial_df['Daily Total Revenue'])))
        st.markdown(text, unsafe_allow_html=True)
        text = '<span style="color:gray;">Annualized protocol revenue:</span><br><span style="color:black;">{}</span>'.format('${:,.2f}'.format(annualize_value(financial_df['Daily Protocol Revenue'])))
        st.markdown(text, unsafe_allow_html=True)

    with col5:
        st.header('')
        text = '<span style="color:gray;">P/S Ratio:</span><br><span style="color:black;">{}</span>'.format('{:,.2f}'.format(revenue_df.iloc[-1]['P/S Ratio']))
        st.markdown(text, unsafe_allow_html=True)
        text = '<span style="color:gray;">P/E Ratio:</span><br><span style="color:black;">{}</span>'.format('{:,.2f}'.format(revenue_df.iloc[-1]['P/E Ratio']))
        st.markdown(text, unsafe_allow_html=True)

    with col6:
        st.header('')
        text = '<span style="color:gray;">Total value locked:</span><br><span style="color:black;">{}</span>'.format(market_data['tvl'])
        st.markdown(text, unsafe_allow_html=True)

    st.header('Key Metrics')

    col1, col2, col3 = st.columns(3)

    with col1:
        key = 'Total Value Locked'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(financial_df.index[len(financial_df.index)-1])
            xaxis_start = int(financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        tvl1_chart = charts.generate_line_chart(financial_df, key, yaxis=key, xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])

        st_pyecharts(
            chart=tvl1_chart.LINE_CHART,
            height='450px',
            key=key,
        )

    with col2:
        key = 'Daily Volume'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(financial_df.index[len(financial_df.index)-1])
            xaxis_start = int(financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)

        chart = charts.generate_line_chart(financial_df, key, yaxis=key, xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])

        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key=key,
        )

    with col3:
        key = 'Total Pool Count'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(usage_df.index[len(usage_df.index)-1])
            xaxis_start = int(usage_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': None}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)

        chart = charts.generate_line_chart(usage_df, key, yaxis= key, xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])

        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        key = 'Daily Swap Count'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(usage_df.index[len(usage_df.index)-1])
            xaxis_start = int(usage_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': None}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
                
        chart = charts.generate_line_chart(usage_df, key, yaxis=key, xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])

        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )
    with col2:
        key = 'Daily Supply Revenue'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(financial_df.index[len(financial_df.index)-1])
            xaxis_start = int(financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
                
        chart = charts.generate_line_chart(financial_df, key, yaxis=key, xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )
    with col3:
        key = 'Protocol Treasury'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(financial_df.index[len(financial_df.index)-1])
            xaxis_start = int(financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
                
        chart = charts.generate_line_chart(financial_df, key, yaxis='Protocol Controlled Value', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        key = 'Locked Balance'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(veBAL_locked_df['Days'][len(veBAL_locked_df['Days'])-1])
            xaxis_start = int(veBAL_locked_df['Days'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'veBAL'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        veBAL_locked_df = pd.DataFrame({'Locked Balance': veBAL_locked_df.groupby('Days')['Locked Balance'].sum(),'Days': veBAL_locked_df.groupby('Days')['Days'].first()})
        veBAL_locked_df = veBAL_locked_df.set_index("Days")
        chart = charts.generate_line_chart(veBAL_locked_df, key, yaxis=key, xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )
    with col2:
        key = 'veBAL revenues'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(financial_df.index[len(financial_df.index)-1])
            xaxis_start = int(financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)

        daily_veBAL_revenues = charts.generate_combo_chart(financial_df, 'veBAL Holder Revenues', 'Daily veBAL Holder Revenue', 'Cumulative veBAL Holder Revenue', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'])
        st_pyecharts(
            chart=daily_veBAL_revenues.BAR_CHART.overlap(daily_veBAL_revenues.LINE_CHART),
            height='450px',
            key= key,
        )

    with col3:
        # veBAL_unlocks =  charts.build_bar_chart(veBAL_unlocks_df, 'Amount To Unlock')
        key = 'Future unlocks'
        now = int(datetime.datetime.timestamp(datetime.datetime.now()))
        if key not in st.session_state['chart_states']:
            st.session_state['chart_states'][key] = {'window_start': now, 'window_end': now + 365*86400, 'agg': 'D', 'ccy': "veBAL"}
        state_val = st.session_state['chart_states'][key]
        buttons = st.container()
        with buttons:
            st.button('Daily', key=key+'Daily', on_click=set_agg, args=(key,'D'))
            st.button('Weekly', key=key+'Weekly', on_click=set_agg, args=(key,'W'))
            st.button('Monthly', key=key+'Monthly', on_click=set_agg, args=(key,'M'))
        state_val = st.session_state['chart_states'][key]

        if state_val['agg']=='D':            
            veBAL_unlocks_df=pd.DataFrame({"Days": veBAL_unlocks_df.groupby('Days')['Days'].first(), "Date": veBAL_unlocks_df.groupby('Days')['Date'].first(), 'Amount To Unlock': veBAL_unlocks_df.groupby('Days')['Amount To Unlock'].sum().round(2)})
            veBAL_unlocks_df['Date'] = veBAL_unlocks_df['Date'].apply(lambda x: str(x.month) + '-' + str(x.day) + '-' + str(x.year))
        
        elif state_val['agg']=='W':
            veBAL_unlocks_df['Weeks'] = veBAL_unlocks_df['Days'].apply(lambda x: math.ceil(x/7))
            veBAL_unlocks_df=pd.DataFrame({"Weeks": veBAL_unlocks_df.groupby('Weeks')['Weeks'].first(), "Date": veBAL_unlocks_df.groupby('Weeks')['Date'].first(), 'Amount To Unlock': veBAL_unlocks_df.groupby('Weeks')['Amount To Unlock'].sum().round(2)})
            veBAL_unlocks_df['Days']=veBAL_unlocks_df["Weeks"]*7
            veBAL_unlocks_df['Date'] = veBAL_unlocks_df['Date'].apply(lambda x: str(x.month) + '-' + str(x.day) + '-' + str(x.year))
        elif state_val['agg']=='M':
            veBAL_unlocks_df['Month'] = veBAL_unlocks_df['Date'].apply(lambda x: (x.month))
            veBAL_unlocks_df['Date'] = veBAL_unlocks_df['Date'].apply(lambda x: datetime.datetime(x.year, x.month, 1))
            veBAL_unlocks_df['Days'] = veBAL_unlocks_df['Date'].apply(lambda x: math.ceil(int(x.timestamp())/86400))
            veBAL_unlocks_df=pd.DataFrame({"Month": veBAL_unlocks_df.groupby('Month')['Month'].first(), "Days": veBAL_unlocks_df.groupby('Month')['Days'].first(), "Date": veBAL_unlocks_df.groupby('Month')['Date'].first(),'Amount To Unlock': veBAL_unlocks_df.groupby('Month')['Amount To Unlock'].sum().round(2)})
            veBAL_unlocks_df['Date'] = veBAL_unlocks_df['Date'].apply(lambda x: str(x.month) + '-' + str(x.year))
            veBAL_unlocks_df=veBAL_unlocks_df.sort_values('Days', ascending=True)

        # timeAgg = get days/7 round up and save to timeAgg field. Groupby timeAgg field and display the date string
        veBAL_unlocks_df.index = range(1, len(veBAL_unlocks_df) + 1)
        chart = charts.generate_forward_unlock_bar_chart(veBAL_unlocks_df, key, yaxis='Amount To Unlock', xaxis='Days', ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.BAR_CHART,
            height='450px',
            key= key,
        )
        st.dataframe(veBAL_unlocks_df[['Date', 'Amount To Unlock']])


    col1, col2, col3 = st.columns(3)


    with col1:
        key = 'Mainnet LP Yield'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(mainnet_financial_df.index[len(mainnet_financial_df.index)-1])
            xaxis_start = int(mainnet_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': '%'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)

        chart = charts.generate_line_chart(mainnet_financial_df, key, yaxis='Base Yield', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )
    with col2:
        key = 'Matic LP Yield'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(matic_financial_df.index[len(matic_financial_df.index)-1])
            xaxis_start = int(matic_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': '%'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)

        chart = charts.generate_line_chart(matic_financial_df, key, yaxis='Base Yield', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )

    with col3:
        key = 'Arbitrum LP Yield'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(arbitrum_financial_df.index[len(arbitrum_financial_df.index)-1])
            xaxis_start = int(arbitrum_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': '%'}
        
        state_val = st.session_state['chart_states'][key]
        chart_window_input(key, state_val)

        chart = charts.generate_line_chart(arbitrum_financial_df, key, yaxis='Base Yield', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )

    st.header('Quarterly Report')

    quarters = quarterTable.get_quarter_table(financial_df, usage_df)
    st.table(data=quarters)

elif st.session_state['tab'] == 'Liquidity Providers':
    if 'Withdrawls' not in st.session_state['table_states']:
        st.session_state['table_states']['Withdrawls'] = {'rank_col': 'Amount', 'ccy': 'USD'}
    if 'Pool Snaps' not in st.session_state['table_states']:
        st.session_state['table_states']['Pool Snaps'] = {'rank_col': 'Total Value Locked', 'ccy': 'USD'}

    mainnet_withdrawals_30d_df = datafields.get_30d_withdraws(balancerV2_mainnet, sg)
    matic_withdrawals_30d_df = datafields.get_30d_withdraws(balancerV2_matic, sg)
    arbitrum_withdrawals_30d_df = datafields.get_30d_withdraws(balancerV2_arbitrum, sg)

    withdrawals_30d_df = datafields.merge_dfs([mainnet_withdrawals_30d_df, matic_withdrawals_30d_df, arbitrum_withdrawals_30d_df], 'Amount')
    
    now = int(int(datetime.datetime.timestamp(datetime.datetime.now())))
    timestamp_gt_60hrs = now - 60*3600
    timestamp_lt_24hrs = now - 24*3600

    mainnet_24h_pool_snapshots_df = datafields.get_pool_timeseries_df(balancerV2_mainnet, sg, _conditions_list=[balancerV2_mainnet.LiquidityPoolDailySnapshot.timestamp > timestamp_gt_60hrs, balancerV2_mainnet.LiquidityPoolDailySnapshot.timestamp < timestamp_lt_24hrs])
    matic_24h_pool_snapshots_df = datafields.get_pool_timeseries_df(balancerV2_matic, sg, _conditions_list=[balancerV2_matic.LiquidityPoolDailySnapshot.timestamp > timestamp_gt_60hrs, balancerV2_matic.LiquidityPoolDailySnapshot.timestamp < timestamp_lt_24hrs])
    arbitrum_24h_pool_snapshots_df = datafields.get_pool_timeseries_df(balancerV2_arbitrum, sg, _conditions_list=[balancerV2_arbitrum.LiquidityPoolDailySnapshot.timestamp > timestamp_gt_60hrs, balancerV2_arbitrum.LiquidityPoolDailySnapshot.timestamp < timestamp_lt_24hrs])

    all_24h_pool_snapshots_df = datafields.merge_dfs([mainnet_24h_pool_snapshots_df, matic_24h_pool_snapshots_df, arbitrum_24h_pool_snapshots_df], st.session_state['table_states']['Pool Snaps']['rank_col'])

    mainnet_top_10_rev = datafields.get_top_x_liquidityPools(balancerV2_mainnet, sg, 'cumulativeTotalRevenueUSD', 10)
    matic_top_10_rev = datafields.get_top_x_liquidityPools(balancerV2_matic, sg, 'cumulativeTotalRevenueUSD', 10)
    arbitrum_top_10_rev = datafields.get_top_x_liquidityPools(balancerV2_arbitrum, sg, 'cumulativeTotalRevenueUSD', 10)

    top_10_rev = datafields.merge_dfs([mainnet_top_10_rev, matic_top_10_rev, arbitrum_top_10_rev], 'cumulativeTotalRevenueUSD')

    mainnet_top_10_vol = datafields.get_top_x_liquidityPools(balancerV2_mainnet, sg, 'cumulativeVolumeUSD', 10)
    matic_top_10_vol = datafields.get_top_x_liquidityPools(balancerV2_matic, sg, 'cumulativeVolumeUSD', 10)
    arbitrum_top_10_vol = datafields.get_top_x_liquidityPools(balancerV2_arbitrum, sg, 'cumulativeVolumeUSD', 10)

    top_10_vol = datafields.merge_dfs([mainnet_top_10_vol, matic_top_10_vol, arbitrum_top_10_vol], 'cumulativeVolumeUSD')
    col1, col2, col3 = st.columns(3)

    with col1:
        state_val = st.session_state['table_states']['Pool Snaps']
        st.subheader('Top 10 Liquidity Pools by ' +  st.session_state['table_states']['Pool Snaps']['rank_col'] + ' (' + state_val['ccy'] + ')')
        st.button('Total Value Locked', key='Top 10 TVL', on_click=(lambda:set_table_rank_col('Pool Snaps','Total Value Locked')))
        st.button('Daily Volume', key='Top 10 Vol', on_click=(lambda:set_table_rank_col('Pool Snaps','Daily Volume')))
        st.button('Base Yield', key='Top 10 Base Yield', on_click=(lambda:set_table_rank_col('Pool Snaps','Base Yield')))

        ccy_selection('table','Pool Snaps', state_val)

        all_24h_pool_snapshots_df.index = range(1, len(all_24h_pool_snapshots_df) + 1)
        copy_df=all_24h_pool_snapshots_df.copy()
        if state_val['ccy'] in ccy_options:
            copy_df['Total Value Locked'] = all_24h_pool_snapshots_df['Total Value Locked']/all_24h_pool_snapshots_df[state_val['ccy'] + ' prices']
            copy_df['Daily Volume'] = all_24h_pool_snapshots_df['Daily Volume']/all_24h_pool_snapshots_df[state_val['ccy'] + ' prices']

        copy_df = copy_df.sort_values(by=state_val['rank_col'],ascending=False)
        copy_df.index = range(1, len(copy_df) + 1)
        top_10_table = charts.generate_standard_table(copy_df[['Pool Name', 'Total Value Locked', 'Daily Volume', 'Base Yield']][:10])
        st.markdown(top_10_table, unsafe_allow_html=True)

    with col2:
        st.subheader('Largest Depositors')

    with col3:
        state_val = st.session_state['table_states']['Withdrawls']
        st.subheader('Largest Withdraws in Previous 30 days in ' + ' (' + state_val['ccy'] + ')')
        ccy_selection('table','Withdrawls', state_val)

        withdrawals_30d_df.index = range(1, len(withdrawals_30d_df) + 1)
        copy_df=withdrawals_30d_df.copy()
        if state_val['ccy'] in ccy_options:
            copy_df['Amount'] = withdrawals_30d_df['Amount']/withdrawals_30d_df[state_val['ccy'] + ' prices']

        copy_df = copy_df.sort_values(by=state_val['rank_col'],ascending=False)
        copy_df.index = range(1, len(copy_df) + 1)
        largest_withdraws = charts.generate_standard_table(copy_df[['Pool', 'Wallet', 'Amount']][:10])
        st.markdown(largest_withdraws, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Number of LPs')

    with col2:
        key = 'Historical Yield'
        st.subheader(key)
        if key not in st.session_state['chart_states']:
            xaxis_end = int(financial_df.index[len(financial_df.index)-1])
            xaxis_start = int(financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': '%'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
                        
        historical_yield = charts.generate_line_chart(financial_df, key,yaxis='Historical Yield', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=historical_yield.LINE_CHART,
            height='450px',
            key= key,
        )
    with col3:
        st.subheader('Median TVL')


    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Most Concentrated')

    with col2:
        st.subheader('Least Concentrated')

    with col3:
        st.subheader('Number of LPs by chain')

elif st.session_state['tab'] == 'Traders':
    mainnet_swaps_df = datafields.get_swaps_df(balancerV2_mainnet, sg, 'amountInUSD')
    matic_swaps_df = datafields.get_swaps_df(balancerV2_matic, sg, 'amountInUSD')
    arbitrum_swaps_df = datafields.get_swaps_df(balancerV2_arbitrum, sg, 'amountInUSD')
    swaps_df = datafields.merge_dfs([mainnet_swaps_df, matic_swaps_df, arbitrum_swaps_df], 'Amount In')
    
    if 'Largest Trades' not in st.session_state['table_states']:
        xaxis_end = int(int(datetime.datetime.timestamp(datetime.datetime.now()))/86400)
        xaxis_start = xaxis_end - 30
        st.session_state['table_states']['Largest Trades'] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}

    mainnet_largest_swaps_window_df = datafields.get_swaps_df(balancerV2_mainnet, sg, 'amountInUSD', window_start=st.session_state['table_states']['Largest Trades']['window_start']*86400)
    matic_largest_swaps_window_df = datafields.get_swaps_df(balancerV2_matic, sg, 'amountInUSD', window_start=st.session_state['table_states']['Largest Trades']['window_start']*86400)
    arbitrum_largest_swaps_window_df = datafields.get_swaps_df(balancerV2_arbitrum, sg, 'amountInUSD', window_start=st.session_state['table_states']['Largest Trades']['window_start']*86400)
    largest_df = datafields.merge_dfs([mainnet_largest_swaps_window_df, matic_largest_swaps_window_df, arbitrum_largest_swaps_window_df], 'Amount In')    
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Daily Unique Traders')

    with col2:
        st.subheader('Daily Number of Trades')
        
        key = 'Daily Number of Trades'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(usage_df.index[len(usage_df.index)-1])
            xaxis_start = int(usage_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': None}
        
        state_val = st.session_state['chart_states'][key]
        chart_window_input(key, state_val)
        trade_count = charts.generate_line_chart(usage_df, key, yaxis='Daily Swap Count', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])

        st_pyecharts(
            chart=trade_count.LINE_CHART,
            height='450px',
            key=key,
        )

    with col3:
        st.subheader('MAUs')


    col1, col2, col3 = st.columns(3)

    with col1:
        if 'now' not in st.session_state:
            st.session_state['now'] = datetime.datetime.now()
        pools_accounted_for = {}
        timestamp_30d_ago = int(datetime.datetime.timestamp(st.session_state['now'])) - 86400 * 30
        timestamp_25d_ago = int(datetime.datetime.timestamp(st.session_state['now'])) - 86400 * 25
        conditions_list = [balancerV2_mainnet.LiquidityPoolDailySnapshot.timestamp > timestamp_30d_ago, balancerV2_mainnet.LiquidityPoolDailySnapshot.timestamp < timestamp_25d_ago]
        earliest_5d_snapshots_mainnet = datafields.get_pool_timeseries_df(balancerV2_mainnet, sg, _conditions_list=conditions_list)
        
        conditions_list = [balancerV2_arbitrum.LiquidityPoolDailySnapshot.timestamp > timestamp_30d_ago, balancerV2_arbitrum.LiquidityPoolDailySnapshot.timestamp < timestamp_25d_ago]
        earliest_5d_snapshots_arbitrum = datafields.get_pool_timeseries_df(balancerV2_arbitrum, sg, _conditions_list=conditions_list)

        conditions_list = [balancerV2_matic.LiquidityPoolDailySnapshot.timestamp > timestamp_30d_ago, balancerV2_matic.LiquidityPoolDailySnapshot.timestamp < timestamp_25d_ago]
        earliest_5d_snapshots_matic = datafields.get_pool_timeseries_df(balancerV2_matic, sg, _conditions_list=conditions_list)

        earliest_5d_snapshots = datafields.merge_dfs([earliest_5d_snapshots_mainnet, earliest_5d_snapshots_matic, earliest_5d_snapshots_arbitrum], 'timestamp')
        earliest_5d_snapshots = pd.DataFrame({'Pool ID': earliest_5d_snapshots.groupby('Pool ID')['Pool ID'].first(), 'Pool': earliest_5d_snapshots.groupby('Pool ID')['Pool Name'].first(), 'Starting Volume': earliest_5d_snapshots.groupby('Pool ID')['Cumulative Volume USD'].last(), 'Current Volume': 0, 'Volume Difference': 0})
        
        recently_created_mainnet=datafields.get_pools_df(balancerV2_mainnet, sg, chain="mainnet", sort_col='createdTimestamp', _conditions_list=[balancerV2_mainnet.LiquidityPool.createdTimestamp > timestamp_25d_ago])
        recently_created_matic=datafields.get_pools_df(balancerV2_matic, sg, chain="matic", sort_col='createdTimestamp', _conditions_list=[balancerV2_matic.LiquidityPool.createdTimestamp > timestamp_25d_ago])
        recently_created_arbitrum=datafields.get_pools_df(balancerV2_arbitrum, sg, chain="arbitrum", sort_col='createdTimestamp', _conditions_list=[balancerV2_arbitrum.LiquidityPool.createdTimestamp > timestamp_25d_ago])
        
        recently_created = datafields.merge_dfs([recently_created_mainnet, recently_created_matic, recently_created_arbitrum], 'Created Timestamp')
        recently_created = pd.DataFrame({'Pool ID': recently_created.groupby('id')['id'].first(), 'Pool': recently_created.groupby('id')['Pool'].first(), 'Starting Volume': 0, 'Current Volume': recently_created.groupby('id')['Cumulative Volume USD'].max(), 'Volume Difference': 0})
        
        pool_volumes = datafields.merge_dfs([earliest_5d_snapshots,recently_created], 'Current Volume')

        current_pools = pool_volumes['Pool ID'].tolist()

        conditions_list = [balancerV2_mainnet.LiquidityPoolDailySnapshot.timestamp > timestamp_25d_ago, balancerV2_mainnet.LiquidityPoolDailySnapshot.pool.id not in current_pools, balancerV2_mainnet.LiquidityPoolDailySnapshot.dailyVolumeUSD > 50000]
        unchecked_pool_snapshots_mainnet = datafields.get_pool_timeseries_df(balancerV2_mainnet, sg, _conditions_list=conditions_list)
        
        conditions_list = [balancerV2_arbitrum.LiquidityPoolDailySnapshot.timestamp > timestamp_25d_ago, balancerV2_arbitrum.LiquidityPoolDailySnapshot.pool.id not in current_pools, balancerV2_arbitrum.LiquidityPoolDailySnapshot.dailyVolumeUSD > 50000]
        unchecked_pool_snapshots_arbitrum = datafields.get_pool_timeseries_df(balancerV2_arbitrum, sg, _conditions_list=conditions_list)

        conditions_list = [balancerV2_matic.LiquidityPoolDailySnapshot.timestamp > timestamp_25d_ago, balancerV2_matic.LiquidityPoolDailySnapshot.pool.id not in current_pools, balancerV2_matic.LiquidityPoolDailySnapshot.dailyVolumeUSD > 50000]
        unchecked_pool_snapshots_matic = datafields.get_pool_timeseries_df(balancerV2_matic, sg, _conditions_list=conditions_list)

        unchecked_pool_snapshots = datafields.merge_dfs([unchecked_pool_snapshots_mainnet, unchecked_pool_snapshots_matic, unchecked_pool_snapshots_arbitrum], 'timestamp')
        unchecked_pool_snapshots = pd.DataFrame({'Pool ID': unchecked_pool_snapshots.groupby('Pool ID')['Pool ID'].first(),'Pool': unchecked_pool_snapshots.groupby('Pool ID')['Pool Name'].first(),'Starting Volume': unchecked_pool_snapshots.groupby('Pool ID')['Cumulative Volume USD'].last(), 'Current Volume': 0, 'Volume Difference': 0})
        

        current_volume_mainnet=datafields.get_pools_df(balancerV2_mainnet, sg, chain="mainnet", sort_col='cumulativeVolumeUSD', _conditions_list=[])
        current_volume_matic=datafields.get_pools_df(balancerV2_matic, sg, chain="matic", sort_col='cumulativeVolumeUSD', _conditions_list=[])
        current_volume_arbitrum=datafields.get_pools_df(balancerV2_arbitrum, sg, chain="arbitrum", sort_col='cumulativeVolumeUSD', _conditions_list=[])
        
        current_volume = datafields.merge_dfs([current_volume_mainnet, current_volume_matic, current_volume_arbitrum], 'Created Timestamp')
        current_volume = pd.DataFrame({'Pool ID': current_volume.groupby('id')['id'].first(),'Pool': current_volume.groupby('id')['Pool'].first(), 'Starting Volume': current_volume.groupby('id')['Cumulative Volume USD'].max(), 'Current Volume': current_volume.groupby('id')['Cumulative Volume USD'].max(), 'Volume Difference': 0})
        
        pool_volumes = pd.concat([pool_volumes,unchecked_pool_snapshots,current_volume], join='outer', axis=0).fillna(0)
        pool_volumes = pd.DataFrame({
            'Pool ID': pool_volumes.groupby('Pool ID')['Pool ID'].first(),
            'Pool': pool_volumes.groupby('Pool ID')['Pool'].first(),
            'Starting Volume': pool_volumes.groupby('Pool ID')['Starting Volume'].first(),
            'Current Volume': pool_volumes.groupby('Pool ID')['Current Volume'].last(),
            'Volume Difference': 0,
            'USD prices': 1,
            'ETH prices': datafields.get_ccy_current_value('ETH'),
            'BTC prices': datafields.get_ccy_current_value('BTC'),
            'BAL prices': datafields.get_ccy_current_value('BAL')
        })
        
        
        pool_volumes['Volume Difference'] = pool_volumes['Current Volume'] - pool_volumes['Starting Volume']
        
        copy_df = pool_volumes.copy()
        key = 'Pools by Volume Last 30 Days'
        if key not in st.session_state['table_states']:
            st.session_state['table_states'][key] = {'ccy': 'USD'}
        state_val = st.session_state['table_states'][key]
        st.subheader(key)
        ccy_selection('table',key, state_val)

        if state_val['ccy'] in ccy_options:
            copy_df['Volume Difference'] = round(pool_volumes['Volume Difference']/pool_volumes[state_val['ccy'] + ' prices'],2)

        copy_df = copy_df.sort_values('Volume Difference', ascending=False)[:20]
        copy_df.index = range(1, len(copy_df) + 1)
        pools_highest_volume = charts.generate_standard_table(copy_df[['Pool', 'Volume Difference']][:20])        
        st.markdown(pools_highest_volume, unsafe_allow_html=True)

    with col2:
        key = 'Largest Trades'
        state_val = st.session_state['table_states'][key]
        st.subheader(key)
        
        chart_window_input(key, state_val)
        ccy_selection('table',key, state_val)
        largest_df.index = range(1, len(largest_df) + 1)
        amount_col = 'Amount (' + state_val['ccy'] + ')'
        largest_df = largest_df.rename(columns={'Amount In':amount_col, 'Date String': 'Tx Date'})
        copy_df = largest_df.copy()
        if state_val['ccy'] in ccy_options:
            copy_df[amount_col] = round(largest_df[amount_col]/largest_df[state_val['ccy'] + ' prices'],2)


        copy_df = copy_df.sort_values(by=amount_col,ascending=False)
        copy_df.index = range(1, len(copy_df) + 1)
        largest_tx_table = charts.generate_standard_table(copy_df[['Pool', amount_col, 'Tx Date', 'Transaction Hash']][:20])        
        st.markdown(largest_tx_table, unsafe_allow_html=True)

    with col3:
        st.subheader('Highest Volume Tokens 30d')


    col1, col2, col3 = st.columns(3)

    with col1:
        key = 'Transactions Daily Median/High'
        tx_df = pd.DataFrame({'Amount': swaps_df.groupby('Date String')['Amount In'].max(),'Median': swaps_df.groupby('Date String')['Amount In'].median(), 'timestamp': swaps_df.groupby('Date String')['timestamp'].first(), 'Date String': swaps_df.groupby('Date String')['Date String'].first()})
        tx_df['Date'] = tx_df['Date String'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
        tx_df['Days'] = tx_df['timestamp'].apply(lambda x: x/86400)
        if key not in st.session_state['chart_states']:
            xaxis_end = int(tx_df['Days'][len(tx_df['Days'])-1])
            xaxis_start = int(tx_df['Days'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365

            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        chart_window_input(key, state_val)
        tx_by_day_combo = charts.generate_combo_chart(tx_df, key, 'Amount', 'Median', xaxis='Days', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'])
        st_pyecharts(
            chart=tx_by_day_combo.BAR_CHART.overlap(tx_by_day_combo.LINE_CHART),
            height='450px',
            key= key,
        )
        
    with col2:
        st.subheader('Tx amounts by size pie chart')

    with col3:
        st.subheader('Tx by trader type')

elif st.session_state['tab'] == 'Treasury':

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Treasury Revenues')

    with col2:
        st.subheader('Treasury Value Timeseries')

    with col3:
        st.subheader('Table of tokens in treasury')



    with st.container():
        st.subheader('Treasury Investments/Stakes')


    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('BAL Balance in treasury')

    with col2:
        st.subheader('wstETH/wETH Balance in treasury')

    with col3:
        st.subheader('Stablecoin Balances in treasury')


    col1, col2 = st.columns(2)

    with col1:
        st.subheader('Top 10 pools by lifetime treasury revenue')

    with col2:
        st.subheader('Barchart weekly withdraws from treasury')

elif st.session_state['tab'] == 'veBAL':

    col1, col2, col3 = st.columns(3)

    with col1:
        key = 'Locked Balance'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(veBAL_locked_df['Days'][len(veBAL_locked_df['Days'])-1])
            xaxis_start = int(veBAL_locked_df['Days'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'veBAL'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        veBAL_locked_df = pd.DataFrame({'Locked Balance': veBAL_locked_df.groupby('Days')['Locked Balance'].sum(),'Days': veBAL_locked_df.groupby('Days')['Days'].first()})
        veBAL_locked_df = veBAL_locked_df.set_index("Days")
        chart = charts.generate_line_chart(veBAL_locked_df, key, yaxis=key, xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.LINE_CHART,
            height='450px',
            key= key,
        )
    with col2:
        key = 'veBAL revenues'
        if key not in st.session_state['chart_states']:
            xaxis_end = int(financial_df.index[len(financial_df.index)-1])
            xaxis_start = int(financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)

        daily_veBAL_revenues = charts.generate_combo_chart(financial_df, 'veBAL Holder Revenues', 'Daily veBAL Holder Revenue', 'Cumulative veBAL Holder Revenue', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'])
        st_pyecharts(
            chart=daily_veBAL_revenues.BAR_CHART.overlap(daily_veBAL_revenues.LINE_CHART),
            height='450px',
            key= key,
        )

    with col3:
        # veBAL_unlocks =  charts.build_bar_chart(veBAL_unlocks_df, 'Amount To Unlock')
        key = 'Future unlocks'
        now = int(datetime.datetime.timestamp(datetime.datetime.now()))
        if key not in st.session_state['chart_states']:
            st.session_state['chart_states'][key] = {'window_start': now, 'window_end': now + 365*86400, 'agg': 'D', 'ccy': "veBAL"}
        state_val = st.session_state['chart_states'][key]
        buttons = st.container()
        with buttons:
            st.button('Daily', key=key+'Daily', on_click=set_agg, args=(key,'D'))
            st.button('Weekly', key=key+'Weekly', on_click=set_agg, args=(key,'W'))
            st.button('Monthly', key=key+'Monthly', on_click=set_agg, args=(key,'M'))
        state_val = st.session_state['chart_states'][key]

        if state_val['agg']=='D':            
            veBAL_unlocks_df=pd.DataFrame({"Days": veBAL_unlocks_df.groupby('Days')['Days'].first(), "Date": veBAL_unlocks_df.groupby('Days')['Date'].first(), 'Amount To Unlock': veBAL_unlocks_df.groupby('Days')['Amount To Unlock'].sum().round(2)})
            veBAL_unlocks_df['Date'] = veBAL_unlocks_df['Date'].apply(lambda x: str(x.month) + '-' + str(x.day) + '-' + str(x.year))
        
        elif state_val['agg']=='W':
            veBAL_unlocks_df['Weeks'] = veBAL_unlocks_df['Days'].apply(lambda x: math.ceil(x/7))
            veBAL_unlocks_df=pd.DataFrame({"Weeks": veBAL_unlocks_df.groupby('Weeks')['Weeks'].first(), "Date": veBAL_unlocks_df.groupby('Weeks')['Date'].first(), 'Amount To Unlock': veBAL_unlocks_df.groupby('Weeks')['Amount To Unlock'].sum().round(2)})
            veBAL_unlocks_df['Days']=veBAL_unlocks_df["Weeks"]*7
            veBAL_unlocks_df['Date'] = veBAL_unlocks_df['Date'].apply(lambda x: str(x.month) + '-' + str(x.day) + '-' + str(x.year))
        elif state_val['agg']=='M':
            veBAL_unlocks_df['Month'] = veBAL_unlocks_df['Date'].apply(lambda x: (x.month))
            veBAL_unlocks_df['Date'] = veBAL_unlocks_df['Date'].apply(lambda x: datetime.datetime(x.year, x.month, 1))
            veBAL_unlocks_df['Days'] = veBAL_unlocks_df['Date'].apply(lambda x: math.ceil(int(x.timestamp())/86400))
            veBAL_unlocks_df=pd.DataFrame({"Month": veBAL_unlocks_df.groupby('Month')['Month'].first(), "Days": veBAL_unlocks_df.groupby('Month')['Days'].first(), "Date": veBAL_unlocks_df.groupby('Month')['Date'].first(),'Amount To Unlock': veBAL_unlocks_df.groupby('Month')['Amount To Unlock'].sum().round(2)})
            veBAL_unlocks_df['Date'] = veBAL_unlocks_df['Date'].apply(lambda x: str(x.month) + '-' + str(x.year))
            veBAL_unlocks_df=veBAL_unlocks_df.sort_values('Days', ascending=True)

        # timeAgg = get days/7 round up and save to timeAgg field. Groupby timeAgg field and display the date string
        veBAL_unlocks_df.index = range(1, len(veBAL_unlocks_df) + 1)
        chart = charts.generate_forward_unlock_bar_chart(veBAL_unlocks_df, key, yaxis='Amount To Unlock', xaxis='Days', ccy=state_val['ccy'])
        st_pyecharts(
            chart=chart.BAR_CHART,
            height='450px',
            key= key,
        )
        st.dataframe(veBAL_unlocks_df[['Date', 'Amount To Unlock']])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Gauges')

    with col2:
        st.subheader('Top 20 wallets by voting power')
        top_wallets_df = datafields.get_veBAL_top_wallets(veBAL_Subgraph, sg)
        top_wallets_df.index = range(1, len(top_wallets_df) + 1)
        top_wallet_table = charts.generate_standard_table(top_wallets_df[['Address', 'Locked Balance']])
        st.markdown(top_wallet_table, unsafe_allow_html=True)

    with col3:
        st.subheader('veBAL gauge rewards')

elif st.session_state['tab'] == 'By Pool':

    pool_selections = liquidityPools_df['pool_label'].tolist()

    if 'pool_label' not in st.session_state:
        st.session_state['pool_label'] = pool_selections[0]

    st.selectbox('Select Pool', pool_selections, key='pool_label')

    chain = st.session_state['pool_label'].split(' - ')[2]
    subgraph_to_use = globals()['balancerV2_' + chain]

    pool_data = datafields.get_pool_data_df(subgraph_to_use, sg, st.session_state['pool_label'])
    pool = st.session_state['pool_label']
    pool_timeseries = datafields.get_pool_timeseries_df(subgraph_to_use, sg, _conditions_list=[subgraph_to_use.LiquidityPoolDailySnapshot.pool == pool.split(' - ')[1]])
    pool_timeseries['timestamp'] = pool_timeseries['timestamp']/86400

    days_range = 14
    if 'now' not in st.session_state:
        st.session_state['now'] = datetime.datetime.now()
    window_start = int(datetime.datetime.timestamp(st.session_state['now'])) - 86400 * days_range
    swaps_by_range = []
    labels = []
    range_df_100 =datafields.get_swaps_df(subgraph_to_use, sg, 'amountInUSD', window_start=window_start, tx_above=0,tx_below=100, pool_id=pool_data.index.tolist()[0])
    if isinstance(range_df_100, str) is False:
        labels.append("$0-$100")
        swaps_by_range.append(len((range_df_100).index))
    range_df_1000 =datafields.get_swaps_df(subgraph_to_use, sg, 'amountInUSD', window_start=window_start, tx_above=100,tx_below=1000, pool_id=pool_data.index.tolist()[0])
    if isinstance(range_df_1000, str) is False:
        labels.append("$100-$1k")
        swaps_by_range.append(len((range_df_1000).index))
    range_df_10000 =datafields.get_swaps_df(subgraph_to_use, sg, 'amountInUSD', window_start=window_start, tx_above=1000,tx_below=10000, pool_id=pool_data.index.tolist()[0])
    if isinstance(range_df_10000, str) is False:
        labels.append("$1k-$10k")
        swaps_by_range.append(len((range_df_10000).index))
    range_df_over_10000 =datafields.get_swaps_df(subgraph_to_use, sg, 'amountInUSD', window_start=window_start, tx_above=10000, pool_id=pool_data.index.tolist()[0])
    if isinstance(range_df_over_10000, str) is False:
        labels.append(">$10k")
        swaps_by_range.append(len((range_df_over_10000).index))
       
    with st.container():
        st.subheader(str(pool_data['Name'].tolist()[0]))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<br><span style="color:gray;">ID: ' + str(pool_data.index.tolist()[0]) + '</span><br>'+
            '<br><span style="color:gray;">Pool name: ' + str(pool_data['Name'].tolist()[0]) + '</span><br>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            '<br><span style="color:gray;">Chain: ' + chain + '</span><br>',
            unsafe_allow_html=True
        )

    with col3:
        st.markdown('<br><span style="color:gray;">Pool Created:' + str(pool_data['Creation Date'].tolist()[0]) + '</span><br>', unsafe_allow_html=True)        


    col1, col2, col3 = st.columns(3)

    with col1:
        key = 'Total Value Locked ' + str(pool_data['Name'].tolist()[0])
        if key not in st.session_state['chart_states']:
            xaxis_end = int(pool_timeseries['timestamp'][len(pool_timeseries['timestamp'])-1])
            xaxis_start = int(pool_timeseries['timestamp'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)                
        tvl = charts.generate_line_chart(pool_timeseries, key, xaxis='timestamp', yaxis='Total Value Locked', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=tvl.LINE_CHART,
            height='450px',
            key=key,
        )
    with col2:
        key = 'Daily Volume ' + str(pool_data['Name'].tolist()[0])
        if key not in st.session_state['chart_states']:
            xaxis_end = int(pool_timeseries['timestamp'][len(pool_timeseries['timestamp'])-1])
            xaxis_start = int(pool_timeseries['timestamp'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)             
        vol = charts.generate_line_chart(pool_timeseries, key, xaxis='timestamp', yaxis='Daily Volume', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=vol.LINE_CHART,
            height='450px',
            key=key,
        )
    with col3:
        key = 'Daily Supply Revenue ' + str(pool_data['Name'].tolist()[0])
        if key not in st.session_state['chart_states']:
            xaxis_end = int(pool_timeseries['timestamp'][len(pool_timeseries['timestamp'])-1])
            xaxis_start = int(pool_timeseries['timestamp'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        vol = charts.generate_line_chart(pool_timeseries, key, xaxis='timestamp', yaxis='Daily Supply Revenue', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=vol.LINE_CHART,
            height='450px',
            key=key,
        )
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Number of LPs')

    with col2:
        key = 'LP Yield ' + str(pool_data['Name'].tolist()[0])
        if key not in st.session_state['chart_states']:
            xaxis_end = int(pool_timeseries['timestamp'][len(pool_timeseries['timestamp'])-1])
            xaxis_start = int(pool_timeseries['timestamp'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        base_yield_pool = charts.generate_line_chart(pool_timeseries, key, xaxis='timestamp', yaxis='Base Yield', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=base_yield_pool.LINE_CHART,
            height='450px',
            key=key,
        )
    with col3:
        key = 'Daily Protocol Revenue ' + str(pool_data['Name'].tolist()[0])
        if key not in st.session_state['chart_states']:
            xaxis_end = int(pool_timeseries['timestamp'][len(pool_timeseries['timestamp'])-1])
            xaxis_start = int(pool_timeseries['timestamp'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        protocol_rev_from_pool = charts.generate_line_chart(pool_timeseries, key, xaxis='timestamp', yaxis='Daily Protocol Revenue', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=protocol_rev_from_pool.LINE_CHART,
            height='450px',
            key=key,
        )
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Number of traders')

    with col2:
        key = 'Holder Revenue ' + str(pool_data['Name'].tolist()[0])
        if key not in st.session_state['chart_states']:
            xaxis_end = int(pool_timeseries['timestamp'][len(pool_timeseries['timestamp'])-1])
            xaxis_start = int(pool_timeseries['timestamp'][0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        protocol_rev_from_pool = charts.generate_line_chart(pool_timeseries, key, xaxis='timestamp', yaxis="Daily veBAL Holder Revenue", xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=protocol_rev_from_pool.LINE_CHART,
            height='450px',
            key=key,
        )
    with col3:
        st.subheader('Number of swaps')


    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Largest 10 Depositors on pool')

    with col2:
        st.subheader('Largest 10 Traders by volume past 30d')

    with col3:
        if len(swaps_by_range) > 0:
            st.subheader("Transactions By Size (Last 14 days)")
            tx_by_size=charts.generate_donut_chart(labels, swaps_by_range, ['rgb(74, 144, 226)', 'rgb(255, 148, 0)', 'rgb(255, 0, 0)','rgb(99, 210, 142)', 'rgb(6, 4, 4)'])
            st.plotly_chart(tx_by_size, use_container_width=True)
        else:
            st.subheader('No swaps in the last ' + str(days_range) + ' days.')

elif st.session_state['tab'] == 'By Chain':
    
    st.selectbox('Select Network', networks, key='network')

    current_financial_df = globals()[st.session_state['network'] + '_financial_df']
    current_usage_df = globals()[st.session_state['network'] + '_usage_df']

    col1, col2, col3 = st.columns(3)

    with col1:
        key = 'Total Value Locked ' + st.session_state['network']
        if key not in st.session_state['chart_states']:
            xaxis_end = int(current_financial_df.index[len(current_financial_df.index)-1])
            xaxis_start = int(current_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        tvl = charts.generate_line_chart(current_financial_df, key, yaxis='Total Value Locked', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=tvl.LINE_CHART,
            height='450px',
            key=key,
        )
    with col2:
        key = 'Daily Volume ' + st.session_state['network']
        if key not in st.session_state['chart_states']:
            xaxis_end = int(current_financial_df.index[len(current_financial_df.index)-1])
            xaxis_start = int(current_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        vol = charts.generate_line_chart(current_financial_df, key, yaxis='Daily Volume', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=vol.LINE_CHART,
            height='450px',
            key=key,
        )
    with col3:
        key = 'Total Pool Count ' + st.session_state['network']
        if key not in st.session_state['chart_states']:
            xaxis_end = int(current_financial_df.index[len(current_financial_df.index)-1])
            xaxis_start = int(current_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': None}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        pools = charts.generate_line_chart(current_usage_df, key, yaxis='Total Pool Count', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=pools.LINE_CHART,
            height='450px',
            key=key,
        )
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Number of LPs')

    with col2:
        key = 'LP Revenues ' + st.session_state['network']
        if key not in st.session_state['chart_states']:
            xaxis_end = int(current_financial_df.index[len(current_financial_df.index)-1])
            xaxis_start = int(current_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        LP_revenues = charts.generate_line_chart(current_financial_df,key, yaxis='Daily Supply Revenue', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=LP_revenues.LINE_CHART,
            height='450px',
            key=key,
        )
    with col3:
        key = 'LP Yield ' + st.session_state['network']
        if key not in st.session_state['chart_states']:
            xaxis_end = int(current_financial_df.index[len(current_financial_df.index)-1])
            xaxis_start = int(current_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': '%'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        LP_yield = charts.generate_line_chart(current_financial_df, key, yaxis='Base Yield', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=LP_yield.LINE_CHART,
            height='450px',
            key=key,
        )
    col1, col2, col3 = st.columns(3)

    with col1:
        key = 'Number of Swaps ' + st.session_state['network']
        if key not in st.session_state['chart_states']:
            xaxis_end = int(current_financial_df.index[len(current_financial_df.index)-1])
            xaxis_start = int(current_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': None}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        daily_swaps_by_chain = charts.generate_line_chart(current_usage_df, key, yaxis='Daily Swap Count', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=daily_swaps_by_chain.LINE_CHART,
            height='450px',
            key=key,
        )

    with col2:
        key = 'Protocol Revenue ' + st.session_state['network']
        if key not in st.session_state['chart_states']:
            xaxis_end = int(current_financial_df.index[len(current_financial_df.index)-1])
            xaxis_start = int(current_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        protocol_revenue = charts.generate_line_chart(current_financial_df,key, yaxis='Daily Protocol Revenue', xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=protocol_revenue.LINE_CHART,
            height='450px',
            key=key,
        )

    with col3:
        key = 'veBAL Revenue ' + st.session_state['network']
        if key not in st.session_state['chart_states']:
            xaxis_end = int(current_financial_df.index[len(current_financial_df.index)-1])
            xaxis_start = int(current_financial_df.index[0])
            if (xaxis_end - xaxis_start) > 365:
                xaxis_start = xaxis_end - 365
            st.session_state['chart_states'][key] = {'window_start': xaxis_start, 'window_end': xaxis_end, 'ccy': 'USD'}
        
        state_val = st.session_state['chart_states'][key]
        
        chart_window_input(key, state_val)
        ccy_selection('chart',key, state_val)
        protocol_revenue = charts.generate_line_chart(current_financial_df, "veBAL Holder Revenue " + st.session_state['network'], yaxis="Daily veBAL Holder Revenue", xaxis_zoom_start=state_val['window_start'], xaxis_zoom_end=state_val['window_end'], ccy=state_val['ccy'])
        st_pyecharts(
            chart=protocol_revenue.LINE_CHART,
            height='450px',
            key=key,
        )

elif st.session_state['tab'] == 'By Product':
    st.subheader('BY PRODUCT')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Donut TVL by product')

    with col2:
        st.subheader('Donut Vol by product')

    with col3:
        st.subheader('Donut revenue by product')

    st.selectbox('Pool Types', [])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Timeseries TVL sum of all assets in group')

    with col2:
        st.subheader('Timeseries Vol sum of all assets in group')

    with col3:
        st.subheader('Number of pools in group')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Timeseries #LPs in group')

    with col2:
        st.subheader('Timeseries LP revs in group')

    with col3:
        st.subheader('Timeseries LP yield in group')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Timeseries # swaps in group')

    with col2:
        st.subheader('Timeseries protocol revenues in group')

    with col3:
        st.subheader('veBal rewards received in group')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Donut TVL by pool in group')

    with col2:
        st.subheader('Donut Vol by pool in group')

    with col3:
        st.subheader('Donut revenue by pools in group')
