# 💻 MEMBER B — Frontend & Backend Developer
## AquaSentry | SmartEarth 2026 | Pre-Hackathon Task Plan

> **Your job:** Build the interactive map dashboard, the FastAPI backend, and get everything deployed.
> By Day 3 evening, the live URL must be working end-to-end with real predictions from Member A.
> The demo runs on YOUR code — it must not crash.

---

## ⏰ Daily Sync Commitment
- **9:00 AM** — 15-min team standup (report what you'll do today)
- **9:00 PM** — 20-min check-in (share screenshots, flag blockers, demo progress)
- **Respond to WhatsApp within 2 hours** during working hours

---

---

# 📅 DAY 1 — Repository, Scaffold & Deployment

---

### ✅ Task B1.1 — Create the GitHub Repository
**Time: 30 minutes**

**Step-by-step:**

1. Go to GitHub → New Repository
   - Name: `aquasentry-2026`
   - Visibility: Public (required for hackathon submission)
   - Add README: Yes
   - .gitignore: Python

2. Add collaborators: Settings → Collaborators → invite Member A and Member C

3. Clone locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/aquasentry-2026.git
   cd aquasentry-2026
   ```

4. Create this folder structure:
   ```bash
   mkdir -p backend frontend/src/components data/raw data/processed scripts
   touch backend/main.py backend/requirements.txt
   touch frontend/src/App.jsx frontend/src/index.css
   touch .gitignore
   ```

5. Add to `.gitignore`:
   ```
   node_modules/
   __pycache__/
   *.pyc
   .env
   aquasentry-env/
   data/raw/
   *.nc
   *.pkl
   .DS_Store
   ```

6. Commit and push:
   ```bash
   git add .
   git commit -m "Initial project structure"
   git push origin main
   ```

**Share with team:**
- Post the GitHub repo link in WhatsApp
- Message: "✅ B1.1 done — Repo live: [LINK]. A and C please accept collaborator invite."

---

### ✅ Task B1.2 — Scaffold FastAPI Backend with Mock Data
**Time: 1.5 hours**

This gives Member A a clear target for the JSON format their predictions must match.

**Step-by-step:**

1. Create `backend/main.py`:
   ```python
   from fastapi import FastAPI, HTTPException
   from fastapi.middleware.cors import CORSMiddleware
   from pathlib import Path
   import json

   app = FastAPI(title="AquaSentry API", version="1.0.0")

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

   # Load predictions from JSON file (Member A will generate the real one)
   PREDICTIONS_FILE = Path(__file__).parent / "predictions.json"

   def load_predictions():
       if PREDICTIONS_FILE.exists():
           with open(PREDICTIONS_FILE) as f:
               return json.load(f)
       # Fallback mock data while waiting for Member A
       return {
           "Akmola":    {"stress_30d":"Watch",    "stress_60d":"Warning",  "stress_90d":"Warning",   "color_30d":"#f39c12","confidence":0.82,"rainfall_anomaly":-18.4,"current_level":"Watch"},
           "Almaty":    {"stress_30d":"Normal",   "stress_60d":"Watch",    "stress_90d":"Watch",     "color_30d":"#2ecc71","confidence":0.79,"rainfall_anomaly": -5.1,"current_level":"Normal"},
           "Atyrau":    {"stress_30d":"Warning",  "stress_60d":"Warning",  "stress_90d":"Emergency", "color_30d":"#e67e22","confidence":0.84,"rainfall_anomaly":-31.2,"current_level":"Warning"},
           "Turkistan": {"stress_30d":"Warning",  "stress_60d":"Emergency","stress_90d":"Emergency", "color_30d":"#e67e22","confidence":0.87,"rainfall_anomaly":-38.7,"current_level":"Warning"},
           "Kyzylorda": {"stress_30d":"Emergency","stress_60d":"Emergency","stress_90d":"Emergency", "color_30d":"#e74c3c","confidence":0.88,"rainfall_anomaly":-52.1,"current_level":"Emergency"},
           "Zhambyl":   {"stress_30d":"Warning",  "stress_60d":"Warning",  "stress_90d":"Emergency", "color_30d":"#e67e22","confidence":0.81,"rainfall_anomaly":-29.3,"current_level":"Warning"},
       }

   @app.get("/")
   def root():
       return {"message": "AquaSentry API is running", "version": "1.0.0"}

   @app.get("/health")
   def health():
       return {"status": "ok", "predictions_loaded": PREDICTIONS_FILE.exists()}

   @app.get("/api/predictions")
   def get_all_predictions():
       return load_predictions()

   @app.get("/api/prediction/{oblast}")
   def get_oblast_prediction(oblast: str):
       preds = load_predictions()
       if oblast not in preds:
           raise HTTPException(status_code=404, detail=f"Oblast '{oblast}' not found")
       return preds[oblast]

   @app.get("/api/scenarios/{deviation}")
   def get_scenario(deviation: int):
       """Return predictions for rainfall deviation scenarios: -40, -20, 0, +20, +40"""
       preds = load_predictions()
       scenario_shift = {-40: 2, -20: 1, 0: 0, 20: -1, 40: -2}
       stress_order   = ['Normal','Watch','Warning','Emergency']
       shift = scenario_shift.get(deviation, 0)
       result = {}
       for oblast, data in preds.items():
           current_idx = stress_order.index(data['stress_30d'])
           new_idx = max(0, min(3, current_idx + shift))
           result[oblast] = {**data, "stress_30d": stress_order[new_idx]}
       return result
   ```

2. Create `backend/requirements.txt`:
   ```
   fastapi==0.110.0
   uvicorn==0.27.0
   python-dotenv==1.0.0
   ```

3. Test locally:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

4. Open browser at `http://localhost:8000/api/predictions` — confirm JSON shows up

5. Open `http://localhost:8000/docs` — confirm Swagger UI works

**Share with team:**
- Screenshot of the `/api/predictions` JSON in browser
- Message: "✅ B1.2 done — Backend running. API format confirmed. A, this is the exact JSON structure your predictions.json must match."

---

### ✅ Task B1.3 — Scaffold React Frontend with Leaflet Map
**Time: 2.5 hours**

**Step-by-step:**

1. Set up React + Vite:
   ```bash
   cd frontend
   npm create vite@latest . -- --template react
   npm install leaflet react-leaflet d3 axios
   ```

2. Replace `frontend/src/App.jsx` with:
   ```jsx
   import { useEffect, useState } from 'react';
   import Map from './components/Map';
   import PredictionPanel from './components/PredictionPanel';
   import WhatIfTool from './components/WhatIfTool';
   import AlertMockup from './components/AlertMockup';
   import axios from 'axios';
   import './index.css';

   const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

   export default function App() {
     const [predictions, setPredictions]   = useState({});
     const [selectedOblast, setSelectedOblast] = useState(null);
     const [activeTab, setActiveTab]       = useState('map');
     const [scenario, setScenario]         = useState(0);
     const [loading, setLoading]           = useState(true);

     useEffect(() => {
       axios.get(`${API_URL}/api/predictions`)
         .then(res => { setPredictions(res.data); setLoading(false); })
         .catch(() => setLoading(false));
     }, []);

     const handleScenario = async (deviation) => {
       setScenario(deviation);
       const res = await axios.get(`${API_URL}/api/scenarios/${deviation}`);
       setPredictions(res.data);
     };

     return (
       <div className="app-container">
         <header className="app-header">
           <h1>🌊 AquaSentry</h1>
           <p>AI Water Stress Forecaster — Central Asia</p>
           <nav>
             {['map','whatif','alerts'].map(tab => (
               <button key={tab} className={activeTab===tab ? 'active' : ''}
                 onClick={() => setActiveTab(tab)}>
                 {tab === 'map' ? '🗺️ Map' : tab === 'whatif' ? '📊 What-If' : '🔔 Alerts'}
               </button>
             ))}
           </nav>
         </header>

         {loading && <div className="loading">Loading predictions...</div>}

         <main className="app-main">
           {activeTab === 'map' && (
             <>
               <div className="map-wrapper">
                 <Map predictions={predictions} onOblastClick={setSelectedOblast} />
               </div>
               <PredictionPanel oblast={selectedOblast}
                 data={predictions[selectedOblast]} />
             </>
           )}
           {activeTab === 'whatif' && (
             <WhatIfTool predictions={predictions} onScenarioChange={handleScenario} />
           )}
           {activeTab === 'alerts' && (
             <AlertMockup predictions={predictions} />
           )}
         </main>
       </div>
     );
   }
   ```

3. Create `frontend/src/index.css`:
   ```css
   @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
   * { box-sizing: border-box; margin: 0; padding: 0; }
   body { font-family: 'Inter', sans-serif; background: #0a0e1a; color: #ffffff; }
   .app-container { display: flex; flex-direction: column; height: 100vh; }
   .app-header { padding: 12px 24px; background: #111827; border-bottom: 1px solid #1f2937; display: flex; align-items: center; gap: 24px; }
   .app-header h1 { font-size: 1.4rem; font-weight: 700; }
   .app-header p  { font-size: 0.85rem; color: #6b7280; flex: 1; }
   nav button { padding: 8px 16px; margin: 0 4px; background: #1f2937; border: 1px solid #374151; border-radius: 8px; color: #9ca3af; cursor: pointer; font-size: 0.85rem; }
   nav button.active { background: #1d4ed8; border-color: #3b82f6; color: white; }
   .app-main { display: flex; flex: 1; overflow: hidden; }
   .map-wrapper { flex: 2; }
   .loading { text-align: center; padding: 40px; color: #6b7280; }
   ```

4. Create placeholder components (you'll fill them in Day 2):
   ```bash
   touch frontend/src/components/Map.jsx
   touch frontend/src/components/PredictionPanel.jsx
   touch frontend/src/components/WhatIfTool.jsx
   touch frontend/src/components/AlertMockup.jsx
   ```

5. Run: `npm run dev` → confirm the app loads (header will show, map area will be blank — that's fine)

**Share with team:**
- Screenshot of the running app
- Message: "✅ B1.3 done — React app running. Dark theme, header, tabs working."

---

### ✅ Task B1.4 — Deploy Backend to Railway
**Time: 45 minutes**

**Step-by-step:**

1. Go to [https://railway.app](https://railway.app) → Sign up with GitHub
2. New Project → Deploy from GitHub repo → select `aquasentry-2026`
3. In settings: Root Directory = `backend`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Deploy and wait for build to complete
6. Copy the public URL (e.g., `https://aquasentry-production.up.railway.app`)
7. Test: visit `[URL]/health` → should return `{"status":"ok"}`

**Share with team:**
- Message: "✅ B1.4 done — Backend live at: [URL]"

---

### 🗂️ Day 1 Deliverables Checklist
```
[ ] GitHub repo created, A and C added as collaborators
[ ] FastAPI backend running locally with mock data
[ ] React + Leaflet app running locally (dark theme, tabs)
[ ] Backend deployed to Railway with public URL
[ ] Screenshots shared with team
```

### 🔗 Day 1 Coordination
- **9 AM sync:** Share repo link immediately. Confirm A has the right folder structure.
- **9 PM sync:** Demo the running app to team via screen share or screenshots. Confirm with A the exact JSON schema for `predictions.json`.

---
---

# 📅 DAY 2 — Interactive Map & Component Build

---

### ✅ Task B2.1 — Build the Colour-Coded Kazakhstan Map
**Time: 3 hours**

Coordinate with A: get `kazakhstan_oblasts.geojson` and put it in `frontend/public/data/`

**Create `frontend/src/components/Map.jsx`:**
```jsx
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import { useEffect, useState } from 'react';
import 'leaflet/dist/leaflet.css';

const RISK_COLORS = {
  Normal:    '#2ecc71',
  Watch:     '#f39c12',
  Warning:   '#e67e22',
  Emergency: '#e74c3c',
  Unknown:   '#4b5563',
};

export default function Map({ predictions, onOblastClick }) {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    fetch('/data/kazakhstan_oblasts.geojson')
      .then(r => r.json())
      .then(setGeoData);
  }, []);

  const nameKey = (feature) =>
    feature.properties.NAME_1 || feature.properties.name || 'Unknown';

  const style = (feature) => {
    const name   = nameKey(feature);
    const stress = predictions[name]?.stress_30d || 'Unknown';
    return {
      fillColor:   RISK_COLORS[stress],
      weight:      1.5,
      opacity:     1,
      color:       '#1f2937',
      fillOpacity: 0.75,
    };
  };

  const onEachFeature = (feature, layer) => {
    const name   = nameKey(feature);
    const data   = predictions[name];
    const stress = data?.stress_30d || 'No data';
    const conf   = data ? `${(data.confidence * 100).toFixed(0)}%` : '—';

    layer.bindTooltip(
      `<div style="font-family:Inter,sans-serif;font-size:13px">
        <b>${name}</b><br/>
        30-day: <span style="color:${RISK_COLORS[stress]}">${stress}</span><br/>
        Confidence: ${conf}
      </div>`,
      { sticky: true, className: 'aqua-tooltip' }
    );

    layer.on({
      mouseover: (e) => { e.target.setStyle({ weight: 3, fillOpacity: 0.9 }); },
      mouseout:  (e) => { e.target.setStyle({ weight: 1.5, fillOpacity: 0.75 }); },
      click:     ()  => { onOblastClick(name); },
    });
  };

  return (
    <div style={{ position: 'relative', height: '100%' }}>
      <MapContainer
        center={[48.0, 67.0]}
        zoom={5}
        style={{ height: '100%', background: '#0a0e1a' }}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution="&copy; CartoDB"
        />
        {geoData && (
          <GeoJSON key={JSON.stringify(predictions)}
            data={geoData} style={style} onEachFeature={onEachFeature} />
        )}
      </MapContainer>

      {/* Legend */}
      <div style={{
        position:'absolute', bottom:24, left:24, zIndex:1000,
        background:'rgba(17,24,39,0.92)', padding:'12px 16px',
        borderRadius:10, border:'1px solid #374151'
      }}>
        <p style={{fontSize:'0.75rem',color:'#9ca3af',marginBottom:6}}>30-Day Risk</p>
        {Object.entries(RISK_COLORS).filter(([k])=>k!=='Unknown').map(([label,color])=>(
          <div key={label} style={{display:'flex',alignItems:'center',gap:8,marginBottom:4}}>
            <div style={{width:12,height:12,borderRadius:3,background:color}}/>
            <span style={{fontSize:'0.78rem',color:'#e5e7eb'}}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Run and test. Click different oblasts — they should highlight. Share screenshot.

---

### ✅ Task B2.2 — Build the Prediction Panel
**Time: 1.5 hours**

**Create `frontend/src/components/PredictionPanel.jsx`:**
```jsx
const COLORS = {
  Normal:'#2ecc71', Watch:'#f39c12', Warning:'#e67e22', Emergency:'#e74c3c'
};

export default function PredictionPanel({ oblast, data }) {
  if (!oblast) return (
    <div style={panelStyle}>
      <p style={{color:'#6b7280',marginTop:40,textAlign:'center'}}>
        👆 Click an oblast on the map
      </p>
    </div>
  );

  if (!data) return (
    <div style={panelStyle}>
      <h3 style={{color:'white'}}>{oblast}</h3>
      <p style={{color:'#6b7280'}}>No prediction data available</p>
    </div>
  );

  const horizons = [
    {label:'30 Days', value: data.stress_30d},
    {label:'60 Days', value: data.stress_60d},
    {label:'90 Days', value: data.stress_90d},
  ];

  return (
    <div style={panelStyle}>
      <h3 style={{color:'white',marginBottom:4}}>{oblast}</h3>
      <p style={{color:'#9ca3af',fontSize:'0.8rem',marginBottom:16}}>
        Rainfall anomaly: {data.rainfall_anomaly > 0 ? '+' : ''}{data.rainfall_anomaly}% vs historical
      </p>

      <p style={{color:'#6b7280',fontSize:'0.75rem',marginBottom:8}}>WATER STRESS FORECAST</p>
      {horizons.map(h => (
        <div key={h.label} style={{
          display:'flex', justifyContent:'space-between', alignItems:'center',
          padding:'10px 14px', marginBottom:8,
          background:'#1f2937', borderRadius:8,
          borderLeft:`4px solid ${COLORS[h.value]||'#4b5563'}`
        }}>
          <span style={{color:'#d1d5db',fontSize:'0.9rem'}}>{h.label}</span>
          <span style={{color:COLORS[h.value],fontWeight:600}}>{h.value}</span>
        </div>
      ))}

      <div style={{marginTop:16, padding:'10px 14px', background:'#111827', borderRadius:8}}>
        <p style={{color:'#6b7280',fontSize:'0.75rem'}}>MODEL CONFIDENCE</p>
        <p style={{color:'#10b981',fontSize:'1.2rem',fontWeight:700}}>
          {(data.confidence * 100).toFixed(0)}%
        </p>
      </div>
    </div>
  );
}

const panelStyle = {
  width: 280, padding: '20px', background: '#111827',
  borderLeft: '1px solid #1f2937', overflowY: 'auto'
};
```

---

### ✅ Task B2.3 — Build the What-If Tool
**Time: 2 hours**

**Create `frontend/src/components/WhatIfTool.jsx`:**
```jsx
import { useState } from 'react';

const COLORS = {Normal:'#2ecc71',Watch:'#f39c12',Warning:'#e67e22',Emergency:'#e74c3c'};
const DEVIATIONS = [-40, -20, 0, 20, 40];

export default function WhatIfTool({ predictions, onScenarioChange }) {
  const [idx, setIdx] = useState(2); // default = baseline (0%)
  const deviation = DEVIATIONS[idx];

  const handleChange = (e) => {
    const newIdx = parseInt(e.target.value);
    setIdx(newIdx);
    onScenarioChange(DEVIATIONS[newIdx]);
  };

  const emergencyCount = Object.values(predictions)
    .filter(d => d.stress_30d === 'Emergency').length;

  return (
    <div style={{flex:1,padding:'32px',maxWidth:700,margin:'0 auto'}}>
      <h2 style={{color:'white',marginBottom:8}}>📊 What-If Scenario Tool</h2>
      <p style={{color:'#6b7280',marginBottom:32}}>
        Adjust rainfall deviation to see how water stress changes across Kazakhstan
      </p>

      <div style={{background:'#111827',padding:24,borderRadius:12,marginBottom:24}}>
        <label style={{color:'#9ca3af',fontSize:'0.85rem'}}>RAINFALL DEVIATION</label>
        <div style={{display:'flex',alignItems:'center',gap:16,marginTop:12}}>
          <span style={{color:'#ef4444',fontSize:'0.8rem'}}>−40%</span>
          <input type="range" min={0} max={4} value={idx} onChange={handleChange}
            style={{flex:1,accentColor:'#3b82f6'}} />
          <span style={{color:'#10b981',fontSize:'0.8rem'}}>+40%</span>
        </div>
        <p style={{textAlign:'center',color:'white',fontSize:'1.5rem',fontWeight:700,marginTop:12}}>
          {deviation > 0 ? '+' : ''}{deviation}% rainfall vs. normal
        </p>
      </div>

      <div style={{background:'#1f2937',padding:16,borderRadius:10,marginBottom:24,
                   borderLeft:'4px solid #e74c3c'}}>
        <p style={{color:'#9ca3af',fontSize:'0.8rem'}}>OBLASTS IN EMERGENCY STATUS</p>
        <p style={{color:'#e74c3c',fontSize:'2rem',fontWeight:700}}>{emergencyCount}</p>
        <p style={{color:'#6b7280',fontSize:'0.8rem'}}>out of 17 total oblasts</p>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
        {Object.entries(predictions).map(([name, data]) => (
          <div key={name} style={{
            padding:'10px 14px',background:'#111827',borderRadius:8,
            borderLeft:`4px solid ${COLORS[data.stress_30d]||'#4b5563'}`
          }}>
            <p style={{color:'#e5e7eb',fontSize:'0.85rem',fontWeight:600}}>{name}</p>
            <p style={{color:COLORS[data.stress_30d],fontSize:'0.78rem'}}>{data.stress_30d}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### ✅ Task B2.4 — Build the Alert Mockup
**Time: 1.5 hours**

**Create `frontend/src/components/AlertMockup.jsx`:**
```jsx
export default function AlertMockup({ predictions }) {
  const highRisk = Object.entries(predictions)
    .filter(([, d]) => ['Warning','Emergency'].includes(d.stress_30d))
    .sort((a,b) => (b[1].stress_30d==='Emergency'?1:-1));

  return (
    <div style={{flex:1,padding:'32px',maxWidth:680,margin:'0 auto'}}>
      <h2 style={{color:'white',marginBottom:8}}>🔔 Active Water Stress Alerts</h2>
      <p style={{color:'#6b7280',marginBottom:24}}>
        SMS alerts automatically sent to district water offices & farmers
      </p>

      {highRisk.length === 0 && (
        <p style={{color:'#10b981'}}>✅ All oblasts currently at Normal or Watch level.</p>
      )}

      {highRisk.map(([name, data]) => (
        <div key={name} style={{
          background:'#111827',borderRadius:12,padding:20,marginBottom:16,
          borderLeft:`5px solid ${data.stress_30d==='Emergency'?'#e74c3c':'#e67e22'}`
        }}>
          <div style={{display:'flex',justifyContent:'space-between',marginBottom:8}}>
            <span style={{color:'white',fontWeight:600}}>📱 {name} Oblast</span>
            <span style={{
              padding:'3px 10px',borderRadius:20,fontSize:'0.75rem',fontWeight:600,
              background: data.stress_30d==='Emergency'?'#7f1d1d':'#78350f',
              color: data.stress_30d==='Emergency'?'#fca5a5':'#fcd34d'
            }}>
              {data.stress_30d}
            </span>
          </div>
          <div style={{background:'#1f2937',borderRadius:8,padding:'12px 14px'}}>
            <p style={{color:'#9ca3af',fontSize:'0.75rem',marginBottom:4}}>SMS MESSAGE</p>
            <p style={{color:'#e5e7eb',fontSize:'0.88rem',lineHeight:1.5}}>
              ⚠️ <b>Water Alert — {name}</b><br/>
              Water stress projected to reach <b>{data.stress_30d}</b> level within 30 days.<br/>
              {data.stress_30d === 'Emergency'
                ? 'Action required: Reduce irrigation by 40%. Contact district water authority immediately.'
                : 'Recommendation: Reduce irrigation by 20%. Monitor daily updates.'}
            </p>
          </div>
          <p style={{color:'#4b5563',fontSize:'0.72rem',marginTop:8}}>
            Confidence: {(data.confidence*100).toFixed(0)}% · Rainfall anomaly: {data.rainfall_anomaly}%
          </p>
        </div>
      ))}
    </div>
  );
}
```

---

### 🗂️ Day 2 Deliverables Checklist
```
[ ] Colour-coded Kazakhstan map working (click-to-select)
[ ] Prediction panel shows 30/60/90-day forecasts
[ ] What-If tool updates map on slider change
[ ] Alert mockup shows SMS messages for high-risk oblasts
[ ] Screenshot of full app shared with team
```

### 🔗 Day 2 Coordination
- **9 AM sync:** Ask A: "What are the exact property names in the GeoJSON (NAME_1 vs name)?" Mismatch = blank map.
- **Midday:** Share a screenshot of the interactive map for Member C to use in Slide 2.
- **9 PM sync:** Demo the 4 tabs to the team. A reviews that their oblast names match your map.

---
---

# 📅 DAY 3 — Real Data Integration & End-to-End Testing

---

### ✅ Task B3.1 — Integrate Member A's Real Predictions
**Time: 1.5 hours**

**Wait for A to send `predictions.json` — this is the critical midday handoff.**

**Step-by-step:**

1. Save Member A's `predictions.json` to `backend/predictions.json`

2. Restart the backend — it auto-loads from the file:
   ```bash
   uvicorn main:app --reload
   ```

3. Hit `http://localhost:8000/api/predictions` — verify you see real oblast data (not just 6 mocked ones)

4. Open the frontend — verify the map now shows 17 coloured oblasts, not just 6

5. Click through 5 different oblasts — confirm prediction panel shows different values

6. Commit the predictions.json:
   ```bash
   git add backend/predictions.json
   git commit -m "Add real ML predictions for all 17 oblasts"
   git push
   ```

**Share with team:**
- Screenshot of the map with all 17 real oblasts coloured
- Message: "✅ B3.1 done — Real predictions integrated. 17 oblasts on map. 🎉"

---

### ✅ Task B3.2 — Redeploy Backend + Deploy Frontend
**Time: 2 hours**

1. **Redeploy backend to Railway:**
   - Push code to GitHub → Railway auto-deploys
   - Verify live API URL returns 17 oblasts

2. **Deploy frontend to Vercel:**
   ```bash
   npm install -g vercel
   cd frontend
   vercel --prod
   ```
   - Set environment variable: `VITE_API_URL = [your Railway URL]`
   - Copy the Vercel URL (e.g., `https://aquasentry.vercel.app`)

3. Open the Vercel URL on your **phone** — verify it loads correctly

4. Run the full 5-step demo path on the live URL:
   - Step 1: Map loads, coloured oblasts visible ✓
   - Step 2: Click Turkistan → prediction panel shows Warning/Emergency ✓
   - Step 3: Switch to What-If tab → slide to -40% → more red oblasts appear ✓
   - Step 4: Switch to Alerts tab → Turkistan and Kyzylorda show SMS alerts ✓
   - Step 5: (In pitch) Show validation chart image separately ✓

**Share with team:**
- Live URLs for both frontend and backend
- Message: "✅ B3.2 done — Frontend: [VERCEL URL] | Backend: [RAILWAY URL]"

---

### ✅ Task B3.3 — Run Full Demo 3 Times & Fix Issues
**Time: 2 hours**

Do this on the live deployed URL, not localhost.

**Each run, check:**
- [ ] Map loads in under 3 seconds
- [ ] Clicking an oblast shows data immediately (no lag)
- [ ] What-If slider responds instantly
- [ ] Alert tab shows at least 3 oblasts with alerts
- [ ] No console errors (open DevTools → Console)
- [ ] No CORS errors in console

**Fix the top 3 bugs you find.** Do not add new features.

After all 3 runs, message team: "✅ B3.3 done — 3 demo runs complete. Fixed: [list bugs]."

---

### 🗂️ Day 3 Deliverables Checklist
```
[ ] predictions.json from Member A integrated
[ ] Map shows all 17 real oblasts with correct colours
[ ] Backend + Frontend both live on public URLs
[ ] End-to-end demo path runs 3 times without crashes
[ ] URLs shared with full team
```

### 🔗 Day 3 Coordination
- **9 AM:** Confirm you're ready to integrate predictions.json the moment A sends it.
- **Critical midday:** A sends predictions.json → you integrate within 1 hour → confirm to team.
- **9 PM:** Full team does a demo run together. Member C records the backup video during this session.

---
---

# 📅 DAY 4 — Polish, Prep & Demo Device Setup

---

### ✅ Task B4.1 — UI Polish Pass
**Time: 2 hours**

Go through the full app systematically. Fix only things that hurt the demo:

```
Visual polish:
[ ] All text is legible (minimum 13px, good contrast)
[ ] Loading state shows while predictions fetch (spinner or "Loading...")
[ ] Error state: if API fails, show "Offline mode — using cached data" gracefully
[ ] Map legend is clearly visible
[ ] Prediction panel shows "Click an oblast" when nothing is selected
[ ] What-If slider label shows current value clearly

Performance:
[ ] GeoJSON file is simplified (use mapshaper.org if map is slow)
[ ] Predictions are cached — no re-fetch on tab switch
[ ] Map doesn't re-render on every state change (use React.memo or useMemo)
```

---

### ✅ Task B4.2 — Prepare the Demo Device
**Time: 45 minutes**

Set up the exact laptop you'll present from:

1. Open browser → navigate to the live Vercel URL → bookmark it
2. Set browser to full-screen (F11 or Cmd+Shift+F on Mac)
3. Close all other browser tabs
4. Turn on Do Not Disturb / Focus mode
5. Set screen resolution: 1920×1080 (check Display Settings)
6. Disable screen sleep: set to "never" during hackathon
7. Open a second tab with the backup demo video (from Google Drive)
8. Have your phone hotspot ready as WiFi backup
9. Plug in charger

Test one final time: open the live URL, run the full demo path on this specific device.

---

### ✅ Task B4.3 — Attend Both Pitch Rehearsals
**Time: Member C leads these**

Your role in rehearsals:
- **Rehearsal 1 (morning):** Run the live demo when C cues you. Note anything that felt awkward in the demo flow.
- **Rehearsal 2 (evening):** Run demo again. Aim for a smooth, confident hand-off between C's pitch and your demo clicks.

Practice saying 1–2 sentences when demoing:
> *"Here's the live map — I'll click on Turkistan Oblast in the south. You can see it's forecast at Warning for the next 30 days, moving to Emergency at 60 and 90 days. Confidence is 87%."*

---

### 🗂️ Day 4 Deliverables Checklist
```
[ ] UI polish pass complete
[ ] Demo device fully prepped
[ ] Final live URL confirmed working on demo device
[ ] 2 full pitch rehearsals attended
[ ] Demo lines practiced aloud
```

---

## 📊 Your Full Output Summary (All 4 Days)

| Output | Location | Used By |
|--------|----------|---------|
| GitHub Repository | `github.com/...` | Everyone |
| FastAPI Backend | Railway URL | Frontend |
| React Dashboard | Vercel URL | Demo |
| Colour-coded Map | `Map.jsx` | Demo |
| Prediction Panel | `PredictionPanel.jsx` | Demo |
| What-If Tool | `WhatIfTool.jsx` | Demo |
| Alert Mockup | `AlertMockup.jsx` | Demo |

---

*AquaSentry | Member B Task Plan | SmartEarth 2026*
