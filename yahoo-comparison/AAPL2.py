import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import os

# Sample period
# startdate = pd.to_datetime('20230102', format='%Y%m%d')
# enddate = pd.to_datetime('20230104', format='%Y%m%d')

# =============================================================================
#  Yahoo Finance Data
# =============================================================================

# Download historical stock data for AAPL
yfdata = yf.download('AAPL')

# Calculate (adjusted) returns
yfdata['Return'] = yfdata['Adj Close'].pct_change() * 100

# =============================================================================
# CRSP Data
# =============================================================================

# Path to data directory
filepath = os.getcwd()

# Import CRSP data
crspdata = pd.read_csv(f'{filepath}\\AAPL.csv')

# Keep only the necessary columns
crspdata = crspdata[['datadate', 'GVKEY', 'prccd', 'ajexdi', 'trfd']]

# Convert 'datadate' to datetime format
crspdata['datadate'] = pd.to_datetime(crspdata['datadate'], format='%Y%m%d')

# Drop duplicate rows based on datadate and GVKEY
crspdata = crspdata.drop_duplicates(subset=['datadate', 'GVKEY'])

# Ensure data is sorted by 'datadate'
crspdata = crspdata.sort_values('datadate')

# Shift the columns to get the prior period's values
crspdata['prccd_prior'] = crspdata['prccd'].shift(1)
crspdata['ajexdi_prior'] = crspdata['ajexdi'].shift(1)
crspdata['trfd_prior'] = crspdata['trfd'].shift(1)

# Adjusted price
crspdata['ajprc'] = (crspdata['prccd'] / crspdata['ajexdi']) * crspdata['trfd']

# Adjusted return
crspdata['ajret'] = (((((crspdata['prccd'] / crspdata['ajexdi']) * crspdata['trfd']) /
                             ((crspdata['prccd_prior'] / crspdata['ajexdi_prior']) * crspdata['trfd_prior'])) - 1) * 100)

# Drop rows with NaN values for key variables
crspdata = crspdata.dropna(subset=['datadate'])
crspdata = crspdata.dropna(subset=['ajprc'])

# =============================================================================
# Merged Dataset
# =============================================================================

### Subset and join both datasets

# Remove timezone from yfdata index
yfdata.index = yfdata.index.tz_localize(None)

# Find the minimum and maximum dates in each DataFrame
min_date_yf = yfdata.index.min()
max_date_yf = yfdata.index.max()
min_date_crsp = crspdata['datadate'].min()
max_date_crsp = crspdata['datadate'].max()

# Determine the largest of the minimum dates and the smallest of the maximum dates
largest_min_date = max(min_date_yf, min_date_crsp)
smallest_max_date = min(max_date_yf, max_date_crsp)

# Subset both DataFrames to only include data between these dates
yfdata = yfdata.loc[largest_min_date:smallest_max_date]
crspdata = crspdata[(crspdata['datadate'] >= largest_min_date) & (crspdata['datadate'] <= smallest_max_date)]

# Create a new DataFrame from yfdata3 with the required columns
mergeddf = yfdata[['Adj Close', 'Return']].reset_index(drop=False)

# Perform an outer join with crspdata on the date columns
mergeddf = pd.merge(mergeddf, crspdata[['datadate', 'ajprc', 'ajret']], left_on='Date',
                    right_on='datadate', how='outer', indicator=True)

# Check the rows that are in only one dataset
unmatched_rows = mergeddf[mergeddf['_merge'] != 'both']
print("Unmatched Rows:")
print(unmatched_rows)

# Rename the columns for clarity
mergeddf.rename(columns={'Date': 'date', 'Adj Close': 'prc_yf', 'Return': 'ret_yf',
                         'ajprc': 'prc_crsp', 'ajret': 'ret_crsp'}, inplace=True)

# Handle missing values
mergeddf['date'] = mergeddf['date'].combine_first(mergeddf['datadate'])

# Drop the duplicate datadate column
mergeddf.drop(columns=['datadate'], inplace=True)

# Order by the date column
mergeddf = mergeddf.sort_values(by='date').reset_index(drop=True)

# Set the date column as the index
mergeddf.set_index('date', inplace=True)

# Calculate the correlation between 'ret_yf' and 'ret_crsp' ignoring NaN values
correlation = mergeddf['ret_yf'].corr(mergeddf['ret_crsp'])

# Print the correlation
print("Correlation between 'ret_yf' and 'ret_crsp':", correlation)

# =============================================================================
# Plot
# =============================================================================

# Plot the (adjusted) price
plt.figure(figsize=(24, 10))
plt.plot(mergeddf.index, mergeddf['prc_yf'], label='YF Price')
plt.plot(mergeddf.index, mergeddf['prc_crsp'], label='CRSP Price')
plt.title('Price (Adjusted)')
plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.grid(True)
plt.show()
