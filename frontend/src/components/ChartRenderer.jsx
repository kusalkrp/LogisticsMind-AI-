import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';


export default function ChartRenderer({ chartJson }) {
  const chart = useMemo(() => {
    try {
      const parsed = typeof chartJson === 'string' ? JSON.parse(chartJson) : chartJson;
      return {
        data: (parsed.data || []).map(trace => ({
          ...trace,
          marker: { ...trace.marker, color: trace.marker?.color || 'var(--accent-blue)' },
          line: { ...trace.line, color: trace.line?.color || 'var(--accent-blue)' }
        })),
        layout: {
          ...parsed.layout,
          plot_bgcolor: 'transparent',
          paper_bgcolor: 'transparent',
          font: { color: 'var(--text-main)', family: 'Outfit' },
          autosize: true,
          margin: { l: 40, r: 20, t: 40, b: 40 },
          xaxis: { 
            ...parsed.layout?.xaxis, 
            gridcolor: 'rgba(255, 255, 255, 0.05)', 
            zerolinecolor: 'rgba(255, 255, 255, 0.1)' 
          },
          yaxis: { 
            ...parsed.layout?.yaxis, 
            gridcolor: 'rgba(255, 255, 255, 0.05)', 
            zerolinecolor: 'rgba(255, 255, 255, 0.1)' 
          },
        },
      };
    } catch {
      return null;
    }
  }, [chartJson]);

  if (!chart) return null;

  return (
    <div className="glass-card animate-fade-in" style={{
      margin: '16px 0',
      padding: '16px',
      width: '100%',
      background: 'rgba(255, 255, 255, 0.02)',
      border: '1px solid var(--border-light)'
    }}>
      <Plot
        data={chart.data}
        layout={chart.layout}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '350px' }}
      />
    </div>
  );
}
