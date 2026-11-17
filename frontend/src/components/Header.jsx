import React from 'react';
import { Volume2, VolumeX } from 'lucide-react';

export default function Header({ voiceHook }) {
  const { isAutoSpeakEnabled, setIsAutoSpeakEnabled, isSpeaking, stopSpeaking } = voiceHook;

  return (
    <header className="ieee-header">
      <div className="header-left">
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
          className={`voice-toggle-btn ${isAutoSpeakEnabled ? 'active' : ''} ${isSpeaking ? 'speaking' : ''}`}
          onClick={() => {
            const next = !isAutoSpeakEnabled;
            setIsAutoSpeakEnabled(next);
            if (!next && isSpeaking) {
              stopSpeaking();
            }
          }}
          title={isAutoSpeakEnabled ? "Mute automatic speech" : "Read answers aloud automatically"}
          aria-label="Toggle Voice Output"
        >
          {isAutoSpeakEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          <span className="voice-btn-label">
            {isAutoSpeakEnabled ? (isSpeaking ? "Speaking..." : "Speaker On") : "Speaker Off"}
          </span>
        </button>
      </div>
    </header>
  );
}
