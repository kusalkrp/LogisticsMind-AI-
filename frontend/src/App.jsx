import React, { useState } from 'react';
import ChatPanel from './components/ChatPanel';
import SchemaExplorer from './components/SchemaExplorer';
import SuggestedQuestions from './components/SuggestedQuestions';


export default function App() {
  const [messages, setMessages] = useState([]);

  const handleSendMessage = (text) => {
    setMessages(prev => [...prev, { role: 'user', content: text }]);
  };

  return (
    <div className="app-container" style={{ display: 'flex', height: '100vh' }}>
      <aside className="glass-panel sidebar" style={{ 
        width: '320px', 
        padding: '24px', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '24px',
        zIndex: 10
      }}>
        <div className="logo" style={{ 
          fontSize: '22px', 
          fontWeight: '700', 
          color: 'var(--accent-gold)',
          letterSpacing: '-0.02em',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <span style={{ fontSize: '28px' }}>📦</span>
          LogisticsMind <span style={{ fontWeight: '300', color: 'white', opacity: 0.6 }}>AI</span>
        </div>
        
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <SchemaExplorer />
          {messages.length === 0 && (
            <SuggestedQuestions onSelect={handleSendMessage} />
          )}
        </div>

        <div className="sidebar-footer" style={{ 
          fontSize: '11px', 
          color: 'var(--text-dim)', 
          textAlign: 'center',
          opacity: 0.5
        }}>
          Automated Logistics Intelligence v1.0
        </div>
      </aside>
      
      <main style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column' }}>
        <ChatPanel messages={messages} setMessages={setMessages} />
      </main>
    </div>
  );
}
