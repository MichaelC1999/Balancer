from subgrounds.subgrounds import Subgrounds
import subgrounds.subgraph

from datetime import datetime
import pandas as pd
import streamlit as st
from utilities.coingecko import get_coin_market_cap


# Initialize Subgrounds
@st.cache(hash_funcs={subgrounds.subgraph.object.Object: lambda _: None})
def get_financial_snapshots(subgraph, sg):
    financialSnapshot = subgraph.Query.financialsDailySnapshots(
    orderBy=subgraph.FinancialsDailySnapshot.timestamp,
    orderDirection='desc',
    first=1000
    )
    df = sg.query_df([
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
        'financialsDailySnapshots_protocolControlledValueUSD':'Protocol Controlled Value USD',
        'financialsDailySnapshots_dailyVolumeUSD':'Daily Volume USD',
        'financialsDailySnapshots_cumulativeVolumeUSD':'Cumulative Volume USD',
        'financialsDailySnapshots_cumulativeSupplySideRevenueUSD':'Cumulative Supply Side Revenue USD',
        'financialsDailySnapshots_cumulativeProtocolSideRevenueUSD':'Cumulative Protocol Side Revenue USD',
        'financialsDailySnapshots_cumulativeTotalRevenueUSD':'Cumulative Total Revenue USD',
        'financialsDailySnapshots_timestamp':'timestamp'
        })
    df['id'] = df['financialsDailySnapshots_id']
    df["Daily veBAL Holder Revenue"] = df["Daily Protocol Revenue"] * .75
    df["Cumulative veBAL Holder Revenue"] = df['Cumulative Protocol Side Revenue USD'] * .75
    df['HistoricalYield'] = df['Total Value Locked']/df['Daily Total Revenue']
    df["Base Yield"] = df["Daily Supply Revenue"]/df["Total Value Locked"] * 100
    df = df.set_index("id")
    print(df)
    return df

def merge_financials_dfs(dfs, sg):
    df_return = pd.concat(dfs, join='outer', axis=0).fillna(0)
    df_return = df_return.groupby('id').sum().round(2)
    df_return["Date"] = dfs[0]["Date"]
    df_return["timestamp"] = dfs[0]["timestamp"]

    return df_return

@st.cache(hash_funcs={subgrounds.subgraph.object.Object: lambda _: None})
def get_usage_metrics_df(subgraph, sg, latest_schema=True):
    usageMetrics = subgraph.Query.usageMetricsDailySnapshots(
    orderBy=subgraph.UsageMetricsDailySnapshot.timestamp,
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
    df = sg.query_df(query_fields)
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
    

    df['id'] = df['usageMetricsDailySnapshots_id']
    df = df.set_index("id")
    return df

def merge_usage_dfs(dfs, sg):
    df_return = pd.concat(dfs, join='outer', axis=0).fillna(0)
    df_return = df_return.groupby('id').sum().round(2)
    df_return["Date"] = dfs[0]["Date"]
    df_return["timestamp"] = dfs[0]["timestamp"]

    return df_return

@st.cache(hash_funcs={subgrounds.subgraph.object.Object: lambda _: None})
def get_pools_df(subgraph, sg, chain="mainnet"):
    liquidityPools = subgraph.Query.liquidityPools(
        first=100,
        orderBy=subgraph.LiquidityPool.totalValueLockedUSD,
        orderDirection='desc',
        where=[subgraph.LiquidityPool.id != '0x0000000000000000000000000000000000000000']
    )
    liquidityPools_df = sg.query_df([
        liquidityPools.id,
        liquidityPools.name,
        liquidityPools.totalValueLockedUSD
    ])
    liquidityPools_df = liquidityPools_df.rename(columns={'liquidityPools_totalValueLockedUSD':'Total Value Locked', 'liquidityPools_name':'Pool', 'liquidityPools_id': 'id'})
    liquidityPools_df['pool_label'] = liquidityPools_df['Pool'] + ' - ' + liquidityPools_df['id'] + ' - ' + chain
    return liquidityPools_df

def get_top_10_liquidityPools_revenue(subgraph, sg):
    liquidityPools = subgraph.Query.liquidityPools(
        first=1000,
        orderBy=subgraph.LiquidityPool.cumulativeTotalRevenueUSD,
        orderDirection='desc',
        where=[subgraph.LiquidityPool.id != '0x0000000000000000000000000000000000000000']
    )
    liquidityPools_df = sg.query_df([
        liquidityPools.id,
        liquidityPools.name,
        liquidityPools.cumulativeTotalRevenueUSD
    ])
    liquidityPools_df = liquidityPools_df.rename(columns={'liquidityPools_cumulativeTotalRevenueUSD':'Revenues', 'liquidityPools_name':'Pool', 'liquidityPools_id': 'id'})
    liquidityPools_df['pool_label'] = liquidityPools_df['Pool'] + ' - ' + liquidityPools_df['id']
    return liquidityPools_df

def merge_dfs(dfs, sg, sort_col):
    df_return = pd.concat(dfs, join='outer', axis=0).fillna(0)
    df_return.sort_values(sort_col)
    return df_return

def get_swaps_df(subgraph,sg,sort_value):
    event = subgraph.Query.swaps(
        orderBy=subgraph.Swap.__getattribute__(sort_value),
        orderDirection='desc',
        first=1000
    )
    df = sg.query_df([
        event.timestamp,
        event.hash,
        event.__getattribute__('from'),
        event.to,
        event.pool.name,
        event.amountInUSD,
        event.amountOutUSD
    ])
    df['Date'] = df['swaps_timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    # Date String is used to group data rows by the date, rather than the exact same Y/M/D H/M/S value on Date
    df['Date String'] = df['swaps_timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)).strftime("%Y-%m-%d"))
    df = df.rename(columns={
        'swaps_hash':'Transaction Hash',
        'swaps_from':'From',
        'swaps_to':'To',
        'swaps_pool_name':'Pool',
        'swaps_amountInUSD':'Amount In',
        'swaps_amountOutUSD':'Amount Out',
        'swaps_timestamp':'Timestamp'
    })
    df['Amount In'] = df['Amount In']
    df['Amount Out'] = df['Amount Out']
    return df

def get_14d_swaps_df(subgraph,sg):
    now = int(datetime.timestamp(datetime.now()))
    within14dTimestamp = now - (86400 * 14)
    event = subgraph.Query.swaps(
        orderBy=subgraph.Swap.amountInUSD,
        orderDirection='desc',
        where=[subgraph.Swap.timestamp > within14dTimestamp],
        first=1000
    )
    df = sg.query_df([
        event.timestamp,
        event.hash,
        event.__getattribute__('from'),
        event.to,
        event.pool.name,
        event.amountInUSD,
        event.amountOutUSD
    ])
    df['Date'] = df['swaps_timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df = df.rename(columns={
        'swaps_hash':'Transaction Hash',
        'swaps_from':'From',
        'swaps_to':'To',
        'swaps_pool_name':'Pool',
        'swaps_amountInUSD':'Amount In',
        'swaps_amountOutUSD':'Amount Out'

    })
    df['Amount In'] = df['Amount In'].apply(lambda x: "${:.1f}k".format((x/1000)))
    df['Amount Out'] = df['Amount Out'].apply(lambda x: "${:.1f}k".format((x/1000)))
    return df

def get_30d_withdraws(subgraph, sg):
    now = int(datetime.timestamp(datetime.now()))
    withinMonthTimestamp = now - (86400 * 30)
    slug = 'withdraws'
    event = subgraph.Query.__getattribute__(slug)(
        orderBy=subgraph.__getattribute__('Withdraw').amountUSD,
        orderDirection='desc',
        first=100,
        where={"timestamp_gt": withinMonthTimestamp}
    )
    df = sg.query_df([
        event.timestamp,
        event.hash,
        event.__getattribute__('from'),
        event.to,
        event.pool.name,
        event.amountUSD
    ])
    df = df.rename(columns={
        slug+'_hash':'Transaction Hash',
        slug+'_from':'From',
        slug+'_to':'To',
        slug+'_pool_name':'Pool',
        slug+'_amountUSD':'Amount'
    })

    return df

def get_events_df(subgraph, sg,event_name='Deposit'):
    now = int(datetime.timestamp(datetime.now()))
    withinMonthTimestamp = now - (86400 * 30)
    slug = event_name.lower()+'s'
    event = subgraph.Query.__getattribute__(slug)(
        orderBy=subgraph.__getattribute__(event_name).amountUSD,
        orderDirection='desc',
        first=100,
        where={"timestamp_gt": withinMonthTimestamp}
    )
    df = sg.query_df([
        event.timestamp,
        event.hash,
        event.__getattribute__('from'),
        event.to,
        event.pool.name,
        event.amountUSD
    ])
    # df['Date'] = df[slug+'_timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df = df.rename(columns={
        slug+'_hash':'Transaction Hash',
        slug+'_from':'From',
        slug+'_to':'To',
        slug+'_pool_name':'Pool',
        slug+'_amountUSD':'Amount'
    })
    # df.drop(columns=[slug+'_timestamp'], axis=1, inplace=True)
    # df['Amount'] = df['Amount'].apply(lambda x: "${:.1f}k".format((x/1000)))
    return df


def get_revenue_df(df, sg):
    mcap_df = get_coin_market_cap('balancer')
    revenue_df = df.merge(mcap_df, how='inner', on='Date')
    revenue_df = revenue_df[(revenue_df['Daily Protocol Revenue']>0) | (revenue_df['Daily Total Revenue']>0)]
    revenue_df['P/E Ratio'] = (revenue_df['mcap'] / revenue_df['Daily Protocol Revenue'])/1000
    revenue_df['P/S Ratio'] = (revenue_df['mcap'] / revenue_df['Daily Total Revenue'])/1000
    revenue_df = revenue_df.sort_values(by='Date')[:-1]
    return revenue_df


def get_veBAL_df(veBAL_subgraph, sg):
    veBAL_data = veBAL_subgraph.Query.votingEscrow(
        id="0xc128a9954e6c874ea3d62ce62b468ba073093f25"
    )
    df = sg.query_df([
      veBAL_data.stakedSupply
    ])

    df = df.rename(columns={
        'votingEscrow_stakedSupply':'Staked Supply'
        })
    return df

def get_veBAL_unlocks_df(veBAL_subgraph, sg):
    now = datetime.now()
    veBAL_data = veBAL_subgraph.Query.votingEscrowLocks(
        where={"unlockTime_gt": int(datetime.timestamp(now))},
        orderBy='unlockTime',
        orderDirection='asc'
    )
    df = sg.query_df([
      veBAL_data.unlockTime,
      veBAL_data.lockedBalance
    ])
    df['Date'] = df['votingEscrowLocks_unlockTime'].apply(lambda x: datetime.utcfromtimestamp(int(x)))

    df = df.rename(columns={
        'votingEscrowLocks_lockedBalance':'Amount To Unlock'
        })
    print(df)
    return df

def get_veBAL_locked_df(veBAL_subgraph, sg):
    now = datetime.now()
    veBAL_data = veBAL_subgraph.Query.votingEscrowLocks(
        where={"unlockTime_lt": int(datetime.timestamp(now))},
        orderBy='unlockTime',
        orderDirection='asc'
    )
    df = sg.query_df([
      veBAL_data.unlockTime,
      veBAL_data.lockedBalance
    ])
    df['Date'] = df['votingEscrowLocks_unlockTime'].apply(lambda x: datetime.utcfromtimestamp(int(x)))

    df = df.rename(columns={
        'votingEscrowLocks_lockedBalance':'Locked Balance'
        })
    print(df)
    return df

def get_pool_data_df(subgraph, sg, pool):
    poolId = pool.split(' - ')[1]
    liquidityPool = subgraph.Query.liquidityPool(id=poolId)
    df = sg.query_df([
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

def get_pool_timeseries_df(subgraph, sg, pool):
    poolId = pool.split(' - ')[1]
    liquidityPoolSnapshots = subgraph.Query.liquidityPoolDailySnapshots(
    where=[subgraph.LiquidityPoolDailySnapshot.pool == poolId],
    orderBy=subgraph.LiquidityPoolDailySnapshot.timestamp,
    orderDirection='desc'
    ) 
    df = sg.query_df([
        liquidityPoolSnapshots.id,
        liquidityPoolSnapshots.timestamp,
        liquidityPoolSnapshots.totalValueLockedUSD,
        liquidityPoolSnapshots.dailyVolumeUSD,
        liquidityPoolSnapshots.dailySupplySideRevenueUSD,
        liquidityPoolSnapshots.dailyProtocolSideRevenueUSD
    ])
    df = df.rename(columns={
        'liquidityPoolDailySnapshots_id':'id',
        'liquidityPoolDailySnapshots_dailySupplySideRevenueUSD':'Daily Supply Revenue',
        'liquidityPoolDailySnapshots_dailyProtocolSideRevenueUSD':'Daily Protocol Revenue',
        'liquidityPoolDailySnapshots_totalValueLockedUSD':'Total Value Locked',
        'liquidityPoolDailySnapshots_dailyVolumeUSD':'Daily Volume USD',
        'liquidityPoolDailySnapshots_timestamp':'timestamp'
        })
    df['Date'] = df['timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df["Base Yield"] = df["Daily Supply Revenue"]/df["Total Value Locked"] * 100
    df = df.set_index("id")
    print(df)
    return df

