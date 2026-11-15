import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles, Trash, Mic, MicOff, Volume2, VolumeX, AlertCircle } from 'lucide-react';
import MessageBubble from './MessageBubble';

export default function ChatArea({
  messages,
  onSendMessage,
  isLoading,
  onClearChat,
  documentsCount,
  voiceHook
}) {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const {
    isSpeechRecognitionSupported,
    isListening,
    transcript,
    setTranscript,
    voiceError,
    setVoiceError,
    startListening,
    stopListening,
    isSpeaking,
    speakingMsgId,
    speak,
    stopSpeaking,
    isAutoSpeakEnabled,
    setIsAutoSpeakEnabled,
  } = voiceHook;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Update input text with speech transcript in real time
  useEffect(() => {
    if (transcript) {
      setInputText(transcript);
    }
  }, [transcript]);

  // Handle auto-speaking the latest AI message if enabled
  useEffect(() => {
    if (isAutoSpeakEnabled && messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.sender === 'bot' && !lastMsg.isError && lastMsg.text) {
        speak(lastMsg.text, lastMsg.id);
      }
    }
  }, [messages, isAutoSpeakEnabled, speak]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;

    if (isListening) {
      stopListening();
    }

    onSendMessage(trimmed);
    setInputText('');
    setTranscript('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handlePromptClick = (prompt) => {
    if (isLoading) return;
    onSendMessage(prompt);
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
      if (transcript.trim()) {
        handleSubmit();
      }
    } else {
      startListening();
    }
  };

  return (
    <main className="chat-main-container">
      {/* Messages Scroll Area */}
      <div className="chat-messages-area">
        {messages.length === 0 ? (
          <div className="chat-welcome-container">
            <div className="welcome-shield-icon">
              <span className="welcome-ieee-emblem">IEEE</span>
            </div>
            <h2 className="welcome-title">IEEE AI Assistant</h2>
            <p className="welcome-subtitle">
              Your intelligent guide to IEEE membership, student branches, competitions, technical societies, standards, and scholarships.
            </p>

            <div className="welcome-stats-bar">
              <div className="stat-badge">
                <span className="stat-dot"></span>
                <span>Preloaded Authentic Knowledge Base Active ({documentsCount} Domains)</span>
              </div>
              <div className="stat-badge">
                <span>NVIDIA Nemotron 70B Grounded</span>
              </div>
              <div className="stat-badge">
                <span>Voice Enabled</span>
              </div>
            </div>

            <div className="suggested-prompts-group">
              <p className="suggested-title">Ask any question or choose a topic below:</p>
              <div className="prompts-grid">
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What is the history of IEEE and what two organizations merged to form it?")}
                >
                  <span className="prompt-chip-category">Organization</span>
                  "What two organizations merged in 1963 to form IEEE?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What exclusive benefits do IEEE Student Members receive?")}
                >
                  <span className="prompt-chip-category">Membership</span>
                  "What exclusive benefits do IEEE Student Members receive?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What are the requirements to establish an IEEE Student Branch?")}
                >
                  <span className="prompt-chip-category">Student Branches</span>
                  "What are the requirements to form an IEEE Student Branch?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What is the IEEEXtreme programming competition and when is it held?")}
                >
                  <span className="prompt-chip-category">Competitions</span>
                  "What is IEEEXtreme and what are the rules and prizes?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("Which IEEE technical societies focus on computing, communications, and power?")}
                >
                  <span className="prompt-chip-category">Technical Societies</span>
                  "Which technical societies focus on computing and communications?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What scholarships and fellowships does IEEE offer for students?")}
                >
                  <span className="prompt-chip-category">Scholarships</span>
                  "What scholarships and graduate fellowships does IEEE offer?"
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="messages-stream">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onSpeak={speak}
                isSpeakingThis={speakingMsgId === msg.id}
                onFollowUpClick={handlePromptClick}
              />
            ))}

            {isLoading && (
              <div className="loading-message-row">
                <div className="avatar-container bot-avatar">
                  <Sparkles size={18} className="spin" />
                </div>
                <div className="loading-card">
                  <Loader2 size={18} className="spin text-blue" />
                  <div className="loading-text">
                    <span className="loading-main">Querying ChromaDB vector store...</span>
                    <span className="loading-sub">NVIDIA Nemotron synthesizing grounded answer</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Voice Error Notification Banner */}
      {voiceError && (
        <div className="voice-error-toast">
          <AlertCircle size={15} />
          <span>{voiceError}</span>
          <button className="voice-error-close" onClick={() => setVoiceError(null)}>×</button>
        </div>
      )}

      {/* Input Form Bar */}
      <div className="chat-input-bar-container">
        <div className="chat-actions-row">
          <div className="actions-left">
            <button
              type="button"
              className={`speaker-toggle-btn ${isAutoSpeakEnabled ? 'active' : ''}`}
              onClick={() => {
                const nextState = !isAutoSpeakEnabled;
                setIsAutoSpeakEnabled(nextState);
                if (!nextState && isSpeaking) {
                  stopSpeaking();
                }
              }}
              title={isAutoSpeakEnabled ? "Auto-speak answers: Enabled (Click to mute)" : "Auto-speak answers: Disabled (Click to enable)"}
            >
              {isAutoSpeakEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
              <span>{isAutoSpeakEnabled ? "Voice Output On" : "Voice Output Off"}</span>
            </button>
          </div>

          {messages.length > 0 && (
            <div className="actions-right">
              <button
                className="clear-chat-btn"
                onClick={onClearChat}
                title="Clear current session chat history"
              >
                <Trash size={13} />
                <span>Clear Session</span>
              </button>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="chat-form">
          <div className={`input-field-wrapper ${isListening ? 'listening-active' : ''}`}>
            {/* Microphone STT Button */}
            <button
              type="button"
              className={`voice-mic-btn ${isListening ? 'recording' : ''}`}
              onClick={toggleListening}
              title={
                !isSpeechRecognitionSupported
                  ? "Speech recognition not supported in this browser"
                  : isListening
                  ? "Listening... Click to stop"
                  : "Click to speak your question"
              }
              disabled={isLoading || !isSpeechRecognitionSupported}
            >
              {isListening ? (
                <div className="pulse-wrapper">
                  <MicOff size={18} className="mic-recording-icon" />
                  <span className="recording-ping"></span>
                </div>
              ) : (
                <Mic size={18} />
              )}
            </button>

            <textarea
              ref={inputRef}
              className="chat-textarea"
              rows={1}
              value={inputText}
              placeholder={
                isListening
                  ? "Listening... Speak your IEEE question now..."
                  : "Ask any question about IEEE membership, branches, societies, standards..."
              }
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />

            <button
              type="submit"
              className="send-button"
              disabled={!inputText.trim() || isLoading}
              aria-label="Send Message"
            >
              {isLoading ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
            </button>
          </div>

          <div className="input-helper-text">
            <span>
              {isListening ? (
                <strong className="text-red">Recording audio... Click mic to stop and submit.</strong>
              ) : (
                <>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for new line</>
              )}
            </span>
            <span className="rag-guardrail-tag">100% Grounded RAG Architecture</span>
          </div>
        </form>
      </div>
    </main>
  );
}
