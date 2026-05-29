import os
import time
import requests
import pandas as pd
import json

# Kazakhstan Oblasts (centroids)
OBLASTS = {
    "Almatinskaya": {"lat": 44.85, "lon": 76.95},
    "Akmolinskaya": {"lat": 51.55, "lon": 70.35},
    "Aktubinskaya": {"lat": 48.75, "lon": 58.65},
    "Atyrauskaya": {"lat": 47.45, "lon": 52.45},
    "Vostochno-Kazakhstanskaya": {"lat": 48.55, "lon": 82.25},
    "Zhambylskaya": {"lat": 44.45, "lon": 71.55},
    "Zapadno-Kazakhstanskaya": {"lat": 49.55, "lon": 50.85},
    "Karagandinskaya": {"lat": 48.55, "lon": 72.85},
    "Kostanayskaya": {"lat": 51.55, "lon": 64.25},
    "Kyzylordinskaya": {"lat": 44.85, "lon": 64.05},
    "Mangistauskaya": {"lat": 43.85, "lon": 53.85},
    "Pavlodarskaya": {"lat": 52.55, "lon": 76.55},
    "Severo-Kazakhstanskaya": {"lat": 53.85, "lon": 68.45},
    "Yuzhno-Kazakhstanskaya": {"lat": 42.85, "lon": 68.55}
}

API_URL = "https://archive-api.open-meteo.com/v1/archive"
START_DATE = "2014-01-01"
END_DATE = "2023-12-31"

def main():
    print("=" * 60)
    print("Fetching Open-Meteo Soil Moisture (as vegetation proxy)")
    print("=" * 60)
    
    all_rows = []
    
    for i, (oblast, coords) in enumerate(OBLASTS.items()):
        print(f"[{i+1}/{len(OBLASTS)}] {oblast}...")
        
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "start_date": START_DATE,
            "end_date": END_DATE,
            "hourly": "soil_moisture_0_to_7cm",
            "timezone": "GMT"
        }
        
        resp = requests.get(API_URL, params=params)
        if resp.status_code != 200:
            print(f"❌ Failed to fetch {oblast}: {resp.status_code} - {resp.text}")
            continue
            
        data = resp.json()
        if "hourly" not in data or "soil_moisture_0_to_7cm" not in data["hourly"]:
            print(f"❌ Unexpected data format for {oblast}")
            continue
            
        times = data["hourly"]["time"]
        soil = data["hourly"]["soil_moisture_0_to_7cm"]
        
        # Create a dataframe of hourly data
        df = pd.DataFrame({"time": pd.to_datetime(times), "soil_moisture": soil})
        
        # Add year and month
        df['year'] = df['time'].dt.year
        df['month'] = df['time'].dt.month
        
        # Drop NaNs
        df = df.dropna(subset=['soil_moisture'])
        
        # Monthly mean
        monthly = df.groupby(['year', 'month'])['soil_moisture'].mean().reset_index()
        monthly['oblast'] = oblast
        
        all_rows.append(monthly)
        print(f"  ✅ Fetched {len(monthly)} monthly records.")
        
        time.sleep(1) # Small delay to respect Open-Meteo's API limits
        
    df_final = pd.concat(all_rows, ignore_index=True)
    df_final = df_final.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)
    
    os.makedirs('data/processed', exist_ok=True)
    out_path = 'data/processed/openmeteo_by_oblast.csv'
    df_final.to_csv(out_path, index=False)
    print(f"\n✅ Saved {len(df_final)} rows → {out_path}")

if __name__ == "__main__":
    main()
