"""
Test script for MovieVector repository and API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_process_and_save_vector():
    """Test processing movie vector and saving to database"""
    print("\n=== Test 1: Process and Save Movie Vector ===")
    
    payload = {
        "movie_id": 12345,
        "title": "인셉션",
        "overview": "꿈 속의 꿈을 통해 생각을 훔치는 특수 요원의 이야기",
        "synopsis": "긴장감 넘치고 복잡한 서사 구조를 가진 SF 스릴러",
        "genres": ["SF", "스릴러", "액션"],
        "keywords": ["꿈", "잠재의식", "복잡한", "긴장"],
        "directors": ["크리스토퍼 놀란"],
        "cast": ["레오나르도 디카프리오", "마리온 코티야르"],
        "save_to_db": True
    }
    
    response = requests.post(f"{BASE_URL}/movie/vector", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Saved: {result.get('saved', False)}")
    print(f"Vector ID: {result.get('vector_id', 'N/A')}")
    print(f"Top emotion scores: {list(result.get('emotion_scores', {}).items())[:3]}")
    
    return response.status_code == 200


def test_get_movie_vector():
    """Test retrieving saved movie vector"""
    print("\n=== Test 2: Get Movie Vector ===")
    
    movie_id = 12345
    response = requests.get(f"{BASE_URL}/movies/{movie_id}/vector")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Movie ID: {result.get('movie_id')}")
        print(f"Emotion scores count: {len(result.get('emotion_scores', {}))}")
        print(f"Updated at: {result.get('updated_at')}")
    else:
        print(f"Error: {response.json()}")
    
    return response.status_code == 200


def test_process_without_saving():
    """Test processing movie vector without saving to database"""
    print("\n=== Test 3: Process Without Saving ===")
    
    payload = {
        "movie_id": 99999,
        "title": "테스트 영화",
        "overview": "따뜻하고 감동적인 가족 드라마",
        "genres": ["드라마", "가족"],
        "save_to_db": False
    }
    
    response = requests.post(f"{BASE_URL}/movie/vector", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Saved: {result.get('saved', False)}")
    print(f"Title: {result.get('title')}")
    
    return response.status_code == 200


def test_update_existing_vector():
    """Test updating an existing movie vector"""
    print("\n=== Test 4: Update Existing Vector ===")
    
    payload = {
        "movie_id": 12345,
        "title": "인셉션 (업데이트)",
        "overview": "꿈 속의 꿈을 통해 생각을 훔치는 특수 요원의 이야기. 감동적인 결말.",
        "synopsis": "긴장감과 감동이 공존하는 SF 스릴러",
        "genres": ["SF", "스릴러", "액션", "드라마"],
        "save_to_db": True
    }
    
    response = requests.post(f"{BASE_URL}/movie/vector", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Saved: {result.get('saved', False)}")
    
    # Verify update
    response2 = requests.get(f"{BASE_URL}/movies/12345/vector")
    if response2.status_code == 200:
        print(f"\nUpdated vector retrieved successfully")
        print(f"Updated at: {response2.json().get('updated_at')}")
    
    return response.status_code == 200


def test_batch_get_vectors():
    """Test getting multiple movie vectors at once"""
    print("\n=== Test 5: Batch Get Vectors ===")
    
    # First, create a few more vectors
    for movie_id in [11111, 22222, 33333]:
        payload = {
            "movie_id": movie_id,
            "title": f"영화 {movie_id}",
            "overview": "테스트 영화입니다",
            "save_to_db": True
        }
        requests.post(f"{BASE_URL}/movie/vector", json=payload)
    
    # Now get them in batch
    payload = {
        "movie_ids": [12345, 11111, 22222, 33333, 99999]  # 99999 doesn't exist
    }
    
    response = requests.post(f"{BASE_URL}/movies/vectors/batch", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Total vectors found: {result.get('total')}")
        print(f"Movie IDs: {list(result.get('vectors', {}).keys())}")
    
    return response.status_code == 200


if __name__ == "__main__":
    print("Starting MovieVector API Tests...")
    print("Make sure the backend server is running on http://localhost:8000")
    
    try:
        # Run tests
        test1 = test_process_and_save_vector()
        test2 = test_get_movie_vector()
        test3 = test_process_without_saving()
        test4 = test_update_existing_vector()
        test5 = test_batch_get_vectors()
        
        # Summary
        print("\n" + "="*50)
        print("Test Summary:")
        print(f"Test 1 (Process & Save): {'✓ PASS' if test1 else '✗ FAIL'}")
        print(f"Test 2 (Get Vector): {'✓ PASS' if test2 else '✗ FAIL'}")
        print(f"Test 3 (Process Only): {'✓ PASS' if test3 else '✗ FAIL'}")
        print(f"Test 4 (Update): {'✓ PASS' if test4 else '✗ FAIL'}")
        print(f"Test 5 (Batch Get): {'✓ PASS' if test5 else '✗ FAIL'}")
        print("="*50)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to backend server")
        print("Please start the backend server first: python app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
