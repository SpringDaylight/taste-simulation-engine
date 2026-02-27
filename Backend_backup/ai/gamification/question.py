
import os
import json
from typing import List, Dict
from datetime import date
# from database import db
from models import QuestionHistory

START_QUESTIONS_FILE = "start_questions.json"
DAILY_QUESTIONS_FILE = "daily_questions.json"
REVIEW_REWARD_TRACKING_QUESTION = "__review_reward_tracking__"

class DailyQuestionMixin:

    def _load_questions(self) -> List[str]:
        """질문 리스트 로드"""
        # moviemong 패키지의 상위 폴더(model_sample)의 상위 폴더(루트) -> data 폴더 접근
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, 'data', DAILY_QUESTIONS_FILE)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 질문 파일 로드 실패: {e}")
                
        return ["오늘의 영화 추천은 무엇인가요?"] # 기본 질문

    def get_daily_question(self) -> Dict:
        """오늘의 질문 가져오기"""
        user_data = self.get_user_data()
        today = date.today().isoformat()
        

        questions = self._load_questions()
        idx = user_data.get("current_question_index", 0)

        # 이미 오늘 답변했다면, 방금 답변한 질문(이전 인덱스)을 보여줌
        if user_data.get("last_question_date") == today and idx > 0:
            idx = idx - 1
        
        result = {
            "question_id": idx,
            "question": "",
            "can_answer": False,
            "message": ""
        }

        if idx >= len(questions):
            result["message"] = "모든 질문을 완료했습니다!"
            return result
            
        result["question"] = questions[idx]
        
        if user_data.get("last_question_date") == today:
            result["can_answer"] = False
            result["message"] = "오늘의 질문에 이미 답변하셨습니다."
        else:
            result["can_answer"] = True
            result["message"] = "답변을 기다리고 있어요!"
            
        return result

    def answer_daily_question(self, answer: str) -> Dict:
        """데일리 질문 답변 및 보상"""
        today = date.today().isoformat()
        user = self._get_user_model()
        
        if user.last_question_date == today:
            return {"success": False, "message": "오늘은 이미 답변했습니다."}

        current_idx = user.current_question_index
        user.current_question_index = current_idx + 1
        
        reward_exp = 20
        reward_popcorn = 5
        
        # 보상 지급 (Core 메소드 활용 - 내부적으로 commit 호출)
        self.add_exp(reward_exp)
        self.add_popcorn(reward_popcorn)
        
        # 마지막 답변 날짜 업데이트
        user.last_question_date = today
        
        # 히스토리 저장
        question_text = self._load_questions()[current_idx] if current_idx < len(self._load_questions()) else "Unknown Question"
        
        history_item = QuestionHistory(
            user_id=user.id,
            date=today,
            question=question_text,
            answer=answer
        )
        self.db.add(history_item)
        self.db.commit()
        
        return {
            "success": True,
            "message": "답변이 기록되었습니다!",
            "reward": {"exp": reward_exp, "popcorn": reward_popcorn}
        }

    def get_question_history(self) -> List[Dict]:
        """질문/답변 히스토리 반환"""
        # Legacy: return all history entries without filtering
        # return self.get_user_data().get("question_history", [])
        history = self.get_user_data().get("question_history", [])
        return [
            item for item in history
            if item.get("question") != REVIEW_REWARD_TRACKING_QUESTION
        ]
