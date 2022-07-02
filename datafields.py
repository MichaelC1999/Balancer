from subgrounds.subgrounds import Subgrounds
import subgrounds.subgraph

from datetime import datetime
import pandas as pd
import streamlit as st
from utilities.coingecko import get_coin_market_cap, get_coin_market_chart
ETH_HISTORY = get_coin_market_chart('ethereum')
ETH_HISTORY_DF = pd.DataFrame(ETH_HISTORY['prices'], columns=['timestamp', 'prices'])[:-1]
ETH_HISTORY_DF['Days'] = (ETH_HISTORY_DF['timestamp']/86400000).astype(int)
ETH_HISTORY_DF=ETH_HISTORY_DF.set_index('Days')
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
    df["Base Yield"] = round(df["Daily Supply Revenue"]/df["Total Value Locked"] * 100,2)
    df = df.iloc[::-1]

    df = df.join(ETH_HISTORY_DF['prices'], on="Days")
    df = df.set_index("id")
    print(ETH_HISTORY_DF, df.index, df)

    print(df)
    return df

def merge_financials_dfs(dfs, sg):
    df_return = pd.concat(dfs, join='outer', axis=0).fillna(0)
    df_return = df_return.groupby('id').sum().round(2)
    df_return['prices'] = dfs[0]["prices"]
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
    df['Days'] = df['usageMetricsDailySnapshots_id'].astype(int)
    
    df = df.join(ETH_HISTORY_DF['prices'], on="Days")
    df = df.iloc[::-1]

    df['id'] = df['usageMetricsDailySnapshots_id']
    df = df.set_index("id")
    return df

def merge_usage_dfs(dfs, sg):
    df_return = pd.concat(dfs, join='outer', axis=0).fillna(0)
    df_return = df_return.groupby('id').sum().round(2)
    df_return["Date"] = dfs[0]["Date"]
    df_return["timestamp"] = dfs[0]["timestamp"]
    df_return['prices'] = dfs[0]["prices"]
    print(df_return)
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

def get_top_x_liquidityPools(subgraph, sg, field, limit):
    # Field is the sort category, limit is the count of instances to return
    liquidityPools = subgraph.Query.liquidityPools(
        first=limit,
        orderBy=subgraph.LiquidityPool.__getattribute__(field),
        orderDirection='desc',
        where=[subgraph.LiquidityPool.id != '0x0000000000000000000000000000000000000000']
    )
    liquidityPools_df = sg.query_df([
        liquidityPools.id,
        liquidityPools.name,
        liquidityPools.__getattribute__(field)
    ])
    liquidityPools_df = liquidityPools_df.rename(columns={'liquidityPools_' + field: field, 'liquidityPools_name':'Pool', 'liquidityPools_id': 'id'})
    liquidityPools_df['pool_label'] = liquidityPools_df['Pool'] + ' - ' + liquidityPools_df['id']
    print(liquidityPools_df)
    return liquidityPools_df

def get_recent_24h_pool_snapshots(subgraph, sg):
    # Because there is no "Days Since Epoch" field on the snapshot and snapshot timestamps can vary on when they start/end, select snapshots with timestamps in a 36 hr window
    # Snapshots that appear more than once will be filtered out
    # The time window is specifically over 24 hrs ago because snapshots within the last 24 hrs maybe the current in-progress snapshot and may innacurately reflect the average daily statistic
    now = int(int(datetime.timestamp(datetime.now())))
    timestamp_gt_60hrs = now - 60*3600
    timestamp_lt_24hrs = now - 24*3600
    liquidityPoolSnapshots = subgraph.Query.liquidityPoolDailySnapshots(
        orderBy=subgraph.LiquidityPoolDailySnapshot.id,
        where={"timestamp_gt": timestamp_gt_60hrs, "timestamp_lt": timestamp_lt_24hrs}
    ) 
    df = sg.query_df([
        liquidityPoolSnapshots.id,
        liquidityPoolSnapshots.pool.id,
        liquidityPoolSnapshots.pool.name,
        liquidityPoolSnapshots.timestamp,
        liquidityPoolSnapshots.totalValueLockedUSD,
        liquidityPoolSnapshots.dailyVolumeUSD,
        liquidityPoolSnapshots.dailySupplySideRevenueUSD,
    ])
    df = df.rename(columns={
        'liquidityPoolDailySnapshots_id':'id',
        'liquidityPoolDailySnapshots_pool_id':'Pool ID',
        'liquidityPoolDailySnapshots_pool_name':'Pool Name',
        'liquidityPoolDailySnapshots_dailySupplySideRevenueUSD':'Daily Supply Revenue',
        'liquidityPoolDailySnapshots_totalValueLockedUSD':'Total Value Locked',
        'liquidityPoolDailySnapshots_dailyVolumeUSD':'Daily Volume',
        'liquidityPoolDailySnapshots_timestamp':'timestamp'
        })
    df = df.drop_duplicates(subset="Pool ID")
    df['Date'] = df['timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df = df.set_index("Days")
    df['Total Value Locked'] = df['Total Value Locked'].round(2)
    df['Daily Volume'] = df['Daily Volume'].round(2)
    df["Base Yield"] = round(df["Daily Supply Revenue"]/df["Total Value Locked"] * 100, 2)
    df = df.join(ETH_HISTORY_DF['prices'], on="Days")
    df = df.set_index("id")

    return df

def merge_dfs(dfs, sg, sort_col):
    df_return = pd.concat(dfs, join='outer', axis=0).fillna(0)
    df_return = df_return.sort_values(sort_col, ascending=False)
    return df_return

def get_swaps_df(subgraph,sg,sort_value,window_start=0):
    event = subgraph.Query.swaps(
        orderBy=subgraph.Swap.__getattribute__(sort_value),
        orderDirection='desc',
        first=1000,
        where=[subgraph.Swap.timestamp > window_start]
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
        'swaps_timestamp':'timestamp'
    })
    df['Amount In'] = df['Amount In'].round(2)
    df['Amount Out'] = df['Amount Out'].round(2)

    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df = df.join(ETH_HISTORY_DF['prices'], on="Days")
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
        slug+'_timestamp':'timestamp',
        slug+'_from':'From',
        slug+'_to':'Wallet',
        slug+'_pool_name':'Pool',
        slug+'_amountUSD':'Amount'
    })
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df = df.join(ETH_HISTORY_DF['prices'], on="Days")

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
        orderDirection='desc',
        first=1000
    )
    df = sg.query_df([
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
    df['Amount To Unlock'] = df['Amount To Unlock'].round(2)
    print(df)
    return df

def get_veBAL_locked_df(veBAL_subgraph, sg):
    now = datetime.now()
    veBAL_data = veBAL_subgraph.Query.votingEscrowLocks(
        where={"unlockTime_lt": int(datetime.timestamp(now))},
        orderBy='unlockTime',
        orderDirection='asc',
        first=1000
    )
    df = sg.query_df([
      veBAL_data.unlockTime,
      veBAL_data.lockedBalance
    ])
    df['Date'] = df['votingEscrowLocks_unlockTime'].apply(lambda x: datetime.utcfromtimestamp(int(x)))

    df = df.rename(columns={
        'votingEscrowLocks_lockedBalance':'Locked Balance',
        'votingEscrowLocks_unlockTime':'timestamp'
        })
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df = df.join(ETH_HISTORY_DF['prices'], on="Days")
    df['Locked Balance'] = df['Locked Balance'].round(2)
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
        'liquidityPoolDailySnapshots_dailyVolumeUSD':'Daily Volume',
        'liquidityPoolDailySnapshots_timestamp':'timestamp'
        })
    df['Date'] = df['timestamp'].apply(lambda x: datetime.utcfromtimestamp(int(x)))
    df['Days'] = df['timestamp'].apply(lambda x: int(int(x)/86400))
    df["Daily veBAL Holder Revenue"] = df['Daily Protocol Revenue'] * .75
    df = df.set_index("Days")
    df = df.iloc[::-1]
    df["Base Yield"] = round(df["Daily Supply Revenue"]/df["Total Value Locked"] * 100,2)
    df = df.join(ETH_HISTORY_DF['prices'], on="Days")
    df = df.set_index("id")

    return df

