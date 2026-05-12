# Local LAN Conversational AI

A fully local, GPU-accelerated AI assistant accessible over your home network.

This is currently built/configured for deplyoment to a **Windows Host**, but should be easily replicated on Linux since it's just using Docker containers and Ollama. 

Ollama is currently deployed naitively on the host mainly because my host has an AMD GPU, and AMD GPU's aren't really supported well in containers for Ollama yet. If you have an NVIDIA GPU, you could put everything in containers and make it a very clean deployment. Alternatively, you could run ollama in CPU mode, but then you lose some acceleration.

### Tech Stack
- **LLM:** Ollama (Llama 3 is an easy small model to deploy)
- **TTS:** Kokoro (Local, CPU-optimized)
- **Backend:** FastAPI (Python)
- **Frontend:** Straight Vanilla JavaScript + Web Audio API
- **Deployment:** Docker Compose

### Prerequisites
- Windows Host with an AMD GPU (ROCm)
- [Ollama for Windows](https://ollama.com/) installed on host
- [Docker Desktop](https://docs.docker.com/desktop/) installed on host

### Setup
1. Set Windows Env Var `OLLAMA_HOST=0.0.0.0`.
2. Run `docker-compose up --build -d`.
3. Access at `http://localhost:80` or your LAN IP.
