import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  MessageSquare, 
  Send, 
  Activity, 
  Layers, 
  AlertTriangle, 
  FileText, 
  ExternalLink,
  Clock, 
  Cpu, 
  RefreshCw,
  Plus,
  ChevronRight,
  TrendingUp,
  MapPin
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(`conv-${Date.now()}`);
  const [pastTraces, setPastTraces] = useState([]);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [activeTraceId, setActiveTraceId] = useState(null);
  const [activeSource, setActiveSource] = useState(null);
  const [apiOnline, setApiOnline] = useState(false);

  const messagesEndRef = useRef(null);

  // Check backend health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`);
        if (res.ok) setApiOnline(true);
      } catch (err) {
        setApiOnline(false);
      }
    };
    checkHealth();
    fetchTraces();
  }, []);

  // Fetch past traces for the left sidebar
  const fetchTraces = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/chat/traces`);
      if (res.ok) {
        const data = await res.json();
        setPastTraces(data.reverse()); // Show newest first
      }
    } catch (err) {
      console.error("Failed to fetch traces", err);
    }
  };

  // Scroll to bottom when messages list changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load a past trace as a chat message for analysis
  const handleLoadTrace = (trace) => {
    setSelectedTrace(trace);
    setConversationId(trace.conversation_id);
    
    // Construct fake messages array to simulate the visual response
    const mockUserMsg = {
      id: `user-${trace.trace_id}`,
      sender: 'user',
      text: trace.prompt
    };

    // Build steps from trace details
    const steps = [
      { step: 'started', message: 'Iniciando atendimento...' }
    ];
    if (trace.latencies.routing) {
      const intentName = trace.tool_calls.length > 0 
        ? trace.tool_calls[0].tool_name 
        : (trace.documents_retrieved.length > 0 ? 'rag' : 'direct');
      steps.push({ step: 'routing', message: `Intencao detectada: ${intentName}` });
    }
    if (trace.documents_retrieved.length > 0) {
      steps.push({ step: 'retrieval', message: 'Buscando informações nas bulas...' });
    }
    if (trace.tool_calls.length > 0) {
      steps.push({ step: 'tool_call', message: `Executando tool: ${trace.tool_calls[0].tool_name}` });
    }

    const mockAssistantMsg = {
      id: `assistant-${trace.trace_id}`,
      sender: 'assistant',
      text: trace.answer,
      trace_id: trace.trace_id,
      steps: steps,
      sources: trace.documents_retrieved,
      toolCalls: trace.tool_calls,
      doneData: {
        provider: trace.provider,
        model: trace.model,
        latency_ms: trace.latency_total_ms,
        input_tokens: trace.input_tokens,
        output_tokens: trace.output_tokens,
        total_tokens: trace.total_tokens
      }
    };

    setMessages([mockUserMsg, mockAssistantMsg]);
  };

  // Start new clean conversation
  const handleNewConversation = () => {
    setMessages([]);
    setInput('');
    setConversationId(`conv-${Date.now()}`);
    setSelectedTrace(null);
    setActiveTraceId(null);
  };

  // Handle message submission (POST to /chat/stream and consume stream)
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);

    const userMsgObj = { id: `user-${Date.now()}`, sender: 'user', text: userMessage };
    const assistantMsgObj = { 
      id: `assistant-${Date.now()}`, 
      sender: 'assistant', 
      text: '', 
      steps: [], 
      sources: [], 
      toolCalls: [] 
    };

    setMessages(prev => [...prev, userMsgObj, assistantMsgObj]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: userMessage
        })
      });

      if (!response.body) {
        throw new Error('ReadableStream not supported by response');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // save incomplete line

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.replace('event:', '').trim();
          } else if (trimmed.startsWith('data:')) {
            const dataStr = trimmed.replace('data:', '').trim();
            if (!dataStr) continue;

            try {
              const payload = JSON.parse(dataStr);
              handleSseEvent(currentEvent, payload);
            } catch (err) {
              console.error('Error parsing JSON from SSE', err, dataStr);
            }
            currentEvent = ''; // reset
          }
        }
      }
    } catch (err) {
      console.error('SSE connection failed', err);
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        last.error = 'Falha de comunicação com o backend.';
        return updated;
      });
    } finally {
      setIsLoading(false);
      fetchTraces(); // Refresh sidebar list
    }
  };

  // Dispatch events to state
  const handleSseEvent = (event, data) => {
    setMessages(prev => {
      const list = [...prev];
      const target = list[list.length - 1];
      if (!target || target.sender !== 'assistant') return prev;

      switch (event) {
        case 'trace':
          target.trace_id = data.trace_id;
          setActiveTraceId(data.trace_id);
          target.steps = [...(target.steps || []), data];
          break;
        case 'source':
          target.sources = [...(target.sources || []), data];
          break;
        case 'tool_call':
          target.toolCalls = [...(target.toolCalls || []), data];
          break;
        case 'token':
          target.text += data.token;
          break;
        case 'done':
          target.doneData = data;
          // Trigger automatic side drawer info
          fetchTraceDetails(data.trace_id);
          break;
        case 'error':
          target.error = data.message || 'Erro inesperado no pipeline.';
          break;
        default:
          break;
      }
      return list;
    });
  };

  const fetchTraceDetails = async (traceId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/chat/traces/${traceId}`);
      if (res.ok) {
        const trace = await res.json();
        setSelectedTrace(trace);
      }
    } catch (err) {
      console.error("Failed to fetch single trace details", err);
    }
  };

  return (
    <div className="app-container">
      
      {/* 1. LEFT SIDEBAR: History & Traces */}
      <div className="sidebar">
        <div className="sidebar-header">
          <img 
            src="/logo-panvel.png" 
            alt="Grupo Panvel" 
            style={{ 
              height: '28px', 
              objectFit: 'contain', 
              filter: 'brightness(0) invert(1) contrast(1.2)' 
            }} 
          />
          <div className="status-indicator">
            <div className={`status-dot ${apiOnline ? 'online' : 'offline'}`} />
            <span className="brand-text">ASSISTENTE VIRTUAL</span>
          </div>
        </div>

        <button onClick={handleNewConversation} className="new-conv-btn">
          <Plus size={15} />
          Nova Conversa
        </button>

        <div className="sidebar-content">
          <div className="sidebar-title">
            <TrendingUp size={11} />
            DIAGNÓSTICOS DE INTERAÇÕES
          </div>
          {pastTraces.length === 0 ? (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '24px', fontFamily: 'monospace' }}>
              Nenhum trace recente
            </div>
          ) : (
            pastTraces.map((trace) => (
              <div 
                key={trace.trace_id}
                onClick={() => handleLoadTrace(trace)}
                className={`trace-card ${selectedTrace?.trace_id === trace.trace_id ? 'active' : ''}`}
              >
                <div className="trace-card-title">{trace.prompt}</div>
                <div className="trace-card-meta">
                  <div className="meta-item">
                    <Clock size={9} />
                    {trace.latency_total_ms}ms
                  </div>
                  <div>{trace.model}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 2. CENTER PANEL: Chat Space */}
      <div className="chat-container">
        <div className="chat-header">
          <div>
            <h2 className="chat-header-title">Assistente de Saúde & Filiais</h2>
            <p className="chat-header-subtitle">Sessão: {conversationId}</p>
          </div>
        </div>

        {/* Message area */}
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="welcome-container">
              <div className="welcome-icon-box">
                <MessageSquare size={28} style={{ color: 'white' }} />
              </div>
              <h1 className="welcome-title">Como posso ajudar você hoje?</h1>
              <p className="welcome-desc">
                Faça perguntas farmacológicas sobre posologias de medicamentos (RAG) ou localize filiais Panvel que oferecem comodidades no Paraná (Tools).
              </p>
              
              <div className="welcome-suggestions">
                <div onClick={() => setInput("Para que serve a losartana?")} className="suggestion-card">
                  <div className="suggestion-tag rag">Dúvida Médica (RAG)</div>
                  <div className="suggestion-text">"Para que serve a losartana?"</div>
                </div>
                <div onClick={() => setInput("Quais filiais em Curitiba têm Panvel Clinic?")} className="suggestion-card">
                  <div className="suggestion-tag tool">Localização (Tools)</div>
                  <div className="suggestion-text">"Filiais em Curitiba com Panvel Clinic"</div>
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`message-row ${msg.sender === 'user' ? 'user' : 'assistant'}`}>
                <div className="message-meta">
                  {msg.sender === 'user' ? 'VOCÊ' : 'ASSISTENTE PANVEL'}
                </div>
                
                {msg.sender === 'user' ? (
                  <div className="message-bubble">
                    {msg.text}
                  </div>
                ) : (
                  <div className="message-bubble">
                    
                    {/* 1. SSE Stepper Tracker */}
                    {msg.steps && msg.steps.length > 0 && (
                      <div className="stepper-container">
                        {msg.steps.map((st, i) => (
                          <div 
                            key={i} 
                            onClick={() => msg.trace_id && fetchTraceDetails(msg.trace_id)}
                            className="step-pill"
                            title="Clique para inspecionar etapa de telemetria"
                          >
                            <span className="step-status-dot" />
                            <span className="step-text-highlight">[{st.step}]</span>
                            <span>{st.message}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* 2. Text response body */}
                    {msg.text ? (
                      <div className="markdown-body">
                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                      </div>
                    ) : (
                      !msg.error && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '12px', fontFamily: 'var(--font-mono)' }} className="blink-dots">
                          <Cpu size={14} className="spinner" style={{ color: 'var(--cyan-accent)' }} />
                          <span>Orquestrando dados do pipeline</span><span>.</span><span>.</span><span>.</span>
                        </div>
                      )
                    )}

                    {/* 3. Error alert if any */}
                    {msg.error && (
                      <div style={{ display: 'flex', gap: '8px', padding: '12px', border: '1px solid var(--error)', backgroundColor: 'var(--error-bg)', color: 'var(--error)', borderRadius: 'var(--radius-md)', fontSize: '11.5px', alignItems: 'center' }}>
                        <AlertTriangle size={15} style={{ flexShrink: 0 }} />
                        <span>{msg.error}</span>
                      </div>
                    )}

                    {/* 4. Sources list (RAG) */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="sources-container">
                        <div className="sources-title">FONTES UTILIZADAS (RAG)</div>
                        <div className="sources-list">
                          {msg.sources.map((src, i) => (
                            <div 
                              key={i}
                              onClick={() => setActiveSource(src)}
                              className="source-pill"
                            >
                              <FileText size={11} style={{ color: 'var(--cyan-accent)' }} />
                              <span>{src.arquivo}</span>
                              <span className="source-page-badge">pág. {src.pagina}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 5. Tool Call results */}
                    {msg.toolCalls && msg.toolCalls.map((tc, i) => (
                      <div key={i} className="tool-call-section">
                        <div className="tool-call-title">CHAMADA DE FERRAMENTA (TOOL)</div>
                        <div className="tool-call-card">
                          <div className="tool-call-header">
                            <span className="tool-call-name">{tc.tool_name}()</span>
                            <span className="tool-call-status">Orquestrado com Sucesso</span>
                          </div>
                          
                          <div className="tool-call-args">
                            <span>Argumentos:</span> {JSON.stringify(tc.arguments)}
                          </div>

                          {tc.result && (
                            <div style={{ marginTop: '8px' }}>
                              {/* Details tool result */}
                              {tc.tool_name === 'detalhes_filial' && tc.result.filial && (
                                <div className="filial-detail-box">
                                  <div className="filial-title">Filial {tc.result.filial.codigo_filial} - {tc.result.filial.localidade}</div>
                                  <div className="filial-desc">{tc.result.filial.endereco}, {tc.result.filial.bairro}</div>
                                  <div className="filial-features">
                                    <span className={`feature-badge ${tc.result.filial.atendimento_24_horas ? 'active' : 'inactive'}`}>24h</span>
                                    <span className={`feature-badge ${tc.result.filial.panvel_clinic ? 'active' : 'inactive'}`}>Clinic</span>
                                    <span className={`feature-badge ${tc.result.filial.delivery ? 'active' : 'inactive'}`}>Delivery</span>
                                  </div>
                                </div>
                              )}

                              {/* Search tool result */}
                              {tc.tool_name === 'buscar_filiais' && tc.result.filiais && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: '600' }}>Filiais encontradas ({tc.result.total_results}):</div>
                                  <div className="filiais-grid">
                                    {tc.result.filiais.map((f, idx) => (
                                      <div key={idx} className="filiais-grid-item">
                                        <div className="filial-title">Filial {f.codigo_filial} - {f.localidade}</div>
                                        <div className="filial-desc">{f.endereco}</div>
                                        <div className="filial-features">
                                          {f.atendimento_24_horas && <span className="feature-badge active">24h</span>}
                                          {f.panvel_clinic && <span className="feature-badge active">Clinic</span>}
                                          {f.delivery && <span className="feature-badge active">Delivery</span>}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {tc.result.error && (
                                <div style={{ color: 'var(--error)', backgroundColor: 'var(--error-bg)', border: '1px solid var(--error)', padding: '8px', borderRadius: '4px', fontSize: '11px' }}>
                                  {tc.result.error.message}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}

                    {/* 6. Execution metadata footer */}
                    {msg.doneData && (
                      <div style={{ display: 'flex', gap: '12px', borderTop: '1px solid var(--border-color)', fontSize: '10.5px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', paddingTop: '10px' }}>
                        <div>Latência: {msg.doneData.latency_ms}ms</div>
                        <div>Modelo: {msg.doneData.provider}/{msg.doneData.model}</div>
                        {msg.doneData.total_tokens && <div>Tokens: {msg.doneData.total_tokens}</div>}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Floating Input Bar */}
        <div className="input-container">
          <form onSubmit={handleSubmit} className="input-form">
            <input 
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Digite sua dúvida sobre posologia de remédios ou localize filiais da Panvel..."
              disabled={isLoading}
              className="chat-input"
            />
            <button 
              type="submit"
              disabled={!input.trim() || isLoading}
              className="send-btn"
            >
              {isLoading ? (
                <RefreshCw size={16} className="spinner" />
              ) : (
                <Send size={16} />
              )}
            </button>
          </form>
        </div>
      </div>

      {/* 3. RIGHT SIDEBAR: Active Trace & Details */}
      <div className="inspector-panel">
        <div className="inspector-header">
          <Activity size={16} style={{ color: 'var(--cyan-accent)', filter: 'drop-shadow(0 0 5px var(--cyan-accent))' }} />
          <span className="brand-text" style={{ color: 'white' }}>TELEMETRIA E LOGS</span>
        </div>

        <div className="inspector-content">
          {selectedTrace ? (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              <div>
                <div className="inspector-title">ID DO TRACE</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--cyan-accent)', wordBreak: 'break-all', marginTop: '4px' }}>
                  {selectedTrace.trace_id}
                </div>
              </div>

              <div>
                <div className="inspector-title">DISTRIBUIÇÃO DE LATÊNCIA</div>
                <div className="inspector-metric-box" style={{ marginTop: '8px' }}>
                  <div className="metric-row">
                    <span>Total Latency:</span>
                    <span style={{ fontWeight: '800', color: 'var(--cyan-accent)', fontFamily: 'var(--font-mono)' }}>{selectedTrace.latency_total_ms} ms</span>
                  </div>

                  <div className="metric-bar-group">
                    {Object.entries(selectedTrace.latencies).map(([stage, lat]) => {
                      const pct = Math.min(100, Math.max(5, (lat / selectedTrace.latency_total_ms) * 100));
                      return (
                        <div key={stage} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <div className="metric-bar-label">
                            <span style={{ textTransform: 'capitalize' }}>{stage}</span>
                            <span>{lat}ms</span>
                          </div>
                          <div className="metric-bar-track">
                            <div className="metric-bar-fill" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div>
                <div className="inspector-title">TOKENS DO TURNO</div>
                <div className="tokens-grid">
                  <div className="token-cell">
                    <div className="token-cell-title">PROMPT</div>
                    <div className="token-cell-value">{selectedTrace.input_tokens || '-'}</div>
                  </div>
                  <div className="token-cell">
                    <div className="token-cell-title">RESPOSTA</div>
                    <div className="token-cell-value">{selectedTrace.output_tokens || '-'}</div>
                  </div>
                  <div className="token-cell">
                    <div className="token-cell-title">TOTAL</div>
                    <div className="token-cell-value">{selectedTrace.total_tokens || '-'}</div>
                  </div>
                </div>
              </div>

              <div>
                <div className="inspector-title">STATUS GERAL</div>
                <div className="inspector-metric-box" style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Fallback Ativado:</span>
                    <span style={{ fontWeight: '800', color: selectedTrace.fallback ? 'var(--warning)' : 'var(--success)' }}>
                      {selectedTrace.fallback ? 'SIM' : 'NÃO'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Citações de Bula:</span>
                    <span style={{ fontWeight: '700' }}>{selectedTrace.sources_cited.length}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>Chamadas de Tool:</span>
                    <span style={{ fontWeight: '700' }}>{selectedTrace.tool_calls.length}</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={() => alert(JSON.stringify(selectedTrace, null, 2))}
                className="raw-json-btn"
              >
                <ExternalLink size={11} />
                Visualizar Payload JSON
              </button>

            </div>
          ) : (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '11px', fontFamily: 'var(--font-mono)', padding: '24px' }}>
              <Activity size={24} style={{ color: 'var(--border-color)', marginBottom: '12px' }} />
              Selecione uma interação para visualizar os dados de auditoria em tempo real.
            </div>
          )}
        </div>
      </div>

      {/* 4. MODAL: Source Document Preview */}
      {activeSource && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-header">
              <div>
                <h3 className="modal-title">Fonte RAG Recuperada</h3>
                <p className="modal-subtitle">{activeSource.arquivo} - Página {activeSource.pagina}</p>
              </div>
              <button onClick={() => setActiveSource(null)} className="modal-close-btn">
                Fechar
              </button>
            </div>
            
            <div className="modal-body">
              {activeSource.texto}
            </div>

            <div className="modal-footer">
              <span>Score de Similaridade: {activeSource.score}</span>
              <span>Seção: {activeSource.secao || 'N/A'}</span>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
