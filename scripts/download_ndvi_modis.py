#!/usr/bin/env python3
"""
scripts/download_ndvi_modis.py
Downloads REAL MODIS NDVI (MOD13Q1) from ORNL DAAC API for Kazakhstan oblasts.
Handles API limits by chunking dates.
"""
import os
import sys
import time
import requests
import pandas as pd
import numpy as np

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

API_BASE = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
BAND = "250m_16_days_NDVI"

def get_dates(lat, lon):
    url = f"{API_BASE}/dates?latitude={lat}&longitude={lon}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    # Filter for 2015-2024
    dates = [d['modis_date'] for d in resp.json()['dates'] 
             if d['modis_date'].startswith(('A2015','A2016','A2017','A2018','A2019',
                                            'A2020','A2021','A2022','A2023','A2024'))]
    return dates

def fetch_ndvi_chunk(lat, lon, start_date, end_date):
    url = f"{API_BASE}/subset"
    params = {
        'latitude': lat,
        'longitude': lon,
        'band': BAND,
        'startDate': start_date,
        'endDate': end_date,
        'kmAboveBelow': 0,
        'kmLeftRight': 0
    }
    resp = requests.get(url, params=params, timeout=60)
    if resp.status_code != 200:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
    return resp.json().get('subset', [])

def main():
    print("=" * 60)
    print("REAL NDVI Download — ORNL DAAC MODIS API")
    print("=" * 60)

    all_rows = []

    # Get the list of dates for the first coordinate to chunk them
    # Assuming all points have the same dates available
    first_coords = list(OBLAST_COORDS.values())[0]
    print("Fetching available dates...")
    all_dates = get_dates(first_coords['lat'], first_coords['lon'])
    
    # Chunk dates into groups of 10
    chunks = [all_dates[i:i + 10] for i in range(0, len(all_dates), 10)]
    print(f"Total dates: {len(all_dates)}. Batches per oblast: {len(chunks)}")

    for i, (oblast, coords) in enumerate(OBLAST_COORDS.items(), 1):
        lat, lon = coords['lat'], coords['lon']
        print(f"\n[{i}/{len(OBLAST_COORDS)}] {oblast} (lat={lat}, lon={lon})")
        
        oblast_data = []
        for j, chunk in enumerate(chunks, 1):
            start_d, end_d = chunk[0], chunk[-1]
            try:
                subsets = fetch_ndvi_chunk(lat, lon, start_d, end_d)
                for item in subsets:
                    # 'data' is an array, we requested 0x0 km so it has 1 element
                    val = item['data'][0]
                    # Scale factor for NDVI is 0.0001
                    ndvi = val * 0.0001
                    date_str = item['modis_date']  # e.g., A2015001
                    year = int(date_str[1:5])
                    doy = int(date_str[5:8]) # day of year
                    # Convert day of year to month
                    # Approximation: month = int((doy-1)/30.5) + 1
                    month = pd.Timestamp(f'{year}-01-01') + pd.Timedelta(days=doy-1)
                    
                    oblast_data.append({
                        'oblast': oblast,
                        'year': year,
                        'month': month.month,
                        'ndvi': ndvi
                    })
                time.sleep(1) # rate limit
            except Exception as exc:
                print(f"  ❌ Error on batch {j}: {exc}")
                
        if oblast_data:
            df_oblast = pd.DataFrame(oblast_data)
            # Drop fill values
            df_oblast = df_oblast[df_oblast['ndvi'] > -0.2]
            monthly = df_oblast.groupby(['oblast', 'year', 'month'])['ndvi'].mean().reset_index()
            monthly['ndvi'] = monthly['ndvi'].round(4)
            
            # Save incrementally
            out_path = 'data/processed/ndvi_by_oblast.csv'
            header = not os.path.exists(out_path)
            monthly.to_csv(out_path, mode='a', index=False, header=header)
            print(f"  ✅ Saved {len(monthly)} monthly records to {out_path}", flush=True)

    print("\n✅ TASK COMPLETE!", flush=True)

if __name__ == '__main__':
    # Clear old file if exists
    if os.path.exists('data/processed/ndvi_by_oblast.csv'):
        os.remove('data/processed/ndvi_by_oblast.csv')
    main()
