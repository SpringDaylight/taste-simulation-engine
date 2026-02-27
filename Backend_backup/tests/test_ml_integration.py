"""
ML 통합 테스트 스크립트
Backend API의 ML 기능들이 정상 작동하는지 확인
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_a1_preference():
    """A-1: 사용자 취향 분석 테스트"""
    print("\n=== A-1: 사용자 취향 분석 ===")
    
    payload = {
        "text": "저는 슬프고 여운있는 영화를 좋아해요. 긴장감 넘치는 스릴러도 좋아합니다.",
        "dislikes": "무서운 거 싫어, 공포 영화 제외"
    }
    
    response = requests.post(f"{BASE_URL}/analyze/preference", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Emotion Scores (top 5):")
    top_emotions = sorted(result["emotion_scores"].items(), key=lambda x: x[1], reverse=True)[:5]
    for tag, score in top_emotions:
        print(f"  - {tag}: {score}")
    
    print(f"Dislike Tags: {result['dislike_tags']}")
    print(f"Boost Tags: {result['boost_tags']}")
    
    return result


def test_a2_movie_vector():
    """A-2: 영화 벡터화 테스트"""
    print("\n=== A-2: 영화 벡터화 ===")
    
    payload = {
        "movie_id": 123,
        "title": "인생은 아름다워",
        "overview": "2차 세계대전 중 유대인 수용소에 끌려간 아버지가 아들을 위해 게임을 만들어냅니다.",
        "genres": ["드라마", "코미디", "전쟁"],
        "keywords": ["전쟁", "가족", "희망", "유머"]
    }
    
    response = requests.post(f"{BASE_URL}/movie/vector", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Movie: {result['title']}")
    print(f"Emotion Scores (top 5):")
    top_emotions = sorted(result["emotion_scores"].items(), key=lambda x: x[1], reverse=True)[:5]
    for tag, score in top_emotions:
        print(f"  - {tag}: {score}")
    
    print(f"Embedding Text: {result['embedding_text'][:100]}...")
    
    return result


def test_a3_prediction(user_profile, movie_profile):
    """A-3: 만족 확률 계산 테스트"""
    print("\n=== A-3: 만족 확률 계산 ===")
    
    payload = {
        "user_profile": user_profile,
        "movie_profile": movie_profile,
        "dislike_tags": user_profile.get("dislike_tags", []),
        "boost_tags": user_profile.get("boost_tags", [])
    }
    
    response = requests.post(f"{BASE_URL}/predict/satisfaction", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Movie: {result['title']}")
    print(f"Match Rate: {result['match_rate']}%")
    print(f"Probability: {result['probability']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Breakdown:")
    print(f"  - Emotion Similarity: {result['breakdown']['emotion_similarity']}")
    print(f"  - Narrative Similarity: {result['breakdown']['narrative_similarity']}")
    print(f"  - Ending Similarity: {result['breakdown']['ending_similarity']}")
    print(f"  - Boost Score: {result['breakdown']['boost_score']}")
    print(f"  - Dislike Penalty: {result['breakdown']['dislike_penalty']}")
    print(f"  - Top Factors: {', '.join(result['breakdown']['top_factors'])}")
    
    return result


def test_a4_explanation(prediction_result, user_profile):
    """A-4: 설명 생성 테스트"""
    print("\n=== A-4: 설명 생성 ===")
    
    payload = {
        "movie_title": prediction_result["title"],
        "match_rate": prediction_result["match_rate"],
        "probability": prediction_result["probability"],
        "breakdown": prediction_result["breakdown"],
        "user_liked_tags": user_profile.get("boost_tags", []),
        "user_disliked_tags": user_profile.get("dislike_tags", [])
    }
    
    response = requests.post(f"{BASE_URL}/explain/prediction", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Movie: {result['movie_title']}")
    print(f"Match Rate: {result['match_rate']}%")
    print(f"\nExplanation:")
    print(f"  {result['explanation']}")
    print(f"\nKey Factors:")
    for factor in result['key_factors']:
        print(f"  - {factor['label']}: {factor['score']}")
    
    return result


def test_a5_emotional_search():
    """A-5: 감성 검색 테스트"""
    print("\n=== A-5: 감성 검색 ===")
    
    payload = {
        "text": "우울한데 너무 무겁지 않은 영화",
        "genres": ["드라마"],
        "year_from": 2010,
        "year_to": 2024
    }
    
    response = requests.post(f"{BASE_URL}/search/emotional", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Intent: {result['intent']}")
    print(f"Expanded Query (top 5 emotions):")
    top_emotions = sorted(result["expanded_query"]["emotion_scores"].items(), key=lambda x: x[1], reverse=True)[:5]
    for tag, score in top_emotions:
        print(f"  - {tag}: {score}")
    
    return result


def test_a6_group_simulation(user_profile1, user_profile2, movie_profile):
    """A-6: 그룹 추천 테스트"""
    print("\n=== A-6: 그룹 추천 ===")
    
    payload = {
        "members": [
            {
                "user_id": "user1",
                "profile": user_profile1,
                "dislikes": user_profile1.get("dislike_tags", []),
                "likes": user_profile1.get("boost_tags", [])
            },
            {
                "user_id": "user2",
                "profile": user_profile2,
                "dislikes": user_profile2.get("dislike_tags", []),
                "likes": user_profile2.get("boost_tags", [])
            }
        ],
        "movie_profile": movie_profile,
        "strategy": "least_misery"
    }
    
    response = requests.post(f"{BASE_URL}/group/simulate", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Group Score: {result['group_score'] * 100:.1f}%")
    print(f"Strategy: {result['strategy']}")
    print(f"\nMembers:")
    for member in result['members']:
        print(f"  - {member['user_id']}: {member['level']} ({member['probability'] * 100:.1f}%)")
    
    print(f"\nComment: {result['comment']}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"\nStatistics:")
    print(f"  - Min: {result['statistics']['min_satisfaction']}")
    print(f"  - Max: {result['statistics']['max_satisfaction']}")
    print(f"  - Avg: {result['statistics']['avg_satisfaction']}")
    print(f"  - Variance: {result['statistics']['variance']}")
    
    return result


def test_a7_taste_map():
    """A-7: 취향 지도 테스트"""
    print("\n=== A-7: 취향 지도 ===")
    
    payload = {
        "user_text": "감동적이고 따뜻한 영화를 좋아합니다",
        "k": 8
    }
    
    response = requests.post(f"{BASE_URL}/map/taste", json=payload)
    result = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Clusters:")
    for cluster in result['clusters'][:5]:
        print(f"  - {cluster['label']} (count: {cluster['count']})")
    
    print(f"\nUser Location:")
    print(f"  - Position: ({result['user_location']['x']}, {result['user_location']['y']})")
    print(f"  - Nearest Cluster: {result['user_location']['cluster_label']}")
    
    return result


def main():
    """전체 파이프라인 테스트"""
    print("="*60)
    print("ML Integration Test")
    print("="*60)
    
    try:
        # 1. 사용자 취향 분석
        user_profile1 = test_a1_preference()
        
        # 2. 두 번째 사용자 (그룹 테스트용)
        user_profile2 = requests.post(f"{BASE_URL}/analyze/preference", json={
            "text": "밝고 웃긴 영화를 좋아해요. 우울한 건 싫어요.",
            "dislikes": ""
        }).json()
        
        # 3. 영화 벡터화
        movie_profile = test_a2_movie_vector()
        
        # 4. 만족 확률 계산
        prediction = test_a3_prediction(user_profile1, movie_profile)
        
        # 5. 설명 생성
        explanation = test_a4_explanation(prediction, user_profile1)
        
        # 6. 감성 검색
        search_result = test_a5_emotional_search()
        
        # 7. 그룹 추천
        group_result = test_a6_group_simulation(user_profile1, user_profile2, movie_profile)
        
        # 8. 취향 지도
        taste_map = test_a7_taste_map()
        
        print("\n" + "="*60)
        print("✅ All tests completed successfully!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to server")
        print("Please make sure the server is running:")
        print("  uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
