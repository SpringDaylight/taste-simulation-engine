"""
Daily questions API endpoints
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from api.deps import get_current_user
from models import QuestionHistory
from repositories.user import UserRepository
from schemas import DailyQuestionAnswerRequest, DailyQuestionResponse, MessageResponse


router = APIRouter(prefix="/api/questions", tags=["questions"])

_QUESTIONS_CACHE: List[str] | None = None


def _load_questions() -> List[str]:
    global _QUESTIONS_CACHE
    if _QUESTIONS_CACHE is not None:
        return _QUESTIONS_CACHE

    questions_path = Path(__file__).resolve().parents[1] / "ml" / "data" / "daily_questions.json"
    if not questions_path.exists():
        raise RuntimeError("daily_questions.json not found")

    with questions_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise RuntimeError("daily_questions.json must be a list of strings")

    _QUESTIONS_CACHE = data
    return _QUESTIONS_CACHE


def _get_question(index: int) -> str:
    questions = _load_questions()
    if not questions:
        raise RuntimeError("daily_questions.json is empty")
    safe_index = index % len(questions)
    return questions[safe_index]


@router.get("/today", response_model=DailyQuestionResponse)
def get_today_question(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get today's question (must answer to move forward)."""
    user = UserRepository(db).get(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today_str = date.today().isoformat()
    if user.last_question_date == today_str:
        return DailyQuestionResponse(
            answered=True,
            message="오늘의 답변 완료!",
        )

    index = user.current_question_index or 0
    question = _get_question(index)
    return DailyQuestionResponse(
        answered=False,
        question=question,
    )


@router.post("/today", response_model=MessageResponse)
def submit_today_answer(
    payload: DailyQuestionAnswerRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit today's answer and grant rewards."""
    if not payload.answer or not payload.answer.strip():
        raise HTTPException(status_code=400, detail="Answer is required")

    user = UserRepository(db).get(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today_str = date.today().isoformat()
    if user.last_question_date == today_str:
        raise HTTPException(status_code=400, detail="Already answered today")

    index = user.current_question_index or 0
    question = _get_question(index)

    history = QuestionHistory(
        user_id=user.id,
        date=today_str,
        question=question,
        answer=payload.answer.strip(),
    )
    db.add(history)

    user.exp = (user.exp or 0) + 20
    user.popcorn = (user.popcorn or 0) + 5
    user.last_question_date = today_str

    questions = _load_questions()
    user.current_question_index = (index + 1) % len(questions)

    db.commit()
    return MessageResponse(message="오늘의 답변 완료!")
