# -*- coding: utf-8 -*-
"""
Created on Sat Sep 13 13:23:38 2025

@author: serw1
"""

import pandas as pd # type: ignore
import yfinance as yf # type: ignore
import numpy as np # type: ignore
import requests

stock = yf.Ticker("APA")
info = stock.info
latest_close = stock.history(period="1d")["Close"].iloc[-1]
gics_sector = info.get("sector", "Unknown")
dividend_yield = info.get("dividendYield", "N/A")

trailing_pe = info.get("trailingPE", "N/A")
forward_pe = info.get("forwardPE", "N/A")
peg_ratio = info.get("pegRatio", "N/A")
ebitda_margin = info.get("ebitdaMargins", "N/A")
net_income = info.get("netIncomeToCommon", "N/A")
total_revenue = info.get("totalRevenue", None)
eps = info.get("trailingEps", "N/A")
forward_eps = info.get("forwardEps", "N/A")

data = {
            "Close Price": latest_close,
            "GICS Sector": gics_sector,
            "Expected Dividend Yield %": dividend_yield,
            "Trailing P/E": trailing_pe,
            "Forward P/E": forward_pe,
            "PEG Ratio": peg_ratio,
            "EBITDA Margin %": ebitda_margin,
            "Net Income to Common": net_income,
            "EPS": eps,
            "Forward EPS": forward_eps,
        }

print(data)
