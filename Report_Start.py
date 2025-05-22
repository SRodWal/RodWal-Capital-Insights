import pandas as pd
import os

#from PortfolioClosePrice import update_portfolio_close_price

#Lets read the excel file in the same directory as this script
# Get the directory of the current script
f_dir = "XTB_Initial.xlsx"

#read excel sheet names
sheet_names = pd.ExcelFile(f_dir).sheet_names

#Lets keep sheet names that contains "CLOSED POSITIONS", "OPEN POSITION", "CASG OPERARIONS HISTORY"
sheet_keep = ["CLOSED POSITION HISTORY", "OPEN POSITION", "CASH OPERATION"]
sheet_names = [sheet for sheet in sheet_names if any(keep in sheet for keep in sheet_keep)]
sheet_names = sheet_names[:3]  # Limit to the first 3 sheets
skip_rows = [12,10,10]

print("Sheet names in the Excel file:")
for sheet in sheet_names:
    print(sheet)

#Lets display the dataframes on each sheet
dfs = {}
for sheet, rows in zip(sheet_names, skip_rows):
    print(f"\nData in {sheet} sheet:")
    df = pd.read_excel(f_dir, sheet_name=sheet, skiprows=rows)
    print(df.head())  # Display the first few rows of the DataFrame
    print(f"Number of rows: {len(df)}")
    print(f"Number of columns: {len(df.columns)}")
    print(f"Columns: {df.columns.tolist()}")
    print("\n")
    dfs[sheet] = df

# Replace XTB suffix .US with empty string, UK tickers with .L, NL tickers with .AS, MC with PA:
initial_suffix = [".US", ".UK", ".NL", ".FR", ".ES"]
final_suffix = ["", ".L", ".AS", ".PA", ".MC"]
special_map = {
    "VIX": "^VIX",
    "USDJPY": "JPY=X",
    "USDMXN": "MXN=X",
    "US500": "SPY",
    "GOLD": "GC=F"
}

def fix_ticker(symbol):
    if not isinstance(symbol, str):
        return symbol
    # Apply suffix replacement
    for x, y in zip(initial_suffix, final_suffix):
        if symbol.endswith(x):
            symbol = symbol.replace(x, y)
    # Apply special mapping
    return special_map.get(symbol, symbol)

# Apply to all symbols in the list
initial_list = list(set(dfs["CASH OPERATION HISTORY"]['Symbol']))
tickers_used = [fix_ticker(s) for s in initial_list]

print("Used Tickers: ", tickers_used)

# Ensure the folder exists
os.makedirs("Stock Selection", exist_ok=True)

tickers_df = pd.DataFrame({'Ticker': tickers_used})
tickers_df.to_excel(os.path.join("Stock Selection", "tickers_update.xlsx"), index=False)

#update_portfolio_close_price("Stock Selection/tickers_used.xlsx", "Stock Selection/tickers_used.xlsx")

# Apply fix_ticker to each DataFrame before saving
for sheet, df in dfs.items():
    if "Symbol" in df.columns:
        df["Symbol"] = df["Symbol"].apply(fix_ticker)

# Save the DataFrames to Excel files
sheet_names_output = ["CLOSED POSITION HISTORY", "OPEN POSITION", "CASH OPERATION"]
for sheet, df in zip(sheet_names_output, dfs.values()):
    output_file = os.path.join("Stock Selection", f"{sheet}.xlsx")
    df.to_excel(output_file, index=False)
    print(f"Saved {sheet} to {output_file}")




