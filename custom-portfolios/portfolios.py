import pandas as pd
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
