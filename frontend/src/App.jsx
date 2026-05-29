import { useEffect, useState } from 'react';
import Map from './components/Map';
import CyberPanel from './components/CyberPanel';
import axios from 'axios';
import './index.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [predictions, setPredictions] = useState({});
  const [selectedOblast, setSelectedOblast] = useState(null);
  const [simResult, setSimResult] = useState(null);
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [shap, setShap] = useState(null);
  const [modelComparison, setModelComparison] = useState(null);

  useEffect(() => {
    axios.get(`${API_URL}/api/predictions`)
      .then(res => { setPredictions(res.data); setLoading(false); })
      .catch(() => setLoading(false));
    axios.get(`${API_URL}/api/alerts`)
      .then(res => setAlerts(res.data))
      .catch(console.error);
    axios.get(`${API_URL}/api/explainability`)
      .then(res => setShap(res.data))
      .catch(console.error);
    axios.get(`${API_URL}/api/models/comparison`)
      .then(res => setModelComparison(res.data))
      .catch(console.error);
  }, []);

  // When an oblast is selected, fetch its history
  useEffect(() => {
    if (!selectedOblast) { setHistory(null); setSimResult(null); return; }
    setSimResult(null);
    axios.get(`${API_URL}/api/history/${encodeURIComponent(selectedOblast)}`)
      .then(res => setHistory(res.data))
      .catch(() => setHistory(null));
  }, [selectedOblast]);

  const handleSimulate = async (params) => {
    try {
      const res = await axios.post(`${API_URL}/api/simulate`, params);
      setSimResult(res.data);
    } catch (err) {
      console.error('Simulation failed:', err);
      setSimResult(null);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🌊 AquaSentry</h1>
        <p>Central Asia Water Stress & Drought Prediction System</p>
      </header>

      {alerts && alerts.length > 0 && (
        <div className="alert-banner">
          ⚠️ CRITICAL ALERTS: {alerts.map(a => `${a.oblast} (${a.severity})`).join(' | ')}
        </div>
      )}

      {loading && <div className="loading" style={{color:'#ffb000', textAlign:'center', padding:40}}>Loading Map Data...</div>}

      <main className="app-main">
        <div className="map-wrapper">
          <Map predictions={predictions} simResult={simResult} onOblastClick={setSelectedOblast} selectedOblast={selectedOblast} />
        </div>
        <CyberPanel 
          oblast={selectedOblast} 
          data={predictions[selectedOblast]} 
          history={history}
          simResult={simResult}
          shap={shap}
          modelComparison={modelComparison}
          onSimulate={handleSimulate} 
        />
      </main>
    </div>
  );
}
