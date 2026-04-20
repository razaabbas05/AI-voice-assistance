# 🎙️ AI Voice Assistant

A full-stack voice-enabled AI assistant with persistent vector memory, built with React, FastAPI, GPT-4, ElevenLabs, and Pinecone.

![React](https://img.shields.io/badge/React-18-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![Pinecone](https://img.shields.io/badge/Pinecone-Vector%20DB-purple)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-V3-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 🎤 **Voice Input** - Web Speech API for browser-based speech recognition
- 🔊 **Voice Output** - ElevenLabs V3 for natural speech synthesis
- 💬 **Text Chat** - GPT-4o-mini powered conversational AI
- 🧠 **Vector Memory** - Pinecone for persistent, semantic conversation memory
- 🔮 **Animated Orb** - Siri-style visual feedback for listening/thinking/speaking
- ⏹️ **Interrupt Speech** - Tap the orb to stop long responses
- 🔄 **Multi-session** - Isolated conversations with session IDs

## 🛠️ Tech Stack

| Frontend | Backend | AI/ML | Database |
|----------|---------|-------|----------|
| React | FastAPI | OpenAI GPT-4o-mini | Pinecone |
| Web Speech API | Uvicorn | OpenAI Embeddings | |
| Framer Motion | Python 3.10 | ElevenLabs TTS | |
| Axios | | | |

## 📁 Project Structure
Voice-Assistant/
├── backend/
│ ├── app.py # FastAPI server
│ ├── requirements.txt # Python dependencies
│ └── src/
│ ├── llm_controller.py # GPT + Vector memory
│ └── vector_memory.py # Pinecone operations
├── frontend/
│ ├── src/
│ │ ├── App.js # Main React component
│ │ └── index.css # All styles
│ └── package.json
└── README.md


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

cd frontend
npm install
npm start
📡 API Endpoints
Method	Endpoint	Description
POST	/api/chat/text	Send message, get AI response
GET	/api/memory/{session_id}	Get conversation memory
POST	/api/memory/clear/{session_id}	Clear conversation memory
🎯 How It Works
User speaks → Web Speech API transcribes voice to text

Text to backend → FastAPI processes with GPT-4o-mini

Vector memory → Pinecone retrieves relevant past conversations

GPT responds → Context-aware response

Text-to-Speech → ElevenLabs V3 generates natural voice

Audio plays → User hears expressive response

📦 Dependencies
Backend
fastapi

uvicorn

openai

pinecone

python-dotenv

Frontend
react

axios

framer-motion

🚢 Deployment
Backend: Render (free tier)

Frontend: Vercel (free tier)

📄 License
MIT License - feel free to use this project for learning or building your own voice assistant.

🙏 Acknowledgments
OpenAI for GPT and Embeddings API

ElevenLabs for Text-to-Speech API

Pinecone for Vector Database

Web Speech API for browser-based recognition

Built for learning and experimentation ❤️

text

## 📋 Short Description (For GitHub About Section):
🎙️ Voice-enabled AI assistant with persistent vector memory. Built with React, FastAPI, GPT-4, ElevenLabs TTS, and Pinecone. Features voice input/output, animated orb, and semantic conversation memory.

text

## 🏷️ Topics to add on GitHub:
react, fastapi, openai, gpt-4, elevenlabs, pinecone, voice-assistant, vector-database, text-to-speech, speech-recognition, conversational-ai, fullstack, python, javascript

text

## 🚀 Final Step - Add README to Git:

```bash
# Add README
git add README.md
git commit -m "Add README"
git push