############################## Market Cap Project #############################

### Setup ###

# Import libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Read the .csv file
file_path = '//lancs/homes/09/suzanode/My Documents/Code/Market Cap/IndexData.csv'
indexdata = pd.read_csv(file_path)

# Select only the required columns
indexdata = indexdata[['datadate', 'conm', 'prccm']]

# Rename the columns
indexdata.rename(columns={'datadate': 'Date', 'conm': 'Index', 'prccm': 'Price'}, inplace=True)

# Convert the date column to datetime format
indexdata['Date'] = pd.to_datetime(indexdata['Date'])

# Drop duplicates
indexdata = indexdata.drop_duplicates(subset=['Date', 'Index'])

# Pivot the DataFrame to have index names as columns and dates as the index
indexpivot = indexdata.pivot(index='Date', columns='Index', values='Price')

# Drop columns (indices) that do not have a price value on the last day
last_day = indexpivot.index[-1]
indexpivot = indexpivot.dropna(axis=1, subset=[last_day])

###############################################################################

### Calculate metrics ###

# Calculate daily returns
returns = indexpivot.pct_change().dropna()

# Function to calculate CAGR
def calculate_cagr(initial_value, final_value, periods):
    return (final_value / initial_value) ** (1 / periods) - 1

# Function to calculate annualized volatility
def calculate_volatility(returns):
    return returns.std() * np.sqrt(252)  # Assuming 252 trading days in a year

# Assuming a risk-free rate (e.g., 2%)
risk_free_rate = 0.02

# Function to calculate Sharpe ratio
def calculate_sharpe_ratio(returns, risk_free_rate):
    excess_returns = returns.mean() * 252 - risk_free_rate
    annualized_volatility = returns.std() * np.sqrt(252)
    return excess_returns / annualized_volatility

# Initialize lists to store results
cagr_list = []
volatility_list = []
sharpe_ratio_list = []

# Calculate metrics for each index
for index in indexpivot.columns:
    initial_value = indexpivot[index].dropna().iloc[0]
    final_value = indexpivot[index].dropna().iloc[-1]
    periods = len(indexpivot[index].dropna()) / 252  # Assuming 252 trading days in a year
    
    cagr = calculate_cagr(initial_value, final_value, periods)
    volatility = calculate_volatility(returns[index])
    sharpe_ratio = calculate_sharpe_ratio(returns[index], risk_free_rate)
    
    cagr_list.append(cagr)
    volatility_list.append(volatility)
    sharpe_ratio_list.append(sharpe_ratio)

# Create a DataFrame to store the results
results_df = pd.DataFrame({
    'Index': indexpivot.columns,
    'CAGR': cagr_list,
    'Volatility': volatility_list,
    'Sharpe Ratio': sharpe_ratio_list
})
















# Retrieve unique indices and convert to DataFrame
unique_indices = indexdata['Index'].unique()
indices_df = pd.DataFrame(unique_indices, columns=['Index'])

# Count the number of columns
num_columns = indexpivot.shape[1]
print(f'The number of indices is: {num_columns}')

# Filter the pivoted DataFrame to include only the first 50 indices
filtered = indexpivot[unique_indices[:50]]

# Plot the time series for the first 50 indices
filtered.plot(figsize=(15, 10), legend=True)

# Adding labels and title
plt.xlabel('Date')
plt.ylabel('Price')
plt.title('Price Series for the First 50 Indices')
plt.legend(title='Index', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True)
plt.tight_layout()
plt.show()