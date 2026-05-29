# 🤖 AI AGENT TASK PROMPT — MEMBER A (ML & DATA ENGINEER)
## AquaSentry | SmartEarth 2026 Hackathon | Nazarbayev University, Kazakhstan

---

## 🎯 WHAT YOU ARE

You are an autonomous AI coding agent assigned to complete ALL of Member A's technical work
for the AquaSentry water stress forecasting project. AquaSentry predicts water stress
30–90 days in advance for Kazakhstan's 17 oblasts using satellite climate data and ML.

You have full write access to the filesystem. You must complete every task in sequence,
verify outputs at each step before continuing, and produce working files at each stage.

---

## 🛠️ SKILLS TO ACTIVATE

Before starting work, read and follow the instructions in these skill files:

1. **`bash-linux`** — Use for all shell commands (file creation, wget downloads, loops, verification)
2. **`bash-scripting`** — Use for writing defensive download and pipeline scripts with error handling
3. **`matplotlib`** — Use when generating the drought validation chart (Task A3.3)
4. **`python-testing`** — Use to add sanity checks and assertions to each script output
5. **`agentic-engineering`** — Use to decompose this into independently verifiable units and enforce done conditions

Apply these skills throughout every task you execute below.

---

## 📁 WORKING DIRECTORY

All files should be created at:
```
/Users/kotresh/Documents/safeearth kazkastan hackathon/
```

Create the following structure first:
```bash
cd "/Users/kotresh/Documents/safeearth kazkastan hackathon"
mkdir -p data/raw/chirps
mkdir -p data/processed
mkdir -p scripts
mkdir -p backend
mkdir -p tests
```

---

## ⚠️ CRITICAL RULES

1. **NEVER skip verification** — after every script, print a sanity check of the output
2. **NEVER proceed if data is missing** — if a download fails or a file is empty, stop and report it
3. **DO NOT train LSTM, transformer, or deep learning models** — XGBoost ONLY
4. **DO NOT use live satellite APIs during testing** — pre-download everything first
5. **ALWAYS check for NaN values** in DataFrames before using them for training
6. **Save all intermediate outputs** — `chirps_by_oblast.csv`, `stress_index.csv`, `model.pkl`, `predictions.json`, `validation_2021.png`
7. **Print a ✅ confirmation message** at the end of every completed task with the output file path and a 3-line data summary
8. **DO NOT ALLOW DATA LEAKAGE.** Ensure features used for prediction (time T) only use data available *prior* to that time (T-1, T-2, etc.).

---

## 📋 TASKS IN SEQUENCE — EXECUTE IN ORDER

---

# TASK A1 — PROJECT SETUP & DATA ACQUISITION

## A1.1 — Create Folder Structure + Python Environment

**Done condition:** Python environment works, all packages import successfully, requirements.txt committed.

**Execute this exactly:**

```bash
# Navigate to project folder
cd "/Users/kotresh/Documents/safeearth kazkastan hackathon"

# Create all directories
mkdir -p data/raw/chirps data/processed scripts backend tests

# Create Python virtual environment
python3 -m venv aquasentry-env
source aquasentry-env/bin/activate

# Install all required packages including earthengine-api
pip install xarray netCDF4 geopandas rasterstats affine \
            pandas numpy scikit-learn xgboost joblib \
            matplotlib seaborn fastapi uvicorn python-dotenv \
            shapely fiona pyproj pytest earthengine-api
```

**Verify with this Python check — it must pass before continuing:**
```python
python3 -c "
import xarray as xr
import geopandas as gpd
import xgboost as xgb
import rasterstats
import pandas as pd
import numpy as np
import matplotlib
import joblib
import ee
print('✅ TASK A1.1 COMPLETE — All packages installed correctly')
print(f'   xgboost: {xgb.__version__}')
print(f'   geopandas: {gpd.__version__}')
print(f'   pandas: {pd.__version__}')
"
```

**Save requirements:**
```bash
pip freeze > requirements.txt
echo "✅ requirements.txt saved"
```

---

## A1.2 — Download Kazakhstan GeoJSON

**Done condition:** `kazakhstan_oblasts.geojson` exists, loads as GeoDataFrame, shows 17 features.

**Execute:**
```bash
# Download Kazakhstan Level-1 admin boundaries (oblasts) from GADM
cd "/Users/kotresh/Documents/safeearth kazkastan hackathon"
curl -L "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_KAZ_1.json" \
     -o data/raw/kazakhstan_oblasts.geojson

# Verify
python3 -c "
import geopandas as gpd
gdf = gpd.read_file('data/raw/kazakhstan_oblasts.geojson')
print(f'✅ TASK A1.2 COMPLETE — Kazakhstan GeoJSON loaded')
print(f'   Features (oblasts): {len(gdf)}')
print(f'   Column names: {list(gdf.columns)}')
print(f'   CRS: {gdf.crs}')
print(f'   Oblast names: {sorted(gdf[\"NAME_1\"].tolist())}')
"
```

**IMPORTANT:** Note the exact column name that contains oblast names (likely `NAME_1`). You will need this exact column name in every downstream script.

---

## A1.3 — Download CHIRPS Rainfall Data (via Google Earth Engine)

**Done condition:** `data/processed/chirps_by_oblast.csv` exists, containing monthly rainfall data from 2015 to 2024 for all oblasts.

*(Note: Direct HTTP downloads from CHC UCSB are blocked (403 Forbidden). We MUST use GEE.)*

**Create `scripts/download_chirps_gee.py`:**

```python
# scripts/download_chirps_gee.py
"""
Downloads CHIRPS monthly precipitation for Kazakhstan using Google Earth Engine.
"""
import ee
import pandas as pd
import numpy as np
import os
import json

# ── Authenticate ─────────────────────────────────────────────────────
try:
    ee.Initialize()
except Exception:
    print("Google Earth Engine requires authentication.")
    print("Please run `earthengine authenticate` in your terminal.")
    exit(1)

# ── Kazakhstan Oblast Boundaries ──────────────────────────────────────
kaz = ee.FeatureCollection('FAO/GAUL/2015/level1') \
        .filter(ee.Filter.eq('ADM0_NAME', 'Kazakhstan'))

# ── CHIRPS v2.0 Monthly ──────────────────────────────────────────────
chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/PENTAD') \
           .select('precipitation')

# ── Monthly aggregation ───────────────────────────────────────────────
def monthly_sum(year, month):
    start_date = ee.Date.fromYMD(year, month, 1)
    end_date   = start_date.advance(1, 'month')
    monthly    = chirps.filterDate(start_date, end_date).sum()
    stats      = monthly.reduceRegions(
        collection = kaz,
        reducer    = ee.Reducer.mean(),
        scale      = 5566
    )
    return stats.map(lambda f: f.set({
        'year':  year,
        'month': month,
    }))

all_results = []
print("Extracting monthly CHIRPS for all Kazakhstan oblasts (2015–2024)...")
print("This may take a few minutes...")

for year in range(2015, 2025):
    for month in range(1, 13):
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

# Align GEE names with GADM names if necessary (simplification for hackathon)
name_mapping = {
    'East Kazakhstan': 'Vostochno-Kazakhstan',
    'South Kazakhstan': 'Turkestan', # Turkestan was South Kazakhstan
    'West Kazakhstan': 'Zapadno-Kazakhstan',
    'North Kazakhstan': 'Severo-Kazakhstan',
    'Alma-Ata': 'Almaty',
    'Jambyl': 'Zhambyl'
}
df['oblast'] = df['oblast'].replace(name_mapping)

OUTPUT_PATH = 'data/processed/chirps_by_oblast.csv'
df.to_csv(OUTPUT_PATH, index=False)

print(f"\n✅ TASK A1.3 COMPLETE — Saved to {OUTPUT_PATH}")
print(f"   Total rows: {len(df)}")
print(df.groupby('oblast')['rainfall_mm'].mean().sort_values().head(5).to_string())
```

**Run it:**
```bash
cd "/Users/kotresh/Documents/safeearth kazkastan hackathon"
source aquasentry-env/bin/activate
# If GEE is not authenticated, run: earthengine authenticate
python scripts/download_chirps_gee.py
```

**Verify output:**
```python
python3 -c "
import pandas as pd
import os
assert os.path.exists('data/processed/chirps_by_oblast.csv'), 'File not found!'
df = pd.read_csv('data/processed/chirps_by_oblast.csv')
assert len(df) > 1000, f'Too few rows: {len(df)}'
assert df['rainfall_mm'].isna().sum() == 0, 'NaN values found'
print('✅ A1.3 VERIFIED:')
print(f'   Rows: {len(df)}')
print(f'   Oblasts: {df[\"oblast\"].nunique()}')
"
```

---

# TASK A2 — DATA PROCESSING

---

## A2.1 — Compute Drought Stress Index

**Done condition:** `data/processed/stress_index.csv` exists, has columns `[oblast, year, month, rainfall_mm, rainfall_anomaly, rolling_3mo_anomaly, stress_level, stress_name]`.

**Create `scripts/compute_stress.py`:**

```python
# scripts/compute_stress.py
"""
Computes drought stress labels from CHIRPS rainfall anomalies.
Input:  data/processed/chirps_by_oblast.csv
Output: data/processed/stress_index.csv
"""
import pandas as pd
import numpy as np
import os

INPUT_PATH  = 'data/processed/chirps_by_oblast.csv'
OUTPUT_PATH = 'data/processed/stress_index.csv'

print("Loading CHIRPS data...")
df = pd.read_csv(INPUT_PATH)
df = df.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)
print(f"  Rows: {len(df)} | Oblasts: {df['oblast'].nunique()}")

# ── Historical baseline (2015–2022) ─────────────────────────────────
baseline = (
    df[df['year'] <= 2022]
    .groupby(['oblast', 'month'])['rainfall_mm']
    .mean()
    .reset_index()
    .rename(columns={'rainfall_mm': 'historical_mean'})
)
df = df.merge(baseline, on=['oblast', 'month'], how='left')

# ── Rainfall Anomaly (% deviation from historical) ────────────────────
df['rainfall_anomaly'] = (
    (df['rainfall_mm'] - df['historical_mean']) / df['historical_mean'] * 100
).clip(-100, 300).round(2)

# ── Rolling 3-month anomaly (per oblast) ────────────────────────────
df['rolling_3mo_anomaly'] = (
    df.groupby('oblast')['rainfall_anomaly']
    .transform(lambda x: x.rolling(3, min_periods=1).mean())
    .round(2)
)

# ── Stress classification ─────────────────────────────────────────────
# We define the GROUND TRUTH label based on current conditions
def classify_stress(anomaly):
    if pd.isna(anomaly): return 0
    if anomaly > -10:   return 0   # Normal
    elif anomaly > -25: return 1   # Watch
    elif anomaly > -40: return 2   # Warning
    else:               return 3   # Emergency

STRESS_MAP = {0: 'Normal', 1: 'Watch', 2: 'Warning', 3: 'Emergency'}

df['stress_level'] = df['rolling_3mo_anomaly'].apply(classify_stress).astype(int)
df['stress_name']  = df['stress_level'].map(STRESS_MAP)

# ── Save ─────────────────────────────────────────────────────────────
df.to_csv(OUTPUT_PATH, index=False)

print(f"\n── Stress distribution ──────────────────────────")
print(df['stress_name'].value_counts().to_string())

try:
    turk = df[
        df['oblast'].str.contains('Turk', na=False, case=False) &
        (df['year'] == 2021)
    ]
    if not turk.empty:
        print(f"\n── 2021 Turkestan validation ────────────────────")
        print(turk[['oblast','year','month','rainfall_anomaly','stress_name']].head(6).to_string())
except Exception:
    pass

print(f"\n✅ TASK A2.1 COMPLETE — Saved to {OUTPUT_PATH}")
```

**Run it:**
```bash
python scripts/compute_stress.py
```

**Verify:**
```python
python3 -c "
import pandas as pd
df = pd.read_csv('data/processed/stress_index.csv')
required_cols = ['oblast','year','month','rainfall_anomaly','rolling_3mo_anomaly','stress_level']
for col in required_cols:
    assert col in df.columns, f'Missing column: {col}'
print('✅ A2.1 VERIFIED')
"
```

---

# TASK A3 — MACHINE LEARNING

---

## A3.1 — Train XGBoost Drought Prediction Model (NO DATA LEAKAGE)

**Done condition:** `backend/model.pkl` exists, loads correctly, realistic test accuracy (~65-75%).

**Create `scripts/train_model.py`:**

```python
# scripts/train_model.py
"""
Trains an XGBoost classifier to forecast drought stress level.
Critically: To avoid data leakage, we predict stress at time T
using ONLY lagged features from T-1, T-2, T-3.
"""
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib
import warnings
import os
warnings.filterwarnings('ignore')

INPUT_PATH  = 'data/processed/stress_index.csv'
MODEL_PATH  = 'backend/model.pkl'
os.makedirs('backend', exist_ok=True)

df = pd.read_csv(INPUT_PATH).dropna()
df = df.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)

# ── Feature Engineering (Strictly Past Data) ────────────────────────
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

# SHIFT FEATURES: To predict Month T, we only look at T-1, T-2, T-3
df['rain_lag1']  = df.groupby('oblast')['rainfall_anomaly'].shift(1)
df['rain_lag2']  = df.groupby('oblast')['rainfall_anomaly'].shift(2)
df['rain_lag3']  = df.groupby('oblast')['rainfall_anomaly'].shift(3)
df['rain_roll3'] = df.groupby('oblast')['rain_lag1'].transform(lambda x: x.rolling(3, min_periods=1).mean())

FEATURES = ['month_sin', 'month_cos', 'rain_lag1', 'rain_lag2', 'rain_lag3', 'rain_roll3']
TARGET = 'stress_level'

df_clean = df.dropna(subset=FEATURES + [TARGET])

# ── Train / Test Split ────────────────────────────────────────────────
train = df_clean[df_clean['year'] <= 2022]
test  = df_clean[df_clean['year'] >= 2023]

X_train, y_train = train[FEATURES], train[TARGET].astype(int)
X_test,  y_test  = test[FEATURES],  test[TARGET].astype(int)

# ── Model Training ────────────────────────────────────────────────────
model = XGBClassifier(
    n_estimators=100,      # Reduced to prevent overfitting
    max_depth=4,           # Shallow trees for better generalization
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=3,    # Help with imbalanced classes
    eval_metric='mlogloss',
    random_state=42,
)

model.fit(X_train, y_train)

# ── Evaluation ────────────────────────────────────────────────────────
train_preds = model.predict(X_train)
test_preds  = model.predict(X_test)

train_acc = accuracy_score(y_train, train_preds)
test_acc  = accuracy_score(y_test,  test_preds)

print(f"\n── Realistic Model Performance ──────────────────────")
print(f"  Train accuracy: {train_acc:.3f} ({train_acc*100:.1f}%)")
print(f"  Test  accuracy: {test_acc:.3f}  ({test_acc*100:.1f}%)")
print(f"\n── Test Classification Report ───────────────────────")
print(classification_report(y_test, test_preds, target_names=['Normal','Watch','Warning','Emergency'], zero_division=0))

joblib.dump(model, MODEL_PATH)

with open('backend/model_accuracy.txt', 'w') as f:
    f.write(f"Train accuracy: {train_acc*100:.1f}%\n")
    f.write(f"Test accuracy:  {test_acc*100:.1f}%\n")

print(f"\n✅ TASK A3.1 COMPLETE — Model saved")
```

**Run it:**
```bash
python scripts/train_model.py
```

**Verify:**
```python
python3 -c "
import joblib, os
assert os.path.exists('backend/model.pkl'), 'model.pkl not found'
print('✅ A3.1 VERIFIED')
"
```

---

## A3.2 — Generate predictions.json for All Oblasts

**Create `scripts/generate_predictions.py`:**

```python
# scripts/generate_predictions.py
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
import joblib
import json
import geopandas as gpd
import os
from collections import Counter

MODEL_PATH   = 'backend/model.pkl'
STRESS_PATH  = 'data/processed/stress_index.csv'
GEOJSON_PATH = 'data/raw/kazakhstan_oblasts.geojson'
OUTPUT_PATH  = 'backend/predictions.json'

STRESS_MAP = {0:'Normal', 1:'Watch', 2:'Warning', 3:'Emergency'}
COLOR_MAP  = {'Normal':'#2ecc71', 'Watch':'#f39c12', 'Warning':'#e67e22', 'Emergency':'#e74c3c'}

model   = joblib.load(MODEL_PATH)
df      = pd.read_csv(STRESS_PATH).dropna()
oblasts = gpd.read_file(GEOJSON_PATH)

NAME_COL = 'NAME_1' if 'NAME_1' in oblasts.columns else oblasts.columns[0]

def get_forecast(odf, horizon_months):
    # Sort chronologically
    odf = odf.sort_values(['year', 'month']).reset_index(drop=True)
    latest = odf.iloc[-1]

    target_month = int(latest['month']) + horizon_months
    target_month = ((target_month - 1) % 12) + 1

    # Features for the future month rely on known past data
    rain_lag1 = float(latest['rainfall_anomaly'])
    rain_lag2 = float(odf.iloc[-2]['rainfall_anomaly']) if len(odf) > 1 else rain_lag1
    rain_lag3 = float(odf.iloc[-3]['rainfall_anomaly']) if len(odf) > 2 else rain_lag2
    rain_roll3 = np.mean([rain_lag1, rain_lag2, rain_lag3])

    feat = [[
        np.sin(2 * np.pi * target_month / 12),
        np.cos(2 * np.pi * target_month / 12),
        rain_lag1, rain_lag2, rain_lag3, rain_roll3
    ]]
    pred = int(model.predict(feat)[0])
    proba = float(np.max(model.predict_proba(feat)[0]))
    return pred, proba

predictions = {}
for oblast_name in oblasts[NAME_COL].tolist():
    # Fuzzy match
    matches = df[df['oblast'].str.contains(oblast_name[:5], case=False, na=False)]
    if matches.empty: continue
    
    odf = matches.sort_values(['year','month'])
    
    s30, p30 = get_forecast(odf, 1)
    s60, p60 = get_forecast(odf, 2)
    s90, p90 = get_forecast(odf, 3)

    s30_n = STRESS_MAP[s30]
    predictions[oblast_name] = {
        'stress_30d': s30_n,
        'stress_60d': STRESS_MAP[s60],
        'stress_90d': STRESS_MAP[s90],
        'color_30d': COLOR_MAP[s30_n],
        'confidence': round(p30, 2),
        'rainfall_anomaly': round(float(odf.iloc[-1]['rainfall_anomaly']), 1),
        'current_level': STRESS_MAP[int(odf.iloc[-1]['stress_level'])]
    }

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(predictions, f, indent=2, ensure_ascii=False)

print(f"✅ TASK A3.2 COMPLETE — Saved {len(predictions)} forecasts to {OUTPUT_PATH}")
```

**Run it:**
```bash
python scripts/generate_predictions.py
```

---

## A3.3 — Generate 2021 Drought Validation Chart

**Create `scripts/validate_2021.py`:**

```python
# scripts/validate_2021.py
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import joblib

STRESS_PATH = 'data/processed/stress_index.csv'
MODEL_PATH  = 'backend/model.pkl'
OUTPUT_PATH = 'backend/validation_2021.png'

COLORS = ['#2ecc71','#f39c12','#e67e22','#e74c3c']

model = joblib.load(MODEL_PATH)
df = pd.read_csv(STRESS_PATH)

df = df.sort_values(['oblast', 'year', 'month']).reset_index(drop=True)
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
df['rain_lag1'] = df.groupby('oblast')['rainfall_anomaly'].shift(1)
df['rain_lag2'] = df.groupby('oblast')['rainfall_anomaly'].shift(2)
df['rain_lag3'] = df.groupby('oblast')['rainfall_anomaly'].shift(3)
df['rain_roll3'] = df.groupby('oblast')['rain_lag1'].transform(lambda x: x.rolling(3, min_periods=1).mean())

FEATURES = ['month_sin', 'month_cos', 'rain_lag1', 'rain_lag2', 'rain_lag3', 'rain_roll3']
df_model = df.dropna(subset=FEATURES)
df_model['predicted_level'] = model.predict(df_model[FEATURES])

target_oblasts = [o for o in df_model['oblast'].unique() if 'Turk' in o or 'Kyzyl' in o][:2]
if not target_oblasts: target_oblasts = df_model['oblast'].unique()[:2]

period = df_model[(df_model['year'].isin([2020, 2021, 2022])) & (df_model['oblast'].isin(target_oblasts))]

fig, axes = plt.subplots(len(target_oblasts), 1, figsize=(12, 3.5 * len(target_oblasts)), facecolor='#0a0e1a')
if len(target_oblasts) == 1: axes = [axes]

for ax, oblast in zip(axes, target_oblasts):
    odf = period[period['oblast'] == oblast].sort_values(['year','month'])
    x = range(len(odf))
    bar_colors = [COLORS[int(v)] for v in odf['predicted_level']]
    
    ax.bar(x, odf['predicted_level'], color=bar_colors, width=0.8)
    ax.scatter(x, odf['stress_level'], color='white', s=20, label='Actual Ground Truth')
    
    ticks = list(range(0, len(odf), 3))
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{odf.iloc[i]['year']}-{int(odf.iloc[i]['month']):02d}" for i in ticks], color='#9ca3af')
    ax.set_yticks([0,1,2,3])
    ax.set_yticklabels(['Normal','Watch','Warning','Emergency'], color='white')
    ax.set_title(f'{oblast} — Predicted vs Actual Drought Stress', color='white')
    ax.set_facecolor('#111827')

plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight', facecolor='#0a0e1a')
print(f"✅ TASK A3.3 COMPLETE — Chart saved to {OUTPUT_PATH}")
```

**Run it:**
```bash
python scripts/validate_2021.py
```

---

# TASK A4 — FINAL OUTPUTS

## A4.1 — Write Technical README

**Execute:**
```bash
python3 -c "
with open('backend/model_accuracy.txt') as f: lines = f.read().split('\n')
t_acc = next((l.split(':')[1].strip() for l in lines if 'Train' in l), 'N/A')
v_acc = next((l.split(':')[1].strip() for l in lines if 'Test' in l), 'N/A')

content = f'''# 🌊 AquaSentry

## Model Performance
- **Train accuracy (2015–2022):** {t_acc}
- **Test accuracy (2023–2024):** {v_acc}
- **Methodology Note:** The model rigorously separates current ground truth from historical features (1-3 month lags) to ensure zero data leakage and genuine forecasting capabilities.
'''
with open('README.md', 'w') as f: f.write(content)
print('✅ README.md written')
"
```

## A4.2 — Final Check
Review `backend/predictions.json` and ensure it's ready to pass to Member B.
