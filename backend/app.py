import os
import re
import json
import httpx
import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Configuration from Environment
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
KOKORO_URL = os.getenv("KOKORO_HOST", "http://kokoro:8880")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

# Enable LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def stream_llm_and_tts(text_input: str, websocket: WebSocket):
    """Orchestrates Ollama -> Sentence Splitter -> Kokoro -> WebSocket."""
    sentence_buffer = ""
    
    async with httpx.AsyncClient(timeout=None) as client:
        # 1. Start streaming from Ollama
        async with client.stream(
            "POST", 
            f"{OLLAMA_URL}/api/generate", 
            json={"model": "llama3", "prompt": text_input,
                  "system": "You are a helpful and polite assistant. Always use proper spacing and punctuation, and never use profanity."}
        ) as response:
            
            async for line in response.aiter_lines():
                if not line: continue
                
                chunk = json.loads(line)
                token = chunk.get("response", "")

                # Send text to the ui immediatley for live typing effect
                await websocket.send_text(token)

                sentence_buffer += token
                
                # 2. Check for sentence boundaries (. ! ? or Newline)
                if any(punc in token for punc in [".", "!", "?", "\n"]):
                    # Clean up and split
                    parts = re.split(r'(?<=[.!?\n])', sentence_buffer)
                    if len(parts) > 1:
                        complete_sentence = parts[0].strip()
                        sentence_buffer = "".join(parts[1:])
                        
                        if len(complete_sentence) > 2: # Ignore tiny fragments
                            logger.info(f"Synthesizing: {complete_sentence}")
                            
                            # 3. Request TTS from Kokoro (OpenAI-compatible endpoint)
                            tts_res = await client.post(
                                f"{KOKORO_URL}/v1/audio/speech",
                                json={
                                    "model": "kokoro",
                                    "input": complete_sentence,
                                    "voice": "af_bella", # Default high-quality female voice
                                    "response_format": "mp3"
                                }
                            )
                            
                            if tts_res.status_code == 200:
                                # 4. Send binary MP3 chunk to browser
                                await websocket.send_bytes(tts_res.content)

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected via WebSocket")
    
    try:
        while True:
            # Receive text prompt from UI
            data = await websocket.receive_text()
            # Start the processing pipeline
            await stream_llm_and_tts(data, websocket)
            # Signal end of turn (optional)
            await websocket.send_text("__END_OF_TURN__")
            
    except WebSocketDisconnect:
        logger.info("Client disconnected")
