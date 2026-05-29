# 🌊 AquaSentry
### AI-Powered Regional Water Stress Forecaster for Kazakhstan
**SmartEarth 2026 Hackathon | Nazarbayev University, Kazakhstan**

---

## What It Does & Why It Matters
AquaSentry predicts district-level water stress 30–90 days in advance for
Kazakhstan using satellite climate data and machine learning. 

**Equity-First Approach:** Water scarcity disproportionately affects rural agricultural communities. By providing highly localized, early-warning stress predictions, AquaSentry enables decision-makers to equitably coordinate regional water allocation, proactively activate drought reserves, and protect the livelihoods of local farmers before a crisis hits.

## Tech Stack
| Layer | Technology |
|-------|-----------|
| ML Model | XGBoost (multi-class classifier) |
| Data Source | NASA POWER satellite precipitation (MERRA-2, 2015–2024) |
| Boundaries | GADM Kazakhstan Level-1 (14 oblasts) |
| Backend | Python + FastAPI |
| Frontend | React + Leaflet.js |

## Model Performance
- **Train accuracy (2015–2022):** 96.6%
- **Test accuracy (2023–2024):** 87.5%
- **Test F1-Score:** 87.1%
- **Class Balancing:** SMOTE applied on the training set to combat class imbalance.
- **Explainability:** SHAP global importance exported to `backend/shap_importance.json`.
- **Backtested on 2021 Central Asian Drought** — correctly flagged Warning/Emergency
  for southern oblasts (Yujno-kazachstanskaya, Jambylslkaya, Almatinskaya) during 2021

> **Note:** 87.5% test accuracy with no data leakage — all 13 features are
> temporally lagged by 1–2 months to ensure genuine forecasting.

## Drought Stress Levels
| Level | Composite Z-Score Threshold | Color |
|-------|-----------------------------|-------|
| Normal | > −0.3 | 🟢 `#2ecc71` |
| Watch | −0.3 to −0.6 | 🟡 `#f39c12` |
| Warning | −0.6 to −0.9 | 🟠 `#e67e22` |
| Emergency | < −0.9 | 🔴 `#e74c3c` |

## Coverage
- **14 Kazakhstan oblasts** (GADM Level-1 boundaries)
- **30 / 60 / 90-day forecasts** per oblast
- Confidence score per prediction (model probability)

## Features Used (13 Features — All Lag-Shifted, No Data Leakage)
1. `month_sin` / `month_cos` — Cyclical seasonal position
2. `rain_z_lag1`, `rain_z_lag2` — Rainfall Z-score 1-2 months before prediction target
3. `temp_z_lag1`, `temp_z_lag2` — Temperature Z-score 1-2 months before prediction target
4. `soil_z_lag1`, `soil_z_lag2` — Soil Moisture Z-score 1-2 months before prediction target
5. `rain_z_roll3`, `temp_z_roll3`, `soil_z_roll3` — 3-month rolling averages of lagged anomalies
6. `rain_z_trend` — Direction of rainfall change (lag1 − lag2)
7. `roll3_lag1` — Previous month's 3-month rolling composite anomaly

## Data Source
Precipitation data downloaded from **NASA POWER API** (MERRA-2 reanalysis,
bias-corrected). 1680 records: 14 oblasts × 10 years × 12 months.
- API: `https://power.larc.nasa.gov/api/temporal/monthly/point`
- Parameter: `PRECTOTCORR` (mm/day → converted to total monthly mm)
- No synthetic data used.

## How to Run (Backend API)
```bash
cd backend
pip install fastapi uvicorn joblib pandas
uvicorn main:app --reload
# GET /api/predictions → returns predictions.json
```

## Output Files
| File | Description |
|------|-------------|
| `data/processed/chirps_by_oblast.csv` | Monthly rainfall per oblast (1680 rows, real NASA POWER data) |
| `data/processed/stress_index.csv` | Drought stress + all ML features |
| `backend/model.pkl` | Trained XGBoost classifier (n_estimators=400, 13 features) |
| `backend/predictions.json` | 30/60/90-day forecasts for all 14 oblasts |
| `backend/shap_importance.json` | Global SHAP feature importances |
| `backend/model_accuracy.txt` | Train/test accuracy and F1-score numbers |

## GeoJSON Oblast Name Column
- **Column:** `NAME_1`
- **14 oblasts:** Almaty, Aqmola, Aqtöbe, Atyrau, EastKazakhstan, Mangghystau,
  NorthKazakhstan, Pavlodar, Qaraghandy, Qostanay, Qyzylorda, SouthKazakhstan,
  WestKazakhstan, Zhambyl

## Color Scheme for Frontend
```json
{
  "Normal":    "#2ecc71",
  "Watch":     "#f39c12",
  "Warning":   "#e67e22",
  "Emergency": "#e74c3c"
}
```

## Data Sources
- NASA POWER Precipitation: https://power.larc.nasa.gov/
- Kazakhstan Boundaries: https://gadm.org (gadm41_KAZ_1)

## Team
- **Member A** — ML & Data Engineering (satellite data pipeline + XGBoost model)
- **Member B** — Frontend & Backend (React dashboard + FastAPI API)
- **Member C** — Research, Strategy & Pitch

---
*AquaSentry | SmartEarth 2026 Hackathon | Nazarbayev University*
