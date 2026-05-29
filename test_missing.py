import pandas as pd
import numpy as np

df = pd.read_csv('data/processed/stress_index.csv').dropna()
df = df.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)

df['rain_z_lag1']  = df.groupby('oblast')['rain_zscore'].shift(1)
df['rain_z_lag2']  = df.groupby('oblast')['rain_zscore'].shift(2)
df['temp_z_lag1']  = df.groupby('oblast')['temp_zscore'].shift(1)
df['temp_z_lag2']  = df.groupby('oblast')['temp_zscore'].shift(2)
df['soil_z_lag1']  = df.groupby('oblast')['soil_zscore'].shift(1)
df['soil_z_lag2']  = df.groupby('oblast')['soil_zscore'].shift(2)

FEATURES = [
    'month_sin', 'month_cos',
    'rain_z_lag1', 'rain_z_lag2', 'rain_z_roll3', 'rain_z_trend',
    'temp_z_lag1', 'temp_z_lag2', 'temp_z_roll3',
    'soil_z_lag1', 'soil_z_lag2', 'soil_z_roll3',
    'roll3_lag1',
]

df_feat = df.dropna(subset=['rain_z_lag1']) # just check one feature
print("Total after shift:", len(df_feat))
for ob in ['Severo-kazachstanskaya', 'Vostochno-kazachstanskaya', 'Yujno-kazachstanskaya', 'Zapadno-kazachstanskaya']:
    print(ob, len(df_feat[df_feat['oblast'] == ob]))
