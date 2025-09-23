import pandas as pd
import os

import os, time, math, json, sys
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime as dt, timezone

#Use of Alpha Vantage API
API_KEY = 'HGVQJ8SLTEHHCDQQ'
BASE_URL = 'https://www.alphavantage.co/query'

#Target Tickers:
Tickers = ['IBIT.US','VBTC.DE','BTM.US','ADE.DE','BTCE.DE', 'XXTB.DE']


def fetch_av(params, sleep_if_needed=True):
    """Generic Alpha Vantage fetch with basic error handling & optional throttling."""
    params = {**params, "apikey": API_KEY}
    r = requests.get(BASE_URL, params=params, timeout=30)
    try:
        data = r.json()
    except json.JSONDecodeError:
        raise RuntimeError(f"Non-JSON response: {r.text[:200]}")
    if "Error Message" in data:
        raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
    if "Note" in data:  # throttled
        # Respect backoff hint
        note = data["Note"]
        if sleep_if_needed:
            time.sleep(15)
            return fetch_av(params, sleep_if_needed=False)
        else:
            raise RuntimeError(f"Throttled: {note}")
    return data

params = {
    "function": "TIME_SERIES_DAILY_ADJUSTED",
    "symbol": "IBM",
    "outputsize": "compact",  # 'compact' or 'full'
    "datatype": "json"
}
print(fetch_av(params))
