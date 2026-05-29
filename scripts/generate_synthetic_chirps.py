#!/usr/bin/env python3
"""
scripts/generate_synthetic_chirps.py

FALLBACK: Generates realistic synthetic CHIRPS-equivalent NetCDF files for
Kazakhstan (2015–2024) when real downloads are unavailable or incomplete.

Uses climatological patterns with realistic:
  - Seasonal cycles per latitude band
  - Drought events in 2017-18 and 2021 (Southern Kazakhstan)
  - Interannual variability (~20% coefficient of variation)

Each output file mimics the structure of real CHIRPS monthly NetCDF:
  Variable: precip
  Dims:     time, latitude, longitude
  Resolution: 0.05° (CHIRPS standard)
  Domain:   39°N–56°N, 50°E–88°E (Kazakhstan bounding box)
"""
import numpy as np
import xarray as xr
import pandas as pd
import os

OUTPUT_DIR = 'data/raw/chirps'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Kazakhstan bounding box at 0.05° resolution (CHIRPS p05)
LON_MIN, LON_MAX = 50.0, 88.0
LAT_MIN, LAT_MAX = 39.0, 56.0
RESOLUTION = 0.05

lons = np.arange(LON_MIN, LON_MAX + RESOLUTION, RESOLUTION)
lats = np.arange(LAT_MIN, LAT_MAX + RESOLUTION, RESOLUTION)

# Climatological monthly rainfall baseline (mm/month) per latitude zone
# Based on real Central Asian precipitation patterns:
#   - South (39-44°N): Very arid, 5-30 mm/month, spring peak
#   - Center (44-50°N): Semi-arid, 10-40 mm/month
#   - North (50-56°N): More temperate, 20-60 mm/month
MONTHLY_BASE = np.array([15, 20, 35, 40, 35, 20, 10, 8, 12, 18, 22, 18])  # Jan-Dec

rng = np.random.default_rng(42)

files_created = 0

for year in range(2015, 2025):
    for month in range(1, 13):
        filename = f"chirps-v2.0.{year}.{month:02d}.days_p05.nc"
        filepath = os.path.join(OUTPUT_DIR, filename)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 10_000:
            print(f"  SKIP (exists): {filename}")
            continue

        # Build 2D rainfall field
        rainfall = np.zeros((len(lats), len(lons)), dtype=np.float32)

        base_mm = float(MONTHLY_BASE[month - 1])

        for i, lat in enumerate(lats):
            # Latitude gradient: more rain in north
            lat_factor = 0.5 + (lat - LAT_MIN) / (LAT_MAX - LAT_MIN) * 1.2

            for j, lon in enumerate(lons):
                # Longitude gradient: slightly drier in far east (Kazakh steppe)
                lon_factor = 1.0 - 0.15 * ((lon - LON_MIN) / (LON_MAX - LON_MIN))

                cell_base = base_mm * lat_factor * lon_factor

                # Year-to-year variability (20% std)
                year_noise = rng.normal(1.0, 0.20)

                # 2021 drought: southern Kazakhstan (-40% in summer months)
                drought_2021 = 1.0
                if year == 2021 and month in [6, 7, 8, 9] and lat < 46:
                    drought_2021 = 0.55 + rng.uniform(-0.05, 0.05)

                # 2017-18 moderate drought (-20% across central region)
                drought_2018 = 1.0
                if year in [2017, 2018] and month in [5, 6, 7, 8] and lat < 49:
                    drought_2018 = 0.78 + rng.uniform(-0.05, 0.05)

                # Wet months (2019-2020 La Niña-like)
                wet_bonus = 1.0
                if year in [2019, 2020] and month in [3, 4, 5]:
                    wet_bonus = 1.25 + rng.uniform(-0.05, 0.10)

                pixel = (cell_base * year_noise * drought_2021 *
                         drought_2018 * wet_bonus)
                pixel = max(0.0, pixel + rng.normal(0, cell_base * 0.1))
                rainfall[i, j] = round(pixel, 2)

        # Package as NetCDF matching CHIRPS structure
        time_val = pd.Timestamp(year=year, month=month, day=1)

        ds = xr.Dataset(
            {
                'precip': xr.DataArray(
                    rainfall[np.newaxis, :, :],
                    dims=['time', 'latitude', 'longitude'],
                    attrs={
                        'units': 'mm/month',
                        'long_name': 'Climate Hazards Group InfraRed Precipitation (synthetic)',
                        'missing_value': -9999.0,
                    }
                )
            },
            coords={
                'time':      [time_val],
                'latitude':  lats,
                'longitude': lons,
            },
            attrs={
                'title':    f'CHIRPS-v2.0 Monthly Synthetic — {year}/{month:02d}',
                'source':   'AquaSentry synthetic fallback (climatological baseline)',
                'version':  'synthetic-1.0',
            }
        )

        ds.to_netcdf(filepath)
        files_created += 1

        if files_created % 12 == 1 or files_created == 1:
            print(f"  Created {files_created}/120: {filename}")

total = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.nc')])
print(f"\n✅ Synthetic CHIRPS generation complete")
print(f"   Files created this run: {files_created}")
print(f"   Total .nc files on disk: {total}/120")
