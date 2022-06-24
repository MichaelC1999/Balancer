from utilities.coingecko import get_market_data
from subgrounds.subgrounds import Subgrounds
from streamlit_autorefresh import st_autorefresh
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


with open('./treasuryTokens.json', 'r') as f:
  treasuryTokens = json.load(f)

TREASURY_ADDR = "0x10A19e7eE7d7F8a52822f6817de8ea18204F2e4f"

w3 = Web3(Web3.HTTPProvider('https://eth-mainnet.alchemyapi.io/v2/WYmSY_d_bqG0HEb68q7V322WOVc8rELO'))

# Refresh every 60 seconds
REFRESH_INTERVAL_SEC = 600

# Initialize Subgrounds
sg = Subgrounds()

MAINNET_SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/messari/balancer-v2-ethereum" # messari/balancerV2-ethereum
balancerV2_mainnet = sg.load_subgraph(MAINNET_SUBGRAPH_URL)

MATIC_SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/messari/balancer-v2-polygon" # messari/balancerV2-polygon
balancerV2_matic = sg.load_subgraph(MATIC_SUBGRAPH_URL)

ARBITRUM_SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/messari/balancer-v2-arbitrum" # messari/balancerV2-arbitrum
balancerV2_arbitrum = sg.load_subgraph(ARBITRUM_SUBGRAPH_URL)


VOTE_BAL_SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/balancer-labs/balancer-gauges"
veBAL_Subgraph = sg.load_subgraph(VOTE_BAL_SUBGRAPH_URL)
#  python3.10 -m streamlit run protocols/balancerV2.py 

#####################
##### Streamlit #####
#####################

st.set_page_config(layout="wide")

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

ticker = st_autorefresh(interval=REFRESH_INTERVAL_SEC * 1000, key="ticker")
st.title("balancerV2 Analytics")

st.markdown('CURRENT TAB: ' + str(st.session_state['tab']))

data_loading = st.text(f"[Every {REFRESH_INTERVAL_SEC} seconds] Loading data...")

def format_currency(x):
    return "${:.1f}K".format(x/1000)


def get_top_10_liquidityPools_tvl(liquidityPools_df):

    top_10 = liquidityPools_df.sort_values(by='liquidityPools_totalValueLockedUSD',ascending=False)[:10]
    top_10 = top_10.rename(columns={'liquidityPools_totalValueLockedUSD':'Total Value Locked', 'liquidityPools_name':'Pool'})
    return top_10

def get_top_10_liquidityPools_revenue(liquidityPools_df):
    # st.markdown(str(liquidityPools_df.columns.tolist()))
    top_10 = liquidityPools_df.sort_values(by='liquidityPools_cumulativeTotalRevenueUSD',ascending=False)[:10]
    top_10 = top_10.rename(columns={'liquidityPools_cumulativeTotalRevenueUSD':'Revenues', 'liquidityPools_name':'Pool'})
    return top_10    


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

merge_fin = []
merge_usage = []

mainnet_financial_df = None
mainnet_usage_df = None

# matic_financial_df = None
# matic_usage_df = None

arbitrum_financial_df = None
arbitrum_usage_df = None

financial_df = None
usage_df = None

mainnet_liquidityPools_df = None
# matic_liquidityPools_df = None
arbitrum_liquidityPools_df = None

liquidityPools_df = None

pool_selections = None

revenue_df = None
# veBAL_df = None
veBAL_locked_df = None
veBAL_unlocks_df = None

mainnet_liquidityPools_df = None
# matic_liquidityPools_df = None
arbitrum_liquidityPools_df = None
liquidityPools_df = None
top_10 = None
mainnet_top_10_rev = None
# matic_top_10_rev = None
arbitrum_top_10_rev = None

top_10_rev = None

data_loading.text(f"[Every {REFRESH_INTERVAL_SEC} seconds] Loading data... done!")

scales = alt.selection_interval(bind='scales')
# Create a selection that chooses the nearest point & selects based on x-value

date_axis = alt.X("Date:T", axis=alt.Axis(title=None, format="%Y-%m-%d", labelAngle=45, tickCount=20))
nearest = alt.selection(type='single', nearest=True, on='mouseover',
                        fields=['Date'], empty='none')


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

if st.session_state['tab'] == 'Main':

    mainnet_financial_df = datafields.get_financial_snapshots(balancerV2_mainnet, sg)
    mainnet_usage_df = datafields.get_usage_metrics_df(balancerV2_mainnet, sg)
    merge_fin.append(mainnet_financial_df)
    merge_usage.append(mainnet_usage_df)

    # matic_financial_df = datafields.get_financial_snapshots(balancerV2_matic, sg) 
    # matic_usage_df = datafields.get_usage_metrics_df(balancerV2_matic, sg)
    # merge_fin.append(matic_financial_df)
    # merge_usage.append(matic_usage_df)

    arbitrum_financial_df = datafields.get_financial_snapshots(balancerV2_arbitrum, sg)
    arbitrum_usage_df = datafields.get_usage_metrics_df(balancerV2_arbitrum, sg)
    merge_fin.append(arbitrum_financial_df)
    merge_usage.append(arbitrum_usage_df)

    financial_df = datafields.merge_financials_dfs(merge_fin, sg)
    usage_df = datafields.merge_usage_dfs(merge_usage, sg)

    revenue_df = datafields.get_revenue_df(financial_df, sg)
    # veBAL_df = charts.get_veBAL_df(veBAL_Subgraph)
    veBAL_locked_df = datafields.get_veBAL_locked_df(veBAL_Subgraph, sg)
    veBAL_unlocks_df = datafields.get_veBAL_unlocks_df(veBAL_Subgraph, sg)

    st.header('Protocol Snapshot')
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.subheader(market_data["price"])
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
            '<span style="color:{};"> ({})</span>'.format("${:,.2f}".format(sum(financial_df['Daily Total Revenue'][:30])),which_color(rate_change_rev), '{:.2%}'.format(rate_change_rev))
        st.markdown(text, unsafe_allow_html=True)
        rate_change_rev = (sum(financial_df['Daily Protocol Revenue'][:30])-sum(financial_df['Daily Protocol Revenue'][31:60]))/sum(financial_df['Daily Protocol Revenue'][:30])
        text = '<span style="color:gray;">Total protocol revenue 30d:</span><br>' \
            '<span style="color:black;">{}</span>' \
            '<span style="color:{};"> ({})</span>'.format("${:,.2f}".format(sum(financial_df['Daily Protocol Revenue'][:30])),which_color(rate_change_rev), '{:.2%}'.format(rate_change_rev))
        st.markdown(text, unsafe_allow_html=True)

    with col4:
        st.header('')
        text = '<span style="color:gray;">Annualized total revenue:</span><br><span style="color:black;">{}</span>'.format("${:,.2f}".format(annualize_value(financial_df['Daily Total Revenue'])))
        st.markdown(text, unsafe_allow_html=True)
        text = '<span style="color:gray;">Annualized protocol revenue:</span><br><span style="color:black;">{}</span>'.format("${:,.2f}".format(annualize_value(financial_df['Daily Protocol Revenue'])))
        st.markdown(text, unsafe_allow_html=True)

    with col5:
        st.header('')
        text = '<span style="color:gray;">P/S Ratio:</span><br><span style="color:black;">{}</span>'.format("{:,.2f}".format(revenue_df.iloc[-1]['P/S Ratio']))
        st.markdown(text, unsafe_allow_html=True)
        text = '<span style="color:gray;">P/E Ratio:</span><br><span style="color:black;">{}</span>'.format("{:,.2f}".format(revenue_df.iloc[-1]['P/E Ratio']))
        st.markdown(text, unsafe_allow_html=True)

    with col6:
        st.header('')
        text = '<span style="color:gray;">Total value locked:</span><br><span style="color:black;">{}</span>'.format(market_data['tvl'])
        st.markdown(text, unsafe_allow_html=True)

    st.header('Key Metrics')

    col1, col2, col3 = st.columns(3)

    with col1:
        tvl = charts.build_financial_chart(financial_df, 'Total Value Locked')
        st.altair_chart(tvl, use_container_width=False)

    with col2:
        vol = charts.build_financial_chart(financial_df, 'Daily Volume USD')
        st.altair_chart(vol, use_container_width=False)

    with col3:
        pools = charts.build_financial_chart(usage_df, 'Total Pool Count', y_axis_format=None)
        st.altair_chart(pools, use_container_width=False)

    col1, col2, col3 = st.columns(3)

    with col1:
        daily_swaps = charts.build_financial_chart(usage_df, "Daily Swap Count", y_axis_format=None)
        st.altair_chart(daily_swaps, use_container_width=True)

    with col2:
        daily_supply_revenues = charts.build_financial_chart(financial_df, "Daily Supply Revenue")
        st.altair_chart(daily_supply_revenues, use_container_width=True)

    with col3:
        protocol_treasury = charts.build_financial_chart(financial_df, "Protocol Controlled Value USD", "Protocol Treasury")
        st.altair_chart(protocol_treasury, use_container_width=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        veBAL_locked =  charts.build_financial_chart(veBAL_locked_df, "Locked Balance", "Locked Balance", ".2f")
        st.altair_chart(veBAL_locked, use_container_width=False)
    with col2:
        daily_veBAL_revenues = charts.build_multi_line_veBAL_chart(financial_df)
        st.altair_chart(daily_veBAL_revenues, use_container_width=False)

    with col3:
        # veBAL_unlocks =  charts.build_bar_chart(veBAL_unlocks_df, "Amount To Unlock")
        st.bar_chart(veBAL_unlocks_df[["Amount To Unlock", "Date"]].set_index("Date"), use_container_width=False)

    col1, col2, col3 = st.columns(3)


    with col1:
        base_yield = charts.build_financial_chart(mainnet_financial_df, "Base Yield", "Mainnet LP Yield")
        st.altair_chart(base_yield, use_container_width=True)

    with col2:
        st.markdown('TEMP')
        # base_yield = charts.build_financial_chart(matic_financial_df, "Base Yield", "Matic LP Yield")
        # st.altair_chart(base_yield, use_container_width=True)

    with col3:
        base_yield = charts.build_financial_chart(arbitrum_financial_df, "Base Yield", "Arbitrum LP Yield")
        st.altair_chart(base_yield, use_container_width=True)

    st.header('Quarterly Report')

    quarters = quarterTable.get_quarter_table(financial_df, usage_df)
    st.table(data=quarters)

elif st.session_state['tab'] == 'Liquidity Providers':

    mainnet_withdrawals_30d_df = datafields.get_30d_withdraws(balancerV2_mainnet, sg)
    # matic_withdrawals_30d_df = datafields.get_30d_withdraws(balancerV2_matic, sg)
    arbitrum_withdrawals_30d_df = datafields.get_30d_withdraws(balancerV2_arbitrum, sg)

    withdrawals_30d_df = datafields.merge_dfs([mainnet_withdrawals_30d_df, arbitrum_withdrawals_30d_df], sg, 'Amount')
    if financial_df is None:
        mainnet_financial_df = datafields.get_financial_snapshots(balancerV2_mainnet, sg)
        merge_fin.append(mainnet_financial_df)

        # matic_financial_df = datafields.get_financial_snapshots(balancerV2_matic, sg) 
        # merge_fin.append(matic_financial_df)

        arbitrum_financial_df = datafields.get_financial_snapshots(balancerV2_arbitrum, sg)
        merge_fin.append(arbitrum_financial_df)

        financial_df = datafields.merge_financials_dfs(merge_fin, sg)
    if liquidityPools_df is None:
        mainnet_liquidityPools_df = datafields.get_pools_df(balancerV2_mainnet, sg, 'mainnet')
        # matic_liquidityPools_df = datafields.get_pools_df(balancerV2_matic, sg, 'matic')
        arbitrum_liquidityPools_df = datafields.get_pools_df(balancerV2_arbitrum, sg, 'arbitrum')

        liquidityPools_df = datafields.merge_dfs([mainnet_liquidityPools_df, arbitrum_liquidityPools_df], sg, 'Total Value Locked') 
        top_10 = liquidityPools_df.iloc[:10]
        mainnet_top_10_rev = datafields.get_top_10_liquidityPools_revenue(balancerV2_mainnet, sg)
        # matic_top_10_rev = datafields.get_top_10_liquidityPools_revenue(balancerV2_matic, sg)
        arbitrum_top_10_rev = datafields.get_top_10_liquidityPools_revenue(balancerV2_arbitrum, sg)

        top_10_rev = datafields.merge_dfs([mainnet_top_10_rev, arbitrum_top_10_rev], sg, 'Revenues')
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Top 10 Liquidity Pools by TVL")
        top_10_liquidity_pools = charts.build_pie_chart(top_10, "Total Value Locked", "Pool")
        st.altair_chart(top_10_liquidity_pools, use_container_width=False)

    with col2:
        st.subheader("Largest Depositors")

    with col3:
        st.subheader("Largest Withdraws in Previous 30 days")
        st.dataframe(withdrawals_30d_df[['To', 'Amount', 'Pool']])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Number of LPs")
        # LP_count = charts.build_financial_chart(usage_df, "Total Pool Count")
        # st.altair_chart(LP_count, use_container_width=True)

    with col2:
        st.subheader("Historical Yield")
        historical_yield = charts.build_financial_chart(financial_df, "HistoricalYield")
        st.altair_chart(historical_yield, use_container_width=True)

    with col3:
        st.subheader("Median TVL")


    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Most Concentrated")

    with col2:
        st.subheader("Least Concentrated")

    with col3:
        st.subheader("Number of LPs by chain")

elif st.session_state['tab'] == 'Traders':
    mainnet_swaps_df = datafields.get_swaps_df(balancerV2_mainnet, sg, "amountInUSD")
    # matic_swaps_df = datafields.get_swaps_df(balancerV2_matic, sg, "amountInUSD")
    arbitrum_swaps_df = datafields.get_swaps_df(balancerV2_arbitrum, sg, "amountInUSD")
    swaps_df = datafields.merge_dfs([mainnet_swaps_df, arbitrum_swaps_df], sg, 'Amount In')

    mainnet_14d_swaps_df = datafields.get_14d_swaps_df(balancerV2_mainnet, sg)
    # matic_14d_swaps_df = datafields.get_14d_swaps_df(balancerV2_matic, sg)
    arbitrum_14d_swaps_df = datafields.get_14d_swaps_df(balancerV2_arbitrum, sg)
    swaps_14d_df = datafields.merge_dfs([mainnet_14d_swaps_df, arbitrum_14d_swaps_df], sg, 'Amount In')
    
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Daily Unique Traders")

    with col2:
        st.subheader("Daily Number of Trades")

    with col3:
        st.subheader("MAUs")


    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Largest Pools By Volume 30d")

    with col2:
        st.subheader("Largest Trades 30d")

        st.dataframe(swaps_df[['Date', 'Pool', 'Amount In']][:20])

    with col3:
        st.subheader("Highest Volume Tokens 30d")


    col1, col2, col3 = st.columns(3)

    with col1:
        tx_df = pd.DataFrame({"Amount In": swaps_df.groupby('Date String')["Amount In"].max(), "Date String": swaps_df.groupby('Date String')["Date String"].first()})
        tx_df["Date"] = tx_df["Date String"].apply(lambda x: datetime.strptime(x, "%Y-%m-%d"))
        date_axis = alt.X("Date:T", axis=alt.Axis(title=None, format="%Y-%m-%d", labelAngle=45, tickCount=20))
        bar = alt.Chart(tx_df).mark_bar().encode(
            x=date_axis,
            y='Amount In'
        )
        st.altair_chart(bar, use_container_width=False)
        
    with col2:
        st.subheader("Tx amounts by size pie chart")

    with col3:
        st.subheader("Tx by trader type")

elif st.session_state['tab'] == 'Treasury':

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Treasury Revenues")

    with col2:
        st.subheader("Treasury Value Timeseries")

    with col3:
        st.subheader("Table of tokens in treasury")



    with st.container():
        st.subheader("Treasury Investments/Stakes")


    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("BAL Balance in treasury")

    with col2:
        st.subheader("wstETH/wETH Balance in treasury")

    with col3:
        st.subheader("Stablecoin Balances in treasury")


    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 10 pools by lifetime treasury revenue")

    with col2:
        st.subheader("Barchart weekly withdraws from treasury")

elif st.session_state['tab'] == 'veBAL':

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Timeseries veBAL locked")

    with col2:
        st.subheader("Timeseries veBAL holder revs")

    with col3:
        st.subheader("Barchart veBAL upcoming unlocks")


    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Gauges")

    with col2:
        st.subheader("Top 20 wallets by voting power")

    with col3:
        st.subheader("veBAL gauge rewards")

elif st.session_state['tab'] == 'By Pool':
    mainnet_liquidityPools_df = datafields.get_pools_df(balancerV2_mainnet, sg, 'mainnet')
    # matic_liquidityPools_df = datafields.get_pools_df(balancerV2_matic, sg, 'matic')
    arbitrum_liquidityPools_df = datafields.get_pools_df(balancerV2_arbitrum, sg, 'arbitrum')

    liquidityPools_df = datafields.merge_dfs([mainnet_liquidityPools_df, arbitrum_liquidityPools_df], sg, 'Total Value Locked')

    pool_selections = liquidityPools_df['pool_label'].tolist()

    if 'pool_label' not in st.session_state:
        st.session_state['pool_label'] = pool_selections[0]

    st.selectbox('Select Pool', pool_selections, key='pool_label')


    chain = st.session_state['pool_label'].split(' - ')[2]
    subgraph_to_use = globals()['balancerV2_' + chain]
    pool_data = datafields.get_pool_data_df(subgraph_to_use, sg, st.session_state['pool_label'])
    pool_timeseries = datafields.get_pool_timeseries_df(subgraph_to_use, sg, st.session_state['pool_label'])
    with st.container():
        st.subheader("Pool ENtity data" + str(pool_data['Name'].tolist()[0]))


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
        tvl = charts.build_financial_chart(pool_timeseries, 'Total Value Locked')
        st.altair_chart(tvl, use_container_width=False)
    with col2:
        vol = charts.build_financial_chart(pool_timeseries, 'Daily Volume USD')
        st.altair_chart(vol, use_container_width=False)
    with col3:
        vol = charts.build_financial_chart(pool_timeseries, 'Daily Supply Revenue')
        st.altair_chart(vol, use_container_width=False)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Number of LPs")

    with col2:
        st.subheader("LP Yield")
        base_yield_pool = charts.build_financial_chart(pool_timeseries, 'Base Yield', 'LP Yield')
        st.altair_chart(base_yield_pool, use_container_width=False)
    with col3:
        st.subheader("protocol revenue")
        protocol_rev_from_pool = charts.build_financial_chart(pool_timeseries, 'Daily Protocol Revenue')
        st.altair_chart(protocol_rev_from_pool, use_container_width=False)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Number of traders")

    with col2:
        st.subheader("veBal rewards received")

    with col3:
        st.subheader("Number of swaps")


    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Largest 10 Depositors on pool")

    with col2:
        st.subheader("Largest 10 Traders by volume past 30d")

    with col3:
        st.subheader("donut chart transactions by size over last 30d")

elif st.session_state['tab'] == 'By Chain':
    
    st.selectbox('Select Network', networks, key='network')

    current_financial_df = globals()[st.session_state['network'] + '_financial_df']
    if current_financial_df is None:
        current_financial_df = datafields.get_financial_snapshots(globals()['balancerV2_' + st.session_state['network']], sg)
    
    current_usage_df = globals()[st.session_state['network'] + '_usage_df']
    if current_usage_df is None:
        current_usage_df  = datafields.get_usage_metrics_df(globals()['balancerV2_' + st.session_state['network']], sg)


    col1, col2, col3 = st.columns(3)

    with col1:
        tvl = charts.build_financial_chart(current_financial_df, 'Total Value Locked')
        st.altair_chart(tvl, use_container_width=False)

    with col2:
        vol = charts.build_financial_chart(current_financial_df, 'Daily Volume USD')
        st.altair_chart(vol, use_container_width=False)

    with col3:
        pools = charts.build_financial_chart(current_usage_df, 'Total Pool Count', y_axis_format=None)
        st.altair_chart(pools, use_container_width=False)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Number of LPs")

    with col2:
        LP_revenues = charts.build_financial_chart(current_financial_df, "Daily Supply Revenue", "LP Revenues")
        st.altair_chart(LP_revenues, use_container_width=True)

    with col3:
        LP_yield = charts.build_financial_chart(current_financial_df, "Base Yield", "LP Yield")
        st.altair_chart(LP_yield, use_container_width=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        daily_swaps_by_chain = charts.build_financial_chart(current_usage_df, "Daily Swap Count", "Number of Swaps", y_axis_format=None)
        st.altair_chart(daily_swaps_by_chain, use_container_width=True)

    with col2:
        protocol_rev_by_chain = charts.build_multi_line_rev_chart(datafields.get_revenue_df(current_financial_df, sg))
        st.altair_chart(protocol_rev_by_chain, use_container_width=False)

    with col3:
        st.subheader("vebal rewards received")

elif st.session_state['tab'] == 'By Product':
    st.subheader('BY PRODUCT')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Donut TVL by product")

    with col2:
        st.subheader("Donut Vol by product")

    with col3:
        st.subheader("Donut revenue by product")

    st.selectbox('Pool Types', [])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Timeseries TVL sum of all assets in group")

    with col2:
        st.subheader("Timeseries Vol sum of all assets in group")

    with col3:
        st.subheader("Number of pools in group")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Timeseries #LPs in group")

    with col2:
        st.subheader("Timeseries LP revs in group")

    with col3:
        st.subheader("Timeseries LP yield in group")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Timeseries # swaps in group")

    with col2:
        st.subheader("Timeseries protocol revenues in group")

    with col3:
        st.subheader("veBal rewards received in group")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Donut TVL by pool in group")

    with col2:
        st.subheader("Donut Vol by pool in group")

    with col3:
        st.subheader("Donut revenue by pools in group")
else:
        

    st.header('Financial Statement')

    statement_df = get_financial_statement_df(financial_df)

    st.table(data=statement_df[:10])


    st.header('Financial Metrics')

    col1, col2, col3 = st.columns(3)

    with col1:
        protocol_rev = charts.build_multi_line_rev_chart(revenue_df)
        st.altair_chart(protocol_rev, use_container_width=False)

    with col2:
        ps_ratio = charts.build_financial_chart(revenue_df, 'P/S Ratio', y_axis_format=None)
        st.altair_chart(ps_ratio, use_container_width=False)

    with col3:
        pe_ratio = charts.build_financial_chart(revenue_df, 'P/E Ratio', y_axis_format=None)
        st.altair_chart(pe_ratio, use_container_width=False)

    st.header('Usage Metrics')

    with st.container():
        active = charts.build_financial_chart(usage_df, 'Daily Active Users', y_axis_format=None)
        new = charts.build_financial_chart(usage_df, 'Cumulative New Users', y_axis_format=None)

        st.altair_chart(active | new, use_container_width=False)


    st.header('Live Transactions')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader('Swaps')
        # # Swaps have a different set of fields than deposits/withdraws
        # swaps_df = datafields.get_swaps_df(balancerV2_mainnet, sg, 'Swap')
        # st.dataframe(swaps_df)

    with col2:
        st.subheader('Withdrawals')
        withdrawals_df = datafields.get_events_df(balancerV2_mainnet, sg, 'Withdraw')
        st.dataframe(withdrawals_df)

    with col3:
        st.subheader('Deposits')
        deposits_df = datafields.get_events_df(balancerV2_mainnet, sg, 'Deposit')
        st.dataframe(deposits_df)