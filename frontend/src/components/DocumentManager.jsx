import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Trash2, CheckCircle2, AlertCircle, Loader2, RefreshCw, X, ExternalLink, ShieldCheck } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export default function DocumentManager({
  documents,
  onUploadSuccess,
  onDeleteSuccess,
  isLoadingDocs,
  fetchDocuments,
  onClose
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelected = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadError('Only PDF documents (.pdf) are supported.');
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setUploadError('File size exceeds the 20 MB limit.');
      return;
    }

    setUploadError(null);
    setUploadSuccessMsg(null);
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to process document');
      }

      setUploadSuccessMsg(`Successfully indexed "${file.name}" (${data.document.pages_count} pages, ${data.document.chunks_count} chunks in ChromaDB)`);
      if (onUploadSuccess) onUploadSuccess(data.document);
    } catch (err) {
      setUploadError(err.message || 'An error occurred during document ingestion');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Are you sure you want to remove "${filename}" and its vector embeddings from ChromaDB?`)) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/documents/${docId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete document');
      }

      if (onDeleteSuccess) onDeleteSuccess(docId);
    } catch (err) {
      alert(`Deletion error: ${err.message}`);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 KB';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  return (
    <aside className="document-manager-pane">
      <div className="pane-header">
        <div className="pane-title-group">
          <FileText size={18} className="pane-title-icon" />
          <h2 className="pane-title">Knowledge Base & Documents</h2>
        </div>
        <div className="pane-header-actions">
          <button
            className="refresh-btn"
            onClick={fetchDocuments}
            title="Refresh knowledge base"
          >
            <RefreshCw size={14} className={isLoadingDocs ? 'spin' : ''} />
          </button>
          {onClose && (
            <button
              className="pane-close-btn"
              onClick={onClose}
              title="Close drawer"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      <div className="preloaded-notice-card">
        <div className="notice-icon-title">
          <ShieldCheck size={16} className="text-blue" />
          <span>Preloaded Authentic IEEE Knowledge</span>
        </div>
        <p className="notice-desc">
          The chatbot is preloaded with verified official IEEE resources covering membership, student branches, events, technical societies, and standards.
        </p>
      </div>

      {/* Optional PDF Upload Dropzone */}
      <div className="optional-upload-header">
        <span className="optional-tag">Optional</span>
        <h3 className="optional-title">Upload Additional IEEE PDF</h3>
      </div>

      <div
        className={`upload-dropzone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          style={{ display: 'none' }}
          onChange={(e) => e.target.files && handleFileSelected(e.target.files[0])}
        />

        {isUploading ? (
          <div className="dropzone-loading">
            <Loader2 size={28} className="spin text-blue" />
            <p className="upload-main-text">Extracting text & generating embeddings...</p>
            <p className="upload-sub-text">Storing chunks in ChromaDB</p>
          </div>
        ) : (
          <div className="dropzone-idle">
            <UploadCloud size={28} className="upload-icon" />
            <p className="upload-main-text">Click or drop custom IEEE PDF</p>
            <p className="upload-sub-text">Branch bylaws, event CFPs, local guidelines (Max 20MB)</p>
          </div>
        )}
      </div>

      {uploadSuccessMsg && (
        <div className="status-box success-box">
          <CheckCircle2 size={16} />
          <span>{uploadSuccessMsg}</span>
        </div>
      )}

      {uploadError && (
        <div className="status-box error-box">
          <AlertCircle size={16} />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Document List */}
      <div className="documents-list-section">
        <div className="list-heading-row">
          <h3 className="list-title">Indexed Knowledge Sources ({documents.length})</h3>
        </div>

        {documents.length === 0 ? (
          <div className="empty-docs-placeholder">
            <FileText size={28} className="empty-icon" />
            <p className="empty-title">No documents in index</p>
          </div>
        ) : (
          <div className="documents-cards-container">
            {documents.map((doc) => (
              <div key={doc.id} className="doc-card">
                <div className="doc-card-main">
                  <div className="doc-icon-wrap">
                    <FileText size={18} className="doc-file-svg" />
                  </div>
                  <div className="doc-info-wrap">
                    <div className="doc-filename" title={doc.filename}>{doc.filename}</div>
                    <div className="doc-stats">
                      <span>{doc.pages_count} {doc.pages_count === 1 ? 'page' : 'pages'}</span>
                      <span className="dot">•</span>
                      <span>{doc.chunks_count} chunks</span>
                      <span className="dot">•</span>
                      <span>{formatFileSize(doc.file_size_bytes)}</span>
                    </div>
                    {doc.source_url && doc.source_url.startsWith('http') && (
                      <a
                        href={doc.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="doc-url-link"
                      >
                        Official URL <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                </div>

                <button
                  className="doc-delete-btn"
                  onClick={() => handleDelete(doc.id, doc.filename)}
                  title="Remove from ChromaDB"
                  aria-label={`Delete ${doc.filename}`}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
