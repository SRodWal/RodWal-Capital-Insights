import pandas as pd
import yfinance as yf
import seaborn as sns
import matplotlib.pyplot as plt
import webbrowser
import os, sys
import sqlite3
import streamlit as st

# List of stock tickers and chapters:
portfolio_dir = r'Stock Selection/tickers_used.xlsx'
portfolio_df = pd.read_excel(portfolio_dir)[['Chapter','Name','Ticker','GICS Sector']]
portfolio_df = portfolio_df.loc[portfolio_df['Chapter']=="ETF"]

# Create GUI
st.title("Stock Correlation Matrix")
chapters = st.sidebar.multiselect("Select Chapters", options=portfolio_df['Chapter'].unique(), default=portfolio_df['Chapter'].unique())
sectors = st.sidebar.multiselect("Select Sectors", options=portfolio_df['GICS Sector'].unique(), default=portfolio_df['GICS Sector'].unique())

filtered_df = portfolio_df.copy()
if chapters:
    filtered_df = filtered_df[filtered_df['Chapter'].isin(chapters)]
if sectors:
    filtered_df = filtered_df[filtered_df['GICS Sector'].isin(sectors)]

tickers = st.sidebar.multiselect("Select Tickers", options=filtered_df['Ticker'].unique(), default=filtered_df['Ticker'].unique())

st.write('### Selected Tickers')
st.dataframe(filtered_df[filtered_df['Ticker'].isin(tickers)])

if tickers:
    # Query Internal Database:
    db_path = "Database/stock_history.db"
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM prices"
    df = pd.read_sql(query, conn)
    conn.close()

    # Manipulate DataFrame; Fix date formats,
    df['date'] = pd.to_datetime(df['date'])
    df_filtered = df[df['ticker'].isin(tickers)]
    pivot_df = df_filtered.pivot(index='date', columns='ticker', values='adj_close')

    # Compute correlation matrix
    correlation_matrix = pivot_df.corr()

    # Save correlation matrix to CSV
    correlation_matrix.to_csv("correlation_matrix.csv")

    # Create a heatmap and save as HTML
    plt.figure(figsize=(10, 8))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title("Stock Correlation Matrix")
    plt.tight_layout()

    # Save the plot as an image
    plot_filename = "correlation_heatmap.png"
    plt.savefig(plot_filename)

    # Generate HTML file to display the image
    html_content = f"""
    <html>
    <head><title>Correlation Heatmap</title></head>
    <body>
    <h2>Correlation Heatmap</h2>
    <img src="{plot_filename}" alt="Correlation Heatmap">
    </body>
    </html>
    """

    html_filename = "correlation_heatmap.html"
    with open(html_filename, "w") as f:
        f.write(html_content)

    # Open the HTML file in the default web browser
    webbrowser.open('file://' + os.path.realpath(html_filename))

    print("Correlation matrix saved to 'correlation_matrix.csv' and heatmap displayed in browser.")
else:
    st.warning("Please select at least one ticker to view the correlation matrix.")

if __name__ == "__main__":
    # Run the Streamlit app
    os.system(f"streamlit run {sys.argv[0]}")
