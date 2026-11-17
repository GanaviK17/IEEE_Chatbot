import React, { useState, useEffect, useRef } from 'react';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
import { 
  ShieldCheck, 
  Lock, 
  User, 
  LogOut, 
  ArrowLeft, 
  UploadCloud, 
  FileText, 
  Trash2, 
  RefreshCw, 
  Database, 
  Cpu, 
  AlertCircle, 
  CheckCircle, 
  ExternalLink,
  Layers,
  FileCheck
} from 'lucide-react';

export default function AdminPortal({ onBack }) {
  const [token, setToken] = useState(() => localStorage.getItem('ieee_admin_token') || '');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [adminUsername, setAdminUsername] = useState('admin');
  
  // Login form state
  const [loginUsername, setLoginUsername] = useState('admin');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Dashboard state
  const [healthStats, setHealthStats] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', text: '' }

  // Upload state
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Delete modal confirmation state
  const [documentToDelete, setDocumentToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Verify token on mount
  useEffect(() => {
    if (token) {
      verifyToken(token);
    }
  }, [token]);

  const verifyToken = async (authToken) => {
    try {
      const resp = await fetch(`${API_BASE_URL}/admin/verify`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (resp.ok) {
        const data = await resp.json();
        setIsAuthenticated(true);
        setAdminUsername(data.username || 'admin');
        fetchHealthAndDocs(authToken);
      } else {
        handleLogout();
      }
    } catch {
      handleLogout();
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);

    try {
      const resp = await fetch(`${API_BASE_URL}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loginUsername.trim(),
          password: loginPassword
        })
      });

      const data = await resp.json();
      if (resp.ok && data.access_token) {
        localStorage.setItem('ieee_admin_token', data.access_token);
        setToken(data.access_token);
        setIsAuthenticated(true);
        setAdminUsername(data.username || loginUsername);
        setLoginPassword('');
        fetchHealthAndDocs(data.access_token);
      } else {
        setLoginError(data.detail || 'Invalid username or password.');
      }
    } catch (err) {
      setLoginError('Could not connect to authentication server. Please check backend status.');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('ieee_admin_token');
    setToken('');
    setIsAuthenticated(false);
    setDocuments([]);
    setHealthStats(null);
  };

  const fetchHealthAndDocs = async (authToken) => {
    setIsLoadingDocs(true);
    try {
      // 1. Fetch public health stats
      const hResp = await fetch(`${API_BASE_URL}/health`);
      if (hResp.ok) {
        const hData = await hResp.json();
        setHealthStats(hData);
      }

      // 2. Fetch admin-protected documents
      const dResp = await fetch(`${API_BASE_URL}/documents`, {
        headers: { 'Authorization': `Bearer ${authToken || token}` }
      });

      if (dResp.ok) {
        const dData = await dResp.json();
        setDocuments(dData.documents || []);
      } else if (dResp.status === 401 || dResp.status === 403) {
        handleLogout();
      }
    } catch (err) {
      console.error('Failed to fetch admin data:', err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  // Re-index authentic knowledge base
  const handleReindex = async () => {
    if (isReindexing) return;
    setIsReindexing(true);
    setFeedback(null);

    try {
      const resp = await fetch(`${API_BASE_URL}/admin/reindex`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await resp.json();
      if (resp.ok) {
        setFeedback({
          type: 'success',
          text: `Knowledge base re-indexed successfully: ${data.details?.total_documents || 7} documents and ${data.details?.total_chunks || 28} semantic chunks verified.`
        });
        fetchHealthAndDocs(token);
      } else {
        setFeedback({ type: 'error', text: data.detail || 'Re-indexing failed.' });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: 'Error connecting to re-indexing service.' });
    } finally {
      setIsReindexing(false);
    }
  };

  // Handle PDF file upload
  const handleFileUpload = async (file) => {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setFeedback({ type: 'error', text: 'Invalid file format. Only PDF files (.pdf) are supported.' });
      return;
    }

    if (file.size > 20 * 1024 * 1024) {
      setFeedback({ type: 'error', text: 'File exceeds 20MB maximum allowed upload limit.' });
      return;
    }

    setIsUploading(true);
    setFeedback(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const resp = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      const data = await resp.json();
      if (resp.ok) {
        setFeedback({
          type: 'success',
          text: data.message || `Document "${file.name}" indexed successfully.`
        });
        fetchHealthAndDocs(token);
      } else {
        setFeedback({ type: 'error', text: data.detail || 'Upload and indexing failed.' });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: 'Network error while uploading document.' });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Confirm delete document
  const confirmDelete = async () => {
    if (!documentToDelete || isDeleting) return;
    setIsDeleting(true);

    try {
      const resp = await fetch(`${API_BASE_URL}/documents/${documentToDelete.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      const data = await resp.json();
      if (resp.ok) {
        setFeedback({
          type: 'success',
          text: `Document "${documentToDelete.filename}" and its vector embeddings were removed.`
        });
        setDocumentToDelete(null);
        fetchHealthAndDocs(token);
      } else {
        setFeedback({ type: 'error', text: data.detail || 'Failed to delete document.' });
      }
    } catch (err) {
      setFeedback({ type: 'error', text: 'Error connecting to server to delete document.' });
    } finally {
      setIsDeleting(false);
    }
  };

  // ============================================================================
  // Unauthenticated: Login Screen
  // ============================================================================
  if (!isAuthenticated) {
    return (
      <div className="admin-login-wrapper">
        <div className="admin-login-card">
          <div className="admin-login-header">
            <div className="admin-lock-icon">
              <Lock size={28} />
            </div>
            <h2 className="admin-login-title">IEEE Assistant Administration</h2>
            <p className="admin-login-subtitle">
              Authorized access to IEEE Knowledge Base management, vector indexes, and system diagnostics.
            </p>
          </div>

          {loginError && (
            <div className="admin-alert-banner error">
              <AlertCircle size={18} />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="admin-login-form">
            <div className="admin-input-group">
              <label htmlFor="admin-user">Administrator Username</label>
              <div className="input-with-icon">
                <User size={18} className="field-icon" />
                <input
                  id="admin-user"
                  type="text"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  placeholder="admin"
                  required
                />
              </div>
            </div>

            <div className="admin-input-group">
              <label htmlFor="admin-pwd">Administrator Password</label>
              <div className="input-with-icon">
                <Lock size={18} className="field-icon" />
                <input
                  id="admin-pwd"
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="Enter administrator password"
                  required
                />
              </div>
            </div>

            <button 
              type="submit" 
              className="admin-primary-btn"
              disabled={loginLoading}
            >
              {loginLoading ? (
                <>
                  <RefreshCw size={16} className="spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <ShieldCheck size={18} />
                  <span>Sign In to Admin Portal</span>
                </>
              )}
            </button>
          </form>

          <div className="admin-login-footer">
            <button 
              type="button" 
              className="admin-secondary-btn"
              onClick={onBack}
            >
              <ArrowLeft size={16} />
              <span>Back to Public Assistant</span>
            </button>
            <p className="admin-hint-text">
              Default credentials: <code>admin</code> / <code>admin123</code> (configured in <code>backend/.env</code>)
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // Authenticated: Admin Dashboard
  // ============================================================================
  return (
    <div className="admin-dashboard-container">
      {/* Admin Top Navbar */}
      <header className="admin-navbar">
        <div className="admin-nav-left">
          <div className="ieee-diamond small">
            <span>IEEE</span>
          </div>
          <div className="admin-nav-titles">
            <h1 className="admin-nav-heading">IEEE Knowledge Administration</h1>
            <span className="admin-role-badge">Protected Area</span>
          </div>
        </div>

        <div className="admin-nav-right">
          <div className="admin-user-info">
            <User size={15} />
            <span>{adminUsername}</span>
          </div>
          <button 
            className="admin-nav-btn"
            onClick={onBack}
            title="Return to Public Assistant"
          >
            <ArrowLeft size={16} />
            <span>Back to Chat</span>
          </button>
          <button 
            className="admin-logout-btn"
            onClick={handleLogout}
            title="Log Out"
          >
            <LogOut size={16} />
            <span>Log Out</span>
          </button>
        </div>
      </header>

      {/* Main Admin Content Body */}
      <main className="admin-main-body">
        {/* Feedback Alert Toast */}
        {feedback && (
          <div className={`admin-feedback-toast ${feedback.type}`}>
            {feedback.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
            <span>{feedback.text}</span>
            <button 
              className="toast-close-btn"
              onClick={() => setFeedback(null)}
            >
              ×
            </button>
          </div>
        )}

        {/* Diagnostics & Stats Cards */}
        <section className="admin-stats-grid">
          <div className="admin-stat-card">
            <div className="stat-card-icon blue">
              <Database size={22} />
            </div>
            <div className="stat-card-details">
              <span className="stat-label">Vector Database</span>
              <span className="stat-value">ChromaDB Persistent</span>
              <span className="stat-sub">
                {healthStats ? `${healthStats.documents_count} Docs • ${healthStats.chunks_count} Chunks` : 'Loading...'}
              </span>
            </div>
          </div>

          <div className="admin-stat-card">
            <div className="stat-card-icon green">
              <Layers size={22} />
            </div>
            <div className="stat-card-details">
              <span className="stat-label">Embedding Model</span>
              <span className="stat-value">all-MiniLM-L6-v2</span>
              <span className="stat-sub">384-dim Dense Embeddings</span>
            </div>
          </div>

          <div className="admin-stat-card">
            <div className="stat-card-icon purple">
              <Cpu size={22} />
            </div>
            <div className="stat-card-details">
              <span className="stat-label">Answer Generator</span>
              <span className="stat-value">NVIDIA Nemotron</span>
              <span className="stat-sub">
                {healthStats?.api_key_configured ? 'API Key Active' : 'Fallback / Verified Mode'}
              </span>
            </div>
          </div>
        </section>

        {/* Document Ingestion & Toolbar Section */}
        <div className="admin-content-columns">
          {/* Left Column: Upload New PDF */}
          <div className="admin-card upload-section-card">
            <div className="card-header-row">
              <h3 className="admin-card-title">
                <UploadCloud size={20} className="card-icon" />
                <span>Upload IEEE Knowledge Document</span>
              </h3>
            </div>
            <p className="admin-card-desc">
              Upload official IEEE guidelines, bylaws, or conference calls (.pdf). Chunks are embedded and stored in ChromaDB automatically.
            </p>

            <div
              className={`admin-dropzone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files?.[0]) {
                  handleFileUpload(e.dataTransfer.files[0]);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden-file-input"
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />
              <UploadCloud size={38} className="dropzone-icon" />
              {isUploading ? (
                <div className="dropzone-text-group">
                  <span className="dropzone-primary-text">Processing and embedding PDF...</span>
                  <span className="dropzone-secondary-text">Extracting text pages into ChromaDB semantic chunks</span>
                </div>
              ) : (
                <div className="dropzone-text-group">
                  <span className="dropzone-primary-text">Click to choose or drag & drop a PDF</span>
                  <span className="dropzone-secondary-text">Maximum file size: 20 MB (.pdf only)</span>
                </div>
              )}
            </div>

            <div className="admin-reindex-box">
              <div className="reindex-info">
                <strong>Restore Verified Knowledge Base:</strong>
                <p>Re-embeds the 7 core official IEEE documents (membership, constitution, societies, standards, competitions).</p>
              </div>
              <button
                className="reindex-btn"
                onClick={handleReindex}
                disabled={isReindexing}
              >
                <RefreshCw size={15} className={isReindexing ? "spin" : ""} />
                <span>{isReindexing ? 'Re-indexing...' : 'Re-index Base Data'}</span>
              </button>
            </div>
          </div>

          {/* Right Column: Indexed Documents Catalog */}
          <div className="admin-card docs-table-card">
            <div className="card-header-row">
              <div className="card-title-group">
                <FileCheck size={20} className="card-icon" />
                <h3 className="admin-card-title">Indexed Knowledge Sources ({documents.length})</h3>
              </div>
              <button 
                className="table-refresh-btn"
                onClick={() => fetchHealthAndDocs(token)}
                disabled={isLoadingDocs}
                title="Refresh Documents List"
              >
                <RefreshCw size={15} className={isLoadingDocs ? "spin" : ""} />
                <span>Refresh</span>
              </button>
            </div>

            {isLoadingDocs ? (
              <div className="admin-loading-indicator">
                <RefreshCw size={24} className="spin text-blue" />
                <span>Loading indexed knowledge documents...</span>
              </div>
            ) : documents.length === 0 ? (
              <div className="admin-empty-table">
                <FileText size={36} className="empty-icon" />
                <p>No knowledge documents found in ChromaDB.</p>
                <button className="admin-primary-btn compact" onClick={handleReindex}>
                  Load Authentic Preloaded Knowledge Base
                </button>
              </div>
            ) : (
              <div className="docs-table-wrapper">
                <table className="admin-docs-table">
                  <thead>
                    <tr>
                      <th>Document Name</th>
                      <th>Pages</th>
                      <th>Chunks</th>
                      <th>Size</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {documents.map((doc) => (
                      <tr key={doc.id}>
                        <td className="doc-name-cell">
                          <div className="doc-name-group">
                            <span className="doc-table-filename">{doc.filename}</span>
                            {doc.source_url && (
                              <a 
                                href={doc.source_url} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="doc-table-url"
                              >
                                <span>{doc.source_url}</span>
                                <ExternalLink size={11} />
                              </a>
                            )}
                          </div>
                        </td>
                        <td>{doc.pages_count}</td>
                        <td>
                          <span className="chunk-badge">{doc.chunks_count}</span>
                        </td>
                        <td>{(doc.file_size_bytes / 1024).toFixed(1)} KB</td>
                        <td>
                          <button
                            className="doc-delete-action-btn"
                            onClick={() => setDocumentToDelete(doc)}
                            title={`Delete ${doc.filename}`}
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Confirmation Modal for Document Deletion */}
      {documentToDelete && (
        <div className="admin-modal-backdrop">
          <div className="admin-modal-card">
            <div className="modal-icon-badge danger">
              <Trash2 size={24} />
            </div>
            <h3 className="modal-title">Delete Knowledge Source?</h3>
            <p className="modal-desc">
              Are you sure you want to delete <strong>"{documentToDelete.filename}"</strong>?
              This will remove all associated vector embeddings from ChromaDB. The public assistant will no longer retrieve answers from this document.
            </p>
            <div className="modal-actions-row">
              <button
                className="admin-secondary-btn"
                onClick={() => setDocumentToDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                className="admin-danger-btn"
                onClick={confirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
