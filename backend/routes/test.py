from fastapi import APIRouter
import os
import requests

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/list-gemini-models")
def list_gemini_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "No API key found"}

    url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
    resp = requests.get(url)
    if resp.ok:
        data = resp.json()
        models = []
        for model in data.get("models", []):
            name = model.get("name", "")
            if "generateContent" in model.get("supportedGenerationMethods", []):
                models.append({
                    "name": name,
                    "displayName": model.get("displayName", ""),
                })
        return {"models": models}
    else:
        return {"error": resp.text, "status": resp.status_code}


