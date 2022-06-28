import pytz
import datetime
from pyecharts.types import JsCode

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


