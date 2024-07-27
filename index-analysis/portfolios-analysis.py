import pandas as pd
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk

# =============================================================================
# Import data
# =============================================================================

# Get the current working directory
cwd = os.getcwd()

# Import data
portfolios = pd.read_csv(os.path.join(cwd, 'portfolios.csv'))

# =============================================================================
# Prepare data
# =============================================================================

# Convert `caldt` to datetime
portfolios['caldt'] = pd.to_datetime(portfolios['caldt'], format='%Y%m%d')

# Preserve the order of 'prtnam' values
prtnam_order = portfolios['prtnam'].unique()

# Pivot the DataFrame
portfolios = portfolios.pivot(index='caldt', columns='prtnam', values='totret')

# Reorder the columns based on the preserved order
portfolios = portfolios[prtnam_order]

# Drop the first row and the `sprtrn` column
portfolios = portfolios.drop(portfolios.index[0])

# Compute compounded price for each column starting from 1
prices = (1 + portfolios).cumprod()

# =============================================================================
# Define date range for subsetting
# =============================================================================

start_date = '1990-01-01'
end_date = '2023-12-31'

# Subset the prices DataFrame based on the date range
prices = prices.loc[start_date:end_date]

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
