# RodWal-Capital-Insights

Overview
RodWal Capital Insights is a consulting portfolio management report designed to provide a data-driven analysis of investment holdings. It offers a structured framework for performance evaluation, risk assessment, portfolio optimization, and strategic decision-making.
This repository contains the models, scripts, and reports used to analyze Open Positions, Closed Positions, and Portfolio Efficiency, incorporating statistical methods and financial optimization techniques.
Features
- Portfolio Summary: A high-level snapshot of market allocation, sector exposure, and risk-adjusted performance.
- Open Positions Analysis: A deep dive into active holdings, sectoral risk, expected EPS growth, volatility, and current vs. optimal portfolio comparisons.
- Closed Positions Review: Performance attribution for realized trades, including historical P&L and sector-specific trends.
- Markowitz Efficient Frontier Visualization: A data-driven optimization model using Monte Carlo simulations and risk aversion calculations to compare existing allocation vs. optimal strategies.
- Risk & Return Metrics: Comprehensive analysis of Sharpe ratios, volatility trends, sector performance differentials, and forward-looking risk scenarios.
Installation & Dependencies
Ensure the following Python libraries are installed:
pip install numpy pandas matplotlib seaborn scipy plotly


Recommended Environment:
- Python 3.8 or later
- Jupyter Notebook or a Python IDE (e.g., VS Code, PyCharm)
- Power BI (for integrated dashboard visualization)
Usage
1. Data Preparation
Ensure your dataset includes the following key financial metrics:
- Ticker: Asset identifier
- EPS_Growth %: Expected earnings per share growth percentage
- Weighted_Volatility: Historical volatility weighted by market exposure
- Open_MarketValueUSD: Total market value of the position
2. Running the Portfolio Analysis
Use the included Python scripts (portfolio_analysis.py) to generate the portfolio summary, risk metrics, and optimization models.
python portfolio_analysis.py


3. Visualization
- Seaborn & Matplotlib generate static risk-return plots
- Plotly enables interactive portfolio comparison
Modify config.py to adjust parameters such as risk-free rate assumptions and sector classifications.
Methodology
Markowitz Efficient Frontier Calculation
- Monte Carlo Simulations—Thousands of random portfolio weight allocations simulated to determine risk-adjusted returns.
- Risk Aversion Model—Tangential function applied to optimize portfolio selection based on risk-return tradeoffs.
- Sharpe Ratio Optimization—Comparing the current portfolio allocation against the maximum risk-adjusted return strategy.
- Scenario Analysis—Stress-testing portfolio performance under varied market conditions.
Performance Attribution
- Sector Breakdown: Identifies return drivers and underperforming asset classes
- Holding Period Analysis: Evaluates duration-based gains/losses
- Risk Management Review: Measures volatility deviations from projected benchmarks
Future Enhancements
- Dynamic Rebalancing Model—Automated recommendations for adjusting market exposures
- Factor Exposure Insights—Decomposing portfolio risk into macroeconomic and asset-specific drivers
- Enhanced Visualization—Integration with Power BI & interactive dashboards
Contributors
- Lead Analyst: RodWal Capital Consulting Team
- Data & Quant Models: Portfolio Risk & Optimization Division
- Development: Python-based analytics group


