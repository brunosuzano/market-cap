import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

# =============================================================================
# Import data
# =============================================================================

# Get the current working directory
cwd = os.getcwd()

# Import data
crsp = pd.read_csv(os.path.join(cwd, 'custom-portfolios/crspm.csv'))

# =============================================================================
# Prepare data
# =============================================================================

### Clean data

# Convert the date column to datetime (assuming the column is named 'date')
crsp['date'] = pd.to_datetime(crsp['date'], format='%Y%m%d')

# Keep only rows where EXCHCD is equal to 1, 2, or 3
crsp = crsp[crsp['EXCHCD'].isin([1, 2, 3])]

# Keep only rows where EXCHCD is equal to 1, 2, or 3
crsp = crsp[crsp['SHRCD'].isin([10, 11, 12])]

# # Subset to only include rows where SHRCD is equal to 12
# subset_crsp = crsp[crsp['SHRCD'] == 12]

# # Subset to include only rows where the date is in 2023
# subset_crsp = subset_crsp[subset_crsp['date'].dt.year == 2023]

# Create the MKTCAP column as the product of PRC and SHROUT
crsp['MKTCAP'] = abs(crsp['PRC']) * crsp['SHROUT']

# Convert RET column to numeric, coercing errors to NaN
crsp['RET'] = pd.to_numeric(crsp['RET'], errors='coerce')

# Find the number of instances where RET is smaller than -60
num_instances = (crsp['RET'] < -60).sum()

# Convert values smaller than -60 in RET to NaN
crsp.loc[crsp['RET'] < -60, 'RET'] = pd.NA

print(f"Number of instances where RET < -60: {num_instances}")

# Convert PRC column to numeric, coercing errors to NaN
crsp['PRC'] = pd.to_numeric(crsp['PRC'], errors='coerce')

# =============================================================================

# Pivot for TICKER
ticker_df = crsp.pivot_table(index='date', columns='PERMNO', values='TICKER', aggfunc='first')

# Pivot for PRC
prc_df = crsp.pivot_table(index='date', columns='PERMNO', values='PRC', aggfunc='first')

# Pivot for RET
ret_df = crsp.pivot_table(index='date', columns='PERMNO', values='RET', aggfunc='first')

# Pivot for MKTCAP
mktcap_df = crsp.pivot_table(index='date', columns='PERMNO', values='MKTCAP', aggfunc='first')

# Pivot for vwretd
vwretd_df = crsp.pivot_table(index='date', columns='PERMNO', values='vwretd', aggfunc='first')

# Pivot for vwretd
ewretd_df = crsp.pivot_table(index='date', columns='PERMNO', values='ewretd', aggfunc='first')

# Forward fill the missing values across rows for both vwretd and ewretd
vwretd_df.ffill(axis=1, inplace=True)
ewretd_df.ffill(axis=1, inplace=True)

# Extract the continuous vwretd nad ewretd time series by taking the first non-NaN value across columns for each row
vwretd_df = vwretd_df.bfill(axis=1).iloc[:, 0].rename('vwretd')
ewretd_df = ewretd_df.bfill(axis=1).iloc[:, 0].rename('ewretd')

# =============================================================================
# Decile portfolios
# =============================================================================

## Create deciles/rank

# Function to rank stocks into deciles based on market cap
def rank_to_deciles(row):
    ranked = row.rank(method='first')
    deciles = pd.qcut(ranked, 10, labels=False) + 1  # Add 1 to make deciles 1-10
    return deciles

# Apply the ranking function to each row (each date)
deciles_df = mktcap_df.apply(rank_to_deciles, axis=1)

# # Function to rank stocks into deciles based on market cap, considering only stocks with returns in the next period
# def rank_to_deciles(row, next_returns):
#     valid_stocks = row.dropna().index.intersection(next_returns.dropna().index)
#     ranked = row[valid_stocks].rank(method='first')
#     deciles = pd.qcut(ranked, 10, labels=False) + 1  # Add 1 to make deciles 1-10

#     # Create a full series initialized to NaN and update with deciles
#     full_deciles = pd.Series(np.nan, index=row.index)
#     full_deciles[valid_stocks] = deciles
#     return full_deciles

# # Apply the ranking function to each row (each date), considering the returns of the next period
# deciles_df = pd.DataFrame(index=mktcap_df.index, columns=mktcap_df.columns)

# for i in range(len(mktcap_df) - 1):
#     current_date = mktcap_df.index[i]
#     next_date = mktcap_df.index[i + 1]

#     current_market_caps = mktcap_df.loc[current_date]
#     next_returns = ret_df.loc[next_date]

#     deciles_df.loc[current_date] = rank_to_deciles(current_market_caps, next_returns)

# # Forward fill the last date to ensure all dates are covered
# deciles_df.loc[mktcap_df.index[-1]] = np.nan

# =============================================================================

### Equal-weighted return

# Function to calculate equal-weighted return for each decile
def equal_weighted_return(prev_deciles, curr_returns):
    decile_returns = {}
    for decile in range(1, 11):
        stocks_in_decile = prev_deciles[prev_deciles == decile].index
        valid_stocks = stocks_in_decile.intersection(curr_returns.dropna().index)
        if len(valid_stocks) > 0:
            decile_returns[decile] = curr_returns[valid_stocks].mean()
        else:
            decile_returns[decile] = np.nan
    return pd.Series(decile_returns)

# Apply the equal-weighted return calculation for each date
ewret_df = pd.DataFrame(index=ret_df.index, columns=range(1, 11))

# Loop through each date starting from the second date
for i in range(1, len(ret_df)):
    prev_date = ret_df.index[i - 1]
    curr_date = ret_df.index[i]

    prev_deciles = deciles_df.loc[prev_date]
    curr_returns = ret_df.loc[curr_date]

    ewret_df.loc[curr_date] = equal_weighted_return(prev_deciles, curr_returns)

# Add prefix to each column name
ewret_df = ewret_df.add_prefix('dec_ew_')

# =============================================================================

### Value-weighted return

# Function to calculate value-weighted return for each decile
def value_weighted_return(prev_deciles, curr_returns, prev_market_caps):
    decile_returns = {}
    for decile in range(1, 11):
        stocks_in_decile = prev_deciles[prev_deciles == decile].index
        valid_stocks = stocks_in_decile.intersection(curr_returns.dropna().index)
        if len(valid_stocks) > 0:
            weights = prev_market_caps[valid_stocks]
            weighted_returns = curr_returns[valid_stocks] * weights
            decile_returns[decile] = weighted_returns.sum() / weights.sum()
        else:
            decile_returns[decile] = np.nan
    return pd.Series(decile_returns)

# Apply the value-weighted return calculation for each date
vwret_df = pd.DataFrame(index=ret_df.index, columns=range(1, 11))

# Loop through each date starting from the second date
for i in range(1, len(ret_df)):
    prev_date = ret_df.index[i - 1]
    curr_date = ret_df.index[i]

    prev_deciles = deciles_df.loc[prev_date]
    curr_returns = ret_df.loc[curr_date]
    prev_market_caps = mktcap_df.loc[prev_date]

    vwret_df.loc[curr_date] = value_weighted_return(prev_deciles, curr_returns, prev_market_caps)

# Add prefix to each column name
vwret_df = vwret_df.add_prefix('dec_vw_')

# =============================================================================
# Top X largest stocks portfolios (monthly)
# =============================================================================

### Preferences

# List of portfolio sizes
portfolio_sizes = [50, 100, 500, 1000]

# =============================================================================

### Equal-weighted return

# Initialize a DataFrame to store the results
topxm_ew_df = pd.DataFrame(index=ret_df.index)

# Loop through each portfolio size
for size in portfolio_sizes:
    portfolio_returns = []

    # Loop through each date starting from the second date
    for i in range(1, len(ret_df)):
        prev_date = ret_df.index[i - 1]
        curr_date = ret_df.index[i]

        # Check if the portfolio size exceeds the number of available stocks
        actual_size = min(size, mktcap_df.loc[prev_date].dropna().size)

        # Get the largest X stocks based on the market cap of the previous date
        largest_stocks = mktcap_df.loc[prev_date].nlargest(actual_size).index

        # Filter out the stocks that do not exist in the current period
        available_stocks = ret_df.loc[curr_date].dropna().index
        valid_stocks = largest_stocks.intersection(available_stocks)

        # Calculate the equal-weighted return for these stocks on the current date
        if len(valid_stocks) > 0:
            portfolio_return = ret_df.loc[curr_date, valid_stocks].mean()
        else:
            portfolio_return = np.nan

        portfolio_returns.append(portfolio_return)

    # Add the portfolio returns to the DataFrame
    topxm_ew_df[size] = [np.nan] + portfolio_returns

# Add prefix to each column name
topxm_ew_df = topxm_ew_df.add_prefix('topx_m_ew_')

# =============================================================================

### Value-weighted return

# Initialize a DataFrame to store the results
topxm_vw_df = pd.DataFrame(index=ret_df.index)

# Loop through each portfolio size
for size in portfolio_sizes:
    portfolio_returns = []

    # Loop through each date starting from the second date
    for i in range(1, len(ret_df)):
        prev_date = ret_df.index[i - 1]
        curr_date = ret_df.index[i]

        # Check if the portfolio size exceeds the number of available stocks
        actual_size = min(size, mktcap_df.loc[prev_date].dropna().size)

        # Get the largest X stocks based on the market cap of the previous date
        largest_stocks = mktcap_df.loc[prev_date].nlargest(actual_size).index

        # Filter out the stocks that do not exist in the current period
        available_stocks = ret_df.loc[curr_date].dropna().index
        valid_stocks = largest_stocks.intersection(available_stocks)

        # Calculate the value-weighted return for these stocks on the current date
        if len(valid_stocks) > 0:
            weights = mktcap_df.loc[prev_date, valid_stocks]
            weighted_returns = ret_df.loc[curr_date, valid_stocks] * weights
            portfolio_return = weighted_returns.sum() / weights.sum()
        else:
            portfolio_return = np.nan

        portfolio_returns.append(portfolio_return)

    # Add the portfolio returns to the DataFrame
    topxm_vw_df[size] = [np.nan] + portfolio_returns

# Add prefix to each column name
topxm_vw_df = topxm_vw_df.add_prefix('topx_m_vw_')

# =============================================================================
# Top X largest stocks portfolios (yearly)
# =============================================================================

### Preferences

# List of portfolio sizes
portfolio_sizes = [50, 100, 500, 1000]

# =============================================================================

### Equal-weighted return

# Initialize a DataFrame to store the results
topxy_ew_df = pd.DataFrame(index=ret_df.index)

# Function to get the last business day of December for each year
def get_end_of_year_dates(df):
    return df.groupby(df.index.year).apply(lambda x: x.loc[x.index.month == 12].index.max()).tolist()

# Get the end-of-year dates
end_of_year_dates = get_end_of_year_dates(mktcap_df)

# Dictionary to store the ranks for each year
yearly_ranks = {}

# Loop through each end-of-year date to assign ranks based on market cap
for date in end_of_year_dates:
    next_year = date.year + 1
    if next_year in mktcap_df.index.year:
        end_of_year_market_caps = mktcap_df.loc[date]
        yearly_ranks[next_year] = end_of_year_market_caps.rank(ascending=False)

# Loop through each portfolio size
for size in portfolio_sizes:
    portfolio_returns = []

    # Loop through each date starting from the second date
    for i in range(1, len(ret_df)):
        curr_date = ret_df.index[i]
        curr_year = curr_date.year

        # Use the ranks for the current year
        if curr_year in yearly_ranks:
            prev_ranks = yearly_ranks[curr_year]

            # Get the largest X stocks based on the ranks of the previous year
            largest_stocks = prev_ranks.nsmallest(size).index

            # Filter out the stocks that do not exist in the current period
            available_stocks = ret_df.loc[curr_date].dropna().index
            valid_stocks = largest_stocks.intersection(available_stocks)

            # Calculate the equal-weighted return for these stocks on the current date
            if len(valid_stocks) > 0:
                portfolio_return = ret_df.loc[curr_date, valid_stocks].mean()
            else:
                portfolio_return = np.nan
        else:
            portfolio_return = np.nan

        portfolio_returns.append(portfolio_return)

    # Add the portfolio returns to the DataFrame
    topxy_ew_df[size] = [np.nan] + portfolio_returns

# Add prefix to each column name
topxy_ew_df = topxy_ew_df.add_prefix('topx_y_ew_')

# =============================================================================

### Value-weighted return

# Initialize a DataFrame to store the results
topxy_vw_df = pd.DataFrame(index=ret_df.index)

# Function to get the last business day of December for each year
def get_end_of_year_dates(df):
    return df.groupby(df.index.year).apply(lambda x: x.loc[x.index.month == 12].index.max()).tolist()

# Get the end-of-year dates
end_of_year_dates = get_end_of_year_dates(mktcap_df)

# Dictionary to store the ranks for each year
yearly_ranks = {}

# Loop through each end-of-year date to assign ranks based on market cap
for date in end_of_year_dates:
    next_year = date.year + 1
    if next_year in mktcap_df.index.year:
        end_of_year_market_caps = mktcap_df.loc[date]
        yearly_ranks[next_year] = end_of_year_market_caps.rank(ascending=False)

# Loop through each portfolio size
for size in portfolio_sizes:
    portfolio_returns = []

    # Loop through each date starting from the second date
    for i in range(1, len(ret_df)):
        curr_date = ret_df.index[i]
        curr_year = curr_date.year

        # Use the ranks for the current year
        if curr_year in yearly_ranks:
            prev_ranks = yearly_ranks[curr_year]

            # Get the largest X stocks based on the ranks of the previous year
            largest_stocks = prev_ranks.nsmallest(size).index

            # Filter out the stocks that do not exist in the current period
            available_stocks = ret_df.loc[curr_date].dropna().index
            valid_stocks = largest_stocks.intersection(available_stocks)

            # Calculate the value-weighted return for these stocks on the current date
            if len(valid_stocks) > 0:
                weights = mktcap_df.loc[curr_date, valid_stocks]
                weighted_returns = ret_df.loc[curr_date, valid_stocks] * weights
                portfolio_return = weighted_returns.sum() / weights.sum()
            else:
                portfolio_return = np.nan
        else:
            portfolio_return = np.nan

        portfolio_returns.append(portfolio_return)

    # Add the portfolio returns to the DataFrame
    topxy_vw_df[size] = [np.nan] + portfolio_returns

# Add prefix to each column name
topxy_vw_df = topxy_vw_df.add_prefix('topx_y_vw_')

# =============================================================================
# Merge and select sample period
# =============================================================================

# List of dataframes to merge
dfs = [
    ewret_df, vwret_df,
    topxm_ew_df, topxm_vw_df,
    topxy_ew_df, topxy_vw_df
]

# Initialize the merged dataframe
portfolios = pd.DataFrame(index=ret_df.index)

# Merge dataframes
for df in dfs:
    if 'df' in locals():
        portfolios = portfolios.join(df, how='outer')

# =============================================================================

start_date = '1990-01-01'
end_date = '2023-12-31'

# Subset the prices DataFrame based on the date range
portfolios = portfolios.loc[start_date:end_date]

# =============================================================================
# Compute prices and merge
# =============================================================================

# Function to calculate cumulative price
def calculate_cumulative_price(returns_df):
    returns_df.iloc[0] = 0  # Set the first row to 0
    cumulative_price_df = (1 + returns_df).cumprod()
    cumulative_price_df.iloc[0] = 1  # Set the initial price to 1
    return cumulative_price_df

# Calculate cumulative prices for each returns DataFrame
prices = calculate_cumulative_price(portfolios)

# =============================================================================
# Create interactive plot
# =============================================================================

# Predefined colors for each series
colors = plt.cm.tab10.colors
color_map = {series: colors[i % len(colors)] for i, series in enumerate(prices.columns)}

# Function to plot selected series
def plot_series(selected_series):
    ax.clear()  # Clear the previous plot
    for series in selected_series:
        ax.plot(prices.index, prices[series], label=series, color=color_map[series])
    ax.set_xlabel('Date')
    ax.set_ylabel('Compounded Price')
    ax.set_title('Compounded Price Series')
    ax.legend()
    ax.grid(True)
    canvas.draw()

# Create the main window
window = tk.Tk()
window.title("Compounded Prices Plotter")

# Create a frame for the controls
frame = tk.Frame(window)
frame.pack(side=tk.TOP, fill=tk.X)

# Create a listbox for series selection with multiple selection enabled
series_listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, exportselection=0)
for col in prices.columns:
    series_listbox.insert(tk.END, col)
series_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

# Create a button to update the plot
def on_plot_button_click():
    selected_indices = series_listbox.curselection()
    selected_series = [prices.columns[i] for i in selected_indices]
    plot_series(selected_series)

plot_button = tk.Button(frame, text="Plot", command=on_plot_button_click)
plot_button.pack(side=tk.LEFT, padx=10)

# Create the initial plot
fig, ax = plt.subplots(figsize=(10, 6))
canvas = FigureCanvasTkAgg(fig, master=window)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Start the Tkinter event loop
window.mainloop()
