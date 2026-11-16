import React, { useState } from 'react';
import { ExternalLink, ChevronDown, ChevronUp, BookOpen, Globe } from 'lucide-react';

export default function SourceCitation({ sources }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!sources || sources.length === 0) {
    return null;
  }

  // Deduplicate by source URL or document name
  const uniqueSources = [];
  const seen = new Set();
  for (const s of sources) {
    const key = s.source_url || s.document_name;
    if (!seen.has(key)) {
      seen.add(key);
      uniqueSources.push(s);
    }
  }

  return (
    <div className="subtle-source-container">
      <button
        className={`source-toggle-link ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="View official IEEE source references"
      >
        <BookOpen size={12} className="source-icon" />
        <span>Sources ({uniqueSources.length})</span>
        {isOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>

      {isOpen && (
        <div className="subtle-source-card">
          <ul className="subtle-source-list">
            {uniqueSources.map((item, idx) => (
              <li key={idx} className="subtle-source-item">
                <span className="source-bullet">•</span>
                {item.source_url ? (
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="source-title-link"
                    title={`Open in new tab: ${item.source_url}`}
                  >
                    {item.document_name}
                    <ExternalLink size={11} className="source-link-icon" />
                  </a>
                ) : (
                  <span className="source-title-text">{item.document_name}</span>
                )}

                {item.is_restricted ? (
                  <a
                    href={item.source_url || 'https://www.ieee.org'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="source-restricted-badge"
                    title="Official IEEE portal link"
                  >
                    <Globe size={10} /> Open on ieee.org
                  </a>
                ) : (
                  item.source_url && (
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="source-external-link"
                      title={item.source_url}
                    >
                      Visit Link <ExternalLink size={10} />
                    </a>
                  )
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
