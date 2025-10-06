from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
try:
    # Running from repo root: uvicorn backend.server:app
    from backend.routes.debug import router as debug_router  # type: ignore
    from backend.routes.test import router as test_router  # type: ignore
    from backend.routes.db import router as db_router  # type: ignore
except Exception:
    # Running from backend dir: uvicorn server:app
    from routes.debug import router as debug_router  # type: ignore
    from routes.test import router as test_router  # type: ignore
    from routes.db import router as db_router  # type: ignore
from routes.db import router as db_router


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
app.include_router(db_router)
app.include_router(db_router)

@app.post("/chat")
def chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    model = payload.get("model", "llama3.2")
    messages: List[Dict[str, str]] = payload.get("messages", [])
    provider = payload.get("provider")  # optional explicit provider
    use_database = bool(payload.get("use_database", True))

    # Optional DB augmentation
    if use_database:
        try:
            context_messages = _build_db_context_messages(messages)
            if context_messages:
                messages = context_messages + messages
        except Exception as e:
            messages = [{"role": "system", "content": f"Note: database retrieval failed: {str(e)}"}] + messages

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


# ---- Database helpers (optional) ----
def _safe_import_db():
    """Import SessionLocal and Product whether running from repo root or backend dir."""
    try:
        from database.database import SessionLocal, Product  # type: ignore
        return SessionLocal, Product
    except ImportError:
        import sys
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if base_dir not in sys.path:
            sys.path.append(base_dir)
        from database.database import SessionLocal, Product  # type: ignore
        return SessionLocal, Product


def _build_db_context_messages(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    print("\n=== DATABASE QUERY DEBUG ===")
    SessionLocal, Product = _safe_import_db()
    db = SessionLocal()
    try:
        user_texts = [m.get("content", "") for m in messages if m.get("role") == "user"]
        last_query = (user_texts[-1] if user_texts else "").lower()
        print(f"User's last query: '{last_query}'")
        
        if not last_query:
            print("No user query found")
            return []

        # Let the LLM decide what to query
        # First, ask it to generate SQL constraints
        import json
        
        # Use a simple prompt to get structured query parameters
        analysis_prompt = f"""Given this user question about a product database: "{last_query}"

The database has a 'products' table with columns: name, category, price, description, stock

Generate a JSON object with these optional filters:
- "category_keywords": list of category/product type keywords to search for (e.g., ["graphics card", "gpu"])
- "min_price": minimum price (number or null)
- "max_price": maximum price (number or null)  
- "search_terms": list of important words to search in name/description (or empty list for "show all")
- "limit": how many results to return (default 20, use 50 for "all items" requests)

Respond with ONLY valid JSON, no other text.

Example 1: "show me graphics cards under $200"
{{"category_keywords": ["graphics card", "gpu"], "max_price": 200, "limit": 20}}

Example 2: "what items cost more than $1000"
{{"min_price": 1000, "limit": 20}}

Example 3: "show me all items"
{{"limit": 50}}

Now analyze: "{last_query}" """

        # Get the AI's interpretation
        # Use Gemini for fast query analysis
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                resp = requests.post(
                    f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-exp:generateContent?key={api_key}",
                    json={
                        "contents": [{
                            "role": "user",
                            "parts": [{"text": analysis_prompt}]
                        }]
                    },
                    timeout=10
                )
                if resp.ok:
                    data = resp.json()
                    ai_response = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
                    # Extract JSON from response (might have markdown code blocks)
                    ai_response = ai_response.strip()
                    if "```json" in ai_response:
                        ai_response = ai_response.split("```json")[1].split("```")[0].strip()
                    elif "```" in ai_response:
                        ai_response = ai_response.split("```")[1].split("```")[0].strip()
                    
                    query_params = json.loads(ai_response)
                    print(f"AI interpreted query as: {query_params}")
                else:
                    print("AI query analysis failed, using fallback")
                    query_params = {"limit": 20}
            except Exception as e:
                print(f"Error in AI query analysis: {e}")
                query_params = {"limit": 20}
        else:
            # Fallback if no Gemini API
            query_params = {"limit": 20}

        # Build query from AI's interpretation
        from sqlalchemy import or_, and_
        
        filters = []
        
        # Category filter
        category_keywords = query_params.get("category_keywords", [])
        if category_keywords:
            category_filters = []
            for keyword in category_keywords:
                category_filters.append(Product.category.ilike(f"%{keyword}%"))
                category_filters.append(Product.name.ilike(f"%{keyword}%"))
            filters.append(or_(*category_filters))
        
        # Search terms
        search_terms = query_params.get("search_terms", [])
        if search_terms:
            search_filters = []
            for term in search_terms:
                search_filters.append(Product.name.ilike(f"%{term}%"))
                search_filters.append(Product.description.ilike(f"%{term}%"))
            filters.append(or_(*search_filters))
        
        # Price filters
        min_price = query_params.get("min_price")
        max_price = query_params.get("max_price")
        if min_price is not None:
            filters.append(Product.price >= min_price)
        if max_price is not None:
            filters.append(Product.price <= max_price)
        
        # Build query
        query = db.query(Product)
        if filters:
            query = query.filter(and_(*filters))
        
        # Order by price if filtered
        if min_price is not None:
            query = query.order_by(Product.price.asc())
        elif max_price is not None:
            query = query.order_by(Product.price.asc())
        
        limit = query_params.get("limit", 20)
        results = query.limit(limit).all()
        
        print(f"SQL Query: {query}")
        print(f"Query returned {len(results)} products (limit: {limit})")
        
        if not results:
            return [{
                "role": "system",
                "content": "DATABASE: No products found matching those criteria."
            }]
        
        # Build simple, clear context
        total_in_db = db.query(Product).count()
        
        context = f"DATABASE RESULTS: Found {len(results)} products (total in database: {total_in_db})\n\n"
        for p in results:
            context += f"- {p.name} | Category: {p.category} | Price: ${p.price} | Stock: {p.stock}\n"
        
        return [{
            "role": "system",
            "content": context
        }]
        
    finally:
        try:
            db.close()
        except Exception:
            pass


