import React from 'react';

const QUESTIONS = [
  'Which routes have the worst on-time delivery rate?',
  'Show warehouse utilisation across Sri Lanka on a map',
  'Are there anomalies in driver fuel consumption?',
  'Forecast shipment volume for next quarter',
  'Which companies have overdue invoices?',
  'What caused the most incidents last month?',
];


export default function SuggestedQuestions({ onSelect }) {
  return (
    <div className="animate-fade-in">
      <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '12px', letterSpacing: '0.05em' }}>
        Insights Explorer
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {QUESTIONS.map((q, i) => (
          <div
            key={i}
            className="glass-card"
            style={{
              padding: '12px 14px',
              cursor: 'pointer',
              fontSize: '13px',
              lineHeight: '1.4',
              color: 'var(--text-main)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}
            onClick={() => onSelect(q)}
          >
            <span style={{ color: 'var(--accent-gold)', fontSize: '16px' }}>✦</span>
            {q}
          </div>
        ))}
      </div>
    </div>
  );
}
