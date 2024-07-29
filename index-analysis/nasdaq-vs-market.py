import pandas as pd
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
market = pd.read_csv(os.path.join(cwd, 'index-analysis/indexes.csv'))
nasdaq = pd.read_csv(os.path.join(cwd, 'index-analysis/nasdaq.csv'))

# =============================================================================
# Prepare data
# =============================================================================

# Convert `caldt` to datetime
market['caldt'] = pd.to_datetime(market['caldt'], format='%Y%m%d')
nasdaq['caldt'] = pd.to_datetime(nasdaq['caldt'], format='%Y%m%d')

# Set `caldt` as the index
market.set_index('caldt', inplace=True)
nasdaq.set_index('caldt', inplace=True)

# Filter the nasdaq dataframe to keep only rows with index >= '1972-12-14'
nasdaq = nasdaq.loc['1972-12-14':]

# Select and rename the required columns
market = market[['vwretd', 'ewretd']].rename(columns={'vwretd': 'market_vw', 'ewretd': 'market_ew'})
nasdaq = nasdaq[['vwretd', 'ewretd']].rename(columns={'vwretd': 'nasdaq_vw', 'ewretd': 'nasdaq_ew'})

# Merge the dataframes on their index
indexes = pd.merge(market, nasdaq, left_index=True, right_index=True, how='inner')

# =============================================================================
# Define date range for subsetting
# =============================================================================

# start_date = '2013-01-01'
# end_date = '2023-12-31'

# # Subset the prices DataFrame based on the date range
# indexes = indexes.loc[start_date:end_date]

# =============================================================================
# Calculate prices
# =============================================================================

# Set first row of returns to zero
indexes.iloc[0] = 0

# Compute compounded price for each column starting from 1
prices = (1 + indexes).cumprod()

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
