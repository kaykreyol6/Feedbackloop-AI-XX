from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path
from anthropic import Anthropic, AnthropicError

router = APIRouter(prefix="/api/ai", tags=["ai"])

_client: Optional[Anthropic] = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        key = os.getenv("CLAUDE_API_KEY")
        if not key:
            raise HTTPException(status_code=500, detail="CLAUDE_API_KEY not configured")
        _client = Anthropic(api_key=key)
    return _client


class ClaudeRequest(BaseModel):
    candidate_id: Optional[int] = None
    message: str


@router.post("/claude")
def proxy_claude(req: ClaudeRequest):
    """Proxy a chat request to Claude using the local system prompt.

    Reads `system_prompt.md` from the repo and forwards the user's message
    via the Messages API. The API key must be set in the `CLAUDE_API_KEY`
    environment variable (the app already loads `.env`).
    """
    spath = Path(__file__).resolve().parent / "system_prompt.md"
    system_prompt = spath.read_text(encoding="utf-8") if spath.exists() else ""

    try:
        response = _get_client().messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-opus-4-8"),
            max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", "800")),
            system=system_prompt,
            messages=[{"role": "user", "content": req.message}],
        )
    except AnthropicError as e:
        raise HTTPException(status_code=502, detail=f"Claude request failed: {e}")

    text = next((b.text for b in response.content if b.type == "text"), "")
    return {"text": text}
