import { useState, useEffect, useCallback } from 'react';

const COLORS = {
  Normal: '#ffb000', Watch: '#f39c12', Warning: '#d32f2f', Emergency: '#c9302c'
};

export default function CyberPanel({ oblast, data, history, simResult, shap, modelComparison, onSimulate }) {
  // Slider state — absolute values in real units
  const [rainMm, setRainMm] = useState(0);
  const [tempC, setTempC] = useState(0);
  const [soilVwc, setSoilVwc] = useState(0);
  const [simulating, setSimulating] = useState(false);

  // Reset sliders when a new oblast is selected, using baselines from the API
  useEffect(() => {
    if (data) {
      setRainMm(data.baseline_rain_mm ?? 25);
      setTempC(data.baseline_temp_c ?? 5);
      setSoilVwc(data.baseline_soil_vwc ?? 0.35);
    }
  }, [oblast, data]);

  const runSimulation = useCallback(() => {
    if (!oblast) return;
    setSimulating(true);
    onSimulate({
      oblast,
      rainfall_mm: rainMm,
      temp_c: tempC,
      soil_moisture_vwc: soilVwc,
    });
    // Small timeout to show the loading state
    setTimeout(() => setSimulating(false), 400);
  }, [oblast, rainMm, tempC, soilVwc, onSimulate]);

  if (!oblast) return (
    <div className="hud-panel" style={{justifyContent:'center', alignItems:'center'}}>
      <p style={{color:'#888', textAlign:'center', opacity:0.8, letterSpacing:'1px'}}>
        [ AWAITING REGION SELECTION ]
      </p>
    </div>
  );

  if (!data) return (
    <div className="hud-panel">
      <h3 className="hud-title">{oblast}</h3>
      <p style={{color:'#d32f2f'}}>ERROR: DATA UNAVAILABLE</p>
    </div>
  );

  // Use simulated projections if available, else fall back to base predictions
  const s30 = simResult?.stress_30d ?? data.stress_30d;
  const s60 = simResult?.stress_60d ?? data.stress_60d;
  const s90 = simResult?.stress_90d ?? data.stress_90d;
  const c30 = simResult?.confidence_30d ?? data.confidence;
  const c60 = simResult?.confidence_60d ?? data.confidence;
  const c90 = simResult?.confidence_90d ?? data.confidence;

  const horizons = [
    {label:'30-DAY', stress: s30, conf: c30},
    {label:'60-DAY', stress: s60, conf: c60},
    {label:'90-DAY', stress: s90, conf: c90},
  ];

  // Probability breakdown from simulation (30-day)
  const probs = simResult?.probabilities_30d;

  return (
    <div className="hud-panel">
      <h3 className="hud-title">{oblast} // DATA LOADED</h3>

      {/* ── VARIABLE CONTROL ── */}
      <div className="hud-section">
        <p className="hud-label">CLIMATE VARIABLE OVERRIDE</p>

        {/* Rainfall slider */}
        <div style={{marginBottom:14}}>
          <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.9rem'}}>
            <span style={{color:'#888'}}>PRECIPITATION</span>
            <span style={{color:'#c4c4c4', fontWeight:'bold'}}>{rainMm.toFixed(1)} mm/month</span>
          </div>
          <input type="range" min={0} max={120} step={0.5} value={rainMm}
            onChange={e => setRainMm(parseFloat(e.target.value))} className="cyber-slider" />
          <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.75rem', color:'#555'}}>
            <span>0 mm (drought)</span>
            <span>120 mm (deluge)</span>
          </div>
        </div>

        {/* Temperature slider */}
        <div style={{marginBottom:14}}>
          <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.9rem'}}>
            <span style={{color:'#888'}}>TEMPERATURE</span>
            <span style={{color:'#c4c4c4', fontWeight:'bold'}}>{tempC.toFixed(1)} °C</span>
          </div>
          <input type="range" min={-30} max={45} step={0.5} value={tempC}
            onChange={e => setTempC(parseFloat(e.target.value))} className="cyber-slider" />
          <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.75rem', color:'#555'}}>
            <span>−30 °C</span>
            <span>+45 °C</span>
          </div>
        </div>

        {/* Soil moisture slider */}
        <div style={{marginBottom:14}}>
          <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.9rem'}}>
            <span style={{color:'#888'}}>SOIL MOISTURE</span>
            <span style={{color:'#c4c4c4', fontWeight:'bold'}}>{soilVwc.toFixed(3)} m³/m³</span>
          </div>
          <input type="range" min={0} max={0.6} step={0.005} value={soilVwc}
            onChange={e => setSoilVwc(parseFloat(e.target.value))} className="cyber-slider" />
          <div style={{display:'flex', justifyContent:'space-between', fontSize:'0.75rem', color:'#555'}}>
            <span>0 VWC (arid)</span>
            <span>0.6 VWC (saturated)</span>
          </div>
        </div>

        <button onClick={runSimulation} className="sim-button" disabled={simulating}>
          {simulating ? '▶ COMPUTING...' : '▶ RUN SVM INFERENCE'}
        </button>
      </div>

      {/* ── FORWARD PROJECTIONS ── */}
      <div className="hud-section">
        <p className="hud-label">FORWARD PROJECTIONS (T+30, 60, 90 DAYS) {simResult ? '(SIMULATED)' : '(BASELINE)'}</p>
        {horizons.map(h => (
          <div key={h.label} style={{
            display:'flex', justifyContent:'space-between', alignItems:'center',
            padding:'8px 10px', marginBottom:8,
            background:'#fff', border:'1px solid #333', borderRadius:4,
            borderLeft:`4px solid ${COLORS[h.stress]||'#555'}`
          }}>
            <span style={{color:'#888',fontSize:'0.9rem'}}>{h.label}</span>
            <div style={{textAlign:'right'}}>
              <span style={{color:COLORS[h.stress],fontWeight:700}}>{h.stress}</span>
              <span style={{color:'#555',fontSize:'0.8rem',marginLeft:8}}>{(h.conf * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}

        {/* Probability breakdown */}
        {probs && (
          <div style={{marginTop:10, borderTop:'1px solid #333', paddingTop:10}}>
            <p style={{fontSize:'0.8rem', color:'#888', marginBottom:6}}>30-DAY CLASS PROBABILITIES</p>
            {Object.entries(probs).map(([cls, prob]) => (
              <div key={cls} style={{display:'flex', alignItems:'center', gap:8, marginBottom:4}}>
                <div style={{width:8,height:8,background:COLORS[cls]||'#555', borderRadius:'50%'}}/>
                <span style={{flex:1, fontSize:'0.85rem', color:'#c4c4c4'}}>{cls}</span>
                <div style={{width:100,height:6,background:'#222',position:'relative', borderRadius:3, overflow:'hidden'}}>
                  <div style={{
                    width:`${(prob*100).toFixed(0)}%`, height:'100%',
                    background:COLORS[cls]||'#555',
                    transition:'width 0.5s ease'
                  }}/>
                </div>
                <span style={{fontSize:'0.8rem', color:'#c4c4c4', minWidth:35, textAlign:'right'}}>{(prob*100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── EXPLAINABILITY (SHAP) ── */}
      {shap && shap[s30] && (
        <div className="hud-section">
          <p className="hud-label">SHAP DRIVERS ({s30})</p>
          {Object.entries(shap[s30])
            .sort((a,b) => b[1] - a[1])
            .slice(0, 5)
            .map(([feat, val]) => (
              <div key={feat} style={{display:'flex', justifyContent:'space-between', fontSize:'0.85rem', marginBottom:4}}>
                <span style={{color:'#888'}}>{feat}</span>
                <span style={{color:'#ffb000', fontWeight:'bold'}}>{val.toFixed(3)}</span>
              </div>
          ))}
        </div>
      )}

      {/* ── MODEL COMPARISON ── */}
      {modelComparison && Object.keys(modelComparison).length > 0 && (
        <div className="hud-section">
          <p className="hud-label">AUTO-ML EVALUATION</p>
          <div style={{fontSize:'0.8rem', color:'#888', marginBottom:8}}>
            Support Vector Machine (SVM) out-performed neural and ensemble architectures during rigorous Cross-Validation.
          </div>
          {Object.entries(modelComparison)
            .sort((a,b) => b[1].f1_score - a[1].f1_score)
            .slice(0, 4)
            .map(([mName, metrics]) => (
              <div key={mName} style={{display:'flex', justifyContent:'space-between', alignItems:'center', padding:'4px 0', borderBottom:'1px solid #222'}}>
                <span style={{color: mName==='SVM' ? '#ffb000' : '#888', fontWeight: mName==='SVM' ? 'bold' : 'normal'}}>{mName}</span>
                <span style={{color:'#c4c4c4', fontSize:'0.8rem'}}>F1: {(metrics.f1_score*100).toFixed(1)}%</span>
              </div>
          ))}
        </div>
      )}

      {/* ── HISTORICAL DATA (3 years) ── */}
      {history && (
        <div className="hud-section">
          <p className="hud-label">HISTORICAL RECORD (3-YEAR)</p>
          <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.9rem'}}>
            <thead>
              <tr style={{borderBottom:'2px solid #333'}}>
                <th style={{textAlign:'left',padding:'6px',color:'#888'}}>YEAR</th>
                <th style={{textAlign:'right',padding:'6px',color:'#888'}}>PRECIP</th>
                <th style={{textAlign:'right',padding:'6px',color:'#888'}}>TEMP</th>
                <th style={{textAlign:'right',padding:'6px',color:'#888'}}>SOIL</th>
              </tr>
            </thead>
            <tbody>
              {history.map(row => (
                <tr key={row.year} style={{borderBottom:'1px solid #222'}}>
                  <td style={{padding:'6px',color:'#c4c4c4'}}>{row.year}</td>
                  <td style={{padding:'6px',color:'#c4c4c4',textAlign:'right'}}>{row.avg_rain_mm?.toFixed(1) ?? '—'} mm</td>
                  <td style={{padding:'6px',color:'#c4c4c4',textAlign:'right'}}>{row.avg_temp_c?.toFixed(1) ?? '—'} °C</td>
                  <td style={{padding:'6px',color:'#c4c4c4',textAlign:'right'}}>{row.avg_soil_vwc != null ? row.avg_soil_vwc.toFixed(3) : '—'} m³/m³</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Visual bar chart for rainfall trend */}
          <div style={{marginTop:15}}>
            <p style={{fontSize:'0.8rem', color:'#888', marginBottom:6}}>ANNUAL PRECIP TREND (mm/mo)</p>
            <div className="bar-chart">
              {history.map(row => {
                const maxRain = Math.max(...history.map(r => r.avg_rain_mm || 1));
                const pct = ((row.avg_rain_mm || 0) / maxRain) * 100;
                return (
                  <div key={row.year} className="bar" style={{height: `${pct}%`}}>
                    <span className="bar-val">{row.avg_rain_mm?.toFixed(0)}</span>
                    <span className="bar-label">{row.year}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
