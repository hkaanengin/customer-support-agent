from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
from routes.debug import router as debug_router
from routes.test import router as test_router


OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1"


load_dotenv()

app = FastAPI(title="Local Llama Chatbot Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(debug_router)
app.include_router(test_router)

@app.post("/chat")
def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    model = payload.get("model", "llama3.2")
    messages: List[Dict[str, str]] = payload.get("messages", [])
    provider = payload.get("provider")  # optional explicit provider

    # Route based on provider or model name
    if provider == "gemini" or model.lower().startswith("gemini"):
        return _chat_with_gemini(model=model, messages=messages)
    else:
        return _chat_with_ollama(model=model, messages=messages)


def _chat_with_ollama(model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    ollama_payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    response = requests.post(OLLAMA_CHAT_URL, json=ollama_payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return {
        "message": data.get("message", {}),
        "done": data.get("done", True),
        "total_duration": data.get("total_duration"),
        "model": data.get("model", model),
        "provider": "ollama",
    }


def _chat_with_gemini(model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")

    # Convert OpenAI-style messages to Gemini contents
    contents: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        text = m.get("content", "")
        if not text:
            continue
        # Gemini expects roles: user|model; map assistant->model
        gemini_role = "model" if role == "assistant" else "user"
        contents.append({
            "role": gemini_role,
            "parts": [{"text": text}],
        })

    # Default to a fast, efficient model if not specified
    if not model or not model.startswith("gemini"):
        model = "gemini-2.5-flash"
    
    # IMPORTANT: Remove "models/" prefix if it exists, we'll add it in the URL
    model_name = model.replace("models/", "")
    
    # Build the URL with the v1 API
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
    
    payload = {"contents": contents}
    
    try:
        resp = requests.post(url, json=payload, timeout=60)
        
        if not resp.ok:
            print(f"Gemini API Error: Status {resp.status_code}")
            print(f"URL: {url.replace(api_key, '***')}")
            print(f"Response: {resp.text}")
            raise HTTPException(
                status_code=resp.status_code, 
                detail=f"Gemini API error: {resp.text}"
            )
        
        data = resp.json()
        
        # Extract first candidate text
        content_text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                content_text = parts[0]["text"]
        
        return {
            "message": {"role": "assistant", "content": content_text},
            "done": True,
            "model": model_name,
            "provider": "gemini",
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}



@app.get("/models")
def list_models() -> Dict[str, Any]:
    """Return available models for the frontend dropdown."""
    models = [
        {
            "provider": "ollama",
            "id": "llama3.2",
            "label": "Llama 3.2 (Ollama - Local)",
        },
        {
            "provider": "gemini",
            "id": "gemini-2.5-flash",
            "label": "Gemini 2.5 Flash (Fastest)",
        },
        {
            "provider": "gemini",
            "id": "gemini-2.5-pro",
            "label": "Gemini 2.5 Pro (Most Capable)",
        },
        {
            "provider": "gemini",
            "id": "gemini-2.0-flash",
            "label": "Gemini 2.0 Flash",
        }
    ]
    return {"models": models}

