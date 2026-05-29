# scripts/download_chirps_gee.py
"""
Downloads CHIRPS monthly precipitation for Kazakhstan using Google Earth Engine.
This is the CORRECT approach — CHIRPS HTTP direct download is blocked (403).
Requires: pip install earthengine-api
Authentication: run `earthengine authenticate` once (free Google account)
"""
import ee
import pandas as pd
import numpy as np
import json
import os

# ── Authenticate ─────────────────────────────────────────────────────
# First time only, run: python -c "import ee; ee.Authenticate()"
try:
    ee.Initialize(project='aquasentry-497512')
except Exception:
    ee.Authenticate()
    ee.Initialize(project='aquasentry-497512')

# ── Kazakhstan Oblast Boundaries ──────────────────────────────────────
# Load from GADM via GEE's built-in datasets or from local file
kaz = ee.FeatureCollection('FAO/GAUL/2015/level1') \
        .filter(ee.Filter.eq('ADM0_NAME', 'Kazakhstan'))

# ── CHIRPS v2.0/v3.0 Monthly (Available in GEE even though HTTP is blocked) ──
chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/PENTAD') \
           .select('precipitation')

# ── Date Range ────────────────────────────────────────────────────────
start = '2015-01-01'
end   = '2024-12-31'

# ── Monthly aggregation ───────────────────────────────────────────────
def monthly_sum(year, month):
    start_date = ee.Date.fromYMD(year, month, 1)
    end_date   = start_date.advance(1, 'month')
    monthly    = chirps.filterDate(start_date, end_date).sum()
    stats      = monthly.reduceRegions(
        collection = kaz,
        reducer    = ee.Reducer.mean(),
        scale      = 5566   # CHIRPS native resolution ~5km
    )
    return stats.map(lambda f: f.set({
        'year':  year,
        'month': month,
    }))

years  = range(2015, 2025)
months = range(1, 13)

all_results = []
print("Extracting monthly CHIRPS for all Kazakhstan oblasts (2015–2024)...")
print("This may take 10–20 minutes for GEE to process...")

for year in years:
    for month in months:
        try:
            result    = monthly_sum(year, month)
            features  = result.getInfo()['features']
            for feat in features:
                props = feat['properties']
                all_results.append({
                    'oblast':      props.get('ADM1_NAME', props.get('NAME_1', 'Unknown')),
                    'year':        year,
                    'month':       month,
                    'rainfall_mm': round(props.get('mean', np.nan), 3)
                })
            print(f"  ✓ {year}-{month:02d} ({len(features)} oblasts)")
        except Exception as e:
            print(f"  ✗ {year}-{month:02d}: {e}")
            continue

os.makedirs('data/processed', exist_ok=True)
df = pd.DataFrame(all_results).dropna(subset=['rainfall_mm'])
df.to_csv('data/processed/chirps_by_oblast.csv', index=False)
print(f"\n✅ Saved {len(df)} rows to data/processed/chirps_by_oblast.csv")
print(df.groupby('oblast')['rainfall_mm'].mean().sort_values().head(5).to_string())
