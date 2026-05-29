#!/usr/bin/env python3
"""
scripts/compute_stress.py
Computes drought stress labels from CHIRPS rainfall anomalies and creates Z-score features.
Input:  data/processed/chirps_by_oblast.csv
Output: data/processed/stress_index.csv
"""
import pandas as pd
import numpy as np
import os

INPUT_CLIMATE = 'data/processed/climate_by_oblast.csv'
INPUT_SOIL    = 'data/processed/openmeteo_by_oblast.csv'
INPUT_SCRAPED = 'data/processed/scraped_features_by_oblast.csv'
OUTPUT_PATH   = 'data/processed/stress_index.csv'

print("Loading Climate and Soil Moisture data...")
df_clim = pd.read_csv(INPUT_CLIMATE)
df_soil = pd.read_csv(INPUT_SOIL)
if os.path.exists(INPUT_SCRAPED):
    df_scraped = pd.read_csv(INPUT_SCRAPED)
else:
    df_scraped = None

df = pd.merge(df_clim, df_soil, on=['oblast', 'year', 'month'], how='left')
if df_scraped is not None:
    df = pd.merge(df, df_scraped, on=['oblast', 'year', 'month'], how='left')

# Forward fill Soil Moisture for missing months
df['soil_moisture'] = df.groupby('oblast')['soil_moisture'].ffill().bfill()
if 'ndvi' in df.columns:
    df['ndvi'] = df.groupby('oblast')['ndvi'].ffill().bfill()
    df['river_flow_m3s'] = df.groupby('oblast')['river_flow_m3s'].ffill().bfill()

df = df.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)
print(f"  Rows: {len(df)} | Oblasts: {df['oblast'].nunique()}")

# ── Historical baseline (2015–2022) ─────────────────────────────────
cols_to_agg = ['rainfall_mm', 'temp_c', 'soil_moisture']
if 'ndvi' in df.columns:
    cols_to_agg.extend(['ndvi', 'river_flow_m3s'])

baseline = (
    df[df['year'] <= 2022]
    .groupby(['oblast', 'month'])[cols_to_agg]
    .agg(['mean', 'std'])
    .reset_index()
)
# Flatten MultiIndex columns
baseline.columns = ['_'.join(col).strip('_') for col in baseline.columns.values]
rename_dict = {
    'rainfall_mm_mean': 'rain_mean', 'rainfall_mm_std': 'rain_std',
    'temp_c_mean': 'temp_mean', 'temp_c_std': 'temp_std',
    'soil_moisture_mean': 'soil_mean', 'soil_moisture_std': 'soil_std'
}
if 'ndvi' in df.columns:
    rename_dict.update({
        'ndvi_mean': 'ndvi_mean', 'ndvi_std': 'ndvi_std',
        'river_flow_m3s_mean': 'flow_mean', 'river_flow_m3s_std': 'flow_std'
    })

baseline = baseline.rename(columns=rename_dict)
# Fill NaN std with 0
std_cols = ['rain_std', 'temp_std', 'soil_std']
if 'ndvi' in df.columns:
    std_cols.extend(['ndvi_std', 'flow_std'])

for col in std_cols:
    baseline[col] = baseline[col].fillna(0)

df = df.merge(baseline, on=['oblast', 'month'], how='left')

df['rainfall_anomaly'] = np.where(
    df['rain_mean'] == 0,
    np.where(df['rainfall_mm'] > 0, 300.0, 0.0),
    ((df['rainfall_mm'] - df['rain_mean']) / df['rain_mean'] * 100)
)
df['rainfall_anomaly'] = np.clip(df['rainfall_anomaly'], -100, 300).round(2)

# ── Rolling 3-month anomaly (per oblast) for Target ───────────────────
df['rolling_3mo_anomaly'] = (
    df.groupby('oblast')['rainfall_anomaly']
    .transform(lambda x: x.rolling(3, min_periods=1).mean())
    .round(2)
)

# ── Standardized Anomalies (Z-scores) for Features ─────────────────────
df['rain_zscore'] = np.where(df['rain_std'] == 0, 0, (df['rainfall_mm'] - df['rain_mean']) / df['rain_std'])
df['rain_zscore'] = np.round(df['rain_zscore'], 4)

df['temp_zscore'] = np.where(df['temp_std'] == 0, 0, (df['temp_c'] - df['temp_mean']) / df['temp_std'])
df['temp_zscore'] = np.round(df['temp_zscore'], 4)

df['soil_zscore'] = np.where(df['soil_std'] == 0, 0, (df['soil_moisture'] - df['soil_mean']) / df['soil_std'])
df['soil_zscore'] = np.round(df['soil_zscore'], 4)

if 'ndvi' in df.columns:
    df['ndvi_zscore'] = np.where(df['ndvi_std'] == 0, 0, (df['ndvi'] - df['ndvi_mean']) / df['ndvi_std'])
    df['ndvi_zscore'] = np.round(df['ndvi_zscore'], 4)
    df['flow_zscore'] = np.where(df['flow_std'] == 0, 0, (df['river_flow_m3s'] - df['flow_mean']) / df['flow_std'])
    df['flow_zscore'] = np.round(df['flow_zscore'], 4)
else:
    df['ndvi_zscore'] = 0.0
    df['flow_zscore'] = 0.0
    df['irrigation_efficiency'] = 0.5

df['rain_zscore_roll3'] = df.groupby('oblast')['rain_zscore'].transform(lambda x: x.rolling(3, min_periods=1).mean()).round(4)
df['rain_zscore_roll6'] = df.groupby('oblast')['rain_zscore'].transform(lambda x: x.rolling(6, min_periods=1).mean()).round(4)

df['temp_zscore_roll3'] = df.groupby('oblast')['temp_zscore'].transform(lambda x: x.rolling(3, min_periods=1).mean()).round(4)
df['soil_zscore_roll3'] = df.groupby('oblast')['soil_zscore'].transform(lambda x: x.rolling(3, min_periods=1).mean()).round(4)

# ── Composite Stress Index for Target ─────────────────────────────────
# We use Z-scores to create a balanced composite drought indicator
df['composite_z'] = (
    0.5 * df['rain_zscore_roll3'] +
    0.3 * df['soil_zscore_roll3'] -
    0.2 * df['temp_zscore_roll3']
).round(4)

# We overwrite 'rolling_3mo_anomaly' so downstream scripts (train_model.py) 
# can use this composite index as the 'roll3_lag1' precursor feature.
df['rolling_3mo_anomaly'] = df['composite_z']

# ── Stress classification (Target) ────────────────────────────────────
def classify_stress(z):
    """Map composite Z-score to drought stress level."""
    if pd.isna(z): return 0
    if z > -0.3:   return 0   # Normal
    elif z > -0.6: return 1   # Watch
    elif z > -0.9: return 2   # Warning
    else:          return 3   # Emergency

STRESS_MAP = {0: 'Normal', 1: 'Watch', 2: 'Warning', 3: 'Emergency'}

df['stress_level'] = df['composite_z'].apply(classify_stress).astype(int)
df['stress_name']  = df['stress_level'].map(STRESS_MAP)

# ── Save ─────────────────────────────────────────────────────────────
df.to_csv(OUTPUT_PATH, index=False)

print(f"\n── Stress distribution ──────────────────────────")
print(df['stress_name'].value_counts().to_string())
print(f"\n── Oblast Z-Score summary ───────────────────────")
print(df.groupby('oblast')['rain_zscore'].mean().sort_values().head(8).to_string())

# Show a known drought event: Turkistan 2021
try:
    turk = df[
        df['oblast'].str.contains('Turkistan|South Kazakhstan', na=False, case=False) &
        (df['year'] == 2021)
    ]
    if not turk.empty:
        print(f"\n── 2021 Turkistan validation ────────────────────")
        print(turk[['oblast', 'year', 'month', 'rain_zscore', 'stress_name']].to_string())
except Exception:
    pass

print(f"\n✅ TASK COMPLETE — Saved to {OUTPUT_PATH}")
print(f"   Rows: {len(df)} | Columns: {list(df.columns)}")
