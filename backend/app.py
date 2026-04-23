"""
FastAPI Backend for Voice Assistant - WebSocket with Full Audio + Multi-Session + Auth
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import traceback
import json
import httpx
import os
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.llm_controller import LLMController
from session_manager import (
    init_db, create_session, update_session_timestamp, update_session_title,
    list_sessions, delete_session, save_message, get_session_messages, auto_generate_title,
    create_session_for_user, list_sessions_for_user
)
from auth import init_auth_db, create_user, authenticate_user, create_token, verify_token, get_user_by_id

app = FastAPI(title="Voice Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_instances = {}

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
DEFAULT_VOICE_ID = os.getenv("DEFAULT_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

@app.on_event("startup")
async def startup():
    await init_db()
    init_auth_db()
    print("✅ Database and Auth ready")

def get_or_create_llm(session_id: str, user_id: int = None) -> LLMController:
    if session_id not in llm_instances:
        llm_instances[session_id] = LLMController(session_id=session_id)
        asyncio.create_task(create_session(session_id, user_id))
        print(f"✅ New session created: {session_id}")
    return llm_instances[session_id]

async def get_full_audio(text: str, voice_id: str = None) -> bytes:
    voice = voice_id or DEFAULT_VOICE_ID
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {
            "stability": 0.3,
            "similarity_boost": 0.75,
            "style": 0.6,
            "use_speaker_boost": True
        },
        "optimize_streaming_latency": 3,
        "output_format": "mp3_44100_128"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ ElevenLabs error: {response.text}")
            return b''
        
        print(f"✅ Full audio generated with voice {voice}: {len(response.content)} bytes")
        return response.content

class TextRequest(BaseModel):
    message: str
    session_id: str = "default_user"

# ─── AUTH ENDPOINTS ───

@app.post("/api/auth/signup")
async def signup(request: dict):
    """Create new user account"""
    email = request.get("email", "").strip()
    username = request.get("username", "").strip()
    password = request.get("password", "")
    
    if not email or not username or not password:
        raise HTTPException(status_code=400, detail="All fields are required")
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    user = create_user(email, username, password)
    
    if not user:
        raise HTTPException(status_code=409, detail="Email or username already exists")
    
    token = create_token(user["id"])
    
    return {"token": token, "user": user}

@app.post("/api/auth/login")
async def login(request: dict):
    """Login user"""
    email = request.get("email", "").strip()
    password = request.get("password", "")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    user = authenticate_user(email, password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_token(user["id"])
    
    return {"token": token, "user": user}

@app.get("/api/auth/me")
async def get_current_user(token: str):
    """Get current user info from token"""
    user_id = verify_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"user": user}

# ─── CHAT ENDPOINTS ───

@app.post("/api/chat/text")
async def chat_text(req: TextRequest):
    print(f"📝 Session: {req.session_id} | Message: {req.message}")
    
    try:
        llm = get_or_create_llm(req.session_id)
        result = llm.process_user_message(req.message)
        
        await save_message(req.session_id, "user", req.message)
        await save_message(req.session_id, "assistant", result["response"], result["emotion"])
        
        messages = await get_session_messages(req.session_id)
        if len([m for m in messages if m["role"] == "user"]) == 1:
            await auto_generate_title(req.session_id, req.message)
        
        return {
            "response": result["response"],
            "tagged_script": result.get("tagged_script", result["response"]),
            "emotion": result["emotion"],
            "intensity": result["intensity"],
            "session_id": req.session_id
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    print(f"🔌 WebSocket connected: {session_id}")
    
    llm = get_or_create_llm(session_id)
    message_count = 0
    
    try:
        while True:
            data = await websocket.receive_json()
            user_text = data.get("text", "")
            voice_id = data.get("voice_id", DEFAULT_VOICE_ID)
            user_id = data.get("user_id", None)
            
            print(f"📝 WS Message: {user_text[:50]}... (Voice: {voice_id})")
            
            await save_message(session_id, "user", user_text)
            message_count += 1
            
            if message_count == 1:
                await auto_generate_title(session_id, user_text)
            
            result = llm.process_user_message(user_text)
            
            await websocket.send_json({
                "type": "text",
                "response": result["response"],
                "emotion": result["emotion"],
                "intensity": result["intensity"]
            })
            
            await save_message(session_id, "assistant", result["response"], result["emotion"])
            
            audio_text = result.get("tagged_script", result["response"])
            print(f"🎤 Getting full audio with voice {voice_id}...")
            audio_data = await get_full_audio(audio_text, voice_id)
            
            if audio_data:
                await websocket.send_bytes(audio_data)
                print(f"✅ Sent full audio: {len(audio_data)} bytes")
            
            await update_session_timestamp(session_id, user_id)
            
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

# ─── SESSION ENDPOINTS ───

@app.get("/api/sessions")
async def get_sessions(user_id: int = None):
    sessions = await list_sessions(user_id)
    return {"sessions": sessions}

@app.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    messages = await get_session_messages(session_id)
    return {"messages": messages}

@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    await delete_session(session_id)
    if session_id in llm_instances:
        llm_instances[session_id].clear_memory()
        del llm_instances[session_id]
    return {"status": "deleted"}

@app.put("/api/sessions/{session_id}/title")
async def update_title(session_id: str, title: str):
    await update_session_title(session_id, title)
    return {"status": "updated"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/memory/clear/{session_id}")
async def clear_memory(session_id: str):
    llm = llm_instances.get(session_id)
    if llm:
        llm.clear_memory()  
        return {"status": f"Memory cleared for session: {session_id}"}
    return {"status": f"No session found: {session_id}"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Voice Assistant with WebSocket + Auth...")
    uvicorn.run(app, host="0.0.0.0", port=8000)