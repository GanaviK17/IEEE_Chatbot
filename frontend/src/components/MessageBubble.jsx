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

    // Normalize any stray inline asterisks or bullets that might be placed inline
    const normalized = text
      .replace(/(?<!\n)\s+[\*•]\s+/g, '\n• ')
      .replace(/\r\n/g, '\n');

    const lines = normalized.split('\n');
    const elements = [];
    let currentList = [];

    const flushList = () => {
      if (currentList.length > 0) {
        elements.push(
          <ul key={`ul-${elements.length}`} className="msg-bullet-list">
            {currentList.map((item, idx) => (
              <li key={idx} className="msg-bullet">{formatInlineText(item)}</li>
            ))}
          </ul>
        );
        currentList = [];
      }
    };

    lines.forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        return;
      }

      // Check if it's a bullet item
      if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const itemContent = trimmed.replace(/^[•\-\*]\s*/, '');
        currentList.push(itemContent);
      } else {
        flushList();
        elements.push(
          <p key={`p-${elements.length}`} className="msg-p">
            {formatInlineText(trimmed)}
          </p>
        );
      }
    });

    flushList();
    return elements;
  };

  const formatInlineText = (str) => {
    if (!str) return '';
    // Regex splits on markdown links [text](url), bold **text**, inline code `code`, or bare URLs
    const regex = /(\[.*?\]\(https?:\/\/[^\s)]+\)|\*\*.*?\*\*|`.*?`|https?:\/\/[^\s)\]]+)/g;
    const parts = str.split(regex);

    return parts.map((part, i) => {
      if (!part) return null;

      // Markdown link: [Title](https://...)
      const mdLinkMatch = part.match(/^\[(.*?)\]\((https?:\/\/[^\s)]+)\)$/);
      if (mdLinkMatch) {
        const cleanTitle = mdLinkMatch[1].replace(/[\[\]]/g, '');
        return (
          <a
            key={i}
            href={mdLinkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="msg-link"
          >
            {cleanTitle}
          </a>
        );
      }

      // Bold: **text**
      if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }

      // Inline code: `code`
      if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
        return <code key={i} className="msg-code">{part.slice(1, -1)}</code>;
      }

      // Bare URL: https://...
      if (part.startsWith('http://') || part.startsWith('https://')) {
        return (
          <a
            key={i}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="msg-link"
          >
            {part}
          </a>
        );
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
