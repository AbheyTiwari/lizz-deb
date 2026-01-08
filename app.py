from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from pathlib import Path
import subprocess
import shutil
import uuid
import time
import atexit
import os
import uvicorn
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List
from AI_module.llm import LLM
from Modules.sr import SpeechRecognizer
from Modules.tts import TextToSpeech
from Modules.db import (
    get_topic_prompt, get_topic, init_db, add_topic,
    create_user, get_user_by_email, verify_password,
    create_session, get_session, delete_session,
    save_chat_message, get_chat_messages
)

# utils
def load_system_prompt(path="prompt.txt"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def cleanup_old_temp_files(temp_dir: Path, max_age_seconds: int = 3600):
    """Remove temp files older than max_age_seconds"""
    if not temp_dir.exists():
        return
    
    current_time = time.time()
    for file in temp_dir.glob("*"):
        if file.is_file():
            file_age = current_time - file.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    file.unlink()
                    print(f"Cleaned up old temp file: {file.name}")
                except Exception as e:
                    print(f"Failed to delete old temp file {file}: {e}")

# Security
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = credentials.credentials
    session = get_session(token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return session

# Optional auth - returns None if not authenticated
def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Optional authentication - returns user_id or None"""
    if not credentials:
        return None
    
    token = credentials.credentials
    session = get_session(token)
    
    return session["user_id"] if session else None

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_names: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, topic_id: str, user_id: str, user_name: str):
        await websocket.accept()
        if topic_id not in self.active_connections:
            self.active_connections[topic_id] = []
        self.active_connections[topic_id].append(websocket)
        self.user_names[user_id] = user_name
        
        # Notify others that user joined
        await self.broadcast(topic_id, {
            "type": "user_joined",
            "user_name": user_name,
            "timestamp": datetime.now().isoformat()
        }, exclude=websocket)
    
    def disconnect(self, websocket: WebSocket, topic_id: str):
        if topic_id in self.active_connections:
            self.active_connections[topic_id].remove(websocket)
    
    async def broadcast(self, topic_id: str, message: dict, exclude: WebSocket = None):
        if topic_id not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[topic_id]:
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections[topic_id].remove(conn)

manager = ConnectionManager()

# app init
app = FastAPI(
    title="Agent API",
    version="2.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = LLM()
sr = SpeechRecognizer(model_size="base")

# Initialize TTS - may take a moment to load the model
print("[TTS] Loading Coqui TTS model...")
tts = TextToSpeech()
print("[TTS] Model loaded successfully")

SYSTEM_PROMPT = load_system_prompt()

TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)

# Cleanup old files on startup
cleanup_old_temp_files(TEMP_DIR)
# Initialize database
init_db()

# Add default topics
add_topic(
    "climate_action",
    "Climate Action",
    "You are an AI debating climate action. Be logical, balanced, and critical. Challenge the user's position constructively while presenting counter-arguments based on science, economics, and policy.try answer in trhe least amount of words possible but s till making a strong Point. do not Use * # or anyother weird symbol or emojis."
)

add_topic(
    "ai_alignment",
    "AI Alignment",
    "You are debating AI alignment and safety. Focus on risk assessment, regulation strategies, and the balance between innovation and control. Challenge assumptions critically.try answer in trhe least amount of words possible but s till making a strong Point. do not Use * # or anyother weird symbol or emojis."
)

add_topic(
    "free_speech",
    "Free Speech",
    "You are debating free speech principles. Navigate the tensions between absolute rights, contextual harm, censorship concerns, and platform responsibilities. Be nuanced and challenge extremes.try answer in trhe least amount of words possible but s till making a strong Point. do not Use * # or anyother weird symbol or emojis."
)

add_topic(
    "education_reform",
    "Education Reform",
    "You are debating education reform. Contrast traditional vs progressive models, discuss credential inflation, and focus on what actually produces competence. Challenge idealistic assumptions.try answer in trhe least amount of words possible but s till making a strong Point. do not Use * # or anyother weird symbol or emojis."
)

add_topic(
    "universal_basic_income",
    "Universal Basic Income",
    "You are debating universal basic income. Focus on economic incentives, inflation risks, productivity effects, and societal transformation. Challenge both utopian and dystopian views.try answer in trhe least amount of words possible but s till making a strong Point. do not Use * # or anyother weird symbol or emojis."
)

add_topic(
    "tech_monopolies",
    "Tech Monopolies",
    "You are debating tech monopolies and market power. Weigh innovation benefits against anti-competitive risks. Discuss breakups, regulation, and market dynamics critically.try answer in trhe least amount of words possible but s till making a strong Point. do not Use * # or anyother weird symbol or emojis."
)

# Cleanup on shutdown
@atexit.register
def cleanup_on_exit():
    """Clean up temp directory on application shutdown"""
    try:
        shutil.rmtree(TEMP_DIR)
        print("Temp directory cleaned up on exit")
    except Exception as e:
        print(f"Failed to clean up temp directory: {e}")

# models
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    token: str
    user_id: str
    name: str
    email: str

class QueryRequest(BaseModel):
    query: str
    topic_id: str

class QueryResponse(BaseModel):
    response: str

class TranscriptionResponse(BaseModel):
    text: str
    language: str | None

class TTSRequest(BaseModel):
    text: str

class ChatMessage(BaseModel):
    message: str


# routes
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return FileResponse("templates/index.html")

@app.get("/auth", response_class=HTMLResponse)
def read_auth_page(request: Request):
    return FileResponse("templates/login.html")

@app.get("/chose_topics", response_class=HTMLResponse)
def read_topics_page(request: Request):
    return FileResponse("templates/topics.html")

@app.get("/room/{topic_id}", response_class=HTMLResponse)
def read_room(request: Request, topic_id: str):
    # Verify topic exists
    topic = get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return FileResponse("templates/room.html")

@app.get("/chat/{topic_id}", response_class=HTMLResponse)
def read_chat_room(request: Request, topic_id: str):
    # Verify topic exists
    topic = get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return FileResponse("templates/chat_room.html")

# Auth endpoints
@app.post("/api/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    """Create a new user account"""
    # Validate input
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    if len(payload.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    
    # Check if user already exists
    existing_user = get_user_by_email(payload.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = create_user(payload.name.strip(), payload.email, payload.password)
    
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    # Create session
    token = create_session(user["id"])
    
    return {
        "token": token,
        "user_id": user["id"],
        "name": user["name"],
        "email": user["email"]
    }

@app.post("/api/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    """Login user and create session"""
    # Get user
    user = get_user_by_email(payload.email)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create session
    token = create_session(user["id"])
    
    return {
        "token": token,
        "user_id": user["id"],
        "name": user["name"],
        "email": user["email"]
    }

@app.post("/api/logout")
def logout(user: dict = Depends(get_current_user)):
    """Logout user and delete session"""
    # The token is in the Authorization header
    # We need to get it from the dependency
    delete_session(user["session_token"])
    return {"message": "Logged out successfully"}

@app.get("/api/me")
def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"]
    }

@app.get("/api/topic/{topic_id}")
def get_topic_info(topic_id: str):
    """API endpoint to get topic information"""
    topic = get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return {
        "id": topic["id"],
        "title": topic["title"]
    }

@app.get("/api/chat/{topic_id}/messages")
def get_messages(topic_id: str, limit: int = 50):
    """Get chat messages for a topic"""
    messages = get_chat_messages(topic_id, limit)
    return {"messages": messages}

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat/{topic_id}")
async def websocket_chat(websocket: WebSocket, topic_id: str, token: str):
    # Verify token
    session = get_session(token)
    if not session:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    user_id = session["user_id"]
    user_name = session["name"]
    
    # Verify topic exists
    topic = get_topic(topic_id)
    if not topic:
        await websocket.close(code=1008, reason="Topic not found")
        return
    
    await manager.connect(websocket, topic_id, user_id, user_name)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                message_text = data.get("message", "").strip()
                if message_text:
                    # Save to database
                    save_chat_message(topic_id, user_id, user_name, message_text)
                    
                    # Broadcast to all connected clients
                    await manager.broadcast(topic_id, {
                        "type": "message",
                        "user_id": user_id,
                        "user_name": user_name,
                        "message": message_text,
                        "timestamp": datetime.now().isoformat()
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, topic_id)
        await manager.broadcast(topic_id, {
            "type": "user_left",
            "user_name": user_name,
            "timestamp": datetime.now().isoformat()
        })

@app.post("/query", response_model=QueryResponse)
def query_llm(payload: QueryRequest):
    """Query the LLM - no auth required for now"""
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Get topic-specific prompt from database
    topic_prompt = get_topic_prompt(payload.topic_id)
    if not topic_prompt:
        raise HTTPException(status_code=404, detail="Invalid topic")

    # Combine base system prompt with topic-specific prompt
    final_system_prompt = f"{SYSTEM_PROMPT}\n\n{topic_prompt}" if SYSTEM_PROMPT else topic_prompt

    try:
        result = llm.generate(
            user_prompt=payload.query,
            system_prompt=final_system_prompt,
        )
        return {"response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/speech-to-text", response_model=TranscriptionResponse)
async def speech_to_text(file: UploadFile = File(...)):
    """Speech to text conversion - no auth required"""
    webm_path = TEMP_DIR / f"{uuid.uuid4()}.webm"
    wav_path = TEMP_DIR / f"{uuid.uuid4()}.wav"

    try:
        # Save uploaded file
        with open(webm_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate uploaded file
        if webm_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty")
        
        print(f"[STT] Received audio: {webm_path.stat().st_size} bytes")
        
        # Convert using ffmpeg with proper error handling
        try:
            result = subprocess.run([
                'ffmpeg', 
                '-i', str(webm_path),
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',
                str(wav_path)
            ], 
            check=True, 
            capture_output=True,
            text=True
            )
            print(f"[STT] FFmpeg conversion successful")
        except subprocess.CalledProcessError as e:
            print(f"[STT] FFmpeg error: {e.stderr}")
            raise HTTPException(
                status_code=500, 
                detail=f"Audio conversion failed: {e.stderr[:200]}"
            )
        
        # Validate converted file
        if not wav_path.exists() or wav_path.stat().st_size == 0:
            raise HTTPException(
                status_code=500, 
                detail="Audio conversion produced empty file"
            )
        
        print(f"[STT] Converted audio: {wav_path.stat().st_size} bytes")
        
        # Transcribe
        try:
            result = sr.transcribe(str(wav_path))
            print(f"[STT] Transcription: '{result['text'][:50]}...' ({result['language']})")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            print(f"[STT] Transcription error: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Transcription failed: {str(e)}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[STT] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp files
        for path in [webm_path, wav_path]:
            try:
                if path.exists():
                    path.unlink()
            except Exception as e:
                print(f"[STT] Failed to delete temp file {path}: {e}")

@app.post("/text-to-speech")
def text_to_speech(payload: TTSRequest):
    """Text to speech conversion - no auth required"""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(payload.text) > 5000000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000000 characters)")

    output_path = TEMP_DIR / f"{uuid.uuid4()}.wav"

    try:
        print(f"[TTS] Generating speech for: '{payload.text[:50]}...'")
        
        # Coqui TTS generates the file directly
        tts.synthesize(payload.text, str(output_path))
        
        if not output_path.exists():
            raise HTTPException(
                status_code=500, 
                detail="TTS failed to create audio file"
            )
        
        file_size = output_path.stat().st_size
        if file_size == 0:
            raise HTTPException(
                status_code=500, 
                detail="TTS created empty audio file"
            )
        
        print(f"[TTS] Generated audio: {file_size} bytes")
        
        with open(output_path, 'rb') as f:
            audio_data = f.read()
        
        output_path.unlink()
        print(f"[TTS] Cleaned up temp file: {output_path.name}")
        
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav",
                "Content-Length": str(len(audio_data)),
                "Cache-Control": "no-cache"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TTS] Error: {e}")
        if output_path.exists():
            try:
                output_path.unlink()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

@app.get("/health")
def health_check():
    health = {
        "status": "healthy",
        "components": {},
        "temp": {},
    }

    # Temp dir check
    try:
        health["temp"] = {
            "path": str(TEMP_DIR),
            "files": len(list(TEMP_DIR.glob("*"))),
            "writable": TEMP_DIR.exists()
        }
    except Exception as e:
        health["status"] = "degraded"
        health["temp"]["error"] = str(e)

    # DB check
    try:
        from Modules.db import get_connection
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
        health["components"]["db"] = "ok"
    except Exception as e:
        health["status"] = "unhealthy"
        health["components"]["db"] = f"error: {e}"

    # LLM check (lightweight)
    try:
        _ = llm.generate(
            user_prompt="ping",
            system_prompt="Reply with 'pong'."
        )
        health["components"]["llm"] = "ok"
    except Exception as e:
        health["status"] = "unhealthy"
        health["components"]["llm"] = f"error: {e}"

    # TTS check - Coqui TTS uses .tts attribute
    try:
        tts.tts  # Check if TTS model is loaded
        health["components"]["tts"] = "ok"
    except Exception as e:
        health["status"] = "unhealthy"
        health["components"]["tts"] = f"error: {e}"

    # STT check (model loaded)
    try:
        sr.model  # model attribute exists?
        health["components"]["stt"] = "ok"
    except Exception as e:
        health["status"] = "unhealthy"
        health["components"]["stt"] = f"error: {e}"

    return health


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port)