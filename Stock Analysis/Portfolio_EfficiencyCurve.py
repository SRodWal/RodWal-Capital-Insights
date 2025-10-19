import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import minimize
import yfinance as yf
import tkinter as tk
import plotly.offline as pyo
import time

# Initialize Plotly in offline mode
pyo.init_notebook_mode(connected=True)

# Custom Modules
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

# Read data from Excel
#f_dir = r"D:/Professional_WorkTools/Github/StockSillines/Portfolio Expected Returns.xlsx"
f_dir = r"Stock Analysis/Open_Positions.xlsx"
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
start = '2024-01-01'
end = '2025-12-31'

def CorMatrix(df, start_date, end_date):
    tickers = list(df["Ticker"])
    attempts = 10
    for attempt in range(attempts):
        try:
            info = yf.download(tickers, start=start_date, end=end_date)['Close']
            if not info.empty:
                break
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2)  # Wait for 2 seconds before retrying
    else:
        raise ValueError("Failed to fetch data from Yahoo Finance after multiple attempts.")
    
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

# Compute the efficient frontier
x = np.linspace(-1, np.pi/2-0.0001, 200)
# Calculate risk aversions using the specified formula
risk_aversions = np.tan(x)
frontier_returns = []
frontier_volatilities = []
frontier_weights = []
sharpe_ratios = []

# Risk-free rate (assuming a placeholder value; replace with actual risk-free rate)
risk_free_rate = 0.01

for risk_aversion in risk_aversions:
    opt_results = minimize(objective_function, weights, args=(cov_matrix, expected_returns, risk_aversion), method='SLSQP', bounds=bounds, constraints=constraints)
    optimal_weights = opt_results.x
    portfolio_return = np.sum(optimal_weights * expected_returns)
    portfolio_volatility = np.sqrt(optimal_weights.T @ cov_matrix @ optimal_weights)
    sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
    frontier_returns.append(portfolio_return)
    frontier_volatilities.append(portfolio_volatility)
    frontier_weights.append(optimal_weights)
    sharpe_ratios.append(sharpe_ratio)

# Find the optimal portfolio with the highest Sharpe Ratio
optimal_index = np.argmax(sharpe_ratios)
optimal_portfolio_return = frontier_returns[optimal_index]*100
optimal_portfolio_volatility = frontier_volatilities[optimal_index]*100
optimal_portfolio_weights = frontier_weights[optimal_index]
optimal_portfolio_hover = "<br>".join([f"{tickers[j]}: {optimal_portfolio_weights[j] * 100:.2f}%" for j in range(len(tickers))])

# Convert to percentage format
frontier_returns = [x * 100 for x in frontier_returns]
frontier_volatilities = [x * 100 for x in frontier_volatilities]
volatilities = [x * 100 for x in volatilities]
expected_returns = [x * 100 for x in expected_returns]

# Calculate the current portfolio return and volatility
current_portfolio_return = np.sum(weights * expected_returns) # Convert to percentage
current_portfolio_volatility = np.sqrt(weights.T @ cov_matrix @ weights)*100  # Convert to percentage
current_portfolio_hover = "<br>".join([f"{tickers[j]}: {weights[j] * 100:.2f}%" for j in range(len(tickers))])

# Hover text for efficient frontier points
hover_texts = []
for i in range(len(frontier_returns)):
    weights_text = "<br>".join([f"{tickers[j]}: {frontier_weights[i][j] * 100:.2f}%" for j in range(len(tickers))])
    hover_text = f"Volatility: {frontier_volatilities[i]:.2f}%<br>Return: {frontier_returns[i]:.2f}%<br>{weights_text}"
    hover_texts.append(hover_text)

# Generate random portfolios to create the portfolio boundary
num_portfolios = 100
random_portfolio_returns = []
random_portfolio_volatilities = []
random_portfolio_hover_texts = []

average_weights = []
for _ in range(num_portfolios):
    random_weights = np.random.random(len(tickers))
    random_weights /= np.sum(random_weights)
    portfolio_return = np.sum(random_weights * expected_returns)
    portfolio_volatility = np.sqrt(random_weights.T @ cov_matrix @ random_weights)
    random_portfolio_returns.append(portfolio_return)
    random_portfolio_volatilities.append(portfolio_volatility)
    
    weights_text = "<br>".join([f"{tickers[j]}: {random_weights[j] * 100:.2f}%" for j in range(len(tickers))])
    hover_text = f"Volatility: {portfolio_volatility*100:.2f}%<br>Return: {portfolio_return:.2f}%<br>{weights_text}"
    random_portfolio_hover_texts.append(hover_text)

# Convert to percentage format
random_portfolio_returns = [x for x in random_portfolio_returns]
random_portfolio_volatilities = [x*100 for x in random_portfolio_volatilities]

# Determine ranges for returns and volatilities
min_return, max_return = min(expected_returns), max(expected_returns)
min_volatility, max_volatility = min(volatilities), max(volatilities)

# Create grid points at intervals of 5%
return_intervals = np.arange(round(min_return/5)*5, round(max_return/5)*5 + 5, 5)
volatility_intervals = np.arange(round(min_volatility/5)*5, round(max_volatility/5)*5 + 5, 5)

# Generate portfolio points within the grid ranges
grid_portfolio_returns = []
grid_portfolio_volatilities = []
grid_portfolio_hover_texts = []

for ret in return_intervals:
    for vol in volatility_intervals:
        closest_index = np.argmin(np.abs(np.array(frontier_returns) - ret) + np.abs(np.array(frontier_volatilities) - vol))
        grid_portfolio_returns.append(frontier_returns[closest_index])
        grid_portfolio_volatilities.append(frontier_volatilities[closest_index])
        weights_text = "<br>".join([f"{tickers[j]}: {frontier_weights[closest_index][j] * 100:.2f}%" for j in range(len(tickers))])
        hover_text = f"Volatility: {frontier_volatilities[closest_index]:.2f}%<br>Return: {frontier_returns[closest_index]:.2f}%<br>{weights_text}"
        grid_portfolio_hover_texts.append(hover_text)

# Plot the efficient frontier using Plotly
fig = go.Figure()

# Add the efficient frontier line
fig.add_trace(go.Scatter(
    x=frontier_volatilities, y=frontier_returns, mode='lines+markers', name='Efficient Frontier',
    hoverinfo='text', text=hover_texts
))

# Add scatter plot for individual assets
fig.add_trace(go.Scatter(
    x=volatilities, y=expected_returns, mode='markers+text', name='Individual Assets', text=tickers, textposition='top center',
    hovertemplate='Volatility: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
))

# Highlight the optimal portfolio with the highest Sharpe Ratio
fig.add_trace(go.Scatter(
    x=[optimal_portfolio_volatility], y=[optimal_portfolio_return],
    mode='markers+text', name='Optimal Portfolio', text=["Optimal Portfolio"],
    textposition='bottom center', marker=dict(size=12, color='green'),
    hovertemplate=f"Volatility: {optimal_portfolio_volatility:.2f}%<br>Return: {optimal_portfolio_return:.2f}%<br>{optimal_portfolio_hover}<extra></extra>"
))

# Highlight the current portfolio
fig.add_trace(go.Scatter(
    x=[current_portfolio_volatility], y=[current_portfolio_return],
    mode='markers+text', name='Current Portfolio', text=["Current Portfolio"],
    textposition='bottom center', marker=dict(size=12, color='red'),
    hovertemplate=f"Volatility: {current_portfolio_volatility:.2f}%<br>Return: {current_portfolio_return:.2f}%<br>{current_portfolio_hover}<extra></extra>"
))

# Add the portfolio boundary
fig.add_trace(go.Scatter(
    x=random_portfolio_volatilities, y=random_portfolio_returns,
    mode='markers', name='Portfolio Boundary',
    marker=dict(size=3, color='blue', opacity=0.5),
    text=random_portfolio_hover_texts,
    hoverinfo='text'
))

# Add the portfolio grid
fig.add_trace(go.Scatter(
    x=grid_portfolio_volatilities, y=grid_portfolio_returns,
    mode='markers', name='Portfolio Grid',
    marker=dict(size=5, color='orange'),
    text=grid_portfolio_hover_texts,
    hoverinfo='text'
))


# Update layout with percentage format
fig.update_layout(
    title='Efficient Frontier',
    xaxis_title='Volatility (Risk) [%]',
    yaxis_title='Expected Return [%]',
    legend_title='Legend',
    template='plotly_white',
    xaxis_tickformat='.2f',
    yaxis_tickformat='.2f'
)

# Show the plot
fig.show()

# Optionally save the plot as an HTML file
fig.write_html("efficient_frontier_Banking_WK18.html")
