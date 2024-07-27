import pandas as pd
import numpy as np
import os

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

### Create deciles/rank

# Function to rank stocks into deciles based on market cap
def rank_to_deciles(row):
    ranked = row.rank(method='first')
    deciles = pd.qcut(ranked, 10, labels=False) + 1  # Add 1 to make deciles 1-10
    return deciles

# Apply the ranking function to each row (each date)
deciles_df = mktcap_df.apply(rank_to_deciles, axis=1)

# =============================================================================

### Equal-weighted return

# Function to calculate equal-weighted return for each decile
def equal_weighted_return(date, deciles, returns):
    decile_returns = {}
    for decile in range(1, 11):
        stocks_in_decile = deciles[deciles == decile].index
        if len(stocks_in_decile) > 0:
            decile_returns[decile] = returns[stocks_in_decile].mean()
        else:
            decile_returns[decile] = np.nan
    return pd.Series(decile_returns)

# Apply the equal-weighted return calculation for each date
ewret_df = pd.DataFrame(index=ret_df.index)

for date in ret_df.index:
    deciles = deciles_df.loc[date]
    returns = ret_df.loc[date]
    ewret_df.loc[date] = equal_weighted_return(date, deciles, returns)

# =============================================================================

### Value-weighted return

# Function to calculate value-weighted return for each decile
def value_weighted_return(date, deciles, returns, market_caps):
    decile_returns = {}
    for decile in range(1, 11):
        stocks_in_decile = deciles[deciles == decile].index
        if len(stocks_in_decile) > 0:
            weights = market_caps[stocks_in_decile]
            weighted_returns = returns[stocks_in_decile] * weights
            decile_returns[decile] = weighted_returns.sum() / weights.sum()
        else:
            decile_returns[decile] = np.nan
    return pd.Series(decile_returns)

# Apply the value-weighted return calculation for each date
vwret_df = pd.DataFrame(index=ret_df.index)

for date in ret_df.index:
    deciles = deciles_df.loc[date]
    returns = ret_df.loc[date]
    market_caps = mktcap_df.loc[date]
    vwret_df.loc[date] = value_weighted_return(date, deciles, returns, market_caps)

# =============================================================================
# Top X largest stocks portfolios
# =============================================================================

### Preferences

# List of portfolio sizes
portfolio_sizes = [50, 100, 500, 1000]

# =============================================================================

### Equal-weighted return

# Initialize a DataFrame to store the results
topx_ew_df = pd.DataFrame(index=ret_df.index)

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
    topx_ew_df[size] = [np.nan] + portfolio_returns

# =============================================================================

### Value-weighted return

# Initialize a DataFrame to store the results
topx_vw_df = pd.DataFrame(index=ret_df.index)

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
    topx_vw_df[size] = [np.nan] + portfolio_returns

