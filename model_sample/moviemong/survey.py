
import json
import os
from typing import Dict, List, Any

class SurveyMixin:
    """
    사용자 초기 설문(Onboarding) 처리 로직
    """

    def get_survey_questions(self) -> List[Dict]:
        """설문 문항 로드"""
        try:
            path = os.path.join(os.path.dirname(__file__), 'survey_questions.json')
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 설문 로드 실패: {e}")
            return []

    def submit_survey(self, answers: Dict[str, Any]) -> Dict:
        """
        설문 응답 처리 및 취향 프로필 생성 (Generic Logic)
        
        Args:
            answers: { "q1_genre_like": ["Romance", "Comedy"], "q3_context": "solo", ... }
        """
        questions = self.get_survey_questions()
        profile = {
            "boost_tags": [],
            "penalty_tags": [],
            "importance_weights": {},
            "runtime_preference": {},
            "context": [],
            "origin_preference": [],
            "safety_filters": []
        }
        
        q_map = {q['id']: q for q in questions}

        for q_id, user_answer in answers.items():
            if q_id not in q_map:
                continue
            
            q_def = q_map[q_id]
            q_type = q_def.get('type')
            
            # 응답 값을 리스트로 통일하여 처리 (Single answer도 리스트로 취급)
            if not isinstance(user_answer, list):
                selected_values = [user_answer]
            else:
                selected_values = user_answer

            for val in selected_values:
                # 옵션 찾기 (label이 일치하거나, 내부적으로 value가 있다면 그것으로 매칭)
                # 프론트엔드가 'label' 텍스트를 그대로 보낼지, 별도 value를 보낼지에 따라 다르지만
                # 현재 구조상 label이 유니크하므로 label 매칭 시도
                
                # 1. Label 매칭
                opt = next((o for o in q_def['options'] if o['label'] == val), None)
                
                # 2. Value 매칭 (혹시 프론트가 value를 보낼 경우)
                if not opt:
                     opt = next((o for o in q_def['options'] if o.get('value') == val), None)

                if opt:
                    # 태그 부스트
                    if 'tags' in opt:
                        profile['boost_tags'].extend(opt['tags'])
                    
                    # 태그 페널티 (불호)
                    if 'negative_tags' in opt:
                        profile['penalty_tags'].extend(opt['negative_tags'])
                    
                    # 가중치 (Importance)
                    if 'weight' in opt:
                        for k, v in opt['weight'].items():
                            # 기존 가중치에 합산 or 최대값? 합산이 자연스러움
                            profile['importance_weights'][k] = profile['importance_weights'].get(k, 1.0) * v
                            
                    # 런타임 선호
                    if 'preference' in opt:
                        profile['runtime_preference'].update(opt['preference'])
                        
                    # 컨텍스트
                    if 'context' in opt:
                         profile['context'].append(opt['context'])
                         
                    # 안전 필터 (레벨 등)
                    if 'safety_level' in opt:
                        profile['safety_filters'].append({q_id: opt['safety_level']})

        # Save Logic
        # 중복 제거
        profile['boost_tags'] = list(set(profile['boost_tags']))
        profile['penalty_tags'] = list(set(profile['penalty_tags']))
        profile['context'] = list(set(profile['context']))

        self._save_survey_preference(profile)
        
        return {
            "success": True, 
            "message": "취향 분석 완료! 이제 딱 맞는 영화를 추천해드릴게요.",
            "profile_summary": {
                "liked_tags": len(profile['boost_tags']),
                "disliked_tags": len(profile['penalty_tags']),
                "weights": profile['importance_weights']
            }
        }

    def _save_survey_preference(self, profile: Dict):
        """user_preferences.json에 저장"""
        file_path = "user_preferences.json"
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            
            user_data = data.get(self.user_id, {})
            
            user_data.update({
                "boost_tags": profile['boost_tags'],
                "penalty_tags": profile['penalty_tags'],
                "importance_weights": profile['importance_weights'],
                "survey_metadata": {
                    "runtime": profile['runtime_preference'],
                    "context": profile['context'],
                    "safety": profile['safety_filters']
                },
                "last_updated": "survey"
            })
            
            data[self.user_id] = user_data
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 취향 저장 실패: {e}")
