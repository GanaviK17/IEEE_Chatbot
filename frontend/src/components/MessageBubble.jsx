import React, { useState } from 'react';
import { User, Copy, Check, Volume2, VolumeX } from 'lucide-react';
import SourceCitation from './SourceCitation';

export default function MessageBubble({
  message,
  onSpeak,
  isSpeakingThis,
  onFollowUpClick
}) {
  const [copied, setCopied] = useState(false);
  const isUser = message.sender === 'user';
  const isError = message.isError;

  const handleCopy = () => {
    if (!message.text) return;
    navigator.clipboard.writeText(message.text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  // Determine intelligent contextual follow-ups based on answer contents
  const getContextualFollowUps = (text) => {
    if (!text || isUser || isError) return [];
    const lower = text.toLowerCase();
    const suggestions = [];

    if (lower.includes('1963') || lower.includes('merger') || lower.includes('founded') || lower.includes('history')) {
      suggestions.push("What was the purpose of the merger that formed IEEE?");
      suggestions.push("What is IEEE's core mission?");
    } else if (lower.includes('student') || lower.includes('membership') || lower.includes('benefit')) {
      suggestions.push("How can I join an IEEE Student Branch?");
      suggestions.push("What opportunities does IEEE offer students?");
    } else if (lower.includes('branch') || lower.includes('counselor')) {
      suggestions.push("What are the benefits of IEEE student membership?");
      suggestions.push("What is IEEEXtreme and who can participate?");
    } else if (lower.includes('scholarship') || lower.includes('award') || lower.includes('fellowship')) {
      suggestions.push("What are the benefits of IEEE student membership?");
      suggestions.push("How can I join an IEEE Student Branch?");
    }

    return Array.from(new Set(suggestions)).slice(0, 2);
  };

  const followUps = !isUser ? getContextualFollowUps(message.text) : [];

  // Clean formatting for conversational answers
  const renderFormattedText = (text) => {
    if (!text) return null;

    const paragraphs = text.split('\n\n');
    return paragraphs.map((para, idx) => {
      if (!para.trim()) return null;

      // Handle bullet lists within a paragraph
      if (para.includes('\n• ') || para.includes('\n- ') || para.startsWith('• ') || para.startsWith('- ')) {
        const lines = para.split('\n');
        return (
          <div key={idx} className="msg-para-group">
            {lines.map((line, lIdx) => {
              if (line.trim().startsWith('• ') || line.trim().startsWith('- ')) {
                const item = line.trim().replace(/^[•\-]\s*/, '');
                return <li key={lIdx} className="msg-bullet">{formatInlineText(item)}</li>;
              }
              return <p key={lIdx} className="msg-p">{formatInlineText(line)}</p>;
            })}
          </div>
        );
      }

      return (
        <p key={idx} className="msg-p">
          {formatInlineText(para.trim())}
        </p>
      );
    });
  };

  const formatInlineText = (str) => {
    const parts = str.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return <code key={i} className="msg-code">{part.slice(1, -1)}</code>;
      }
      return part;
    });
  };

  return (
    <div className={`message-row ${isUser ? 'user-row' : 'bot-row'}`}>
      <div className={`avatar-container ${isUser ? 'user-avatar' : 'bot-avatar'}`}>
        {isUser ? <User size={16} /> : <span className="bot-avatar-text">IEEE</span>}
      </div>

      <div className="message-content-wrapper">
        <div className="message-meta">
          <span className="sender-name">
            {isUser ? 'You' : 'IEEE Assistant'}
          </span>
          <span className="message-timestamp">
            {message.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>

          {!isUser && !isError && (
            <div className="message-action-buttons">
              {onSpeak && (
                <button
                  className={`msg-action-btn ${isSpeakingThis ? 'speaking-active' : ''}`}
                  onClick={() => onSpeak(message.text, message.id)}
                  title={isSpeakingThis ? "Stop audio" : "Listen to answer"}
                  aria-label="Listen"
                >
                  {isSpeakingThis ? <VolumeX size={13} className="text-blue" /> : <Volume2 size={13} />}
                </button>
              )}

              <button
                className="msg-action-btn"
                onClick={handleCopy}
                title="Copy answer"
                aria-label="Copy"
              >
                {copied ? <Check size={13} className="text-green" /> : <Copy size={13} />}
                {copied && <span className="copied-text">Copied</span>}
              </button>
            </div>
          )}
        </div>

        <div className={`message-bubble ${isUser ? 'user-bubble' : 'bot-bubble'} ${isError ? 'error-bubble' : ''}`}>
          <div className="message-body">
            {renderFormattedText(message.text)}
          </div>

          {!isUser && message.sources && message.sources.length > 0 && (
            <SourceCitation sources={message.sources} />
          )}
        </div>

        {/* Suggested follow-up questions */}
        {!isUser && followUps.length > 0 && onFollowUpClick && (
          <div className="followup-suggestions-tray">
            {followUps.map((question, i) => (
              <button
                key={i}
                className="followup-chip-btn"
                onClick={() => onFollowUpClick(question)}
              >
                {question}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
