## A-2 영화 특성 추출 및 벡터화

import argparse
import hashlib
import json
import os
from typing import Dict, List
import boto3
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

LLM_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 정서 태그 taxonomy(템플릿) 생성 - LLM으로 정서 태그 추출 시 사용
def load_taxonomy(path: str = 'emotion_tag.json'):
    return load_json(path)

# 정서 태그 값으로 더미 값 입력(fallback 용도로 유지)
def stable_score(text: str, tag: str) -> float:
    h = hashlib.sha256((text + '||' + tag).encode('utf-8')).hexdigest()
    v = int(h[:8], 16) / 0xFFFFFFFF
    return round(v, 3)

# AWS Bedrock 클라이언트 초기화
def get_bedrock_client():
    """AWS Bedrock Runtime 클라이언트를 생성합니다."""
    try:
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'ap-northeast-2'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        return bedrock_runtime
    except Exception as e:
        print(f"Bedrock 클라이언트 초기화 실패: {e}")
        return None

# LLM 활용 실제 분석 로직
def analyze_with_llm(text: str, taxonomy: Dict, bedrock_client=None) -> Dict:
    """
    AWS Bedrock을 사용하여 영화 텍스트를 분석하고 정서 태그를 추출합니다.
    """
    if bedrock_client is None:
        print("Bedrock 클라이언트를 사용할 수 없어 fallback 모드로 실행합니다.")
        return None
    
    # 1. 프롬프트 생성 (안전한 접근)
    emotion_tags = taxonomy.get('emotion', {}).get('tags', [])
    story_tags = taxonomy.get('story_flow', {}).get('tags', [])
    direction_tags = taxonomy.get('direction_mood', {}).get('tags', [])
    char_tags = taxonomy.get('character_relationship', {}).get('tags', [])

    prompt = f"""다음 영화 정보를 분석하여 정서 태그를 추출해주세요.

영화 정보:
{text}

사용 가능한 태그 분류:

감정 (emotion):
{', '.join(emotion_tags)}

스토리 흐름 (story_flow):
{', '.join(story_tags)}

연출/분위기 (direction_mood):
{', '.join(direction_tags)}

캐릭터/관계 (character_relationship):
{', '.join(char_tags)}

각 카테고리에서 영화에 적합한 태그를 선택하고, 각 태그에 대해 0.0에서 1.0 사이의 점수(확신도/강도)를 부여해주세요.
다음 JSON 형식으로 응답해주세요:

{{
  "emotion": {{
    "scores": {{ "태그명": 0.8, "태그명2": 0.6, ... }},
    "intensity": "high|medium|low",
    "dominant_emotion": "주요 감정"
  }},
  "story_flow": {{
    "scores": {{ "태그명": 0.8, ... }},
    "pacing": "fast|medium|slow",
    "structure": "구조 설명"
  }},
  "direction_mood": {{
    "scores": {{ "태그명": 0.8, ... }},
    "visual_style": "시각 스타일",
    "atmosphere": "분위기"
  }},
  "character_relationship": {{
    "scores": {{ "태그명": 0.8, ... }},
    "focus_type": "individual|relationship|ensemble",
    "main_relationship": "주요 관계"
  }},
  "ending_preference": {{
    "happy": 0.0-1.0,
    "open": 0.0-1.0,
    "bittersweet": 0.0-1.0
  }}
}}

반드시 JSON 형식으로만 응답해주세요. JSON 외의 다른 텍스트는 포함하지 마세요."""

    # 2. AWS Bedrock API 호출
    try:
        # 모델 ID는 상수로 관리
        model_id = LLM_MODEL
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000, # Cost Efficiency: 2000 -> 1000
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3
        }
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        # Claude 응답에서 텍스트 추출
        if 'content' in response_body and len(response_body['content']) > 0:
            content_text = response_body['content'][0]['text']
            
            # C. JSON 파싱 정교화 (Robust Parsing)
            llm_result = None
            try:
                # 1차 시도: 전체 텍스트 파싱
                llm_result = json.loads(content_text)
            except json.JSONDecodeError:
                # 2차 시도: 가장 바깥쪽 중괄호 추출 (Greedy Regex 대신 find/rfind 사용)
                start_idx = content_text.find('{')
                end_idx = content_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    try:
                        json_str = content_text[start_idx : end_idx + 1]
                        llm_result = json.loads(json_str)
                    except json.JSONDecodeError:
                        print(f"JSON 재파싱 실패: {content_text[:50]}...")
                else:
                    print("JSON 구조를 찾을 수 없습니다.")

            if llm_result is None:
                return None

            # A. 점수 보정 헬퍼 (Data Validation)
            def _validate_score(val) -> float:
                try:
                    s = float(val)
                    return max(0.0, min(1.0, s)) # Clamp [0.0, 1.0]
                except (ValueError, TypeError):
                    return 0.0

            result = {
                'emotion': {},
                'story_flow': {},
                'direction_mood': {},
                'character_relationship': {},
                'ending_preference': {}
            }

            # B. Taxonomy 동기화 (Tag Consistency) & A. 점수 적용
            categories = {
                'emotion': emotion_tags,
                'story_flow': story_tags,
                'direction_mood': direction_tags,
                'character_relationship': char_tags
            }

            for cat, valid_tags in categories.items():
                scores = llm_result.get(cat, {}).get('scores', {})
                for tag, score in scores.items():
                    # 유효한 태그만 필터링
                    if tag in valid_tags:
                        result[cat][tag] = _validate_score(score)
            
            # Ending preference 처리
            ending_pref = llm_result.get('ending_preference', {})
            for key in ['happy', 'open', 'bittersweet']:
                result['ending_preference'][key] = _validate_score(ending_pref.get(key, 0.5))

            return result
            
        else:
            print("LLM 응답에서 콘텐츠를 찾을 수 없습니다.")
            return None
            
    except Exception as e:
        print(f"LLM 분석 중 오류 발생: {e}")
        return None


def score_tags(text: str, tags: List[str]) -> Dict[str, float]:
    return {tag: stable_score(text, tag) for tag in tags}

# 텍스트 추출
def movie_text(movie: Dict) -> str:
    parts = []
    for key in ['title', 'overview']:
        if movie.get(key):
            parts.append(str(movie[key]))
    for key in ['keywords', 'genres', 'directors', 'cast']:
        val = movie.get(key)
        if isinstance(val, list):
            parts.extend([str(v) for v in val])
    return ' '.join(parts)

# 영화 데이터셋 설정(정서 태그 추가)
def build_profile(movie: Dict, taxonomy: Dict, bedrock_client=None) -> Dict:
    text = movie_text(movie)
    
    # LLM을 사용하여 정서 태그 분석
    llm_analysis = analyze_with_llm(text, taxonomy, bedrock_client)
    
    # LLM 분석 성공 시
    if llm_analysis is not None:
        profile = {
            'movie_id': movie.get('id'),
            'title': movie.get('title'),
            'emotion_scores': llm_analysis['emotion'],
            'narrative_traits': llm_analysis['story_flow'],
            'direction_mood': llm_analysis['direction_mood'],
            'character_relationship': llm_analysis['character_relationship'],
            'ending_preference': llm_analysis['ending_preference'],
        }
    else:
        # Fallback: 기존 stable_score 사용
        print(f"LLM 분석 실패, fallback 모드로 {movie.get('title')} 처리")
        
        # 안전한 접근
        emotion_tags = taxonomy.get('emotion', {}).get('tags', [])
        narrative_tags = taxonomy.get('story_flow', {}).get('tags', [])
        direction_tags = taxonomy.get('direction_mood', {}).get('tags', [])
        char_tags = taxonomy.get('character_relationship', {}).get('tags', [])
        
        profile = {
            'movie_id': movie.get('id'),
            'title': movie.get('title'),
            'emotion_scores': score_tags(text, emotion_tags),
            'narrative_traits': score_tags(text, narrative_tags),
            # 스키마 통일 (누락된 필드 추가)
            'direction_mood': score_tags(text, direction_tags),
            'character_relationship': score_tags(text, char_tags),
            'ending_preference': {
                'happy': stable_score(text, 'ending_happy'),
                'open': stable_score(text, 'ending_open'),
                'bittersweet': stable_score(text, 'ending_bittersweet'),
            },
        }
    
    # 임베딩 텍스트 생성 및 벡터 추가
    emb_txt = embedding_text(profile)
    vector = embedding_vector(emb_txt, bedrock_client)
    profile['embedding'] = vector
    
    # 디버깅/확인용으로 임베딩 텍스트도 포함
    profile['embedding_text'] = emb_txt
    
    return profile

# 임베딩 벡터 생성 규칙 설정
def embedding_text(profile: Dict) -> str:
    """
    임베딩 생성을 위한 텍스트를 구성합니다.
    영화 제목, 주요 감정 태그 등을 조합하여 검색에 최적화된 텍스트를 만듭니다.
    """
    text_parts = [f"Title: {profile['title']}"]
    
    # 상위 감정 태그 3개 추출
    if 'emotion_scores' in profile:
        # 점수가 높은 순으로 정렬
        sorted_emotions = sorted(profile['emotion_scores'].items(), key=lambda x: x[1], reverse=True)[:3]
        emotions_str = ", ".join([tag for tag, score in sorted_emotions])
        if emotions_str:
            text_parts.append(f"Emotions: {emotions_str}")
            
    # 상위 서사 태그 3개 추출
    if 'narrative_traits' in profile:
        sorted_narrative = sorted(profile['narrative_traits'].items(), key=lambda x: x[1], reverse=True)[:3]
        narrative_str = ", ".join([tag for tag, score in sorted_narrative])
        if narrative_str:
            text_parts.append(f"Narrative: {narrative_str}")
            
    return ". ".join(text_parts)

# 임베딩 벡터 생성 및 OpenSearch로 저장 (여기서는 벡터 생성만 수행)
def embedding_vector(text: str, bedrock_client=None) -> List[float]:
    """
    AWS Bedrock Titan Embedding v2 모델을 사용하여 텍스트 임베딩을 생성합니다.
    """
    # 인자로 받은 클라이언트 사용 (없으면 실패)
    if bedrock_client is None:
        return []
        
    try:
        model_id = EMBEDDING_MODEL
        body = json.dumps({
            "inputText": text,
            "dimensions": 1024,
            "normalize": True
        })
        
        response = bedrock_client.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        embedding = response_body.get('embedding')
        return embedding
        
    except Exception as e:
        print(f"임베딩 생성 중 오류 발생: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='A-1 Emotion Taxonomy Scoring (Stable Score + Titan Embedding)')
    parser.add_argument('--movies', default='../movies_small.json')
    parser.add_argument('--taxonomy', default='emotion_tag.json')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--movie-id', type=int, default=None)
    parser.add_argument('--output', default=None)
    parser.add_argument('--pretty', action='store_true')
    args = parser.parse_args()

    # 경로 처리
    movies_path = args.movies
    if not os.path.exists(movies_path):
        # 현재 폴더에 없으면 상위 폴더 확인 (model_sample 폴더에서 실행 시)
        if os.path.exists(os.path.join('..', movies_path)):
            movies_path = os.path.join('..', movies_path)
        # 혹은 그냥 파일명만 있는 경우도 고려
        elif os.path.exists(os.path.basename(movies_path)):
           movies_path = os.path.basename(movies_path)

    taxonomy = load_taxonomy(args.taxonomy)
    try:
        movies = load_json(movies_path)
    except FileNotFoundError:
        print(f"Error: Movie file not found at {movies_path}")
        return
    
    # Bedrock 클라이언트 생성 (Client 재사용)
    bedrock_client = get_bedrock_client()

    if args.movie_id is not None:
        movies = [m for m in movies if m.get('id') == args.movie_id]

    if args.limit is not None:
        movies = movies[: args.limit]

    # 프로필 생성 (bedrock_client 전달)
    profiles = []
    print(f"Processing {len(movies)} movies...")
    for i, m in enumerate(movies):
        print(f"[{i+1}/{len(movies)}] Processing: {m.get('title')}")
        profiles.append(build_profile(m, taxonomy, bedrock_client))

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(profiles, f, ensure_ascii=False, indent=2 if args.pretty else None)
        print(f"Saved results to {args.output}")
    else:
        print(json.dumps(profiles, ensure_ascii=False, indent=2 if args.pretty else None))


if __name__ == '__main__':
    main()