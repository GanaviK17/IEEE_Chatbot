import { useState, useEffect, useRef, useCallback } from 'react';

export function useVoice() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [voiceError, setVoiceError] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState(null);
  const [isAutoSpeakEnabled, setIsAutoSpeakEnabled] = useState(false);

  const recognitionRef = useRef(null);
  const isSpeechRecognitionSupported = typeof window !== 'undefined' && 
    !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  const isSpeechSynthesisSupported = typeof window !== 'undefined' && 'speechSynthesis' in window;

  // Initialize Speech Recognition
  useEffect(() => {
    if (!isSpeechRecognitionSupported) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      setVoiceError(null);
    };

    recognition.onresult = (event) => {
      let currentTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        currentTranscript += event.results[i][0].transcript;
      }
      setTranscript(currentTranscript);
    };

    recognition.onerror = (event) => {
      console.warn('Speech recognition error event:', event.error);
      if (event.error === 'not-allowed') {
        setVoiceError('Microphone permission was denied. Please allow microphone access in your browser settings.');
      } else if (event.error === 'no-speech') {
        setVoiceError('No speech detected. Please try again.');
      } else if (event.error === 'network') {
        setVoiceError('Network error occurred during speech recognition.');
      } else {
        setVoiceError(`Voice input error: ${event.error}`);
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      try {
        recognition.abort();
      } catch {
        // cleanup ignore
      }
    };
  }, [isSpeechRecognitionSupported]);

  const startListening = useCallback(() => {
    if (!isSpeechRecognitionSupported) {
      setVoiceError('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    setTranscript('');
    setVoiceError(null);

    // Stop speaking if currently speaking
    if (isSpeechSynthesisSupported && window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setSpeakingMsgId(null);
    }

    try {
      recognitionRef.current?.start();
    } catch (err) {
      console.warn('Error starting speech recognition:', err);
    }
  }, [isSpeechRecognitionSupported, isSpeechSynthesisSupported]);

  const stopListening = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch (err) {
      console.warn('Error stopping speech recognition:', err);
    }
    setIsListening(false);
  }, []);

  // Text-to-Speech (TTS)
  const cleanTextForSpeech = (text) => {
    if (!text) return '';
    return text
      // Remove Markdown headers (#, ##, ###)
      .replace(/#{1,6}\s+/g, '')
      // Remove bold/italic markers (*, _)
      .replace(/[*_]{1,3}/g, '')
      // Remove inline code
      .replace(/`([^`]+)`/g, '$1')
      // Remove markdown blockquotes
      .replace(/^>\s+/gm, '')
      // Remove markdown bullet points
      .replace(/^[•\-\*]\s+/gm, '')
      // Remove bracket citations e.g. [Source: ...]
      .replace(/\[Source:[^\]]+\]/gi, '')
      // Remove markdown links [text](url)
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      // Clean multiple spaces/newlines
      .replace(/\n+/g, ' ')
      .replace(/\s{2,}/g, ' ')
      .trim();
  };

  const speak = useCallback((text, msgId = null) => {
    if (!isSpeechSynthesisSupported) {
      setVoiceError('Text-to-speech is not supported in this browser.');
      return;
    }

    // If currently speaking this message, toggle stop
    if (isSpeaking && speakingMsgId === msgId) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setSpeakingMsgId(null);
      return;
    }

    window.speechSynthesis.cancel();

    const spokenText = cleanTextForSpeech(text);
    if (!spokenText) return;

    const utterance = new SpeechSynthesisUtterance(spokenText);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pick a pleasant natural voice if available
    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(
      (v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Jenny'))
    ) || voices.find((v) => v.lang.startsWith('en'));

    if (naturalVoice) {
      utterance.voice = naturalVoice;
    }

    utterance.onstart = () => {
      setIsSpeaking(true);
      setSpeakingMsgId(msgId);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      setSpeakingMsgId(null);
    };

    utterance.onerror = (e) => {
      console.warn('Speech synthesis error:', e);
      setIsSpeaking(false);
      setSpeakingMsgId(null);
    };

    window.speechSynthesis.speak(utterance);
  }, [isSpeechSynthesisSupported, isSpeaking, speakingMsgId]);

  const stopSpeaking = useCallback(() => {
    if (isSpeechSynthesisSupported) {
      window.speechSynthesis.cancel();
    }
    setIsSpeaking(false);
    setSpeakingMsgId(null);
  }, [isSpeechSynthesisSupported]);

  return {
    isSpeechRecognitionSupported,
    isSpeechSynthesisSupported,
    isListening,
    transcript,
    setTranscript,
    voiceError,
    setVoiceError,
    startListening,
    stopListening,
    isSpeaking,
    speakingMsgId,
    speak,
    stopSpeaking,
    isAutoSpeakEnabled,
    setIsAutoSpeakEnabled,
  };
}
