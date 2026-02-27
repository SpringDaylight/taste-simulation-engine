"""
LLM Chat API for movie recommendation experimentation
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from llm_lab.client import LLMClient
from llm_lab.async_client import AsyncLLMClient
from llm_lab.prompts import list_prompts
from llm_lab.recommender import LLMRecommender

router = APIRouter(prefix="/api/llm", tags=["llm-chat"])

# LLM 추천기 초기화 (전역)
llm_recommender = LLMRecommender()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000


class ChatResponse(BaseModel):
    response: str
    usage: Optional[dict] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with LLM for movie recommendation experimentation
    """
    try:
        # Use AsyncLLMClient for non-blocking LLM operations
        client = AsyncLLMClient()
        
        # Convert Pydantic models to dicts
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        # Generate response with await
        result = await client.generate(
            messages=messages,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return ChatResponse(
            response=result["response"],
            usage=result["usage"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM chat error: {str(e)}")


@router.get("/system-prompts")
async def get_system_prompts():
    """
    Get predefined system prompts for movie recommendation
    """
    prompts = list_prompts()
    return {
        "prompts": [
            {"name": p["name"], "prompt": p["prompt"]}
            for p in prompts
        ]
    }

