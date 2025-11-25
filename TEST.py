
import requests

API_KEY = "TF28ZZDMC9JZOOA7"  # your key
SYMBOL = "SQM"               # NYSE ticker for ING Group N.V.

url = "https://www.alphavantage.co/query"
params = {
    "function": "OVERVIEW",
    "symbol": SYMBOL,
    "apikey": API_KEY
}

r = requests.get(url, params=params, timeout=20)
data = r.json()


# Extract relevant fields
Name = data.get("Name")
Sector = data.get("Sector")
Industry = data.get("Industry")
TargetPrice = data.get('AnalystTargetPrice')
dividend_yield = data.get("DividendYield")
dividend_per_share = data.get("DividendPerShare")
ex_dividend_date = data.get("ExDividendDate")
TrailingPE = data.get('TrailingPE')
ForwardPE = data.get('ForwardPE')
PEGRatio = data.get('PEGRatio')
OperatingMarginTTM = data.get('OperatingMarginTTM')
ProfitMargin = data.get('ProfitMargin')
DilutedEPSTTM = data.get('DilutedEPSTTM')
CURR = data.get('Currency')
RevenueTTM = data.get('RevenueTTM')

# Print nicely
print(f"""
Name: {Name}
Sector: {Sector}
Industry: {Industry}
Analyst Target Price: {TargetPrice}
Dividend Yield: {dividend_yield}
Dividend per Share: {dividend_per_share}
Ex-Dividend Date: {ex_dividend_date}
Trailing PE: {TrailingPE}
Forward PE: {ForwardPE}
PEG Ratio: {PEGRatio}
Operating Margin (TTM): {OperatingMarginTTM}
Profit Margin: {ProfitMargin}
Diluted EPS (TTM): {DilutedEPSTTM}
Currency: {CURR}
Revenue (TTM): {RevenueTTM}
""")

params = {
    "function": "INCOME_STATEMENT",
    "symbol": SYMBOL,
    "apikey": API_KEY
}

r = requests.get(url, params=params, timeout=20)
data = r.json()



