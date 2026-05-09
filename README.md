# Local LAN Conversational AI

A fully local, GPU-accelerated AI assistant accessible over your home network.

### Tech Stack
- **LLM:** Ollama (Llama 3)
- **TTS:** Kokoro (Local, CPU-optimized)
- **Backend:** FastAPI (Python)
- **Frontend:** Vanilla JS + Web Audio API
- **Deployment:** Docker Compose

### Prerequisites
- Windows Host with an AMD GPU (ROCm)
- [Ollama for Windows](https://ollama.com/) installed on host
- Docker Desktop installed

### Setup
1. Set Windows Env Var `OLLAMA_HOST=0.0.0.0`.
2. Run `docker-compose up --build -d`.
3. Access at `http://localhost:80` or your LAN IP.
