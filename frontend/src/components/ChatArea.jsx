import React, { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff, Trash, AlertCircle } from 'lucide-react';
import MessageBubble from './MessageBubble';

export default function ChatArea({
  messages,
  onSendMessage,
  isLoading,
  onClearChat,
  voiceHook
}) {
  const [inputText, setInputText] = useState('');
  const baseInputTextRef = useRef('');
  const lastSpokenIdRef = useRef(null);
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
  } = voiceHook;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Append incoming speech transcript to previously existing text
  useEffect(() => {
    if (isListening && transcript) {
      const base = baseInputTextRef.current;
      const combined = base ? `${base} ${transcript.trimStart()}` : transcript;
      setInputText(combined);
    }
  }, [transcript, isListening]);

  // When speech session concludes, commit current text as new base
  useEffect(() => {
    if (!isListening && transcript) {
      baseInputTextRef.current = inputText.trim();
    }
  }, [isListening, transcript, inputText]);

  // Auto-speak the latest assistant message reliably across consecutive questions
  useEffect(() => {
    if (!isAutoSpeakEnabled || messages.length === 0) return;

    const lastMsg = messages[messages.length - 1];
    if (
      lastMsg.sender === 'bot' &&
      !lastMsg.isError &&
      lastMsg.text &&
      lastMsg.id !== lastSpokenIdRef.current
    ) {
      lastSpokenIdRef.current = lastMsg.id;
      speak(lastMsg.text, lastMsg.id);
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
    baseInputTextRef.current = '';
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
      baseInputTextRef.current = inputText.trim();
    } else {
      // Capture existing text so newly spoken words are appended
      baseInputTextRef.current = inputText.trim();
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
            <h2 className="welcome-title">How can I help you today?</h2>
            <p className="welcome-subtitle">
              Ask any question about IEEE membership, student branch activities, scholarships, technical societies, and global events.
            </p>

            <div className="suggested-prompts-group">
              <p className="suggested-title">Popular Questions:</p>
              <div className="prompts-grid">
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("When was IEEE established?")}
                >
                  "When was IEEE established?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What was the purpose of the merger that formed IEEE?")}
                >
                  "What was the purpose of the merger that formed IEEE?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What are the benefits of IEEE student membership?")}
                >
                  "What are the benefits of IEEE student membership?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("How can I join an IEEE Student Branch?")}
                >
                  "How can I join an IEEE Student Branch?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What opportunities does IEEE offer students?")}
                >
                  "What opportunities does IEEE offer students?"
                </button>
                <button
                  className="prompt-chip"
                  onClick={() => handlePromptClick("What is IEEE's mission?")}
                >
                  "What is IEEE's mission?"
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

            {/* Subtle Typing Indicator */}
            {isLoading && (
              <div className="message-row bot-row">
                <div className="avatar-container bot-avatar">
                  <span className="bot-avatar-text">IEEE</span>
                </div>
                <div className="typing-bubble">
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Voice Notice Toast */}
      {voiceError && (
        <div className="voice-error-toast">
          <AlertCircle size={15} />
          <span>{voiceError}</span>
          <button className="voice-error-close" onClick={() => setVoiceError(null)}>×</button>
        </div>
      )}

      {/* Input Form Bar */}
      <div className="chat-input-bar-container">
        {messages.length > 0 && (
          <div className="chat-actions-row">
            <button
              className="clear-chat-btn"
              onClick={onClearChat}
              title="Start a new conversation"
            >
              <Trash size={12} />
              <span>New Chat</span>
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="chat-form">
          <div className={`input-field-wrapper ${isListening ? 'listening-active' : ''}`}>
            {/* Microphone Button */}
            <button
              type="button"
              className={`voice-mic-btn ${isListening ? 'recording' : ''}`}
              onClick={toggleListening}
              title={
                !isSpeechRecognitionSupported
                  ? "Speech recognition is not available in this browser"
                  : isListening
                  ? "Listening... Click to pause"
                  : "Click to speak"
              }
              disabled={isLoading || !isSpeechRecognitionSupported}
              aria-label="Voice Input"
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
                  ? "Listening... Speak your question now..."
                  : "Ask a question about IEEE..."
              }
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />

            <button
              type="submit"
              className="send-button"
              disabled={!inputText.trim() || isLoading}
              aria-label="Send"
            >
              <Send size={16} />
            </button>
          </div>

          <div className="input-helper-text">
            <span>
              {isListening ? (
                <strong className="text-red">Listening to your voice... Speak now or click mic to finish.</strong>
              ) : (
                <>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for a new line</>
              )}
            </span>
          </div>
        </form>
      </div>
    </main>
  );
}
