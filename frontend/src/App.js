import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import axios from 'axios';
import { FiMenu, FiPlus, FiTrash2, FiX, FiChevronDown } from 'react-icons/fi';
import Login from './Login';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/chat';

const VOICE_OPTIONS = [
  { id: '21m00Tcm4TlvDq8ikWAM', name: 'Rachel (Warm)' },
  { id: 'AZnzlk1XvdvUeBnXmlld', name: 'Domi (Friendly)' },
  { id: 'EXAVITQu4vr4xnSDxMaL', name: 'Bella (Soft)' },
  { id: 'ErXwobaYiN019PkySvjV', name: 'Antoni (Deep)' },
  { id: 'VR6AewLTigWG4xSOukaG', name: 'Arnold (Powerful)' },
  { id: 'pNInz6obpgDQGcFmaJgB', name: 'Adam (Calm)' },
];

function App() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [recognition, setRecognition] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const audioElementRef = useRef(new Audio());

  const [sessions, setSessions] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteType, setDeleteType] = useState(null);
  const [deleteTargetId, setDeleteTargetId] = useState(null);

  const [selectedVoice, setSelectedVoice] = useState(() => {
    return localStorage.getItem('selectedVoice') || '21m00Tcm4TlvDq8ikWAM';
  });
  const [showVoiceDropdown, setShowVoiceDropdown] = useState(false);

  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing token on load
  useEffect(() => {
    const token = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    
    if (token && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser);
        setUser(parsedUser);
      } catch (e) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    }
    setIsLoading(false);
  }, []);

  const handleLogin = (loggedInUser) => {
    setUser(loggedInUser);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('session_id');
    if (wsRef.current) wsRef.current.close();
    setUser(null);
    setMessages([]);
    setSessions([]);
  };

  const handleVoiceChange = (voiceId) => {
    setSelectedVoice(voiceId);
    localStorage.setItem('selectedVoice', voiceId);
    setShowVoiceDropdown(false);
  };

  // Initialize new session on login
  useEffect(() => {
    if (!user) return;
    
    const sid = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
    setSessionId(sid);
    localStorage.setItem('session_id', sid);
    setMessages([]);
  }, [user]);

  const fetchSessions = async () => {
    try {
      const token = localStorage.getItem('token');
      const savedUser = localStorage.getItem('user');
      const currentUser = savedUser ? JSON.parse(savedUser) : null;
      
      const res = await axios.get(`${API_URL}/api/sessions`, {
        params: { user_id: currentUser?.id },
        headers: { Authorization: `Bearer ${token}` }
      });
      setSessions(res.data.sessions);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  };

  const loadSession = async (sid) => {
    if (sid === sessionId) return;
    
    setLoadingHistory(true);
    stopSpeaking();
    
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_URL}/api/sessions/${sid}/messages`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const loadedMessages = res.data.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        emotion: msg.emotion
      }));
      setMessages(loadedMessages);
      setSessionId(sid);
      localStorage.setItem('session_id', sid);
      setInputText('');
      
      if (wsRef.current) {
        wsRef.current.close();
      }
    } catch (err) {
      console.error('Failed to load session:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const newChat = () => {
    const sid = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 5);
    setSessionId(sid);
    localStorage.setItem('session_id', sid);
    setMessages([]);
    setInputText('');
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  const deleteSessionHandler = (sid) => {
    setDeleteType('session');
    setDeleteTargetId(sid);
    setShowDeleteDialog(true);
  };

  const clearChat = () => {
    setDeleteType('chat');
    setDeleteTargetId(null);
    setShowDeleteDialog(true);
  };

  const confirmDelete = async () => {
    setShowDeleteDialog(false);
    
    if (deleteType === 'session') {
      try {
        const token = localStorage.getItem('token');
        await axios.delete(`${API_URL}/api/sessions/${deleteTargetId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        fetchSessions();
        if (deleteTargetId === sessionId) {
          newChat();
        }
      } catch (err) {
        console.error('Failed to delete session:', err);
      }
    } else if (deleteType === 'chat') {
      stopSpeaking();
      try {
        const token = localStorage.getItem('token');
        await axios.post(`${API_URL}/api/memory/clear/${sessionId}`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setMessages([]);
      } catch (error) {
        console.error('Error clearing memory:', error);
        setMessages([]);
      }
    }
    
    setDeleteType(null);
    setDeleteTargetId(null);
  };

  const cancelDelete = () => {
    setShowDeleteDialog(false);
    setDeleteType(null);
    setDeleteTargetId(null);
  };

  // WebSocket connection
  useEffect(() => {
    if (!sessionId || !user) return;
    
    const ws = new WebSocket(`${WS_URL}/${sessionId}`);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;
    
    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      setWsConnected(true);
      fetchSessions();
    };
    
    ws.onmessage = async (event) => {
      if (event.data instanceof ArrayBuffer) {
        const audioBlob = new Blob([event.data], { type: 'audio/mp3' });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        setIsSpeaking(true);
        audioElementRef.current.src = audioUrl;
        audioElementRef.current.play().catch(e => setIsSpeaking(false));
        
        audioElementRef.current.onended = () => {
          URL.revokeObjectURL(audioUrl);
          setIsSpeaking(false);
        };
        return;
      }
      
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'text') {
          const assistantMessage = {
            role: 'assistant',
            content: data.response,
            emotion: data.emotion
          };
          setMessages(prev => [...prev, assistantMessage]);
          setIsThinking(false);
          fetchSessions();
        }
        
        if (data.type === 'error') {
          console.error('❌ Server error:', data.message);
          setIsThinking(false);
        }
      } catch (error) {
        console.error('Parse error:', error);
      }
    };
    
    ws.onerror = () => setWsConnected(false);
    ws.onclose = () => setWsConnected(false);
    
    return () => ws.close();
  }, [sessionId, user]);

  // Speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = true;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = 'en-IN';
      
      let silenceTimer = null;
      let finalTranscript = '';
      let interimTranscript = '';
      
      recognitionInstance.onresult = (event) => {
        interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }
        
        setInputText(finalTranscript + interimTranscript);
        
        if (silenceTimer) clearTimeout(silenceTimer);
        
        silenceTimer = setTimeout(() => {
          const fullText = (finalTranscript + interimTranscript).trim();
          if (fullText) recognitionInstance.stop();
        }, 2000);
      };
      
      recognitionInstance.onerror = () => {
        setIsRecording(false);
        if (silenceTimer) clearTimeout(silenceTimer);
        finalTranscript = '';
        interimTranscript = '';
      };
      
      recognitionInstance.onend = () => {
        setIsRecording(false);
        if (silenceTimer) clearTimeout(silenceTimer);
        
        const fullText = (finalTranscript + interimTranscript).trim();
        if (fullText) sendMessage(fullText);
        setInputText('');
        finalTranscript = '';
        interimTranscript = '';
      };
      
      setRecognition(recognitionInstance);
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const audio = audioElementRef.current;
    
    const handlePlay = () => setIsSpeaking(true);
    const handleEnded = () => setIsSpeaking(false);
    const handlePause = () => setIsSpeaking(false);
    const handleError = () => setIsSpeaking(false);
    
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('pause', handlePause);
    audio.addEventListener('error', handleError);
    
    return () => {
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('pause', handlePause);
      audio.removeEventListener('error', handleError);
      audio.pause();
      audio.src = '';
    };
  }, []);

  const stopSpeaking = () => {
    audioElementRef.current.pause();
    audioElementRef.current.src = '';
    setIsSpeaking(false);
  };

  const sendMessage = async (voiceInput = null) => {
    const messageText = voiceInput || inputText;
    if (!messageText.trim()) return;
    
    stopSpeaking();
    
    if (!voiceInput) {
      setInputText('');
    }
    
    setMessages(prev => [...prev, { role: 'user', content: messageText }]);
    setIsThinking(true);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ 
        text: messageText,
        voice_id: selectedVoice,
        user_id: user?.id
      }));
    } else {
      try {
        const token = localStorage.getItem('token');
        const response = await axios.post(`${API_URL}/api/chat/text`, {
          message: messageText,
          session_id: sessionId
        }, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.data.response,
          emotion: response.data.emotion
        }]);
        
        setIsThinking(false);
        fetchSessions();
      } catch (error) {
        console.error('Error:', error);
        setIsThinking(false);
      }
    }
  };

  const toggleRecording = () => {
    if (!recognition) {
      alert("Speech recognition not supported. Use Chrome or Edge.");
      return;
    }
    
    if (isRecording) {
      recognition.stop();
    } else {
      stopSpeaking();
      recognition.start();
      setIsRecording(true);
    }
  };

  const getOrbState = () => {
    if (isRecording) return 'listening';
    if (isThinking) return 'thinking';
    if (isSpeaking) return 'speaking';
    return 'idle';
  };

  const orbState = getOrbState();
  const currentVoice = VOICE_OPTIONS.find(v => v.id === selectedVoice)?.name || 'Rachel';

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app">
      <div className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={newChat}>
            <FiPlus /> New Chat
          </button>
          <button className="close-sidebar-btn" onClick={() => setSidebarOpen(false)}>
            <FiX />
          </button>
        </div>
        <div className="session-list">
          {sessions.map(sess => (
            <div
              key={sess.session_id}
              className={`session-item ${sess.session_id === sessionId ? 'active' : ''}`}
              onClick={() => loadSession(sess.session_id)}
            >
              <span className="session-title">{sess.title}</span>
              <span className="session-date">{new Date(sess.last_updated).toLocaleDateString()}</span>
              <button
                className="delete-session-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteSessionHandler(sess.session_id);
                }}
              >
                <FiTrash2 />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="main-chat">
        <header className="header">
          <div className="header-content">
            <button className="menu-btn" onClick={() => setSidebarOpen(true)}>
              <FiMenu />
            </button>
            <div className="header-title">
              <h1>🎙️ Voice Assistant</h1>
              <p>GPT + ElevenLabs V3 {wsConnected && '⚡'}</p>
            </div>
            
            <div className="voice-selector">
              <button 
                className="voice-selector-btn"
                onClick={() => setShowVoiceDropdown(!showVoiceDropdown)}
              >
                <span className="voice-label">{currentVoice}</span>
                <FiChevronDown className={`dropdown-icon ${showVoiceDropdown ? 'open' : ''}`} />
              </button>
              
              {showVoiceDropdown && (
                <div className="voice-dropdown">
                  {VOICE_OPTIONS.map(voice => (
                    <div
                      key={voice.id}
                      className={`voice-option ${selectedVoice === voice.id ? 'active' : ''}`}
                      onClick={() => handleVoiceChange(voice.id)}
                    >
                      {voice.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <button onClick={clearChat} className="clear-btn" title="Clear chat">
              🗑️
            </button>
            <button onClick={handleLogout} className="logout-btn" title="Logout">
              🚪
            </button>
          </div>
        </header>

        <div className="chat-container">
          {loadingHistory ? (
            <div className="loading-history">Loading conversation...</div>
          ) : (
            <div className="messages-wrapper">
              {messages.length === 0 ? (
                <div className="empty-state">
                  <h2>👋 Welcome!</h2>
                  <p>Tap the mic or type to start</p>
                </div>
              ) : (
                messages.map((msg, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className={`message-wrapper ${msg.role}`}
                  >
                    <div className="message-bubble">
                      <p className="message-text">{msg.content}</p>
                      {msg.emotion && (
                        <p className="message-emotion">{msg.emotion}</p>
                      )}
                    </div>
                  </motion.div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="bottom-section">
          <div className="orb-wrapper">
            <div className="orb-container" onClick={isSpeaking ? stopSpeaking : undefined}>
              <motion.div
                className={`orb ${orbState} ${isSpeaking ? 'clickable' : ''}`}
                animate={{
                  scale: orbState === 'listening' ? [1, 1.15, 1] : 
                         orbState === 'speaking' ? [1, 1.1, 0.95, 1.05, 1] :
                         orbState === 'thinking' ? [1, 1.05, 1] : 1,
                }}
                transition={{
                  duration: orbState === 'listening' ? 0.8 :
                            orbState === 'speaking' ? 0.6 :
                            orbState === 'thinking' ? 1.5 : 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <motion.div className="orb-inner" />
                <motion.div className="orb-glow" />
              </motion.div>
              
              <div className="orb-status">
                {orbState === 'listening' && '🎤 Listening...'}
                {orbState === 'thinking' && '💭 Thinking...'}
                {orbState === 'speaking' && '🔊 Speaking (Tap to Stop)'}
                {orbState === 'idle' && (wsConnected ? '⚡ Ready' : '👋 Ready')}
              </div>
            </div>
          </div>

          <div className="input-wrapper">
            <div className="input-container">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                placeholder={isRecording ? "🎤 Listening..." : "Type a message..."}
                className="message-input"
                disabled={isRecording}
              />
              
              <button
                onClick={toggleRecording}
                className={`voice-btn ${isRecording ? 'recording' : ''}`}
              >
                {isRecording ? '⏹️' : '🎤'}
              </button>
              
              <button
                onClick={() => sendMessage()}
                disabled={!inputText.trim()}
                className="send-btn"
              >
                ➤
              </button>
            </div>
          </div>
        </div>
      </div>

      {showDeleteDialog && (
        <div className="dialog-overlay" onClick={cancelDelete}>
          <div className="dialog-box" onClick={(e) => e.stopPropagation()}>
            <h3>Confirm Delete</h3>
            <p>
              {deleteType === 'session' 
                ? 'Are you sure you want to delete this conversation? This action cannot be undone.'
                : 'Are you sure you want to clear the current chat history?'
              }
            </p>
            <div className="dialog-buttons">
              <button className="dialog-btn cancel" onClick={cancelDelete}>Cancel</button>
              <button className="dialog-btn confirm" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;