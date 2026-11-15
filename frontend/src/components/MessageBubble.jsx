import React, { useState } from 'react';
import { User, Cpu, AlertCircle, Sparkles, Copy, Check, Volume2, VolumeX } from 'lucide-react';
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
    const lower = text.lower ? text.lower() : text.toLowerCase();
    const suggestions = [];

    if (lower.includes('student') || lower.includes('membership')) {
      suggestions.push("How do I establish an IEEE Student Branch?");
      suggestions.push("What discounts do students get on technical societies?");
    }
    if (lower.includes('branch') || lower.includes('counselor')) {
      suggestions.push("What are the responsibilities of an IEEE Branch Counselor?");
      suggestions.push("What is the annual reporting deadline for branch rebates?");
    }
    if (lower.includes('ieeextreme') || lower.includes('competition') || lower.includes('hackathon')) {
      suggestions.push("What are the team requirements and prizes for IEEEXtreme?");
      suggestions.push("What happens during IEEE Day on the first Tuesday of October?");
    }
    if (lower.includes('society') || lower.includes('computer society') || lower.includes('xplore')) {
      suggestions.push("Tell me about the IEEE Computer Society and Communications Society.");
      suggestions.push("What standards were created by IEEE Standards Association?");
    }
    if (lower.includes('scholarship') || lower.includes('award') || lower.includes('fellowship')) {
      suggestions.push("Who is eligible for the IEEE Charles LeGeyt Fortescue Scholarship?");
      suggestions.push("What is the Larry K. Wilson Regional Student Activities Award?");
    }

    // Limit to max 2 unique relevant suggestions
    return Array.from(new Set(suggestions)).slice(0, 2);
  };

  const followUps = !isUser ? getContextualFollowUps(message.text) : [];

  // Lightweight markdown-to-HTML formatter
  const renderFormattedText = (text) => {
    if (!text) return null;

    const lines = text.split('\n');
    return lines.map((line, idx) => {
      if (line.startsWith('### ')) {
        return <h4 key={idx} className="msg-h4">{line.replace('### ', '')}</h4>;
      }
      if (line.startsWith('## ')) {
        return <h3 key={idx} className="msg-h3">{line.replace('## ', '')}</h3>;
      }
      if (line.startsWith('# ')) {
        return <h2 key={idx} className="msg-h2">{line.replace('# ', '')}</h2>;
      }

      if (line.startsWith('> ')) {
        return (
          <blockquote key={idx} className="msg-quote">
            {formatInlineText(line.replace('> ', ''))}
          </blockquote>
        );
      }

      if (line.trim().startsWith('• ') || line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        const itemText = line.trim().replace(/^[•\-\*]\s*/, '');
        return (
          <li key={idx} className="msg-bullet">
            {formatInlineText(itemText)}
          </li>
        );
      }

      if (!line.trim()) {
        return <div key={idx} className="msg-spacer" />;
      }

      return (
        <p key={idx} className="msg-p">
          {formatInlineText(line)}
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
        {isUser ? <User size={18} /> : <Cpu size={18} />}
      </div>

      <div className="message-content-wrapper">
        <div className="message-meta">
          <span className="sender-name">
            {isUser ? 'You' : 'IEEE AI Assistant (Nemotron)'}
          </span>
          <span className="message-timestamp">
            {message.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {!isUser && !isError && message.modelUsed && (
            <span className="model-pill">
              <Sparkles size={11} /> {message.modelUsed.replace('nvidia/', '')}
            </span>
          )}

          {/* Action buttons: Speak & Copy */}
          {!isUser && !isError && (
            <div className="message-action-buttons">
              {onSpeak && (
                <button
                  className={`msg-action-btn ${isSpeakingThis ? 'speaking-active' : ''}`}
                  onClick={() => onSpeak(message.text, message.id)}
                  title={isSpeakingThis ? "Stop audio" : "Read answer aloud"}
                >
                  {isSpeakingThis ? <VolumeX size={13} className="text-blue" /> : <Volume2 size={13} />}
                </button>
              )}

              <button
                className="msg-action-btn"
                onClick={handleCopy}
                title="Copy answer to clipboard"
              >
                {copied ? <Check size={13} className="text-green" /> : <Copy size={13} />}
                {copied && <span className="copied-text">Copied</span>}
              </button>
            </div>
          )}
        </div>

        <div className={`message-bubble ${isUser ? 'user-bubble' : 'bot-bubble'} ${isError ? 'error-bubble' : ''}`}>
          {isError && (
            <div className="error-title">
              <AlertCircle size={16} /> Error Processing Request
            </div>
          )}

          <div className="message-body">
            {renderFormattedText(message.text)}
          </div>

          {!isUser && message.sources && message.sources.length > 0 && (
            <SourceCitation sources={message.sources} />
          )}

          {!isUser && message.confidenceNote && (
            <div className="grounding-note" title="RAG Verification Status">
              {message.confidenceNote}
            </div>
          )}
        </div>

        {/* Suggested follow-up questions */}
        {!isUser && followUps.length > 0 && onFollowUpClick && (
          <div className="followup-suggestions-tray">
            <span className="followup-label">Follow-up:</span>
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
