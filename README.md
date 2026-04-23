# 🎙️ AI Voice Assistant

A full-stack voice-enabled AI assistant with persistent vector memory, user authentication, and multi-session support. Built with React, FastAPI, GPT-4, ElevenLabs, and Pinecone.

![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20DB-purple)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-V3-orange)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--time-yellow)
![Auth](https://img.shields.io/badge/Auth-JWT-red)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

## ✨ Features

- 🎤 **Voice Input** - Web Speech API with 2-second pause handling
- 🔊 **Voice Output** - ElevenLabs V3 with 6 selectable voices
- 💬 **Text Chat** - GPT-4o-mini with streaming word-by-word display
- 🧠 **Vector Memory** - Pinecone for persistent, semantic conversation memory
- 🔮 **Animated Orb** - Siri-style visual feedback for listening/thinking/speaking
- ⏹️ **Interrupt Speech** - Tap the orb to stop long responses
- 🔄 **Multi-Session** - Create, switch, and delete conversation threads
- 🔐 **User Authentication** - Signup/Login with JWT tokens
- 🗣️ **Voice Selection** - Choose from 6 different ElevenLabs voices
- 📱 **Responsive Design** - Works on desktop and mobile
- ⚡ **WebSocket Real-time** - Fast text and audio delivery

## 🛠️ Tech Stack

| Frontend | Backend | AI/ML | Database | Auth |
|----------|---------|-------|----------|------|
| React 18 | FastAPI | OpenAI GPT-4o-mini | Pinecone Vector DB | JWT |
| Web Speech API | Uvicorn | OpenAI Embeddings | SQLite | bcrypt |
| Framer Motion | WebSocket | ElevenLabs TTS V3 | | |
| Axios | httpx | | | |


## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 16+
- OpenAI API Key
- ElevenLabs API Key
- Pinecone API Key

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py

### Frontend Setup
```bash
cd frontend
npm install
npm start
Environment Variables
Create .env in backend/:

env
OPENAI_API_KEY=your-openai-key
PINECONE_API_KEY=your-pinecone-key
ELEVENLABS_API_KEY=your-elevenlabs-key
JWT_SECRET=your-secret-key
Create .env in frontend/:

env
REACT_APP_ELEVENLABS_API_KEY=your-elevenlabs-key
