from subgrounds.subgrounds import Subgrounds
import subgrounds.subgraph
import json

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
      usageMetrics.dailyDepositCount,
      usageMetrics.dailyWithdrawCount,
      usageMetrics.dailySwapCount,
      usageMetrics.totalPoolCount,
      usageMetrics.timestamp
    ]
    df = _sg.query_df(query_fields)
    df['Date'] = df['usageMetricsDailySnapshots_id'].apply(lambda x: datetime.utcfromtimestamp(int(x)*86400))
    df = df.rename(columns={
        'usageMetricsDailySnapshots_dailyDepositCount':'Daily Deposit Count',
        'usageMetricsDailySnapshots_dailyWithdrawCount':'Daily Withdraw Count',
        'usageMetricsDailySnapshots_dailySwapCount':'Daily Swap Count',
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

    print(df_return)
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
        event.__getattribute__('from'),
        event.to,
        event.tokenIn.name,
        event.tokenOut.name,
        event.tokenIn.id,
        event.tokenOut.id,
        event.amountInUSD,
        event.amountOutUSD
    ])
    if len(df.index) == 0:
        return 'QUERY RETURNED NO DATA'
    df['Date'] = df['swaps_timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    # Date String is used to group data rows by the date, rather than the exact same Y/M/D H/M/S value on Date
    df['Date String'] = df['swaps_timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)).strftime("%Y-%m-%d"))
    df = df.rename(columns={
        'swaps_hash':'Transaction Hash',
        'swaps_from':'From',
        'swaps_to':'To',
        'swaps_tokenIn_name': 'Token In Name',
        'swaps_tokenOut_name': 'Token Out Name',
        'swaps_tokenIn_id': 'Token In',
        'swaps_tokenOut_id': 'Token Out',
        'swaps_amountInUSD':'Amount In',
        'swaps_amountOutUSD':'Amount Out',
        'swaps_timestamp':'timestamp'
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
    withinMonthTimestamp = now - (86400 * 30)
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
        event.__getattribute__('from'),
        event.to,
        event.pool.name,
        event.amountUSD
    ])
    df = df.rename(columns={
        slug+'_hash':'Transaction Hash',
        slug+'_timestamp':'timestamp',
        slug+'_from':'From',
        slug+'_to':'Wallet',
        slug+'_pool_name':'Pool',
        slug+'_amountUSD':'Amount'
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
    first=1000,
    orderBy=_subgraph.LiquidityPoolDailySnapshot.timestamp,
    orderDirection='desc'
    ) 
    df = _sg.query_df([
        liquidityPoolSnapshots.id,
        liquidityPoolSnapshots.pool.id,
        liquidityPoolSnapshots.pool.name,
        liquidityPoolSnapshots.totalValueLockedUSD,
        liquidityPoolSnapshots.dailyVolumeUSD,
        liquidityPoolSnapshots.dailySupplySideRevenueUSD,
        liquidityPoolSnapshots.dailyProtocolSideRevenueUSD,
        liquidityPoolSnapshots.cumulativeVolumeUSD,
        liquidityPoolSnapshots.timestamp
    ])
    df = df.rename(columns={
        'liquidityPoolDailySnapshots_id':'id',
        'liquidityPoolDailySnapshots_pool_id':'Pool ID',
        'liquidityPoolDailySnapshots_pool_name':'Pool Name',
        'liquidityPoolDailySnapshots_totalValueLockedUSD':'Total Value Locked',
        'liquidityPoolDailySnapshots_dailySupplySideRevenueUSD':'Daily Supply Revenue',
        'liquidityPoolDailySnapshots_dailyProtocolSideRevenueUSD':'Daily Protocol Revenue',
        'liquidityPoolDailySnapshots_dailyVolumeUSD':'Daily Volume',
        'liquidityPoolDailySnapshots_cumulativeVolumeUSD':'Cumulative Volume USD',
        'liquidityPoolDailySnapshots_timestamp':'timestamp'
        })
    if len(df.index) == 0:
        return 'QUERY RETURNED NO DATA'
    df['Date'] = df['timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df["Daily veBAL Holder Revenue"] = df['Daily Protocol Revenue'] * .75
    df = df.set_index("Days")
    df = df.iloc[::-1]
    df["Base Yield"] = df["Daily Supply Revenue"]/df["Total Value Locked"] * 100
    df['USD prices'] = 1
    df = df.join(ETH_HISTORY_DF['ETH prices'], on="Days")
    df = df.join(BTC_HISTORY_DF['BTC prices'], on="Days")
    df = df.join(BAL_HISTORY_DF['BAL prices'], on="Days")
    df = df.set_index("id")

    return df

