import pandas as pd
from datetime import datetime

def get_quarterly_values(financial_df, usage_df, quarterWindows, quartersList, QtReports, index, iterator):
    financialsInQuarter = financial_df.loc[(financial_df['timestamp'] >= quarterWindows[quartersList[index]]["start"]) & (financial_df['timestamp'] <= quarterWindows[quartersList[index]]["end"])]
    usageStatisticsInQuarter = usage_df.loc[(usage_df['timestamp'] >= quarterWindows[quartersList[index]]["start"]) & (usage_df['timestamp'] <= quarterWindows[quartersList[index]]["end"])]
    QtReports["Swaps"][iterator] = str(usageStatisticsInQuarter["Daily Swap Count"].sum().round(2))
    QtReports["LP Fees"][iterator] = str(financialsInQuarter["Daily Supply Revenue"].sum().round(2))
    QtReports["Volume"][iterator] = str(financialsInQuarter["Daily Volume"].sum().round(2))
    QtReports["Liquidity"][iterator] = str(round(financialsInQuarter["Total Value Locked"].mean(),2))
    QtReports["Agg. New Pools"][iterator] = str(usageStatisticsInQuarter["Total Pool Count"].sum().round(2))
    QtReports["Protocol Revenue"][iterator] = str(financialsInQuarter["Daily Total Revenue"].sum().round(2))
    if iterator > 0:
        # Get current iterator swap amaount, subtract it by iterator - 1 amount, take this value and divide by iterator - 1 value, multiply this by 100
        QtReports["growth-Swaps"][iterator - 1] = str(round((float(QtReports["Swaps"][iterator - 1]) - float(QtReports["Swaps"][iterator])) / float(QtReports["Swaps"][iterator]) * 100, 2)) + "%"
        QtReports["growth-Volume"][iterator - 1] = str(round((float(QtReports["LP Fees"][iterator - 1]) - float(QtReports["LP Fees"][iterator])) / float(QtReports["LP Fees"][iterator]) * 100, 2)) + "%"
        QtReports["growth-Fees"][iterator - 1] = str(round((float(QtReports["Volume"][iterator - 1]) - float(QtReports["Volume"][iterator])) / float(QtReports["Volume"][iterator]) * 100, 2)) + "%"
        QtReports["growth-Liquidity"][iterator - 1] = str(round((float(QtReports["Liquidity"][iterator - 1]) - float(QtReports["Liquidity"][iterator])) / float(QtReports["Liquidity"][iterator]) * 100, 2)) + "%"
        QtReports["growth-Agg"][iterator - 1] = str(round((float(QtReports["Agg. New Pools"][iterator - 1]) - float(QtReports["Agg. New Pools"][iterator])) / float(QtReports["Agg. New Pools"][iterator]) * 100, 2)) + "%"
        QtReports["growth-Protocol"][iterator - 1] = str(round((float(QtReports["Protocol Revenue"][iterator - 1]) - float(QtReports["Protocol Revenue"][iterator])) / float(QtReports["Protocol Revenue"][iterator]) * 100, 2)) + "%"
    else:
        QtReports["growth-Swaps"][iterator - 1] = "-"
        QtReports["growth-Volume"][iterator - 1] = "-"
        QtReports["growth-Fees"][iterator - 1] = "-"
        QtReports["growth-Liquidity"][iterator - 1] = "-"
        QtReports["growth-Agg"][iterator - 1] = "-"
        QtReports["growth-Protocol"][iterator - 1] = "-"


def get_quarter_table(financial_df, usage_df):
    currentDay = datetime.now().day
    currentMonth = datetime.now().month
    currentYear = datetime.now().year
    quartersList = ["Q4", "Q3", "Q2", "Q1"]
    currentQuarterIdx = 3
    if (currentMonth > 3):
        currentQuarterIdx = 2
    if (currentMonth > 6):
        currentQuarterIdx = 1
    if (currentMonth > 9):
        currentQuarterIdx = 0
    quarterStarts= {"Q1": {"month": 1, "day": 1}, "Q2": {"month": 4, "day": 1}, "Q3": {"month": 7, "day": 1}, "Q4": {"month": 10, "day": 1}}
    quarterWindows={}
    quarterWindows[quartersList[currentQuarterIdx]] = {}
    iterator = 0
    quarterWindows[quartersList[currentQuarterIdx]]["end"] = datetime(currentYear, currentMonth, currentDay, datetime.now().hour).timestamp()
    quarterWindows[quartersList[currentQuarterIdx]]["start"] = datetime(currentYear, quarterStarts[quartersList[currentQuarterIdx]]["month"], quarterStarts[quartersList[currentQuarterIdx]]["day"]).timestamp()

    prevstart = quarterWindows[quartersList[currentQuarterIdx]]["start"]

    QtReports = {
        "Swaps": ["", "", "", "", ""],
        "growth-Swaps": ["", "", "", "", ""],
        "Volume": ["", "", "", "", ""],
        "growth-Volume": ["", "", "", "", ""],
        "LP Fees": ["", "", "", "", ""],
        "growth-Fees": ["", "", "", "", ""],
        "Liquidity": ["", "", "", "", ""],
        "growth-Liquidity": ["", "", "", "", ""],
        "Agg. New Pools": ["", "", "", "", ""],
        "growth-Agg": ["", "", "", "", ""],
        "Protocol Revenue": ["", "", "", "", ""],
        "growth-Protocol": ["", "", "", "", ""]
        }

    get_quarterly_values(financial_df, usage_df, quarterWindows, quartersList, QtReports, currentQuarterIdx, iterator)
    quarterWindows[quartersList[currentQuarterIdx] + " '" + str(currentYear)[-2:]] = quarterWindows[quartersList[currentQuarterIdx]]
    del quarterWindows[quartersList[currentQuarterIdx]]
    for x in range(4):
        iterator += 1
        if (currentQuarterIdx == 3):
            currentQuarterIdx = 0
            currentYear = currentYear - 1
        else:
            currentQuarterIdx = currentQuarterIdx + 1

        quarterWindows[quartersList[currentQuarterIdx]] = {}
        quarterWindows[quartersList[currentQuarterIdx]]["start"] = datetime(currentYear, quarterStarts[quartersList[currentQuarterIdx]]["month"], quarterStarts[quartersList[currentQuarterIdx]]["day"]).timestamp()
        quarterWindows[quartersList[currentQuarterIdx]]["end"] = prevstart - 1
        
        get_quarterly_values(financial_df, usage_df, quarterWindows, quartersList, QtReports, currentQuarterIdx, iterator)
        prevstart = quarterWindows[quartersList[currentQuarterIdx]]["start"]
        quarterWindows[quartersList[currentQuarterIdx] + " '" + str(currentYear)[-2:]] = quarterWindows[quartersList[currentQuarterIdx]]
        del quarterWindows[quartersList[currentQuarterIdx]]

    quarterWindowSequence = list(quarterWindows.keys())
    quarterWindowList = list(QtReports.values())
    quarterWindowTableRows = list(QtReports.keys())

    for i in range(len(quarterWindowTableRows)):
        if "growth" in quarterWindowTableRows[i]:
            quarterWindowTableRows[i] = "% growth"

    return pd.DataFrame(quarterWindowList, columns = quarterWindowSequence, index = quarterWindowTableRows).astype(str).loc[:,::-1]