from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
import json
import math
import joblib
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="AquaSentry API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
PREDICTIONS_FILE = BASE_DIR / "predictions.json"
MODEL_FILE = BASE_DIR / "model.pkl"
SHAP_FILE = BASE_DIR / "shap_importance.json"
GEOJSON_FILE = BASE_DIR.parent / "data" / "raw" / "kazakhstan_oblasts.geojson"
CSV_FILE = BASE_DIR.parent / "data" / "processed" / "stress_index.csv"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    "month_sin", "month_cos",
    "rain_z_lag1", "rain_z_lag2", "rain_z_roll3", "rain_z_trend",
    "temp_z_lag1", "temp_z_lag2", "temp_z_roll3",
    "soil_z_lag1", "soil_z_lag2", "soil_z_roll3",
    "roll3_lag1",
    "ndvi_z_lag1", "ndvi_z_lag2",
    "flow_z_lag1", "flow_z_lag2",
    "irrigation_efficiency",
]

STRESS_NAMES = {0: "Normal", 1: "Watch", 2: "Warning", 3: "Emergency"}

NAME_MAP = {
    "Aqmola": "Akmolinskaya",
    "Aqtöbe": "Aktyubinskaya",
    "Almaty": "Almatinskaya",
    "Atyrau": "Atyrauskaya",
    "Zhambyl": "Jambylslkaya",
    "Qaraghandy": "Karagandinskaya",
    "Qostanay": "Kustanayskaya",
    "Qyzylorda": "Kyzylordinskaya",
    "Mangghystau": "Mangistauskaya",
    "Pavlodar": "Pavlodarskaya",
    "NorthKazakhstan": "Severo-kazachstanskaya",
    "EastKazakhstan": "Vostochno-kazachstanskaya",
    "SouthKazakhstan": "Yujno-kazachstanskaya",
    "WestKazakhstan": "Zapadno-kazachstanskaya",
}

# Reverse map: CSV name -> GeoJSON name
REVERSE_NAME_MAP = {v: k for k, v in NAME_MAP.items()}

# ---------------------------------------------------------------------------
# Module-level caches (loaded once at startup)
# ---------------------------------------------------------------------------
_model = None
_df = None
_predictions = None


def _load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_FILE)
    return _model


def _load_csv():
    global _df
    if _df is None:
        _df = pd.read_csv(CSV_FILE)
    return _df


def _load_predictions():
    global _predictions
    if _predictions is None:
        if PREDICTIONS_FILE.exists():
            with open(PREDICTIONS_FILE) as f:
                _predictions = json.load(f)
        else:
            _predictions = {}
    return _predictions


def _resolve_oblast(geojson_name: str) -> str:
    """Map GeoJSON oblast name to CSV name. Raises 404 if unknown."""
    csv_name = NAME_MAP.get(geojson_name)
    if csv_name is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown oblast '{geojson_name}'. Valid names: {list(NAME_MAP.keys())}",
        )
    return csv_name


def _safe_div(value: float, std: float) -> float:
    """Compute z-score safely, matching updated training formula."""
    if std is None or std == 0 or (isinstance(std, float) and math.isnan(std)):
        return 0.0
    return value / std


def _nan_safe(v, default=0.0):
    """Convert NaN/None to a default value for JSON-safe output."""
    if v is None:
        return default
    try:
        if math.isnan(v):
            return default
    except TypeError:
        pass
    return v


# ---------------------------------------------------------------------------
# Startup: eagerly load model + CSV so first request is fast
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_load():
    _load_model()
    _load_csv()
    _load_predictions()


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "AquaSentry API is running", "version": "2.0.0"}


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": _model is not None,
        "csv_loaded": _df is not None,
        "predictions_loaded": _predictions is not None,
    }


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------
@app.get("/api/geojson")
def get_geojson():
    if GEOJSON_FILE.exists():
        with open(GEOJSON_FILE) as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="GeoJSON not found")


# ---------------------------------------------------------------------------
# GET /api/predictions — enriched with baselines + climatological stats
# ---------------------------------------------------------------------------
@app.get("/api/predictions")
def get_all_predictions():
    preds = _load_predictions()
    df = _load_csv()

    latest_year = int(df["year"].max())

    enriched: dict = {}
    for geo_name, pred_data in preds.items():
        csv_name = NAME_MAP.get(geo_name)
        if csv_name is None:
            enriched[geo_name] = pred_data
            continue

        obl = df[df["oblast"] == csv_name]
        if obl.empty:
            enriched[geo_name] = pred_data
            continue

        # Baseline: averages for the latest year
        latest = obl[obl["year"] == latest_year]
        baseline_rain = _nan_safe(float(latest["rainfall_mm"].mean())) if not latest.empty else 0.0
        baseline_temp = _nan_safe(float(latest["temp_c"].mean())) if not latest.empty else 0.0
        baseline_soil = _nan_safe(float(latest["soil_moisture"].mean())) if not latest.empty else 0.0

        # Climatological stats (constant per oblast — take from first row)
        first = obl.iloc[0]
        stats = {
            "rain_mean": float(first["rain_mean"]) if pd.notna(first["rain_mean"]) else 0.0,
            "rain_std": float(first["rain_std"]) if pd.notna(first["rain_std"]) else 0.0,
            "temp_mean": float(first["temp_mean"]) if pd.notna(first["temp_mean"]) else 0.0,
            "temp_std": float(first["temp_std"]) if pd.notna(first["temp_std"]) else 0.0,
            "soil_mean": float(first["soil_mean"]) if pd.notna(first["soil_mean"]) else 0.0,
            "soil_std": float(first["soil_std"]) if pd.notna(first["soil_std"]) else 0.0,
        }

        enriched[geo_name] = {
            **pred_data,
            "baseline_rain_mm": round(baseline_rain, 2),
            "baseline_temp_c": round(baseline_temp, 2),
            "baseline_soil_vwc": round(baseline_soil, 4),
            **{k: round(v, 4) for k, v in stats.items()},
        }

    return enriched


# ---------------------------------------------------------------------------
# GET /api/history/{oblast}
# ---------------------------------------------------------------------------
@app.get("/api/history/{oblast}")
def get_history(oblast: str):
    csv_name = _resolve_oblast(oblast)
    df = _load_csv()

    obl = df[df["oblast"] == csv_name].copy()
    if obl.empty:
        raise HTTPException(status_code=404, detail=f"No data for oblast '{oblast}'")

    # Last 3 years
    target_years = [2022, 2023, 2024]
    result = []

    for yr in target_years:
        yr_data = obl[obl["year"] == yr]
        if yr_data.empty:
            continue

        avg_rain = _nan_safe(float(yr_data["rainfall_mm"].mean()))
        avg_temp = _nan_safe(float(yr_data["temp_c"].mean()))
        avg_soil = _nan_safe(float(yr_data["soil_moisture"].mean()))

        # Stress distribution
        dist = yr_data["stress_name"].value_counts().to_dict()
        # Ensure all keys present
        for sn in ["Normal", "Watch", "Warning", "Emergency"]:
            dist.setdefault(sn, 0)
        # Convert numpy ints to plain ints
        dist = {k: int(v) for k, v in dist.items()}

        result.append(
            {
                "year": yr,
                "avg_rain_mm": round(avg_rain, 2),
                "avg_temp_c": round(avg_temp, 2),
                "avg_soil_vwc": round(avg_soil, 4),
                "stress_distribution": dist,
            }
        )

    return result


# ---------------------------------------------------------------------------
# POST /api/simulate — real XGBoost inference with iterative forecasting
# ---------------------------------------------------------------------------
class SimulationRequest(BaseModel):
    oblast: str
    rainfall_mm: float
    temp_c: float
    soil_moisture_vwc: float


@app.post("/api/simulate")
def simulate(req: SimulationRequest):
    csv_name = _resolve_oblast(req.oblast)
    model = _load_model()
    df = _load_csv()

    obl = df[df["oblast"] == csv_name].sort_values(["year", "month"])
    if obl.empty:
        raise HTTPException(status_code=404, detail=f"No data for oblast '{req.oblast}'")

    latest = obl.iloc[-1]

    # ---- BUG #3 FIX: Use per-MONTH climatological stats, not latest row's month ----
    # The simulation predicts for the NEXT month, so use that month's baseline.
    latest_month = int(latest["month"])
    sim_month_30 = (latest_month % 12) + 1  # wraps Dec→Jan

    # Look up stats for the simulation month (per-month, per-oblast)
    sim_month_rows = obl[obl["month"] == sim_month_30]
    if not sim_month_rows.empty:
        stats_row = sim_month_rows.iloc[0]  # stats are constant per (oblast, month)
    else:
        stats_row = latest  # fallback to latest if no data for that month

    rain_mean = float(stats_row["rain_mean"]) if pd.notna(stats_row["rain_mean"]) else 0.0
    rain_std = float(stats_row["rain_std"]) if pd.notna(stats_row["rain_std"]) else 1.0
    temp_mean = float(stats_row["temp_mean"]) if pd.notna(stats_row["temp_mean"]) else 0.0
    temp_std = float(stats_row["temp_std"]) if pd.notna(stats_row["temp_std"]) else 1.0
    soil_mean = float(stats_row["soil_mean"]) if pd.notna(stats_row["soil_mean"]) else 0.0
    soil_std = float(stats_row["soil_std"]) if pd.notna(stats_row["soil_std"]) else 0.0

    # ---- BUG #1 FIX: Compute z-scores safely without mathematical compression ----
    rain_z_new = _safe_div(req.rainfall_mm - rain_mean, rain_std)
    temp_z_new = _safe_div(req.temp_c - temp_mean, temp_std)
    soil_z_new = _safe_div(req.soil_moisture_vwc - soil_mean, soil_std)

    # ---- Existing lag/rolling values from the latest CSV row ----
    def _val(col: str) -> float:
        v = latest.get(col, 0.0)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return 0.0
        return float(v)

    # For 30-day prediction: new values become lag1, old lag1 becomes lag2
    rain_z_lag1 = rain_z_new
    rain_z_lag2 = _val("rain_zscore")  # latest month's actual z-score → now becomes lag2
    
    # Correctly recover lag3 from historical data (z_score from T-1)
    rain_z_lag3 = _val("rain_z_lag1")
    temp_z_lag3 = _val("temp_z_lag1")
    soil_z_lag3 = _val("soil_z_lag1")

    temp_z_lag1 = temp_z_new
    temp_z_lag2 = _val("temp_zscore")
    soil_z_lag1 = soil_z_new
    soil_z_lag2 = _val("soil_zscore")

    # ---- BUG #2 FIX: Compute roll3 as mean(lag1, lag2, lag3) matching training ----
    rain_z_roll3 = (rain_z_lag1 + rain_z_lag2 + rain_z_lag3) / 3.0
    rain_z_trend = rain_z_lag1 - rain_z_lag2
    temp_z_roll3 = (temp_z_lag1 + temp_z_lag2 + temp_z_lag3) / 3.0
    soil_z_roll3 = (soil_z_lag1 + soil_z_lag2 + soil_z_lag3) / 3.0

    # Compute target precursor dynamically so it reacts to UI sliders
    roll3_lag1_val = (0.5 * rain_z_roll3) + (0.3 * soil_z_roll3) - (0.2 * temp_z_roll3)

    # ---- Month for the simulation (already computed above) ----
    sim_month = sim_month_30

    month_sin = math.sin(2 * math.pi * sim_month / 12)
    month_cos = math.cos(2 * math.pi * sim_month / 12)

    ndvi_z_lag1 = _val("ndvi_zscore")
    ndvi_z_lag2 = _val("ndvi_z_lag1")
    flow_z_lag1 = _val("flow_zscore")
    flow_z_lag2 = _val("flow_z_lag1")
    ie = _val("irrigation_efficiency")

    # ---- Helper to build feature vector, predict, and return result ----
    def _predict(
        m_sin, m_cos,
        rz_l1, rz_l2, rz_r3, rz_trend,
        tz_l1, tz_l2, tz_r3,
        sz_l1, sz_l2, sz_r3,
        r3_l1,
        nz_l1, nz_l2,
        fz_l1, fz_l2,
        ie_val
    ):
        features = pd.DataFrame(
            [[m_sin, m_cos, rz_l1, rz_l2, rz_r3, rz_trend,
              tz_l1, tz_l2, tz_r3, sz_l1, sz_l2, sz_r3, r3_l1,
              nz_l1, nz_l2, fz_l1, fz_l2, ie_val]],
            columns=FEATURE_COLS
        )
        try:
            pred_class = int(model.predict(features)[0])
            pred_proba = model.predict_proba(features)[0]
        except AttributeError:
            # For LSTM wrapper fallback or other models without predict_proba sometimes
            pred_class = int(model.predict(features)[0])
            pred_proba = [0.0, 0.0, 0.0, 0.0]
            pred_proba[pred_class] = 1.0

        stress_name = STRESS_NAMES.get(pred_class, "Normal")
        confidence = float(pred_proba[pred_class])
        proba_dict = {STRESS_NAMES[i]: round(float(p), 4) for i, p in enumerate(pred_proba)}
        return stress_name, confidence, proba_dict, features.iloc[0].to_dict()

    stress_30, conf_30, proba_30, feat_30 = _predict(
        month_sin, month_cos,
        rain_z_lag1, rain_z_lag2, rain_z_roll3, rain_z_trend,
        temp_z_lag1, temp_z_lag2, temp_z_roll3,
        soil_z_lag1, soil_z_lag2, soil_z_roll3,
        roll3_lag1_val,
        ndvi_z_lag1, ndvi_z_lag2, flow_z_lag1, flow_z_lag2, ie
    )

    # ---- 60-day prediction (iterative: shift lags, recompute rolls, inc month) ----
    # Shift lags: lag1→lag2, lag2→lag3, new value persists as lag1
    rz_l3_60 = rain_z_lag2   # old lag2 → new lag3
    rz_l2_60 = rain_z_lag1   # old lag1 → new lag2
    rz_l1_60 = rain_z_lag1   # persist same z-score forward (simulate same climate continuing)
    tz_l3_60 = temp_z_lag2
    tz_l2_60 = temp_z_lag1
    tz_l1_60 = temp_z_lag1
    sz_l3_60 = soil_z_lag2
    sz_l2_60 = soil_z_lag1
    sz_l1_60 = soil_z_lag1

    rz_r3_60 = (rz_l1_60 + rz_l2_60 + rz_l3_60) / 3.0   # BUG #2 FIX: proper mean(l1,l2,l3)
    rz_trend_60 = rz_l1_60 - rz_l2_60
    tz_r3_60 = (tz_l1_60 + tz_l2_60 + tz_l3_60) / 3.0
    sz_r3_60 = (sz_l1_60 + sz_l2_60 + sz_l3_60) / 3.0
    r3_l1_60 = (0.5 * rz_r3_60) + (0.3 * sz_r3_60) - (0.2 * tz_r3_60)

    sim_month_60 = (sim_month % 12) + 1
    m_sin_60 = math.sin(2 * math.pi * sim_month_60 / 12)
    m_cos_60 = math.cos(2 * math.pi * sim_month_60 / 12)

    stress_60, conf_60, proba_60, feat_60 = _predict(
        m_sin_60, m_cos_60,
        rz_l1_60, rz_l2_60, rz_r3_60, rz_trend_60,
        tz_l1_60, tz_l2_60, tz_r3_60,
        sz_l1_60, sz_l2_60, sz_r3_60,
        r3_l1_60,
        ndvi_z_lag1, ndvi_z_lag1, flow_z_lag1, flow_z_lag1, ie
    )

    # ---- 90-day prediction (one more iteration) ----
    rz_l3_90 = rz_l2_60
    rz_l2_90 = rz_l1_60
    rz_l1_90 = rz_l1_60
    tz_l3_90 = tz_l2_60
    tz_l2_90 = tz_l1_60
    tz_l1_90 = tz_l1_60
    sz_l3_90 = sz_l2_60
    sz_l2_90 = sz_l1_60
    sz_l1_90 = sz_l1_60

    rz_r3_90 = (rz_l1_90 + rz_l2_90 + rz_l3_90) / 3.0   # BUG #2 FIX: proper mean(l1,l2,l3)
    rz_trend_90 = rz_l1_90 - rz_l2_90
    tz_r3_90 = (tz_l1_90 + tz_l2_90 + tz_l3_90) / 3.0
    sz_r3_90 = (sz_l1_90 + sz_l2_90 + sz_l3_90) / 3.0
    r3_l1_90 = (0.5 * rz_r3_90) + (0.3 * sz_r3_90) - (0.2 * tz_r3_90)

    sim_month_90 = (sim_month_60 % 12) + 1
    m_sin_90 = math.sin(2 * math.pi * sim_month_90 / 12)
    m_cos_90 = math.cos(2 * math.pi * sim_month_90 / 12)

    stress_90, conf_90, proba_90, feat_90 = _predict(
        m_sin_90, m_cos_90,
        rz_l1_90, rz_l2_90, rz_r3_90, rz_trend_90,
        tz_l1_90, tz_l2_90, tz_r3_90,
        sz_l1_90, sz_l2_90, sz_r3_90,
        r3_l1_90,
        ndvi_z_lag1, ndvi_z_lag1, flow_z_lag1, flow_z_lag1, ie
    )

    return {
        "oblast": req.oblast,
        "stress_30d": stress_30,
        "stress_60d": stress_60,
        "stress_90d": stress_90,
        "confidence_30d": round(conf_30, 4),
        "confidence_60d": round(conf_60, 4),
        "confidence_90d": round(conf_90, 4),
        "probabilities_30d": proba_30,
    }

# ---------------------------------------------------------------------------
# GET /api/explainability
# ---------------------------------------------------------------------------
@app.get("/api/explainability")
def get_explainability():
    if SHAP_FILE.exists():
        with open(SHAP_FILE) as f:
            return json.load(f)
    return {}

# ---------------------------------------------------------------------------
# GET /api/alerts
# ---------------------------------------------------------------------------
import random
@app.get("/api/alerts")
def get_alerts():
    preds = _load_predictions()
    alerts = []
    for geo_name, p in preds.items():
        if p.get("stress_30d") in ["Warning", "Emergency"]:
            severity = p.get("stress_30d").upper()
            alerts.append({
                "id": f"alert-{geo_name}-{random.randint(1000,9999)}",
                "oblast": geo_name,
                "severity": severity,
                "message": f"Critical drought {severity.lower()} conditions predicted in {geo_name} within 30 days.",
                "timestamp": pd.Timestamp.now().isoformat()
            })
    # Sort emergencies first
    return sorted(alerts, key=lambda x: 0 if x["severity"] == "EMERGENCY" else 1)

# ---------------------------------------------------------------------------
# GET /api/models/comparison
# ---------------------------------------------------------------------------
@app.get("/api/models/comparison")
def get_models_comparison():
    comp_file = BASE_DIR / "model_comparison.json"
    if comp_file.exists():
        with open(comp_file) as f:
            return json.load(f)
    return {}
