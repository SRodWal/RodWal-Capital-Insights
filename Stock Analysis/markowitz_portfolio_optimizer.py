import pandas as pd
import numpy as np
from scipy.optimize import minimize
import yfinance as yf
import tkinter as tk
from tkinter import simpledialog

#Custom Modules
def Selector(lst):
    def on_select():
        nonlocal selected_items, risk_aversion
        selected_items = [lst[i] for i in lb.curselection()]
        risk_aversion = slider.get() / 100  # Convert to a value between 0 and 1
        root.destroy()
    
    selected_items = []
    risk_aversion = 0.5  # Default value
    
    root = tk.Tk()
    root.title("Multi-Select List")
    root.geometry("400x400")

    lb = tk.Listbox(root, selectmode=tk.MULTIPLE)
    for item in lst:
        lb.insert(tk.END, item)
    lb.pack(padx=10, pady=10)

    slider_label = tk.Label(root, text="Risk Aversion (0: Max Returns, 100: Min Risk):")
    slider_label.pack(pady=10)

    slider = tk.Scale(root, from_=0, to=100, orient=tk.HORIZONTAL)
    slider.pack(pady=10)

    select_button = tk.Button(root, text="Select", command=on_select)
    select_button.pack(pady=10)

    root.mainloop()
    
    return selected_items, risk_aversion

# Create the dataframe from the given data
f_dir = r"Stock Analysis/Open_Positions.xlsx"
#f_dir = r"D:/Professional_WorkTools/Github/StockSillines/Portfolio Expected Returns.xlsx"  
portfolio_df = pd.read_excel(f_dir)
portfolio_df = portfolio_df[["Chapter", "Ticker", "Volume", "Price", "Expected Return QoQ%", "Volatility", "Value"]]
Selected_Chapters, risk_aversion = Selector(list(set(portfolio_df.Chapter)))
df = portfolio_df.loc[portfolio_df.Chapter.isin(Selected_Chapters)].drop("Chapter", axis=1)


# Extract necessary data
tickers = df['Ticker'].values
expected_returns = df['Expected Return QoQ%'].values
volatilities = df['Volatility'].values
weights = df['Value'].values / df['Value'].sum()  # Normalize initial weights

# Measure correlation
start = '2023-01-01'
end = '2024-12-31'

def CorMatrix(df, start_date, end_date):
    tickers = list(df["Ticker"])
    info = yf.download(tickers, start=start_date, end=end_date)['Close']
    # Calculate daily returns
    returns = info.pct_change().dropna()
    # Calculate the correlation matrix
    correlation_matrix = returns.corr()
    return correlation_matrix

correlation_matrix = CorMatrix(df, start, end)

# Covariance matrix
cov_matrix = np.outer(volatilities, volatilities) * correlation_matrix

# Objective Function to minimize: Risk-Adjusted Portfolio Variance
def objective_function(weights, cov_matrix, expected_returns, risk_aversion):
    # Minimize (risk_aversion * variance - (1 - risk_aversion) * returns)
    portfolio_variance = weights.T @ cov_matrix @ weights
    portfolio_return = np.sum(weights * expected_returns)
    return risk_aversion * portfolio_variance - (1 - risk_aversion) * portfolio_return

# Constraints: sum(weights) = 1
constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})

# Boundaries: weights should be between 0 and 1
bounds = tuple((0, 1) for asset in range(len(tickers)))

# Optimize the portfolio
opt_results = minimize(objective_function, weights, args=(cov_matrix, expected_returns, risk_aversion), method='SLSQP', bounds=bounds, constraints=constraints)

# Optimal Weights
optimal_weights = opt_results.x

# Expected Portfolio Return
expected_portfolio_return = np.sum(optimal_weights * expected_returns)

# Expected Portfolio Volatility
expected_portfolio_volatility = np.sqrt(optimal_weights.T @ cov_matrix @ optimal_weights)

# Results
print("Optimal Weights:")
for ticker, weight in zip(tickers, optimal_weights):
    print(f"{ticker}: {weight:.2%}")

print(f"\nExpected Portfolio Return: {expected_portfolio_return:.2%}")
print(f"Expected Portfolio Volatility: {expected_portfolio_volatility:.2%}")

# Redistribution Table
df["Volume %"] = df['Value'].values / df['Value'].sum()
current_weights = df[["Ticker", "Volume %"]]
distribution_df = pd.DataFrame({"Ticker": tickers, "Optimal Weight": optimal_weights})
MixChange_df = pd.merge(current_weights, distribution_df, on="Ticker")

# Convert weights to percentage format
MixChange_df["Volume %"] = MixChange_df["Volume %"].apply(lambda x: "{:.2%}".format(x))
MixChange_df["Optimal Weight"] = MixChange_df["Optimal Weight"].apply(lambda x: "{:.2%}".format(x))

print("\nMerged DataFrame:")
print(MixChange_df)
