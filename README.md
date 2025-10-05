# customer-support-agent

## Local Llama Chatbot

This repo includes a minimal FastAPI backend that proxies to your local Ollama chat API and a simple HTML/JS frontend to chat with your `llama3.2` model. It can also call Gemini if you provide an API key.

### Prereqs
- Python 3.10+
- Ollama running locally with model pulled (e.g., `llama3.2`)
- Node not required (static frontend)

### Start Ollama (if not already)
Ensure Ollama is running and the model is available:

```bash
ollama pull llama3.2
ollama serve
```

### Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

The backend exposes:
- `GET /health` health check
- `POST /chat` with body:

```json
{
  "model": "llama3.2",
  "messages": [{"role": "user", "content": "Hello"}]
}
```

### Frontend
Open `frontend/index.html` in your browser (double-click or serve statically). It will call the backend at `http://127.0.0.1:8000/chat`.
Or run "python3 -m http.server 5173 --directory frontend".
### Use Gemini instead of Ollama (optional)

Set your key and choose a Gemini model (e.g., `gemini-1.5-flash`):

Option A (recommended): create a `.env` file in repo root:

```
GEMINI_API_KEY=YOUR_KEY_HERE
```

Option B: export in your shell for the session:

```bash
export GEMINI_API_KEY=YOUR_KEY_HERE
```

In the UI, set Model to `gemini-1.5-flash` (or include `provider: "gemini"` in body).

The backend will route `/chat` to Gemini when the model starts with `gemini` or when `provider: "gemini"` is set in the request.
### Notes
- Conversation history is kept in the page state; refreshing clears it.
- To change the model, update the field in the header.

Gemini aPI: AIzaSyCUy0JLfBsGP8a5eFoZKOTKK6YlIpjBMHA