#!/usr/bin/env python3
"""
scripts/download_chirps_climateserv.py
Downloads REAL monthly precipitation and temperature for Kazakhstan oblasts via the
NASA POWER API (free, no auth, satellite-derived MERRA-2 data).

NASA POWER returns PRECTOTCORR in mm/day. We convert to total monthly mm
by multiplying by the number of days in each month.
NASA POWER returns T2M as monthly average temperature in Celsius.

No synthetic data. No GEE auth required.
"""
import calendar
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

# ── Kazakhstan Oblast centroids (lat/lon) ─────────────────────────────
# Approximate geographic centroids for each of the 14 oblasts
OBLAST_COORDS = {
    'Almatinskaya':                  {'lat': 44.85, 'lon': 76.95},
    'Akmolinskaya':                  {'lat': 51.15, 'lon': 69.40},
    'Aktyubinskaya':                 {'lat': 49.10, 'lon': 57.20},
    'Atyrauskaya':                   {'lat': 47.10, 'lon': 51.90},
    'Vostochno-kazachstanskaya':     {'lat': 49.00, 'lon': 80.30},
    'Jambylslkaya':                  {'lat': 43.35, 'lon': 71.40},
    'Zapadno-kazachstanskaya':       {'lat': 49.80, 'lon': 51.20},
    'Karagandinskaya':               {'lat': 48.00, 'lon': 71.40},
    'Kustanayskaya':                 {'lat': 52.10, 'lon': 63.60},
    'Kyzylordinskaya':               {'lat': 44.85, 'lon': 65.50},
    'Mangistauskaya':                {'lat': 43.30, 'lon': 53.90},
    'Pavlodarskaya':                 {'lat': 52.30, 'lon': 76.95},
    'Severo-kazachstanskaya':        {'lat': 54.10, 'lon': 69.10},
    'Yujno-kazachstanskaya':         {'lat': 41.80, 'lon': 68.30},
}


def days_in_month(year: int, month: int) -> int:
    """Return number of days in a given month/year."""
    return calendar.monthrange(year, month)[1]


def fetch_climate_nasa_power(lat: float, lon: float,
                             start_year: int = 2015,
                             end_year: int = 2024) -> list[dict]:
    """
    Fetch monthly precipitation and temperature from NASA POWER API.
    Returns list of dicts with year, month, rainfall_mm (total monthly), and temp_c.
    """
    url = (
        f"https://power.larc.nasa.gov/api/temporal/monthly/point"
        f"?parameters=PRECTOTCORR,T2M"
        f"&community=AG"
        f"&longitude={lon}"
        f"&latitude={lat}"
        f"&start={start_year}"
        f"&end={end_year}"
        f"&format=JSON"
    )

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    params = data.get('properties', {}).get('parameter', {})
    precip = params.get('PRECTOTCORR', {})
    temp   = params.get('T2M', {})

    results = []
    for date_key in precip.keys():
        mm_per_day = precip.get(date_key, -999)
        t2m_c = temp.get(date_key, -999)

        if mm_per_day < 0 or t2m_c < -99:  # missing values
            continue
            
        year  = int(date_key[:4])
        month = int(date_key[4:6])
        if month == 13:             # annual average row — skip
            continue
            
        total_mm = round(mm_per_day * days_in_month(year, month), 3)
        results.append({
            'year':        year,
            'month':       month,
            'rainfall_mm': total_mm,
            'temp_c':      round(t2m_c, 2)
        })
    return results


def main():
    print("=" * 60)
    print("REAL Precipitation Download — NASA POWER API")
    print("PRECTOTCORR (mm/day) → total monthly (mm)")
    print("=" * 60)

    all_rows: list[dict] = []

    for i, (oblast, coords) in enumerate(OBLAST_COORDS.items(), 1):
        lat, lon = coords['lat'], coords['lon']
        print(f"\n[{i}/{len(OBLAST_COORDS)}] {oblast} "
              f"(lat={lat}, lon={lon}) ...")

        try:
            records = fetch_climate_nasa_power(lat, lon, 2015, 2024)
            for rec in records:
                rec['oblast'] = oblast
            all_rows.extend(records)
            print(f"  ✅ {len(records)} records  "
                  f"(avg {np.mean([r['rainfall_mm'] for r in records]):.1f} mm/mo, {np.mean([r['temp_c'] for r in records]):.1f}°C)")
        except Exception as exc:
            print(f"  ❌ {exc}")

        time.sleep(1.0)          # respect rate-limit

    if not all_rows:
        print("\n❌ FATAL: No data downloaded!")
        sys.exit(1)

    df = pd.DataFrame(all_rows)
    df = df.dropna(subset=['rainfall_mm'])
    df = df.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)

    # ── Validation ────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("DATA VALIDATION")
    print(f"{'=' * 60}")
    print(f"  Total rows:      {len(df)}")
    print(f"  Oblasts:         {df['oblast'].nunique()}")
    print(f"  Year range:      {df['year'].min()} – {df['year'].max()}")
    print(f"  Months/year:     {df.groupby('year')['month'].nunique().mean():.0f}")
    print(f"  NaN count:       {df['rainfall_mm'].isna().sum()}")
    print(f"  Rainfall range:  {df['rainfall_mm'].min():.1f} – "
          f"{df['rainfall_mm'].max():.1f} mm (total monthly)")

    expected = 14 * 10 * 12
    print(f"  Completeness:    {len(df)/expected*100:.1f}% "
          f"({len(df)}/{expected})")

    # ── Sanity: annual totals should be 100–600 mm for Kazakhstan ────
    annual = (df.groupby(['oblast', 'year'])['rainfall_mm']
                .sum().reset_index())
    print(f"\n  Annual precip range: "
          f"{annual['rainfall_mm'].min():.0f} – "
          f"{annual['rainfall_mm'].max():.0f} mm/yr  "
          f"(expected ~100–600 for Kazakhstan)")

    # ── Save ──────────────────────────────────────────────────────────
    os.makedirs('data/processed', exist_ok=True)
    df.to_csv('data/processed/climate_by_oblast.csv', index=False)

    print(f"\n✅ Saved {len(df)} rows → data/processed/climate_by_oblast.csv")
    print(f"\n── Driest oblasts (mean monthly mm) ────────────────")
    print(df.groupby('oblast')['rainfall_mm']
            .mean().sort_values().head(5).to_string())
    print(f"\n── Wettest months (mean across oblasts) ─────────────")
    print(df.groupby('month')['rainfall_mm']
            .mean().sort_values(ascending=False).head(4).to_string())


if __name__ == '__main__':
    main()
