
import os
import json
from datetime import date
from typing import List, Dict

DAILY_QUESTIONS_FILE = "daily_questions.json"

class DailyQuestionMixin:
    def _load_questions(self) -> List[str]:
        """질문 리스트 로드"""
        # 현재 작업 디렉토리 기준
        if os.path.exists(DAILY_QUESTIONS_FILE):
            try:
                with open(DAILY_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 질문 파일 로드 실패: {e}")
        # 상위 디렉토리 체크 (패키지 내부에서 실행 시)
        elif os.path.exists(os.path.join("..", DAILY_QUESTIONS_FILE)):
            try:
                with open(os.path.join("..", DAILY_QUESTIONS_FILE), 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
                
        return ["오늘의 영화 추천은 무엇인가요?"] # 기본 질문

    def get_daily_question(self) -> Dict:
        """오늘의 질문 가져오기"""
        user_data = self.get_user_data()
        today = date.today().isoformat()
        
        questions = self._load_questions()
        idx = user_data.get("current_question_index", 0)
        
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
        user_data = self.get_user_data()
        
        if user_data.get("last_question_date") == today:
            return {"success": False, "message": "오늘은 이미 답변했습니다."}

        current_idx = user_data.get("current_question_index", 0)
        self._update_user_data("current_question_index", current_idx + 1)
        
        reward_exp = 20
        reward_popcorn = 5
        
        self.add_exp(reward_exp)
        self.add_popcorn(reward_popcorn)
        self._update_user_data("last_question_date", today)
        
        # 히스토리 저장
        history_item = {
            "date": today,
            "question": self._load_questions()[current_idx],
            "answer": answer
        }
        user_data.setdefault("question_history", []).append(history_item)
        self._save_data()
        
        return {
            "success": True,
            "message": "답변이 기록되었습니다!",
            "reward": {"exp": reward_exp, "popcorn": reward_popcorn}
        }

    def get_question_history(self) -> List[Dict]:
        """질문/답변 히스토리 반환"""
        return self.get_user_data().get("question_history", [])
