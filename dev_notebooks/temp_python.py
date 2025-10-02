import pandas as pd

# Load the Parquet file
df = pd.read_parquet('your_file.parquet')

# Write to CSV
df.to_csv('your_file.csv', index=False)
