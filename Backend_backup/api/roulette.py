"""
Roulette API endpoints
"""
from __future__ import annotations

import random
from datetime import date
from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from api.deps import get_current_user
from models import RouletteReward
from repositories.user import UserRepository
from schemas import RouletteSpinRequest, RouletteSpinResponse, RouletteStatusResponse, RouletteConfigResponse, RouletteConfigItem


router = APIRouter(prefix="/api/roulette", tags=["roulette"])

# (item, weight, popcorn_gain, exp_gain)
ROULETTE_ITEMS: List[Tuple[str, int, int, int]] = [
    ("🍿", 50, 3, 15),
    ("🌭", 25, 6, 20),
    ("🍟", 15, 10, 30),
    ("🦑", 9, 15, 50),
    ("🍗", 1, 20, 100),
]


@router.get("/config", response_model=RouletteConfigResponse)
def get_roulette_config():
    items = [
        RouletteConfigItem(
            label=item,
            probability=f"{weight}%",
            popcorn_gain=popcorn_gain,
            exp_gain=exp_gain,
        )
        for item, weight, popcorn_gain, exp_gain in ROULETTE_ITEMS
    ]
    return RouletteConfigResponse(items=items)


def _pick_reward() -> Tuple[str, int, int]:
    total = sum(weight for _, weight, _, _ in ROULETTE_ITEMS)
    pick = random.randint(1, total)
    cursor = 0
    for item, weight, popcorn_gain, exp_gain in ROULETTE_ITEMS:
        cursor += weight
        if pick <= cursor:
            return item, popcorn_gain, exp_gain
    item, _, popcorn_gain, exp_gain = ROULETTE_ITEMS[-1]
    return item, popcorn_gain, exp_gain


@router.get("/status", response_model=RouletteStatusResponse)
def get_roulette_status(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserRepository(db).get(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # NOTE: 테스트용 - 하루 1회 제한 비활성화
    # today_str = date.today().isoformat()
    # if user.last_roulette_date == today_str:
    #     return RouletteStatusResponse(can_spin=False, next_available_at=today_str)
    return RouletteStatusResponse(can_spin=True)


@router.post("/spin", response_model=RouletteSpinResponse)
def spin_roulette(
    payload: RouletteSpinRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserRepository(db).get(current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # NOTE: 테스트용 - 하루 1회 제한 비활성화
    today_str = date.today().isoformat()
    # if user.last_roulette_date == today_str:
    #     raise HTTPException(status_code=400, detail="Already claimed today")

    item, popcorn_gain, exp_gain = _pick_reward()

    reward = RouletteReward(
        user_id=user.id,
        item=item,
        popcorn_gain=popcorn_gain,
        exp_gain=exp_gain,
    )
    db.add(reward)

    user.popcorn = (user.popcorn or 0) + popcorn_gain
    user.exp = (user.exp or 0) + exp_gain
    # NOTE: 테스트용 - 하루 1회 제한 비활성화
    # user.last_roulette_date = today_str

    db.commit()

    return RouletteSpinResponse(
        item=item,
        popcorn_gain=popcorn_gain,
        exp_gain=exp_gain,
        total_popcorn=user.popcorn,
        total_exp=user.exp,
    )
