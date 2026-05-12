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

async def stream_llm_and_tts(messages: list, websocket: WebSocket):
    """Orchestrates Ollama -> Sentence Splitter -> Kokoro -> WebSocket."""
    sentence_buffer = ""
    full_ai_response = "" # track the AI's response to save it for later
    
    async with httpx.AsyncClient(timeout=None) as client:
        # 1. Start streaming from Ollama
        async with client.stream(
            "POST", 
            f"{OLLAMA_URL}/api/chat", 
            json={
                "model": "llama3", 
                "messages": messages,
                "stream": True
            }
                  #"system": "You are a helpful and polite assistant. You speak in an elegant manner, with an air of sophistication as if high aristocracy is in your lineage, with a slight touch of hubris. You are not pandering, and do not respond about the quality or type of question asked of you. For example, you will never say something like *What a great question!* or *What an astute inquiry!* Instead you just get right to the response and answer the question as directly as possible in a succinct manner that still conveys the important takeaways. Your answers should be in 2 to 3 sentences and never take longer than 7 seconds for an average reader to read. You never use profanity."}
        ) as response:
            
            async for line in response.aiter_lines():
                if not line: continue
                
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")

                # Send text to the ui immediatley for live typing effect
                await websocket.send_text(token)

                full_ai_response += token
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
                                    "voice": "bm_george", # wise british gentleman voice
                                    "response_format": "mp3",
                                    "speed": 1.3
                                }
                            )
                            
                            if tts_res.status_code == 200:
                                # 4. Send binary MP3 chunk to browser
                                await websocket.send_bytes(tts_res.content)

    return full_ai_response # allows us to add to history

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected via WebSocket")

    # Max history size to prevent memory issues (adjust as needed)
    MAX_HISTORY = 20

    # Initialize history for this specific connection
    history = [
        {
            "role": "system", 
            "content": "You are a helpful and polite assistant. You speak in an elegant manner, with an air of sophistication as if high aristocracy is in your lineage, with a slight touch of hubris. You are not pandering, and do not respond about the quality or type of question asked of you. For example, you will never say something like *What a great question!* or *What an astute inquiry!* Instead you just get right to the response and answer the question as directly as possible in a succinct manner that still conveys the important takeaways. Your answers should be in 2 to 3 sentences and never take longer than 7 seconds for an average reader to read. You never use profanity."
        }
    ]

    try:
        while True:
            # Receive text prompt from UI
            user_input = await websocket.receive_text()

            history.append({"role": "user", "content": user_input})
            # Start the processing pipeline
            ai_text = await stream_llm_and_tts(history, websocket)
            history.append({"role": "assistant", "content": ai_text})
            # Trim history if it exceeds max size
            if len(history) > MAX_HISTORY:
                history.pop(1)  # Remove the oldest user/assistant pair, keep system prompt

            # Signal end of turn (optional)
            await websocket.send_text("__END_OF_TURN__")
            
    except WebSocketDisconnect:
        logger.info("Client disconnected")
