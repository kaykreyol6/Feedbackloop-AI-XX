from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from pathlib import Path
import requests

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ClaudeRequest(BaseModel):
    candidate_id: int | None = None
    message: str


@router.post("/claude")
def proxy_claude(req: ClaudeRequest):
    """Proxy a chat request to Claude/Anthropic using the local system prompt.

    Reads `system_prompt.md` from the repo, appends the user's message, and
    forwards to the configured Claude API endpoint. The API key must be set in
    the `CLAUDE_API_KEY` environment variable (the app already loads `.env`).
    """
    key = os.getenv("CLAUDE_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="CLAUDE_API_KEY not configured")

    # load the system prompt if present
    spath = Path(__file__).resolve().parent / "system_prompt.md"
    system_prompt = spath.read_text(encoding="utf-8") if spath.exists() else ""

    prompt = f"{system_prompt}\n\nRecruiter: {req.message}\nAssistant:"

    payload = {
        "model": os.getenv("CLAUDE_MODEL", "claude-2"),
        "prompt": prompt,
        "max_tokens_to_sample": int(os.getenv("CLAUDE_MAX_TOKENS", "800")),
        "temperature": float(os.getenv("CLAUDE_TEMPERATURE", "0.2")),
    }

    url = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1/complete")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude request failed: {e}")

    if not r.ok:
        raise HTTPException(status_code=r.status_code, detail="Claude API error")

    data = r.json()

    # Extract text safely from common shapes (Anthropic responses vary by API version)
    text = data.get("completion") or data.get("output") or data.get("text") or ""
    if not text:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            text = choices[0].get("text", "")

    return {"text": text}
