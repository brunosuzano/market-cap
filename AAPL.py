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
aapl = yf.Ticker("AAPL")
yfdata = aapl.history(period="max")
yfdata_alt = yf.download('AAPL')

# # Plot the Close price
# plt.figure(figsize=(24, 10))
# plt.plot(yfdata.index, yfdata['Close'], label='Close Price')
# plt.title('AAPL Close Price Over Time')
# plt.xlabel('Date')
# plt.ylabel('Close Price (USD)')
# plt.legend()
# plt.grid(True)
# plt.show()

# =============================================================================

### Checking dividend adjustments

# # Find the indices (dates) with the max dividend
# div_dates = yfdata[yfdata['Dividends'] == yfdata['Dividends'].max()].index

# # Create a list to store dates of interest
# dates_of_interest = []

# # Add the dates of the dividends and the dates immediately before and after
# for date in div_dates:
#     previous_date = date - pd.tseries.offsets.BDay(1)
#     next_date = date + pd.tseries.offsets.BDay(1)
    
#     if previous_date in yfdata.index:
#         dates_of_interest.append(previous_date)
#     dates_of_interest.append(date)
#     if next_date in yfdata.index:
#         dates_of_interest.append(next_date)

# # Remove duplicates and sort the dates
# dates_of_interest = sorted(set(dates_of_interest))

# # Create a new DataFrame with the selected rows
# split_data = yfdata.loc[dates_of_interest]

# =============================================================================

### Reverse dividends

# Retrieve historical market data
yfdata2 = yfdata

# Shift the Dividends column to get the next day's dividend
yfdata2['Dividends_next'] = yfdata2['Dividends'].shift(-1)

# Calculate the DivMult column based on the given condition
yfdata2['DivMult'] = yfdata2.apply(
    lambda row: 1 if row['Dividends_next'] == 0 else (1 - row['Dividends_next'] / row['Close']),
    axis=1
)

# Set the last observation of DivMult to 1
yfdata2.at[yfdata2.index[-1], 'DivMult'] = 1

# Initialize the cumulative multiplier with 1 at the end
yfdata2['CumMult'] = 1

# Calculate the cumulative multiplier starting from the end
for i in range(len(yfdata2) - 2, -1, -1):
    current_index = yfdata2.index[i]
    next_index = yfdata2.index[i + 1]
    if yfdata2.at[next_index, 'Dividends'] != 0:
        yfdata2.at[current_index, 'CumMult'] = yfdata2.at[next_index, 'CumMult'] * yfdata2.at[next_index, 'DivMult']
    else:
        yfdata2.at[current_index, 'CumMult'] = yfdata2.at[next_index, 'CumMult']

# Calculate the Adj Close by multiplying Close by CumMult
yfdata2['Adj Close'] = yfdata2['Close'] * yfdata2['CumMult']

# Drop the Dividends_next column as it's no longer needed
yfdata2.drop(columns=['Dividends_next'], inplace=True)

# =============================================================================

### Checking split adjustments

# # Find the indices (dates) where Stock Splits are equal to 7
# split_dates = yfdata[yfdata['Stock Splits'] == 7].index

# # Create a list to store dates of interest
# dates_of_interest = []

# # Add the dates of the splits and the dates immediately before and after
# for date in split_dates:
#     previous_date = date - pd.tseries.offsets.BDay(1)
#     next_date = date + pd.tseries.offsets.BDay(1)
    
#     if previous_date in yfdata.index:
#         dates_of_interest.append(previous_date)
#     dates_of_interest.append(date)
#     if next_date in yfdata.index:
#         dates_of_interest.append(next_date)

# # Remove duplicates and sort the dates
# dates_of_interest = sorted(set(dates_of_interest))

# # Create a new DataFrame with the selected rows
# split_data = yfdata.loc[dates_of_interest]

# =============================================================================

### Reverse splits

# Ensure the 'Stock Splits' column is filled with 1.0 where no split occurred
yfdata2['Stock Splits'] = yfdata2['Stock Splits'].replace(0, 1)

# Calculate the cumulative product of stock splits in reverse order
yfdata2['Reverse Cumulative Splits'] = yfdata2['Stock Splits'][::-1].cumprod()[::-1]

# Calculate the unadjusted close price
yfdata2['Unadjusted Close'] = yfdata2['Close'] * yfdata2['Reverse Cumulative Splits']

# =============================================================================
# CRSP Data
# =============================================================================

# Path to data directory
filepath = os.getcwd()

# Import CRSP data
crspdata = pd.read_csv(f'{filepath}\\AAPL.csv')

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
yfdata2.index = yfdata2.index.tz_localize(None)

# Find the minimum and maximum dates in each DataFrame
min_date_yf = yfdata2.index.min()
max_date_yf = yfdata2.index.max()
min_date_crsp = crspdata['datadate'].min()
max_date_crsp = crspdata['datadate'].max()

# Determine the largest of the minimum dates and the smallest of the maximum dates
largest_min_date = max(min_date_yf, min_date_crsp)
smallest_max_date = min(max_date_yf, max_date_crsp)

# Subset both DataFrames to only include data between these dates
yfdata3 = yfdata2.loc[largest_min_date:smallest_max_date]
yfdata_alt = yfdata_alt.loc[largest_min_date:smallest_max_date]
crspdata3 = crspdata[(crspdata['datadate'] >= largest_min_date) & (crspdata['datadate'] <= smallest_max_date)]

# Create a new DataFrame from yfdata3 with the required columns
mergeddf = yfdata3[['Close', 'Unadjusted Close']].reset_index(drop=False)

# Perform an outer join with crspdata3 on the date columns
mergeddf = pd.merge(mergeddf, crspdata3[['datadate', 'ajprc', 'prccd']], left_on='Date',
                    right_on='datadate', how='outer', indicator=True)

# Check the rows that are in only one dataset
unmatched_rows = mergeddf[mergeddf['_merge'] != 'both']
print("Unmatched Rows:")
print(unmatched_rows)

# Rename the columns for clarity
mergeddf.rename(columns={'Date': 'date', 'Close': 'ajprice_yf', 'Unadjusted Close': 'price_yf',
                         'ajprc': 'ajprice_crsp', 'prccd': 'price_crsp'}, inplace=True)

# Handle missing values
mergeddf['date'] = mergeddf['date'].combine_first(mergeddf['datadate'])

# Drop the duplicate datadate column
mergeddf.drop(columns=['datadate'], inplace=True)

# Order by the date column
mergeddf = mergeddf.sort_values(by='date').reset_index(drop=True)

# Set the date column as the index
mergeddf.set_index('date', inplace=True)

# =============================================================================

# Plot the adjusted price
plt.figure(figsize=(24, 10))
plt.plot(mergeddf.index, mergeddf['ajprice_yf'], label='ajprice_yf')
plt.plot(mergeddf.index, mergeddf['ajprice_crsp'], label='ajprice_crsp')
plt.title('Adjusted Price Comparison: ajprice_yf vs. ajprice_crsp')
plt.xlabel('Date')
plt.ylabel('Adjusted Price')
plt.legend()
plt.grid(True)
plt.show()

# Plot the unadjusted price
plt.figure(figsize=(24, 10))
plt.plot(mergeddf.index, mergeddf['price_yf'], label='price_yf')
plt.plot(mergeddf.index, mergeddf['price_crsp'], label='price_crsp')
plt.title('Unadjusted Price Comparison: price_yf vs. price_crsp')
plt.xlabel('Date')
plt.ylabel('Unadjusted Price')
plt.legend()
plt.grid(True)
plt.show()