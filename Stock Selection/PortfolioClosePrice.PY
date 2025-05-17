import pandas as pd
import yfinance as yf

def update_portfolio_close_price(input_file, output_file):
    """
    Reads tickers from an Excel file, fetches latest close price, GICS sector, dividend yield,
    P/E ratios, PEG, EBITDA margin, net income, EPS, and Net Income %, and writes the results to a new Excel file.
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
            "Forward EPS": forward_eps
        })

    output_df = pd.DataFrame(output_data)
    output_df.to_excel(output_file, index=False)
    print(f"Updated data (including Net Income %) has been saved to {output_file}")

# Example usage:
update_portfolio_close_price("Stock Selection/tickers_used.xlsx", "Stock Selection/tickers_used.xlsx")