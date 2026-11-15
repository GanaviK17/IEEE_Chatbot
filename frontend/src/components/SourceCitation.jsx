import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronUp, ExternalLink, BookmarkCheck } from 'lucide-react';

export default function SourceCitation({ sources }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!sources || sources.length === 0) {
    return null;
  }

  const toggleExpand = (idx) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  return (
    <div className="source-citation-container">
      <div className="source-citation-header">
        <BookmarkCheck size={14} className="source-header-icon" />
        <span>Verified Knowledge Base Citations ({sources.length}):</span>
      </div>

      <div className="source-chips-list">
        {sources.map((source, idx) => {
          const isExpanded = expandedIndex === idx;
          const similarityPercent = Math.round(source.similarity_score * 100);

          return (
            <div key={source.chunk_id || idx} className="source-card">
              <div className="source-chip-row">
                <button
                  className={`source-chip-btn ${isExpanded ? 'active' : ''}`}
                  onClick={() => toggleExpand(idx)}
                  title="Click to view verified source chunk excerpt"
                >
                  <div className="source-chip-left">
                    <FileText size={13} className="source-file-icon" />
                    <span className="source-doc-name">{source.document_name}</span>
                    <span className="source-page-badge">Page {source.page_number}</span>
                  </div>

                  <div className="source-chip-right">
                    <span className="similarity-badge" title="Semantic relevance score">
                      {similarityPercent}% match
                    </span>
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>
                </button>

                {source.source_url && (
                  <a
                    href={source.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="source-external-btn"
                    title={`Open official IEEE source: ${source.source_url}`}
                  >
                    <ExternalLink size={13} />
                  </a>
                )}
              </div>

              {isExpanded && (
                <div className="source-excerpt-drawer">
                  <div className="source-meta-row">
                    <span className="meta-chunk-id">Chunk ID: <code>{source.chunk_id}</code></span>
                    {source.source_url && (
                      <a
                        href={source.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="source-url-link"
                      >
                        {source.source_url.replace('https://', '').replace(/\/$/, '')} <ExternalLink size={11} />
                      </a>
                    )}
                  </div>
                  <div className="excerpt-content">
                    <p>"{source.excerpt}"</p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
