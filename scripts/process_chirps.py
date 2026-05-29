#!/usr/bin/env python3
"""
scripts/process_chirps.py
Aggregates CHIRPS pixel-level rainfall to Kazakhstan oblast averages.
Output: data/processed/chirps_by_oblast.csv
Columns: oblast, year, month, rainfall_mm
"""
import xarray as xr
import geopandas as gpd
import pandas as pd
import numpy as np
from rasterstats import zonal_stats
from affine import Affine
import glob
import warnings
import os

warnings.filterwarnings('ignore')

# ── Config ────────────────────────────────────────────────────────────
GEOJSON_PATH = 'data/raw/kazakhstan_oblasts.geojson'
CHIRPS_GLOB  = 'data/raw/chirps/chirps-v2.0.*.days_p05.nc'
OUTPUT_PATH  = 'data/processed/chirps_by_oblast.csv'
NAME_COLUMN  = 'NAME_1'   # update if GeoJSON uses a different column name

# ── Load GeoJSON ──────────────────────────────────────────────────────
print("Loading Kazakhstan GeoJSON...")
oblasts = gpd.read_file(GEOJSON_PATH).to_crs('EPSG:4326')
print(f"  Oblasts loaded: {len(oblasts)}")
print(f"  Names: {sorted(oblasts[NAME_COLUMN].tolist())}")

# ── Process CHIRPS Files ──────────────────────────────────────────────
files = sorted(glob.glob(CHIRPS_GLOB))
print(f"\nProcessing {len(files)} CHIRPS files...")
assert len(files) > 0, f"No CHIRPS files found at {CHIRPS_GLOB}"

results = []
errors  = []

for i, filepath in enumerate(files):
    try:
        # Parse year and month from filename
        # e.g. chirps-v2.0.2015.01.days_p05.nc
        basename = os.path.basename(filepath)
        parts    = basename.replace('.days_p05.nc', '').split('.')
        year     = int(parts[-2])
        month    = int(parts[-1])

        ds       = xr.open_dataset(filepath)
        rainfall = ds['precip'].values.squeeze()
        lats     = ds['latitude'].values
        lons     = ds['longitude'].values
        ds.close()

        # Handle extra time dimension
        if rainfall.ndim == 3:
            rainfall = rainfall[0]

        # Build affine transform
        res_lat   = abs(float(lats[1]) - float(lats[0]))
        res_lon   = abs(float(lons[1]) - float(lons[0]))
        transform = Affine(res_lon, 0.0, float(lons.min()),
                           0.0, -res_lat, float(lats.max()))

        # Flip array so north is up (rasterstats expects north-up)
        rainfall_2d = np.flipud(rainfall)
        rainfall_2d = np.where(rainfall_2d < 0, np.nan, rainfall_2d)

        stats = zonal_stats(
            oblasts,
            rainfall_2d,
            affine=transform,
            stats=['mean'],
            nodata=np.nan
        )

        for j, stat in enumerate(stats):
            results.append({
                'oblast':      oblasts.iloc[j][NAME_COLUMN],
                'year':        year,
                'month':       month,
                'rainfall_mm': round(float(stat['mean']), 3) if stat['mean'] is not None else np.nan
            })

        if (i + 1) % 12 == 0:
            print(f"  Processed {i+1}/{len(files)} files (through {year})")

    except Exception as e:
        errors.append({'file': filepath, 'error': str(e)})
        print(f"  ⚠️  Error on {os.path.basename(filepath)}: {e}")
        continue

# ── Save Output ───────────────────────────────────────────────────────
df       = pd.DataFrame(results)
df_clean = df.dropna(subset=['rainfall_mm'])

print(f"\n── Output summary ──────────────────────────────")
print(f"  Total rows:     {len(df)}")
print(f"  After dropna:   {len(df_clean)}")
print(f"  Oblasts:        {df_clean['oblast'].nunique()}")
print(f"  Year range:     {df_clean['year'].min()} – {df_clean['year'].max()}")
print(f"  Rainfall range: {df_clean['rainfall_mm'].min():.1f} – {df_clean['rainfall_mm'].max():.1f} mm")

if errors:
    print(f"\n  ⚠️  Errors on {len(errors)} files:")
    for e in errors[:5]:
        print(f"     {os.path.basename(e['file'])}: {e['error']}")

df_clean.to_csv(OUTPUT_PATH, index=False)
print(f"\n✅ TASK A2.1 COMPLETE — Saved to {OUTPUT_PATH}")
print("\nTop 5 driest oblasts (mean rainfall mm):")
print(df_clean.groupby('oblast')['rainfall_mm'].mean().sort_values().head(5).to_string())
