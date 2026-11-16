import React, { useState } from 'react';
import { ExternalLink, ChevronDown, ChevronUp, BookOpen } from 'lucide-react';

export default function SourceCitation({ sources }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!sources || sources.length === 0) {
    return null;
  }

  // Deduplicate by document name + page number
  const uniqueSources = [];
  const seen = new Set();
  for (const s of sources) {
    const key = `${s.document_name}_${s.page_number}`;
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
                <span className="source-title-text">{item.document_name}</span>
                {item.page_number && (
                  <span className="source-page-text">Page {item.page_number}</span>
                )}
                {item.source_url && (
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="source-external-link"
                    title={`Visit official IEEE source: ${item.source_url}`}
                  >
                    View Source <ExternalLink size={10} />
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
