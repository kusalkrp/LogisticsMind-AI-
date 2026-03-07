import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { sendMessage } from '../api';
import ChartRenderer from './ChartRenderer';

const TOOL_ICONS = {
  query_database: '🔍',
  generate_chart: '📊',
  detect_anomalies: '⚠️',
  forecast_metric: '📈',
  explain_query: '💡',
  get_schema_info: '📋',
};


// Strip any Mermaid/diagram blocks the agent might still emit (safety net)
function cleanContent(text) {
  if (!text) return '';
  return text
    .replace(/```mermaid[\s\S]*?```/g, '')
    .replace(/```diagram[\s\S]*?```/g, '')
    .trim();
}

const mdComponents = {
  p: ({ children }) => <p style={{ margin: '4px 0' }}>{children}</p>,
  strong: ({ children }) => <strong style={{ color: '#E8B84B' }}>{children}</strong>,
  em: ({ children }) => <em style={{ color: '#AAB8C2' }}>{children}</em>,
  ul: ({ children }) => <ul style={{ paddingLeft: '20px', margin: '6px 0' }}>{children}</ul>,
  ol: ({ children }) => <ol style={{ paddingLeft: '20px', margin: '6px 0' }}>{children}</ol>,
  li: ({ children }) => <li style={{ margin: '2px 0' }}>{children}</li>,
  code: ({ inline, children }) => inline
    ? <code style={{ background: '#0F1923', padding: '1px 5px', borderRadius: '3px', fontSize: '12px', color: '#E8B84B' }}>{children}</code>
    : <pre style={{ background: '#0F1923', padding: '10px', borderRadius: '6px', overflowX: 'auto', fontSize: '12px', color: '#E8EDF2', margin: '8px 0' }}><code>{children}</code></pre>,
  h1: ({ children }) => <h1 style={{ fontSize: '16px', color: '#E8B84B', margin: '8px 0 4px' }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ fontSize: '15px', color: '#E8B84B', margin: '8px 0 4px' }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ fontSize: '14px', color: '#AAB8C2', margin: '6px 0 3px' }}>{children}</h3>,
  table: ({ children }) => (
    <div style={{ overflowX: 'auto', margin: '10px 0' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '12px' }}>{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead style={{ background: '#1B4F8C' }}>{children}</thead>,
  th: ({ children }) => (
    <th style={{ padding: '6px 10px', textAlign: 'left', color: '#E8EDF2', fontWeight: 'bold', borderBottom: '2px solid #2A3A4F' }}>
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td style={{ padding: '5px 10px', borderBottom: '1px solid #2A3A4F', color: '#AAB8C2' }}>
      {children}
    </td>
  ),
  tr: ({ children }) => <tr style={{ ':hover': { background: '#1A2535' } }}>{children}</tr>,
};

export default function ChatPanel({ messages, setMessages }) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEnd = useRef(null);
  const userId = 'analyst_1';

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.role === 'user' && !lastMsg.sent) {
      processMessage(lastMsg.content);
    }
  }, [messages]);

  async function processMessage(text) {
    setLoading(true);
    setMessages(prev => prev.map((m, i) =>
      i === prev.length - 1 ? { ...m, sent: true } : m
    ));

    try {
      const response = await sendMessage(userId, text);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.message,
        tools: response.tools_used || [],
        proactive: response.proactive,
        chartJson: response.chart_json,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
        tools: [],
      }]);
    }
    setLoading(false);
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    setMessages(prev => [...prev, { role: 'user', content: input.trim() }]);
    setInput('');
  }

  return (
    <div className="chat-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      <div className="messages-area" style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '30px',
        display: 'flex', 
        flexDirection: 'column', 
        gap: '24px',
        paddingBottom: '120px'
      }}>
        {messages.map((msg, i) => (
          <div key={i} className="animate-fade-in" style={{ 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            <div className={`message-bubble ${msg.role}-bubble glass-card`} style={{
              padding: '16px 20px',
              maxWidth: msg.role === 'user' ? '70%' : '85%',
              lineHeight: '1.6',
              fontSize: '15px',
              color: 'var(--text-main)',
              background: msg.role === 'user' ? 'rgba(0, 163, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              borderLeft: msg.role === 'assistant' ? '3px solid var(--accent-gold)' : '1px solid var(--border-light)',
              borderRadius: msg.role === 'user' ? '20px 20px 4px 20px' : '4px 20px 20px 20px',
              boxShadow: msg.role === 'user' ? '0 4px 15px rgba(0, 163, 255, 0.1)' : 'none'
            }}>
              {msg.role === 'user'
                ? msg.content
                : <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{cleanContent(msg.content)}</ReactMarkdown>
              }
              
              {msg.tools && msg.tools.length > 0 && (
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
                  {msg.tools.map((t, j) => (
                    <span key={j} className="glass-card" style={{
                      fontSize: '11px', 
                      padding: '4px 10px',
                      color: 'var(--accent-gold)',
                      fontWeight: '600'
                    }}>
                      {TOOL_ICONS[t.name] || '🔧'} {t.name}
                    </span>
                  ))}
                </div>
              )}

              {msg.proactive && (
                <div className="glass-card insight-glow" style={{
                  marginTop: '16px', 
                  padding: '14px', 
                  background: 'rgba(232, 184, 75, 0.05)',
                  border: '1px solid rgba(232, 184, 75, 0.2)',
                }}>
                  <div style={{
                    fontSize: '10px', 
                    fontWeight: '800', 
                    textTransform: 'uppercase',
                    color: 'var(--accent-gold)', 
                    letterSpacing: '0.1em', 
                    marginBottom: '6px'
                  }}>
                    Intelligence Insight
                  </div>
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{cleanContent(msg.proactive)}</ReactMarkdown>
                </div>
              )}
            </div>
            {msg.chartJson && <ChartRenderer chartJson={msg.chartJson} />}
          </div>
        ))}
        {loading && (
          <div className="typing-indicator" style={{ color: 'var(--text-dim)', fontSize: '13px', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <div className="pulse" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-gold)' }}></div>
            Analysing logistics patterns...
          </div>
        )}
        <div ref={messagesEnd} />
      </div>

      <div className="input-wrapper" style={{
        position: 'absolute',
        bottom: '30px',
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'calc(100% - 60px)',
        maxWidth: '900px',
        zIndex: 100
      }}>
        <form onSubmit={handleSubmit} className="glass-panel" style={{
          display: 'flex',
          gap: '12px',
          padding: '8px',
          borderRadius: '16px',
          border: '1px solid var(--border-light)'
        }}>
          <input
            className="glass-input"
            style={{ 
              flex: 1, 
              border: 'none', 
              background: 'transparent',
              backdropFilter: 'none',
              padding: '12px 20px'
            }}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Search Intelligence or Ask anything..."
            disabled={loading}
          />
          <button className="glass-button" type="submit" disabled={loading} style={{ padding: '0 24px' }}>
            {loading ? '...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
}
