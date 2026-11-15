import React from 'react';
import { Database, Cpu, BookOpen, Layers, Menu, X, Volume2, VolumeX } from 'lucide-react';

export default function Header({
  healthData,
  totalDocs,
  totalChunks,
  isSidebarOpen,
  setIsSidebarOpen,
  voiceHook
}) {
  const { isAutoSpeakEnabled, setIsAutoSpeakEnabled, isSpeaking, stopSpeaking } = voiceHook;

  return (
    <header className="ieee-header">
      <div className="header-left">
        <button
          className="mobile-toggle-btn"
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          aria-label="Toggle Document Manager"
        >
          {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        <div className="ieee-logo-badge">
          <div className="ieee-diamond">
            <span>IEEE</span>
          </div>
          <div className="header-titles">
            <h1 className="header-title">IEEE AI Assistant</h1>
            <p className="header-subtitle">RAG Knowledge Engine • NVIDIA Nemotron</p>
          </div>
        </div>
      </div>

      <div className="header-badges">
        <div className="badge-item" title="ChromaDB Persistent Vector Database">
          <Database size={14} className="badge-icon text-blue" />
          <span>ChromaDB</span>
          <span className="badge-count">{totalChunks} chunks</span>
        </div>

        <div className="badge-item" title="Local Dense Embedding Model">
          <Layers size={14} className="badge-icon" />
          <span>all-MiniLM-L6-v2</span>
        </div>

        <div className="badge-item highlight" title="NVIDIA Hosted Inference API">
          <Cpu size={14} className="badge-icon" />
          <span>Nemotron 70B</span>
          <span className={`status-dot ${healthData?.api_key_configured ? 'active' : 'ready'}`}></span>
        </div>

        {/* Global Speaker Voice Toggle */}
        <button
          className={`voice-header-btn ${isAutoSpeakEnabled ? 'active' : ''}`}
          onClick={() => {
            const next = !isAutoSpeakEnabled;
            setIsAutoSpeakEnabled(next);
            if (!next && isSpeaking) {
              stopSpeaking();
            }
          }}
          title={isAutoSpeakEnabled ? "Mute automatic speech" : "Enable automatic speech for answers"}
        >
          {isAutoSpeakEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>

        <button
          className={`sidebar-pill-btn ${isSidebarOpen ? 'active' : ''}`}
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          title="Open knowledge base documents & optional PDF upload"
        >
          <BookOpen size={15} />
          <span>Knowledge Base ({totalDocs})</span>
        </button>
      </div>
    </header>
  );
}
