import pandas as pd # type: ignore
import yfinance as yf # type: ignore
import numpy as np # type: ignore
import requests

def get_forward_eps_from_yahoo(ticker: str, timeout: int = 15):
    """
    Returns a robust Forward EPS for `ticker`.

    Priority:
      1) Yahoo earningsTrend: trend period '+1y' -> earningsEstimate.avg
      2) Implied EPS from price / forwardPE (from yfinance)
      3) info['forwardEps'] as last fallback

    Returns float or None.
    """
    # --- 1) Primary: earningsTrend '+1y' average EPS ---
    try:
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
        params = {"modules": "earningsTrend"}
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        js = r.json()
        trend = js["quoteSummary"]["result"][0]["earningsTrend"]["trend"]
        plus1y = next((t for t in trend if t.get("period") == "+1y"), None)
        if plus1y:
            avg_eps = plus1y["earningsEstimate"]["avg"]
            if isinstance(avg_eps, (int, float)):
                return float(avg_eps)
    except Exception:
        pass  # fall through to implied / fallback

    # Prepare yfinance objects once for the fallbacks
    try:
        stock = yf.Ticker(ticker)
        info = stock.info if hasattr(stock, "info") else {}
    except Exception:
        stock, info = None, {}

    # --- 2) Fallback: implied from price / forwardPE ---
    try:
        if stock is not None:
            price = float(stock.history(period="1d")["Close"].iloc[-1])
            fwd_pe = info.get("forwardPE")
            if fwd_pe and float(fwd_pe) != 0:
                return price / float(fwd_pe)
    except Exception:
        pass

    # --- 3) Last resort: info['forwardEps'] ---
    try:
        val = info.get("forwardEps")
        return float(val) if isinstance(val, (int, float)) else None
    except Exception:
        return None


def update_portfolio_close_price(input_file, output_file):
    """
    Reads tickers from an Excel file, fetches latest close price, GICS sector, dividend yield,
    P/E ratios, PEG, EBITDA margin, net income, EPS, Net Income %, and Volatility %, and writes the results to a new Excel file.
    """
    # Load the Excel file
    df = pd.read_excel(input_file)

    # Create a new DataFrame for the output
    output_data = []

    for index, row in df.iterrows():
        ticker = row.get("Ticker")
        chapter = row.get("Chapter", "")
        name = row.get("Name", "")

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            name = info.get("shortName", name)
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
            forward_eps = get_forward_eps_from_yahoo(ticker)

            # Net Income Margin calculation
            if net_income not in ["N/A", None] and total_revenue not in ["N/A", None, 0]:
                net_income_pct = (net_income / total_revenue) * 100
            else:
                net_income_pct = "N/A"

            # Convert yield and margins to percentage if available
            if dividend_yield not in ["N/A", None]:
                dividend_yield = dividend_yield * 100
            if ebitda_margin not in ["N/A", None]:
                ebitda_margin = ebitda_margin * 100

            # Volatility calculation (annualized std dev of daily returns, last 1 year)
            hist = stock.history(period="1y")
            if not hist.empty and "Close" in hist.columns:
                returns = hist["Close"].pct_change().dropna()
                volatility = returns.std() * np.sqrt(252) * 100  # annualized, in percent
            else:
                volatility = "N/A"

        except Exception as e:
            latest_close = f"Error: {e}"
            gics_sector = "Unknown"
            dividend_yield = 0
            trailing_pe = "N/A"
            forward_pe = "N/A"
            peg_ratio = "N/A"
            ebitda_margin = "N/A"
            net_income = "N/A"
            net_income_pct = "N/A"
            eps = "N/A"
            forward_eps = "N/A"
            volatility = "N/A"

        output_data.append({
            "Chapter": chapter,
            "Name": name,
            "Ticker": ticker,
            "Close Price": latest_close,
            "GICS Sector": gics_sector,
            "Expected Dividend Yield %": dividend_yield,
            "Trailing P/E": trailing_pe,
            "Forward P/E": forward_pe,
            "PEG Ratio": peg_ratio,
            "EBITDA Margin %": ebitda_margin,
            "Net Income to Common": net_income,
            "Net Income %": net_income_pct,
            "EPS": eps,
            "Forward EPS": forward_eps,
            "Volatility %": volatility
        })

    output_df = pd.DataFrame(output_data)
    output_df.to_excel(output_file, index=False)
    print(f"Updated data (including Net Income % and Volatility %) has been saved to {output_file}")

# Example usage:
update_portfolio_close_price("Stock Selection/tickers_used.xlsx", "Stock Selection/tickers_used.xlsx")