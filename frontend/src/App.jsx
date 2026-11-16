import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ChatArea from './components/ChatArea';
import AdminPortal from './components/AdminPortal';
import { useVoice } from './hooks/useVoice';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

export default function App() {
  const [currentView, setCurrentView] = useState(() => 
    window.location.pathname.startsWith('/admin') ? 'admin' : 'chat'
  );
  const [messages, setMessages] = useState([]);
  const [isLoadingChat, setIsLoadingChat] = useState(false);

  const voiceHook = useVoice();

  // Listen to browser forward/back buttons for URL navigation
  useEffect(() => {
    const handlePopState = () => {
      setCurrentView(window.location.pathname.startsWith('/admin') ? 'admin' : 'chat');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = (view) => {
    setCurrentView(view);
    const targetPath = view === 'admin' ? '/admin' : '/';
    if (window.location.pathname !== targetPath) {
      window.history.pushState({}, '', targetPath);
    }
  };

  const handleSendMessage = async (text) => {
    const userMsgId = 'msg_' + Date.now();
    const userMsg = {
      id: userMsgId,
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    // Build recent conversation turns for multi-turn context
    const historyPayload = messages.slice(-4).map((m) => ({
      role: m.sender === 'user' ? 'user' : 'assistant',
      content: m.text,
    }));

    setMessages((prev) => [...prev, userMsg]);
    setIsLoadingChat(true);

    try {
      const res = await fetch('/chat', {
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

  const handleClearChat = () => {
    if (voiceHook.isSpeaking) {
      voiceHook.stopSpeaking();
    }
    setMessages([]);
  };

  // Render Admin Portal if path or state is /admin
  if (currentView === 'admin') {
    return <AdminPortal onBack={() => navigateTo('chat')} />;
  }

  // Render Public Chat Assistant (Knowledge base management completely removed)
  return (
    <div className="app-shell">
      <Header
        voiceHook={voiceHook}
      />

      <div className="app-body-layout">
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
