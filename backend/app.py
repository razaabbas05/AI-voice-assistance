"""
FastAPI Backend for Voice Assistant - GPT with Vector Memory
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import traceback
from pathlib import Path
import uuid

# Add src to path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.llm_controller import LLMController

app = FastAPI(title="Voice Assistant API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store LLM instances per session
llm_instances = {}

def get_or_create_llm(session_id: str) -> LLMController:
    """Get or create LLM instance for a session"""
    if session_id not in llm_instances:
        llm_instances[session_id] = LLMController(session_id=session_id)
        print(f"✅ New session created: {session_id}")
    return llm_instances[session_id]

class TextRequest(BaseModel):
    message: str
    session_id: str = "default_user"

class MemoryResponse(BaseModel):
    total_memories: int
    session_id: str
    user_info: dict

@app.get("/")
async def root():
    return {"status": "Voice Assistant API is running with Vector Memory!"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/chat/text")
async def chat_text(req: TextRequest):
    """Handle text messages with vector memory"""
    print(f"📝 Session: {req.session_id} | Message: {req.message}")
    
    try:
        # Get or create LLM for this session
        llm = get_or_create_llm(req.session_id)
        
        # Process with LLM (includes vector memory)
        result = llm.process_user_message(req.message)
        print(f"✅ LLM Response: {result['response'][:50]}...")
        
        return {
            "response": result["response"],
            "emotion": result["emotion"],
            "intensity": result["intensity"],
            "session_id": req.session_id
        }
        
    except Exception as e:
        print(f"❌ Error processing request: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/{session_id}")
async def get_memory(session_id: str):
    """Get conversation memory for a session"""
    llm = llm_instances.get(session_id)
    if not llm:
        return {"total_memories": 0, "session_id": session_id, "user_info": {}}
    
    return llm.get_memory_summary()

@app.post("/api/memory/clear/{session_id}")
async def clear_memory(session_id: str):
    """Clear conversation memory for a session"""
    llm = llm_instances.get(session_id)
    if llm:
        llm.clear_memory()
        return {"status": f"Memory cleared for session: {session_id}"}
    
    return {"status": f"No session found: {session_id}"}

@app.post("/api/session/new")
async def new_session():
    """Create a new session"""
    session_id = str(uuid.uuid4())[:8]
    return {"session_id": session_id}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Voice Assistant with Vector Memory...")
    uvicorn.run(app, host="0.0.0.0", port=8000)