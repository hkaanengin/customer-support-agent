from fastapi import APIRouter
import os

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/gemini-key")
def debug_key():
    api_key = os.getenv("GEMINI_API_KEY")
    return {"key_exists": bool(api_key), "key_length": len(api_key) if api_key else 0}


