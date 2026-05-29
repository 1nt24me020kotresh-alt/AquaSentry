import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import { useEffect, useState } from 'react';
import 'leaflet/dist/leaflet.css';

const RISK_COLORS = {
  Normal:    '#00f3ff',
  Watch:     '#f39c12',
  Warning:   '#ff003c',
  Emergency: '#ff003c',
  Unknown:   '#4b5563',
};

const KAZAKHSTAN_BOUNDS = [
  [40.0, 46.0],
  [56.0, 88.0]
];

export default function Map({ predictions, simResult, onOblastClick, selectedOblast }) {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    fetch('/data/kazakhstan_oblasts.geojson')
      .then(r => r.json())
      .then(setGeoData);
  }, []);

  const nameKey = (feature) =>
    feature.properties.NAME_1 || feature.properties.name || 'Unknown';

  const getStress = (name) => {
    // If this oblast has a simulation result and it's the selected one, show simulated stress
    if (simResult && name === selectedOblast) {
      return simResult.stress_30d || 'Unknown';
    }
    return predictions[name]?.stress_30d || 'Unknown';
  };

  const style = (feature) => {
    const name   = nameKey(feature);
    const stress = getStress(name);
    const isSelected = name === selectedOblast;
    
    return {
      fillColor: RISK_COLORS[stress] || RISK_COLORS.Unknown,
      weight: isSelected ? 3 : 1,
      opacity: 1,
      color: isSelected ? '#fff' : '#00f3ff',
      dashArray: isSelected ? '' : '3',
      fillOpacity: isSelected ? 0.4 : 0.15,
    };
  };

  const onEachFeature = (feature, layer) => {
    const name   = nameKey(feature);
    const data   = predictions[name];
    const stress = getStress(name);
    const conf   = data ? `${(data.confidence * 100).toFixed(0)}%` : '—';
    const rain   = data?.baseline_rain_mm != null ? `${data.baseline_rain_mm.toFixed(1)} mm` : '—';
    const temp   = data?.baseline_temp_c != null ? `${data.baseline_temp_c.toFixed(1)} °C` : '—';

    layer.bindTooltip(
      `<div>
        <b style="font-size:1.1em">${name}</b><br/>
        STATUS: <span style="color:${RISK_COLORS[stress]}">${stress}</span><br/>
        CONF: ${conf}<br/>
        PRECIP: ${rain} &nbsp; TEMP: ${temp}
      </div>`,
      { sticky: true, className: 'cyber-tooltip' }
    );

    layer.on({
      mouseover: (e) => { 
        if (name !== selectedOblast) {
          e.target.setStyle({ weight: 2, fillOpacity: 0.3, color: '#00f3ff' }); 
        }
      },
      mouseout:  (e) => { 
        if (name !== selectedOblast) {
          e.target.setStyle({ weight: 1, fillOpacity: 0.15, color: '#00f3ff' }); 
        }
      },
      click:     ()  => { onOblastClick(name); },
    });
  };

  return (
    <div style={{ position: 'relative', height: '100%' }}>
      <MapContainer
        bounds={KAZAKHSTAN_BOUNDS}
        maxBounds={KAZAKHSTAN_BOUNDS}
        maxBoundsViscosity={1.0}
        minZoom={4}
        style={{ height: '100%', background: '#020202' }}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution="&copy; CartoDB"
        />
        {geoData && (
          <GeoJSON key={`${JSON.stringify(predictions)}-${selectedOblast}-${JSON.stringify(simResult)}`}
            data={geoData} style={style} onEachFeature={onEachFeature} />
        )}
      </MapContainer>

      {/* Legend */}
      <div style={{
        position:'absolute', bottom:24, left:24, zIndex:1000,
        background:'rgba(5,5,10,0.9)', padding:'12px 16px',
        border:'1px solid #00f3ff',
        boxShadow: '0 0 10px rgba(0,243,255,0.3)'
      }}>
        <p style={{fontSize:'0.75rem',color:'#7df9ff',marginBottom:6, letterSpacing:'1px'}}>SYS.STATUS</p>
        {Object.entries(RISK_COLORS).filter(([k])=>k!=='Unknown').map(([label,color])=>(
          <div key={label} style={{display:'flex',alignItems:'center',gap:8,marginBottom:4}}>
            <div style={{width:12,height:12,background:color, boxShadow:`0 0 5px ${color}`}}/>
            <span style={{fontSize:'0.78rem',color:'#fff'}}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
