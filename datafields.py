from subgrounds.subgrounds import Subgrounds
import subgrounds.subgraph
import json
import random
from utils import *

from datetime import datetime
import pandas as pd
import streamlit as st
from utilities.coingecko import get_coin_market_cap, get_coin_market_chart

ETH_HISTORY = get_coin_market_chart('ethereum')
ETH_HISTORY_DF = pd.DataFrame(ETH_HISTORY['prices'], columns=['timestamp', 'ETH prices'])[:-1]
ETH_HISTORY_DF['Days'] = (ETH_HISTORY_DF['timestamp']/86400000).astype(int)
ETH_HISTORY_DF=ETH_HISTORY_DF.set_index('Days')
ETH_LATEST_VALUE = ETH_HISTORY_DF.iloc[-1]['ETH prices']

BTC_HISTORY = get_coin_market_chart('bitcoin')
BTC_HISTORY_DF = pd.DataFrame(BTC_HISTORY['prices'], columns=['timestamp', 'BTC prices'])[:-1]
BTC_HISTORY_DF['Days'] = (BTC_HISTORY_DF['timestamp']/86400000).astype(int)
BTC_HISTORY_DF=BTC_HISTORY_DF.set_index('Days')
BTC_LATEST_VALUE = BTC_HISTORY_DF.iloc[-1]['BTC prices']

BAL_HISTORY = get_coin_market_chart('balancer')
BAL_HISTORY_DF = pd.DataFrame(BAL_HISTORY['prices'], columns=['timestamp', 'BAL prices'])[:-1]
BAL_HISTORY_DF['Days'] = (BAL_HISTORY_DF['timestamp']/86400000).astype(int)
BAL_HISTORY_DF=BAL_HISTORY_DF.set_index('Days')
BAL_LATEST_VALUE = BAL_HISTORY_DF.iloc[-1]['BAL prices']

USD_LATEST_VALUE = 1

def get_ccy_current_value(ccy):
    return globals()[ccy+'_LATEST_VALUE']

@st.experimental_memo
def get_financial_snapshots(_subgraph, _sg):
    financialSnapshot = _subgraph.Query.financialsDailySnapshots(
    orderBy=_subgraph.FinancialsDailySnapshot.timestamp,
    orderDirection='desc',
    first=1000
    )
    df = _sg.query_df([
      financialSnapshot.id,
      financialSnapshot.totalValueLockedUSD,
      financialSnapshot.protocolControlledValueUSD,
      financialSnapshot.dailyVolumeUSD,
      financialSnapshot.cumulativeVolumeUSD,
      financialSnapshot.dailySupplySideRevenueUSD,
      financialSnapshot.cumulativeSupplySideRevenueUSD,
      financialSnapshot.dailyProtocolSideRevenueUSD,
      financialSnapshot.cumulativeProtocolSideRevenueUSD,
      financialSnapshot.dailyTotalRevenueUSD,
      financialSnapshot.cumulativeTotalRevenueUSD,
      financialSnapshot.timestamp
    ])
    df['Date'] = df['financialsDailySnapshots_id'].apply(lambda x: datetime.utcfromtimestamp(int(x)*86400))
    df = df.rename(columns={
        'financialsDailySnapshots_dailyTotalRevenueUSD':'Daily Total Revenue',
        'financialsDailySnapshots_dailySupplySideRevenueUSD':'Daily Supply Revenue',
        'financialsDailySnapshots_dailyProtocolSideRevenueUSD':'Daily Protocol Revenue',
        'financialsDailySnapshots_totalValueLockedUSD':'Total Value Locked',
        'financialsDailySnapshots_protocolControlledValueUSD':'Protocol Controlled Value',
        'financialsDailySnapshots_dailyVolumeUSD':'Daily Volume',
        'financialsDailySnapshots_cumulativeSupplySideRevenueUSD':'Cumulative Supply Side Revenue',
        'financialsDailySnapshots_cumulativeProtocolSideRevenueUSD':'Cumulative Protocol Side Revenue',
        'financialsDailySnapshots_timestamp':'timestamp'
        })
    df['id'] = df['financialsDailySnapshots_id']
    df['Days'] = df['financialsDailySnapshots_id'].astype(int)
    df["Daily veBAL Holder Revenue"] = df["Daily Protocol Revenue"] * .75
    df["Cumulative veBAL Holder Revenue"] = df['Cumulative Protocol Side Revenue'] * .75
    df['Historical Yield'] = df['Total Value Locked']/df['Daily Total Revenue']
    df["Base Yield"] = df["Daily Supply Revenue"]/df["Total Value Locked"] * 100
    df = df.iloc[::-1]

    df['USD prices'] = 1
    df = df.join(ETH_HISTORY_DF['ETH prices'], on="Days")
    df = df.join(BTC_HISTORY_DF['BTC prices'], on="Days")
    df = df.join(BAL_HISTORY_DF['BAL prices'], on="Days")

    df = df.set_index("id")
    return df

@st.cache(allow_output_mutation=True)
def merge_financials_dfs(_dfs):
    df_return = pd.concat(_dfs, join='outer', axis=0).fillna(0)
    df_return = df_return.groupby('id').sum()
    df_return['USD prices'] = 1
    df_return['ETH prices'] = _dfs[0]["ETH prices"]
    df_return['BTC prices'] = _dfs[0]["BTC prices"]
    df_return['BAL prices'] = _dfs[0]["BAL prices"]

    df_return["Date"] = _dfs[0]["Date"]
    df_return["timestamp"] = _dfs[0]["timestamp"]

    return df_return

@st.experimental_memo
def get_usage_metrics_df(_subgraph, _sg, latest_schema=True):
    usageMetrics = _subgraph.Query.usageMetricsDailySnapshots(
    orderBy=_subgraph.UsageMetricsDailySnapshot.timestamp,
    orderDirection='desc',
    first=1000
    )
    query_fields = [
      usageMetrics.id,
      usageMetrics.cumulativeUniqueUsers,
      usageMetrics.dailyActiveUsers,
      usageMetrics.dailyTransactionCount,
      usageMetrics.depositStats.count,
      usageMetrics.withdrawStats.count,
      usageMetrics.swapStats.count,
      usageMetrics.totalPoolCount,
      usageMetrics.timestamp
    ]
    df = _sg.query_df(query_fields)
    df['Date'] = df['usageMetricsDailySnapshots_id'].apply(lambda x: datetime.utcfromtimestamp(int(x)*86400))
    df = df.rename(columns={
        'usageMetricsDailySnapshots_swapStats_count':'Daily Deposit Count',
        'usageMetricsDailySnapshots_withdrawStats_count':'Daily Withdraw Count',
        'usageMetricsDailySnapshots_depositStats_count':'Daily Swap Count',
        'usageMetricsDailySnapshots_dailyTransactionCount': 'Daily Transaction Count',
        'usageMetricsDailySnapshots_dailyActiveUsers':'Daily Active Users',
        'usageMetricsDailySnapshots_cumulativeUniqueUsers':'Cumulative New Users',
        'usageMetricsDailySnapshots_totalPoolCount': 'Total Pool Count',
        'usageMetricsDailySnapshots_timestamp':'timestamp'
        })
    df['Days'] = df['usageMetricsDailySnapshots_id'].astype(int)
    df['USD prices'] = 1
    df = df.join(ETH_HISTORY_DF['ETH prices'], on="Days")
    df = df.join(BTC_HISTORY_DF['BTC prices'], on="Days")
    df = df.join(BAL_HISTORY_DF['BAL prices'], on="Days")
    df = df.iloc[::-1]
    df['id'] = df['usageMetricsDailySnapshots_id']
    df = df.set_index("id")
    return df

@st.cache(allow_output_mutation=True)
def merge_usage_dfs(_dfs):
    df_return = pd.concat(_dfs, join='outer', axis=0).fillna(0)
    df_return = df_return.groupby('id').sum()
    df_return["Date"] = _dfs[0]["Date"]
    df_return["timestamp"] = _dfs[0]["timestamp"]
    df_return['BAL prices'] = _dfs[0]["BAL prices"]
    df_return['ETH prices'] = _dfs[0]["ETH prices"]
    df_return['BTC prices'] = _dfs[0]["BTC prices"]
    df_return['USD prices'] = 1

    return df_return

@st.experimental_memo
def get_pools_df(_subgraph, _sg, chain="mainnet", sort_col=None, conditions_list="{}"):
    conditions_list = json.loads(conditions_list)
    if sort_col is None:
        sort_col=_subgraph.LiquidityPool.totalValueLockedUSD
    conditions_list['id_not'] = '0x0000000000000000000000000000000000000000'
    liquidityPools = _subgraph.Query.liquidityPools(
        first=1000,
        orderBy=sort_col,
        orderDirection='desc',
        where=conditions_list
    )
    liquidityPools_df = _sg.query_df([
        liquidityPools.id,
        liquidityPools.name,
        liquidityPools.totalValueLockedUSD,
        liquidityPools.cumulativeVolumeUSD,
        liquidityPools.createdTimestamp
    ])
    liquidityPools_df = liquidityPools_df.rename(columns={
        'liquidityPools_totalValueLockedUSD':'Total Value Locked',
        'liquidityPools_cumulativeVolumeUSD':'Cumulative Volume USD',        
        'liquidityPools_name':'Pool',
        'liquidityPools_id': 'id',
        'liquidityPools_createdTimestamp': 'Created Timestamp'
    })
    liquidityPools_df['pool_label'] = liquidityPools_df['Pool'] + ' - ' + liquidityPools_df['id'] + ' - ' + chain
    return liquidityPools_df


@st.experimental_memo
def get_token_ids_by_pool_df(_subgraph, _sg, pool_id_array=[]):    
    liquidityPools = _subgraph.Query.liquidityPools(
        first=1000,
        orderBy=_subgraph.LiquidityPool.totalValueLockedUSD,
        orderDirection='desc',
        where={'id_in': pool_id_array}
    )
    liquidityPools_df = _sg.query_df([
        liquidityPools.id,
        liquidityPools.totalValueLockedUSD,
        liquidityPools.inputTokens.id,
    ])
    liquidityPools_df = liquidityPools_df.rename(columns={
        'liquidityPools_id': 'id',
        'liquidityPools_totalValueLockedUSD':'Total Value Locked',
        'liquidityPools_inputTokens_id':'Token IDs',        
    })
    return liquidityPools_df


@st.experimental_memo
def get_top_x_liquidityPools(_subgraph, _sg, field, limit):
    # Field is the sort category, limit is the count of instances to return
    liquidityPools = _subgraph.Query.liquidityPools(
        first=limit,
        orderBy=_subgraph.LiquidityPool.__getattribute__(field),
        orderDirection='desc',
        where={'id_not': '0x0000000000000000000000000000000000000000'}
    )
    liquidityPools_df = _sg.query_df([
        liquidityPools.id,
        liquidityPools.name,
        liquidityPools.__getattribute__(field)
    ])
    liquidityPools_df = liquidityPools_df.rename(columns={'liquidityPools_' + field: field, 'liquidityPools_name':'Pool', 'liquidityPools_id': 'id'})
    liquidityPools_df['pool_label'] = liquidityPools_df['Pool'] + ' - ' + liquidityPools_df['id']
    return liquidityPools_df

@st.cache(hash_funcs={subgrounds.subgraph.object.Object: lambda _: None}, allow_output_mutation=True)
def merge_dfs(_dfs, sort_col):
    df_return = pd.concat(_dfs, join='outer', axis=0).fillna(0)
    df_return = df_return.sort_values(sort_col, ascending=False)
    return df_return

@st.experimental_memo
def get_swaps_df(_subgraph,_sg,sort_value,window_start=0,tx_above=0,tx_below=1000000000, pool_id=None):
    conditions_list = {'timestamp_gt': window_start, 'amountInUSD_gt': tx_above, 'amountInUSD_lt': tx_below}
    if pool_id is not None:
        conditions_list['pool'] = pool_id
    event = _subgraph.Query.swaps(
        orderBy=_subgraph.Swap.__getattribute__(sort_value),
        orderDirection='desc',
        first=1000,
        where=conditions_list
    )
    
    df = _sg.query_df([
        event.timestamp,
        event.hash,
        event.tokenIn.name,
        event.tokenOut.name,
        event.tokenIn.id,
        event.tokenOut.id,
        event.amountInUSD,
        event.amountOutUSD,
        event.account.id
    ])
    if len(df.index) == 0:
        return 'QUERY RETURNED NO DATA'
    df['Date'] = df['swaps_timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    # Date String is used to group data rows by the date, rather than the exact same Y/M/D H/M/S value on Date
    df['Date String'] = df['swaps_timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)).strftime("%Y-%m-%d"))
    df = df.rename(columns={
        'swaps_hash':'Transaction Hash',
        'swaps_tokenIn_name': 'Token In Name',
        'swaps_tokenOut_name': 'Token Out Name',
        'swaps_tokenIn_id': 'Token In',
        'swaps_tokenOut_id': 'Token Out',
        'swaps_amountInUSD':'Amount In',
        'swaps_amountOutUSD':'Amount Out',
        'swaps_timestamp':'timestamp',
        'swaps_account_id': 'Wallet'
    })

    df['Pool'] = df['Token In Name'] + '/' + df['Token Out Name']
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df['USD prices'] = 1
    df = df.join(ETH_HISTORY_DF['ETH prices'], on="Days")
    df = df.join(BTC_HISTORY_DF['BTC prices'], on="Days")
    df = df.join(BAL_HISTORY_DF['BAL prices'], on="Days")
    return df

@st.experimental_memo
def get_30d_withdraws(_subgraph, _sg):
    now = int(datetime.timestamp(datetime.now()))
    withinMonthTimestamp = now - (86400 * 3000)
    slug = 'withdraws'
    event = _subgraph.Query.__getattribute__(slug)(
        orderBy=_subgraph.__getattribute__('Withdraw').amountUSD,
        orderDirection='desc',
        first=100,
        where={"timestamp_gt": withinMonthTimestamp}
    )
    df = _sg.query_df([
        event.timestamp,
        event.hash,
        event.pool.name,
        event.amountUSD,
        event.account.id
    ])
    df = df.rename(columns={
        slug+'_hash':'Transaction Hash',
        slug+'_timestamp':'timestamp',
        slug+'_pool_name':'Pool',
        slug+'_amountUSD':'Amount',
        slug+'_account_id': 'Wallet'
    })
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df['USD prices'] = 1
    df = df.join(ETH_HISTORY_DF['ETH prices'], on="Days")
    df = df.join(BTC_HISTORY_DF['BTC prices'], on="Days")
    df = df.join(BAL_HISTORY_DF['BAL prices'], on="Days")
    return df

@st.cache(hash_funcs={subgrounds.subgraph.object.Object: lambda _: None}, allow_output_mutation=True)
def get_revenue_df(_df):
    mcap_df = get_coin_market_cap('balancer')
    revenue_df = _df.merge(mcap_df, how='inner', on='Date')
    revenue_df = revenue_df[(revenue_df['Daily Protocol Revenue']>0) | (revenue_df['Daily Total Revenue']>0)]
    revenue_df['P/E Ratio'] = (revenue_df['mcap'] / revenue_df['Daily Protocol Revenue'])/1000
    revenue_df['P/S Ratio'] = (revenue_df['mcap'] / revenue_df['Daily Total Revenue'])/1000
    revenue_df = revenue_df.sort_values(by='Date')[:-1]
    return revenue_df

@st.experimental_memo
def get_veBAL_df(_veBAL_subgraph, _sg):
    veBAL_data = _veBAL_subgraph.Query.votingEscrow(
        id="0xc128a9954e6c874ea3d62ce62b468ba073093f25"
    )
    df = _sg.query_df([
      veBAL_data.stakedSupply
    ])

    df = df.rename(columns={
        'votingEscrow_stakedSupply':'Staked Supply'
        })
    return df

@st.experimental_memo
def get_veBAL_unlocks_df(_veBAL_subgraph, _sg):
    now = datetime.now()
    veBAL_data = _veBAL_subgraph.Query.votingEscrowLocks(
        where={"unlockTime_gt": int(datetime.timestamp(now))},
        orderBy='unlockTime',
        orderDirection='desc',
        first=2000
    )
    df = _sg.query_df([
      veBAL_data.unlockTime,
      veBAL_data.lockedBalance
    ])
    df['Date'] = df['votingEscrowLocks_unlockTime'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df['timestamp'] = df['votingEscrowLocks_unlockTime']
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))

    df = df.rename(columns={
        'votingEscrowLocks_lockedBalance':'Amount To Unlock',
        'votingEscrowLocks_unlockTime':'timestamp'
        })
    print(df)
    return df

@st.experimental_memo
def get_veBAL_locked_df(_veBAL_subgraph, _sg):
    now = datetime.now()
    veBAL_data = _veBAL_subgraph.Query.votingEscrowLocks(
        where={"unlockTime_lt": int(datetime.timestamp(now))},
        orderBy='unlockTime',
        orderDirection='asc',
        first=2000
    )
    df = _sg.query_df([
      veBAL_data.unlockTime,
      veBAL_data.lockedBalance
    ])
    df['Date'] = df['votingEscrowLocks_unlockTime'].apply(lambda x: datetime.utcfromtimestamp(int(x)))

    df = df.rename(columns={
        'votingEscrowLocks_lockedBalance':'Locked Balance',
        'votingEscrowLocks_unlockTime':'timestamp'
        })
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df['USD prices'] = 1
    df = df.join(ETH_HISTORY_DF['ETH prices'], on="Days")
    df = df.join(BTC_HISTORY_DF['BTC prices'], on="Days")
    df = df.join(BAL_HISTORY_DF['BAL prices'], on="Days")
    print(df)
    return df

@st.experimental_memo
def get_veBAL_top_wallets(_veBAL_subgraph, _sg):
    veBAL_data = _veBAL_subgraph.Query.votingEscrowLocks(
        orderBy='lockedBalance',
        orderDirection='desc',
        first=20
    )
    df = _sg.query_df([
        veBAL_data.user.id,
        veBAL_data.lockedBalance
    ])

    df = df.rename(columns={
        'votingEscrowLocks_lockedBalance':'Locked Balance',
        'votingEscrowLocks_user_id':'Address'
        })

    return df

@st.experimental_memo
def get_pool_data_df(_subgraph, _sg, pool):
    poolId = pool.split(' - ')[1]
    liquidityPool = _subgraph.Query.liquidityPool(id=poolId)
    df = _sg.query_df([
      liquidityPool.id,
      liquidityPool.name,
      liquidityPool.inputTokens.name,
      liquidityPool.createdTimestamp
    ])
    df['Creation Date'] = df['liquidityPool_createdTimestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df = df.rename(columns={
        'liquidityPool_id':'id',
        'liquidityPool_name':'Name',
        'liquidityPool_inputTokens_name': 'Input Tokens'
        })

    df = df.set_index("id")
    print(df)
    return df

@st.experimental_memo
def get_pool_timeseries_df(_subgraph, _sg, conditions_list=""):
    conditions_list = json.loads(conditions_list)
    liquidityPoolSnapshots = _subgraph.Query.liquidityPoolDailySnapshots(
    where=conditions_list,
    first=5000,
    orderBy=_subgraph.LiquidityPoolDailySnapshot.timestamp,
    orderDirection='desc'
    ) 
    df = _sg.query_df([
        liquidityPoolSnapshots.id,
        liquidityPoolSnapshots.pool.id,
        liquidityPoolSnapshots.pool.name,
        liquidityPoolSnapshots.totalValueLockedUSD,
        liquidityPoolSnapshots.dailyVolumeUSD,
        liquidityPoolSnapshots.dailyVolumeByTokenUSD,
        liquidityPoolSnapshots.dailySupplySideRevenueUSD,
        liquidityPoolSnapshots.dailyProtocolSideRevenueUSD,
        liquidityPoolSnapshots.cumulativeVolumeUSD,
        liquidityPoolSnapshots.timestamp
    ])
    df = df.rename(columns={
        "liquidityPoolDailySnapshots_id":"id",
        "liquidityPoolDailySnapshots_pool_id":"Pool ID",
        "liquidityPoolDailySnapshots_pool_name":"Pool Name",
        "liquidityPoolDailySnapshots_totalValueLockedUSD":"Total Value Locked",
        "liquidityPoolDailySnapshots_dailyVolumeByTokenUSD":"Daily Volume By Token",
        "liquidityPoolDailySnapshots_dailySupplySideRevenueUSD":"Daily Supply Revenue",
        "liquidityPoolDailySnapshots_dailyProtocolSideRevenueUSD":"Daily Protocol Revenue",
        "liquidityPoolDailySnapshots_dailyVolumeUSD":"Daily Volume",
        "liquidityPoolDailySnapshots_cumulativeVolumeUSD":"Cumulative Volume USD",
        "liquidityPoolDailySnapshots_timestamp":"timestamp"
        })
    if len(df.index) == 0:
        return "QUERY RETURNED NO DATA"
    df["Date"] = df["timestamp"].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df["Days"] = df["timestamp"].apply(lambda x: int(int(x)/86400))
    df["Daily veBAL Holder Revenue"] = df["Daily Protocol Revenue"] * .75
    df["Pool Name"] = df["Pool Name"].apply(lambda x: x.replace("Balancer v2 ", ""))
    df = df.set_index("Days")
    df = df.iloc[::-1]
    df["Base Yield"] = df["Daily Supply Revenue"]/df["Total Value Locked"] * 100
    df["USD prices"] = 1
    df = df.join(ETH_HISTORY_DF["ETH prices"], on="Days")
    df = df.join(BTC_HISTORY_DF["BTC prices"], on="Days")
    df = df.join(BAL_HISTORY_DF["BAL prices"], on="Days")
    df = df.set_index("id")

    return df

@st.experimental_memo
def get_timeseries_on_pool_df(_subgraph, _sg, conditions_list="{}", first=1, skip=1):
    conditions_list = json.loads(conditions_list)
    liquidity_pools = _subgraph.Query.liquidityPools(
    first=1000,
    skip=0,
    orderBy=_subgraph.LiquidityPool.totalValueLockedUSD,
    orderDirection='desc'
    ) 
    dailySnaps = liquidity_pools.dailySnapshots(
    where=conditions_list,
    first=first,
    skip=skip,
    orderBy=liquidity_pools.dailySnapshots.timestamp,
    orderDirection='desc'
    )
    df = _sg.query_df([
        liquidity_pools.id,
        liquidity_pools.name,
        dailySnaps.id,
        dailySnaps.totalValueLockedUSD,
        dailySnaps.dailySupplySideRevenueUSD,
        dailySnaps.dailyProtocolSideRevenueUSD,
        dailySnaps.cumulativeVolumeUSD,
        dailySnaps.dailyVolumeUSD,
        dailySnaps.timestamp
    ])
    df = df.rename(columns={
        "liquidityPools_dailySnapshots_id":"id",
        "liquidityPools_id":"Pool ID",
        "liquidityPools_name":"Pool Name",
        "liquidityPools_dailySnapshots_totalValueLockedUSD":"Total Value Locked",
        "liquidityPools_dailySnapshots_dailySupplySideRevenueUSD":"Daily Supply Revenue",
        "liquidityPools_dailySnapshots_dailyProtocolSideRevenueUSD":"Daily Protocol Revenue",
        "liquidityPools_dailySnapshots_dailyVolumeUSD":"Daily Volume",
        "liquidityPools_dailySnapshots_cumulativeVolumeUSD":"Cumulative Volume USD",
        "liquidityPools_dailySnapshots_timestamp":"timestamp"
        })
    if len(df.index) == 0:
        return "QUERY RETURNED NO DATA"
    df["Date"] = df["timestamp"].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df["Days"] = df["timestamp"].apply(lambda x: int(int(x)/86400))
    df["Daily veBAL Holder Revenue"] = df["Daily Protocol Revenue"] * .75
    df["Pool Name"] = df["Pool Name"].apply(lambda x: x.replace("Balancer v2 ", ""))
    df = df.set_index("Days")
    df = df.iloc[::-1]
    df["Base Yield"] = df["Daily Supply Revenue"]/df["Total Value Locked"] * 100
    df["USD prices"] = 1
    df = df.join(ETH_HISTORY_DF["ETH prices"], on="Days")
    df = df.join(BTC_HISTORY_DF["BTC prices"], on="Days")
    df = df.join(BAL_HISTORY_DF["BAL prices"], on="Days")
    df = df.set_index("id")
    return df

@st.experimental_memo
def get_largest_current_depositors_df(_subgraph, _sg, conditions_list="{}"):
    conditions_list = json.loads(conditions_list)
    conditions_list['totalValueLockedUSD_gt'] = 1000000
    
    liquidityPools = _subgraph.Query.liquidityPools(
        first=1000,
        orderBy=_subgraph.LiquidityPool.totalValueLockedUSD,
        orderDirection='desc',
        where=conditions_list
    )
    positions = liquidityPools.positions(
    where={"timestampClosed": None},
    first=5000,
    orderBy=liquidityPools.positions.outputTokenBalance,
    orderDirection='desc'
    )
    liquidityPools_df = _sg.query_df([
        liquidityPools.totalValueLockedUSD,
        liquidityPools.outputTokenSupply,
        positions.outputTokenBalance,
        positions.timestampClosed,
        positions.account.id,
        positions.id
    ])
    liquidityPools_df = liquidityPools_df.rename(columns={
        'liquidityPools_totalValueLockedUSD':'Total Value Locked',
        'liquidityPools_outputTokenSupply':'Output Token Supply',
        'liquidityPools_positions_outputTokenBalance': 'Output Token Balance',
        'liquidityPools_positions_timestampClosed': 'Timestamp Closed',
        'liquidityPools_positions_account_id': 'Account ID',
        'liquidityPools_positions_id': 'Position ID',
    })
    
    liquidityPools_df['Position Value'] = liquidityPools_df['Total Value Locked'] / 6587568 * liquidityPools_df['Output Token Balance']
    return liquidityPools_df

@st.experimental_memo
def get_pools_gini(_subgraph, _sg, conditions_list="{}"):
    conditions_list = json.loads(conditions_list)
    conditions_list['totalValueLockedUSD_gt'] = 1000000
    # conditions_list["openPositionCount_gt"] = 20
    liquidityPools = _subgraph.Query.liquidityPools(
        first=1000,
        orderBy=_subgraph.LiquidityPool.openPositionCount,
        orderDirection='desc',
        where=conditions_list
    )
    positions = liquidityPools.positions(
    where={"timestampClosed": None},
    first=5000
    )
    liquidityPools_df = _sg.query_df([
        liquidityPools.id,
        liquidityPools.totalValueLockedUSD,
        liquidityPools.outputTokenSupply,
        liquidityPools.openPositionCount,
        positions.outputTokenBalance,
        positions.timestampClosed,
    ])
    liquidityPools_df = liquidityPools_df.rename(columns={
        'liquidityPools_id':'Pool ID',
        'liquidityPools_totalValueLockedUSD':'Total Value Locked',
        'liquidityPools_outputTokenSupply':'Output Token Supply',
        "liquidityPools_openPositionCount": "Open Position Count",
        'liquidityPools_positions_outputTokenBalance': 'Output Token Balance',
    })
    # liquidityPools_df['Portion of Pool'] = liquidityPools_df['Output Token Balance']/liquidityPools_df['Output Token Supply']
    liquidityPools_df['Portion of Pool'] = liquidityPools_df['Output Token Balance']/(liquidityPools_df['Output Token Balance']*random.randint(2, 9))
    # sort here asc token values on positions
    liquidityPools_df = liquidityPools_df.sort_values("Output Token Balance", ascending=False)
    liquidityPools_df["Position Index on Pool"] = liquidityPools_df.groupby("Pool ID").cumcount() + 1
    liquidityPools_df["GINI Data Point"] = liquidityPools_df['Portion of Pool'] / (liquidityPools_df["Position Index on Pool"]/liquidityPools_df["Open Position Count"])
    pool_to_GINI_dataset_mapping = liquidityPools_df.groupby("Pool ID")["GINI Data Point"].apply(list).to_dict()
    pool_to_GINI_mapping = {}
    for pool_id, dataset in pool_to_GINI_dataset_mapping.items():
        pool_to_GINI_mapping[pool_id] = gini(dataset)
    GINI_pools_df = pd.DataFrame({"Pool":pool_to_GINI_mapping.keys(), "GINI": pool_to_GINI_mapping.values()})
    return GINI_pools_df

@st.experimental_memo
def get_swaps_by_pool(_subgraph, _sg, conditions_list="{}"):
    conditions_list = json.loads(conditions_list)
    liquidityPools = _subgraph.Query.liquidityPools(
        first=1000,
        orderBy=_subgraph.LiquidityPool.totalValueLockedUSD,
        orderDirection='desc',
        where=conditions_list
    )
    swaps = liquidityPools.swaps(
    where={"timestamp_gt": int(datetime.timestamp(datetime.now())) - (86400 * 1400)},
    first=5000
    )
    swaps_df = _sg.query_df([
        swaps.amountInUSD
    ])
    swaps_df = swaps_df.rename(columns={
        'liquidityPools_swaps_amountInUSD':'TX Amount',
    })
    tx_amounts = swaps_df['TX Amount'].tolist()

    tx_buckets = {"0-100": 0, "100-1000": 0, "1000-10000": 0, "10000-100000": 0, "100000-1000000": 0, "1000000-10000000": 0, "10000000+": 0}

    for x in tx_amounts:
        if x < 100:
            tx_buckets["0-100"] += 1
        elif x >= 100 and x < 1000:
            tx_buckets["100-1000"] += 1
        elif x >= 1000 and x < 10000:
            tx_buckets["1000-10000"] += 1
        elif x >= 10000 and x < 100000:
            tx_buckets["10000-100000"] += 1
        elif x >= 100000 and x < 1000000:
            tx_buckets["100000-1000000"] += 1
        elif x >= 1000000 and x < 10000000:
            tx_buckets["1000000-10000000"] += 1
        elif x >= 10000000:
            tx_buckets["10000000+"] += 1

    return tx_buckets