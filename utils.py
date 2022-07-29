import pytz
import datetime
import numpy as np
from pyecharts.types import JsCode

ccy_options=['USD', 'ETH', 'BTC', 'BAL']

class fragile(object):
    class Break(Exception):
      """Break out of the with statement"""

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value.__enter__()

    def __exit__(self, etype, value, traceback):
        error = self.value.__exit__(etype, value, traceback)
        if etype == self.Break:
            return True
        return error

# Get the start and end date denominated in number of days since epoch
def get_xaxis_zoom_range(xaxis, start, end):
    xaxis_end = int(xaxis[len(xaxis)-1])
    xaxis_start = int(xaxis[0])
    full_xaxis_diff = xaxis_end - xaxis_start
    start_slider = ((start - xaxis_start) / full_xaxis_diff) * 100
    end_slider = 100 - ((xaxis_end - end) / full_xaxis_diff) * 100
    
    slider_points = {
        "start": start_slider,
        "end": end_slider
    }
    return slider_points



def format_xaxis(series: list[int], Multiplier=60 * 60 * 24, format: str = "%B %d, %Y"):
    return [
        datetime.datetime.fromtimestamp(i).astimezone(pytz.utc).strftime(format)
        for i in list(map(lambda x: int(x) * Multiplier, series))
    ]

def xaxis_label_formatter():
    return JsCode(
        """
        function Formatter(n) {
            let word = n.split(',');
            
            return word[0];
        };
        """
    )

def yaxis_label_formatter():
    return JsCode(
        """
        function Formatter(n) {
            if (n < 1e3) return n;
            if (n >= 1e3 && n < 1e6) return +(n / 1e3).toFixed(1) + "K";
            if (n >= 1e6 && n < 1e9) return +(n / 1e6).toFixed(1) + "M";
            if (n >= 1e9 && n < 1e12) return +(n / 1e9).toFixed(1) + "B";
            if (n >= 1e12) return +(n / 1e12).toFixed(1) + "T";
        };
        """
    )


def gini(x):

    # x is the set of data points calculated from each position on the pool

    # (Warning: This is a concise implementation, but it is O(n**2)
    # in time and memory, where n = len(x).  *Don't* pass in huge
    # samples!)

    # Mean absolute difference
    mad = np.abs(np.subtract.outer(x, x)).mean()
    # Relative mean absolute difference
    rmad = mad/np.mean(x)
    # Gini coefficient
    g = 0.5 * rmad
    return g