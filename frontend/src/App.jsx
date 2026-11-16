import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ChatArea from './components/ChatArea';
import DocumentManager from './components/DocumentManager';
import { useVoice } from './hooks/useVoice';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

export default function App() {
  const [healthData, setHealthData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const voiceHook = useVoice();

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealthData(data);
      }
    } catch (err) {
      console.warn('Backend connection notice:', err);
    }
  };

  const fetchDocuments = async () => {
    setIsLoadingDocs(true);
    try {
      const res = await fetch(`${API_BASE_URL}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchDocuments();
  }, []);

  const handleSendMessage = async (text) => {
    const userMsgId = 'msg_' + Date.now();
    const userMsg = {
      id: userMsgId,
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    // Build recent conversation turns for context in follow-up questions
    const historyPayload = messages.slice(-4).map((m) => ({
      role: m.sender === 'user' ? 'user' : 'assistant',
      content: m.text,
    }));

    setMessages((prev) => [...prev, userMsg]);
    setIsLoadingChat(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          top_k: 4,
          history: historyPayload
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Unable to generate response');
      }

      const botMsg = {
        id: 'bot_' + Date.now(),
        sender: 'bot',
        text: data.answer,
        sources: data.sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const errorMsg = {
        id: 'err_' + Date.now(),
        sender: 'bot',
        text: "I'm temporarily unable to answer right now. Please try again in a moment.",
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoadingChat(false);
    }
  };

  const handleUploadSuccess = () => {
    fetchDocuments();
    fetchHealth();
  };

  const handleDeleteSuccess = (docId) => {
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
    fetchHealth();
  };

  const handleClearChat = () => {
    if (voiceHook.isSpeaking) {
      voiceHook.stopSpeaking();
    }
    setMessages([]);
  };

  return (
    <div className="app-shell">
      <Header
        totalDocs={documents.length}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        voiceHook={voiceHook}
      />

      <div className="app-body-layout">
        <div className={`sidebar-wrapper ${isSidebarOpen ? 'open' : ''}`}>
          <DocumentManager
            documents={documents}
            onUploadSuccess={handleUploadSuccess}
            onDeleteSuccess={handleDeleteSuccess}
            isLoadingDocs={isLoadingDocs}
            fetchDocuments={fetchDocuments}
            onClose={() => setIsSidebarOpen(false)}
          />
        </div>

        {isSidebarOpen && (
          <div
            className="sidebar-backdrop"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        <ChatArea
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoadingChat}
          onClearChat={handleClearChat}
          voiceHook={voiceHook}
        />
      </div>
    </div>
  );
}
