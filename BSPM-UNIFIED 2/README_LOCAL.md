# GBStudio Automation Hub - Local Setup (No Docker!)

**Fuck Docker! Run this thing natively.**

This is a simplified setup guide for running the GBStudio Automation Hub directly on your machine without Docker.

## Prerequisites

1. **Python 3.11+**
   ```bash
   python3 --version
   ```

2. **Ollama** (for the AI agent)
   - macOS: Download from https://ollama.ai
   - Linux:
     ```bash
     curl https://ollama.ai/install.sh | sh
     ```
   - Start Ollama:
     ```bash
     ollama serve
     ```
   - Pull required models:
     ```bash
     ollama pull llama3
     ollama pull nomic-embed-text
     ```

3. **ComfyUI** (optional - only needed for image generation)
   - If you don't need image generation, you can skip this
   - Instructions: https://github.com/comfyanonymous/ComfyUI

## Quick Start

### 1. Install Dependencies

```bash
cd "BSPM-UNIFIED 2"

# Create a virtual environment (HIGHLY recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the setup script
./setup_local.sh
```

Or manually:
```bash
pip install -r backend/requirements.txt
```

### 2. Start Ollama

Make sure Ollama is running:
```bash
# In a separate terminal
ollama serve
```

Check that it's working:
```bash
curl http://localhost:11434/api/tags
```

### 3. Start the FastAPI Backend

```bash
./run_local.sh
```

Or manually:
```bash
# Load environment variables
export $(cat .env.local | grep -v '^#' | xargs)

# Start the server
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the Application

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## What Changed from Docker Setup?

All the Docker-specific paths have been updated:

| Docker Path | Local Path |
|-------------|-----------|
| `/app/logs` | `./app/logs` |
| `/app/project_files` | `./project_files` |
| `/app/temp_outputs` | `./temp_outputs` |
| `/app/vectorstore` | `./vectorstore` |
| `/app/agent_memory` | `./agent_memory` |
| `http://ollama:11434` | `http://localhost:11434` |
| `http://comfyui:8188` | `http://localhost:8188` |

These are all configured in `.env.local` and can be customized.

## Configuration

All configuration is in `.env.local`. You can edit this file to change:
- Service URLs
- File paths
- Model names
- Generation parameters

## Running Without ComfyUI

If you don't have ComfyUI set up, the system will still run but image generation won't work. You can:
1. Use it for testing the chat interface
2. Set up ComfyUI later when you're ready
3. Mock the image generation for development

## Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"
- Install dependencies: `pip install -r backend/requirements.txt`
- Make sure you're in a virtual environment

### "Connection refused" to Ollama
- Make sure Ollama is running: `ollama serve`
- Check it's on the right port: `curl http://localhost:11434/api/tags`

### "API keys file not found"
- The app will still run, just without API key authentication
- For production, create: `./app/secrets/api_keys.txt`

### Frontend not loading
- Make sure the `frontend/` directory exists
- Check the `FRONTEND_PATH` in `.env.local`

## Development Tips

1. **Auto-reload**: The `--reload` flag is enabled by default, so changes to Python files will automatically restart the server

2. **Logs**: Check `./app/logs/app.log` for detailed logs

3. **Debug mode**: Set `LOG_LEVEL=DEBUG` in `.env.local` for more verbose logging

4. **No ComfyUI**: Comment out or skip ComfyUI checks if you're just testing

## Scripts

- `./setup_local.sh` - Install dependencies and check prerequisites
- `./run_local.sh` - Start the FastAPI server
- `./stop.sh` - Stop all services (works for Docker too, adapt as needed)

## What Works Without Docker?

✅ FastAPI backend
✅ Chat interface with PM Agent
✅ Knowledge base search
✅ Conversation memory
✅ Health checks and metrics
✅ API endpoints

⏸️ Image generation (requires ComfyUI)
⏸️ GBStudio integration (if you have GBStudio projects)

## Next Steps

1. Make sure Ollama is running and has the required models
2. Run `./setup_local.sh`
3. Run `./run_local.sh`
4. Open http://localhost:8000
5. Start chatting with the PM agent!

---

**No more Docker headaches!** 🎉
