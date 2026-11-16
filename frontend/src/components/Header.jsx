import React from 'react';
import { BookOpen, Volume2, VolumeX, Menu, X } from 'lucide-react';

export default function Header({
  totalDocs,
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
          aria-label="Toggle Navigation"
        >
          {isSidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>

        <div className="ieee-logo-badge">
          <div className="ieee-diamond">
            <span>IEEE</span>
          </div>
          <div className="header-titles">
            <h1 className="header-title">IEEE Assistant</h1>
            <p className="header-subtitle">Your student & professional guide</p>
          </div>
        </div>
      </div>

      <div className="header-actions">
        {/* Voice Auto-Speak Toggle */}
        <button
          className={`voice-toggle-btn ${isAutoSpeakEnabled ? 'active' : ''}`}
          onClick={() => {
            const next = !isAutoSpeakEnabled;
            setIsAutoSpeakEnabled(next);
            if (!next && isSpeaking) {
              stopSpeaking();
            }
          }}
          title={isAutoSpeakEnabled ? "Mute automatic speech" : "Read answers aloud"}
          aria-label="Toggle Voice Output"
        >
          {isAutoSpeakEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          <span className="voice-btn-label">{isAutoSpeakEnabled ? "Voice On" : "Voice Off"}</span>
        </button>

        {/* Knowledge Base Drawer */}
        <button
          className={`sidebar-pill-btn ${isSidebarOpen ? 'active' : ''}`}
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          title="Browse verified IEEE knowledge documents"
        >
          <BookOpen size={15} />
          <span>Knowledge Base</span>
        </button>
      </div>
    </header>
  );
}
