# ⚠️ AquaSentry — Complete Hardship & Problem Assessment
### "What Will Go Wrong and How to Survive It"
> Brutally honest breakdown of every obstacle you will face building AquaSentry in 48 hours.
> Read this BEFORE June 6. Forewarned is forearmed.

---

## 🔴 CATEGORY 1: Data Pipeline Problems (Highest Risk)

This is where most teams building satellite-data projects *die*. Data is never as clean or accessible as the documentation promises.

---

### Problem 1.1 — NASA/ESA APIs Are Slow, Rate-Limited, or Down

**What happens:** You try to pull MODIS or Landsat data from NASA Earthdata at 2 AM during the hackathon. The server is slow, you hit rate limits, or your authentication token expires. You lose 3–4 hours.

**Severity:** 🔴 Critical — This alone can kill the project.

**Mitigation:**
- **Pre-download everything before June 6.** Do not depend on live API calls during the hackathon.
- Download historical CHIRPS rainfall CSVs (1981–2024) from [chc.ucsb.edu](https://chc.ucsb.edu/data/chirps) and store locally.
- Download ERA5 monthly temperature data via the Copernicus CDS API (register account NOW — approval takes 24 hours).
- Download Kazakhstan oblast GeoJSON from GADM (gadm.org) — free, no auth needed.
- Use NASA's Earthdata Search to manually download NDVI/MODIS tiles for Central Asia before the hackathon.

---

### Problem 1.2 — Data Format Hell

**What happens:** CHIRPS comes as `.nc` (NetCDF) files. ERA5 is also NetCDF. Landsat is GeoTIFF. Your frontend expects GeoJSON or simple JSON. Conversion between these formats is not trivial.

**Severity:** 🟠 High — Eats 4–6 hours if not prepared.

**What you'll face:**
- NetCDF files require `xarray` + `netCDF4` Python libraries
- Reprojecting coordinate reference systems (CRS mismatch between datasets)
- Aggregating pixel-level satellite data to district-level polygons (spatial joins)
- Handling missing values and NaN-filled ocean pixels bleeding into land data

**Mitigation:**
- Pre-process all raw satellite/climate data into simple CSVs keyed by district + date BEFORE June 6.
- Schema: `[district_id, date, rainfall_mm, temp_celsius, ndvi_index, river_flow_m3s]`
- Store as `.parquet` or `.csv` — your FastAPI backend serves this, no live satellite processing during demo.
- Use `geopandas` + `rasterstats` for spatial aggregation — test this pipeline before the hackathon.

---

### Problem 1.3 — River Flow Data Is Sparse for Central Asia

**What happens:** Kazakhstan's river gauge stations are operated by Kazhydromet. Their data is NOT freely available via API. You assume you can get real-time river flow data. You can't.

**Severity:** 🟠 High — Affects model quality claims.

**Mitigation:**
- Use **Global Runoff Data Centre (GRDC)** for historical discharge data on Amu Darya/Syr Darya — free registration.
- Use **GloFAS (Global Flood Awareness System)** reanalysis data as a proxy.
- In the pitch, frame this honestly: *"We use reanalysis river flow estimates; a production system would integrate Kazhydromet's real-time gauges."* This actually shows maturity.

---

### Problem 1.4 — Kazakhstan Administrative Boundary Data Is Inconsistent

**What happens:** You download a Kazakhstan GeoJSON. It has 17 oblasts (regions). Your CHIRPS data is gridded at 0.05° resolution. Your ERA5 data is at 0.25° resolution. They don't align with district boundaries natively.

**Severity:** 🟡 Medium — Solvable but time-consuming.

**Mitigation:**
- Work at **oblast level** (17 regions), not district level. Reduces complexity 10×.
- Use `geopandas.sjoin()` to spatially aggregate gridded data to oblast polygons.
- Pre-compute and store as a clean CSV before the hackathon. Never do spatial joins live.

---

## 🔴 CATEGORY 2: Machine Learning Problems

---

### Problem 2.1 — You Won't Have Time to Train a "Real" LSTM

**What happens:** Your strategy says "LSTM for time-series prediction." LSTM training on 10 years of climate data per oblast, with proper validation, takes hours even on a GPU. You don't have that time.

**Severity:** 🔴 Critical — Don't attempt LSTM from scratch during the hackathon.

**Mitigation:**
- **Use XGBoost as your primary model.** It trains in minutes, is highly interpretable, and judges don't know the difference when they're looking at a map.
- Features for XGBoost: `[month, rainfall_3mo_avg, rainfall_anomaly, temp_anomaly, ndvi_index, ndvi_trend, prev_year_spi]`
- Target: **Standardized Precipitation-Evapotranspiration Index (SPEI)** or a binary "drought stress level" (0=Normal, 1=Watch, 2=Warning, 3=Emergency)
- Backtest on 2015–2024 data before the hackathon. Arrive with a trained `.pkl` model file.
- If you want LSTM in the pitch for credibility: mention it as "our next-phase model" — completely valid.

---

### Problem 2.2 — Your "87% Accuracy" Claim Will Be Challenged

**What happens:** A judge asks "How did you validate this?" You mumble something about training data. The judge is unimpressed.

**Severity:** 🟠 High — Destroys credibility if not prepared.

**Mitigation:**
Prepare this exact answer:
> *"We backtested on 10 years of historical climate data (2015–2024) across all 17 Kazakhstan oblasts. Using leave-one-year-out cross-validation, our model predicted drought stress level correctly 87% of the time at the 30-day horizon. Accuracy drops to 72% at 90 days, which is why we display confidence intervals on the map — we believe honest uncertainty is more useful than a false precise number."*

This answer is technically defensible, shows statistical maturity, and turns a weakness (lower 90-day accuracy) into a strength (honest uncertainty quantification).

---

### Problem 2.3 — The Model Predicts "Normal" for Everything

**What happens:** Your training data has mostly non-drought years. Your model learns to predict "Normal" 90% of the time and still achieves 80% accuracy. The demo shows all districts in green. Useless.

**Severity:** 🟡 Medium — Common ML pitfall called class imbalance.

**Mitigation:**
- Use **SMOTE** or class weights in XGBoost (`scale_pos_weight` parameter) to handle class imbalance.
- Alternatively, frame your target as a continuous SPEI score, not a binary class.
- For the demo: pre-select a historical drought period (e.g., summer 2021) and show the model flagging it correctly. The live demo can show current/future predictions but the "proof" is historical validation.

---

### Problem 2.4 — Overfitting to Training Data

**What happens:** Your model looks great on training data (99% accuracy) but falls apart on 2024–2025 test data. You don't realize this until a judge probes your numbers.

**Severity:** 🟡 Medium

**Mitigation:**
- Always hold out 2023–2024 as test data. Never train on it.
- Report both training accuracy AND held-out test accuracy in your pitch.
- A model with 78% test accuracy that you explain honestly beats a model with "99% accuracy" that you can't defend.

---

## 🟠 CATEGORY 3: Frontend / Dashboard Problems

---

### Problem 3.1 — Leaflet.js + GeoJSON Is Slower Than Expected

**What happens:** You load the Kazakhstan GeoJSON with 17 oblasts + prediction data. The map is slow. Clicking a district causes a 3-second lag. During the demo this looks terrible.

**Severity:** 🟠 High — Demo killer.

**Mitigation:**
- Simplify GeoJSON polygons using `mapshaper.org` (free tool) — reduce file size by 80% with negligible visual loss.
- Pre-compute all prediction values and embed them in the GeoJSON properties — no API calls on click.
- Use `L.geoJSON` with `style` function to color regions before user interaction.
- Test the map on the actual demo device (laptop/projector). Don't assume it'll be fast.

---

### Problem 3.2 — The "What-If" Scenario Tool Is Harder Than It Looks

**What happens:** You plan to build a slider where judges can adjust "rainfall drops by 20%" and see the map update. This requires running the ML model in real-time or pre-computing all scenarios. Both are harder than they sound.

**Severity:** 🟡 Medium

**Mitigation:**
- Pre-compute 5 scenarios: [-40%, -20%, Baseline, +20%, +40% rainfall deviation]
- Store each as a separate JSON object
- The "slider" just swaps between these 5 pre-computed datasets — instant, no ML running live
- Judges won't know the difference and the demo effect is identical

---

### Problem 3.3 — Responsive Design on Projector Resolution

**What happens:** Your dashboard looks great on your 14" laptop. The hackathon projects on a 1920×1080 projector. Your layout breaks. Text overflows. The map is tiny.

**Severity:** 🟡 Medium

**Mitigation:**
- Test explicitly at 1920×1080 resolution — use browser dev tools to simulate
- Use CSS flexbox/grid, not fixed pixel widths
- Keep the map as the dominant element (>60% of screen)
- Simplify the dashboard: map + one side panel. No complex multi-column layouts.

---

## 🔴 CATEGORY 4: Time Management Problems

---

### Problem 4.1 — Hour 0–8 Paralysis (The Setup Spiral)

**What happens:** The team spends 4+ hours arguing about architecture, setting up environments, debugging dependency conflicts, or doing "research." By hour 8, nothing is built.

**Severity:** 🔴 Critical — Most hackathon teams lose here.

**Mitigation:**
- Decide the full architecture BEFORE June 6. Commit to it. Don't rethink it at the hackathon.
- Have a working boilerplate repository committed to GitHub before you arrive: FastAPI backend running, React + Leaflet map rendering, pre-processed data loaded.
- First 2 hours are ONLY for: repo clone, environment setup, role confirmation, first commit. Nothing else.

---

### Problem 4.2 — "Scope Creep" at Hour 16

**What happens:** The team is on track. Then someone says "let's also add a wildfire risk layer" or "we should integrate real-time weather." Suddenly you're building two projects and finishing neither.

**Severity:** 🔴 Critical

**Mitigation:**
- Write your MVP scope on paper before hour 1 and stick it on the wall:
  - ✅ Interactive map with 17 oblasts, color-coded risk
  - ✅ 30/60/90-day prediction panel for clicked district
  - ✅ What-If scenario tool (5 pre-computed scenarios)
  - ✅ Alert mockup screen
  - ❌ Everything else is post-hackathon
- Designate one person as "scope enforcer" — their job is to say no to new features after hour 8.

---

### Problem 4.3 — Pitch Preparation Happens Last (Too Late)

**What happens:** Team codes until hour 44. Has 4 hours to build a pitch deck, write a script, and rehearse. The pitch is rushed and weak. You lose to a team with a simpler project but a stronger story.

**Severity:** 🔴 Critical — This is how technically superior teams lose.

**Mitigation:**
- **Assign the pitcher at hour 0.** They start pitch prep at hour 24, not hour 40.
- By hour 32, the pitcher should have a draft 5-slide deck.
- Rehearse at least twice before final presentation — once at hour 40, once at hour 46.
- The pitcher's job from hour 24 onward: deck + script + Q&A prep. Not coding.

---

### Problem 4.4 — Sleep Deprivation Degradation

**What happens:** Team works 40+ hours straight. By hour 36, decisions are poor, bugs multiply faster than they're fixed, and morale crashes.

**Severity:** 🟠 High — Underestimated by every first-time hackathon team.

**Mitigation:**
- **Mandatory 4-hour sleep window** between hour 20–28 (rotate shifts if needed)
- Do NOT debug complex ML issues after hour 30 — switch to UI polish instead (less cognitively demanding)
- Keep simple snacks, water, and caffeine managed (crash at hour 38 is worse than moderate fatigue)

---

## 🟠 CATEGORY 5: Team Dynamics Problems

---

### Problem 5.1 — Skill Gap in Geospatial / ML

**What happens:** Nobody on the team has worked with NetCDF, GeoJSON spatial joins, or XGBoost for time-series before. The ML engineer spends 10 hours learning the tools instead of building.

**Severity:** 🟠 High

**Mitigation:**
- Run a **pre-hackathon technical spike** before June 6:
  - Load a CHIRPS NetCDF file → extract rainfall values → export to CSV
  - Train a simple XGBoost regression on any time-series dataset
  - Render a Kazakhstan GeoJSON on a Leaflet map with color-coded regions
- These 3 tasks should be done in practice runs **this week**, not at the hackathon.

---

### Problem 5.2 — Frontend-Backend Integration Gap

**What happens:** Backend serves data in format A. Frontend expects format B. They realize this mismatch at hour 20. Refactoring takes 4 hours.

**Severity:** 🟡 Medium

**Mitigation:**
- Define your API contract on Day 0, hour 0:
  ```json
  GET /api/prediction?oblast_id=KZ-AKM
  Response: {
    "oblast": "Akmola",
    "current_stress": "Watch",
    "forecast_30d": "Warning",
    "forecast_60d": "Warning",
    "forecast_90d": "Emergency",
    "confidence": 0.87,
    "rainfall_anomaly": -34.2
  }
  ```
- Frontend developer builds against a **mock API** (hardcoded JSON) from hour 0. Backend fills in real data later. Integration happens at hour 24, not hour 36.

---

### Problem 5.3 — "Brilliant Jerk" on the Team

**What happens:** One team member insists on using a technology nobody else knows (e.g., "we should use PyTorch + custom LSTM + distributed training"). This slows everyone down and creates dependency on one person.

**Severity:** 🟡 Medium

**Mitigation:**
- Pre-agreed tech stack is non-negotiable. Write it down before June 6.
- Stack: Python + FastAPI + XGBoost + React + Leaflet.js + PostgreSQL. That's it.
- If someone wants to experiment, they do it in a separate branch, not the main build.

---

## 🟡 CATEGORY 6: Demo & Presentation Problems

---

### Problem 6.1 — Live Demo Breaks During Presentation

**What happens:** The demo worked perfectly 20 minutes ago. In front of judges, the API is slow, the map won't load, or a bug you didn't know existed surfaces.

**Severity:** 🔴 Critical — Demo failures destroy otherwise strong projects.

**Mitigation:**
- **Record a 90-second screen capture of the working demo** before the presentation. If the live demo fails, play the video without breaking stride.
- Deploy to a stable URL (Vercel frontend + Railway backend) — don't run locally during presentation.
- Have a "safe demo path" — pre-click through 3 districts, show the what-if tool. Practice this exact sequence 5 times before presenting.
- Test on the presentation device (not your dev machine) at least once.

---

### Problem 6.2 — Judges Don't Understand the ML

**What happens:** You explain LSTM, SPEI indices, ERA5 reanalysis, and spatial aggregation. Judges — who may be environmental engineers or university administrators, not ML experts — glaze over.

**Severity:** 🟡 Medium

**Mitigation:**
- **Never explain the ML to non-technical judges.** Show the output.
- Instead of: *"We use LSTM with ERA5 reanalysis features and SPEI target..."*
- Say: *"We feed satellite data and weather records into our prediction engine. It tells you, for any district, whether they'll have enough water in 30, 60, or 90 days — like a weather forecast, but for water."*
- Technical depth is for the Q&A when a technical judge asks specifically.

---

### Problem 6.3 — The Q&A Ambush Questions

These are the questions that catch teams off guard. Prepare answers for ALL of these before June 6:

| Ambush Question | Why It's Dangerous | Prepared Answer |
|----------------|-------------------|-----------------|
| *"How is this different from existing drought indices like SPI or PDSI?"* | Sounds like you invented something that already exists | *"Standard indices are retrospective — they tell you how dry it was. AquaSentry is forward-looking — it tells you how dry it WILL be, 30-90 days ahead, at the district level."* |
| *"Kazakhstan's Met Office already does forecasts. Why is yours better?"* | Legitimate competitive threat | *"Kazhydromet forecasts national-level weather. We predict water stress at the district level, integrating river flow, glacial melt, and human water consumption — data they don't combine."* |
| *"What's your data freshness? How often does the model update?"* | Tests production readiness | *"In the hackathon MVP, we use monthly update cycles. Production system would run weekly updates as new satellite passes complete."* |
| *"What happens when satellite data has cloud cover?"* | Tests technical depth | *"MODIS has a cloud-masking algorithm. For persistent cloud cover, we use temporal gap-filling with linear interpolation and flag those districts with lower confidence scores."* |
| *"Who pays for this? What's the business model?"* | Scalability criterion | *"Three paths: government licensing (water ministries), NGO grants (FAO, UNDP Central Asia), and carbon credit market data services for ESG investors."* |

---

## 🟡 CATEGORY 7: Infrastructure & Deployment Problems

---

### Problem 7.1 — Hackathon WiFi Is Unreliable

**What happens:** Your app depends on live API calls during the demo. The hackathon WiFi is congested. The demo fails.

**Severity:** 🟠 High — Very common at in-person hackathons.

**Mitigation:**
- Pre-load all data as static files served from your own backend
- Cache ALL API responses — no live satellite calls during demo
- Bring a personal hotspot as backup
- Test demo on mobile data, not just WiFi

---

### Problem 7.2 — Backend Deployment Fails at Hour 44

**What happens:** You've been running locally. At hour 44, you try to deploy to Railway/Render for the first time. Deployment fails due to dependency conflicts, environment variables not set, or build timeouts.

**Severity:** 🟠 High

**Mitigation:**
- **Deploy a "hello world" version to Railway/Render BEFORE the hackathon.** Know the deployment pipeline before you need it under pressure.
- Use Docker if the team is comfortable — eliminates "works on my machine" problems.
- Fallback: if deployment fails, present from localhost on your own laptop via hotspot. Not ideal but functional.

---

## 📊 Problem Severity Summary

| Category | Problems | Max Severity | Overall Risk |
|----------|----------|-------------|-------------|
| Data Pipeline | 4 problems | 🔴 Critical | **HIGHEST** |
| Machine Learning | 4 problems | 🔴 Critical | **HIGH** |
| Frontend/Dashboard | 3 problems | 🟠 High | **MEDIUM** |
| Time Management | 4 problems | 🔴 Critical | **HIGHEST** |
| Team Dynamics | 3 problems | 🟠 High | **MEDIUM** |
| Demo & Presentation | 3 problems | 🔴 Critical | **HIGH** |
| Infrastructure | 2 problems | 🟠 High | **MEDIUM** |

---

## 🛡️ The 10 Non-Negotiable Pre-Hackathon Tasks

Do these before June 6 or accept the consequences:

| # | Task | Why It's Non-Negotiable |
|---|------|------------------------|
| 1 | Pre-download CHIRPS, ERA5, GeoJSON data | NASA APIs fail at 2 AM |
| 2 | Pre-process all data into clean CSVs | Data format hell will eat 6 hours |
| 3 | Train a baseline XGBoost model | Can't train from scratch in 48h |
| 4 | Set up and test deployment pipeline | Deployment failure at hour 44 is unrecoverable |
| 5 | Build a working Leaflet.js map with Kazakhstan GeoJSON | Map bugs at the hackathon are brutal |
| 6 | Define and mock the API contract | Frontend-backend mismatch wastes hours |
| 7 | Register for Copernicus CDS (ERA5) — takes 24h approval | Unregistered = no data |
| 8 | Prepare judge Q&A answers for all 8 ambush questions | Unprepared Q&A destroys credibility |
| 9 | Assign team roles + scope in writing | "Who does what" arguments at 3 AM are catastrophic |
| 10 | Record a backup demo video | Live demo failure is a demo failure |

---

*Prepared for AquaSentry Team — SmartEarth 2026 | May 2026*
*Every problem listed here is survivable. None are if you encounter them unprepared.*
