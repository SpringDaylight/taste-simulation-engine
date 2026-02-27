"""
Test script for UserPreference repository and API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_analyze_and_save_preference():
    """Test analyzing preference and saving to database"""
    print("\n=== Test 1: Analyze and Save Preference ===")
    
    payload = {
        "text": "저는 따뜻하고 감동적인 영화를 좋아해요. 무서운 건 싫어요.",
        "dislikes": "무서워요, 긴장돼요",
        "user_id": "test_user_123",
        "save_to_db": True
    }
    
    response = requests.post(f"{BASE_URL}/analyze/preference", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_get_user_preference():
    """Test retrieving saved user preference"""
    print("\n=== Test 2: Get User Preference ===")
    
    user_id = "test_user_123"
    response = requests.get(f"{BASE_URL}/users/{user_id}/preference")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_analyze_without_saving():
    """Test analyzing preference without saving to database"""
    print("\n=== Test 3: Analyze Without Saving ===")
    
    payload = {
        "text": "액션 영화를 좋아합니다. 로맨스는 별로예요.",
        "save_to_db": False
    }
    
    response = requests.post(f"{BASE_URL}/analyze/preference", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Saved: {result.get('saved', False)}")
    print(f"Dislike tags: {result.get('dislike_tags', [])}")
    print(f"Boost tags: {result.get('boost_tags', [])}")
    
    return response.status_code == 200


def test_update_existing_preference():
    """Test updating an existing user preference"""
    print("\n=== Test 4: Update Existing Preference ===")
    
    payload = {
        "text": "이제는 스릴러도 좋아하게 됐어요. 힐링되는 영화도 좋아요.",
        "user_id": "test_user_123",
        "save_to_db": True
    }
    
    response = requests.post(f"{BASE_URL}/analyze/preference", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    # Verify update
    response2 = requests.get(f"{BASE_URL}/users/test_user_123/preference")
    print(f"\nUpdated preference:")
    print(f"Response: {json.dumps(response2.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


if __name__ == "__main__":
    print("Starting UserPreference API Tests...")
    print("Make sure the backend server is running on http://localhost:8000")
    
    try:
        # Run tests
        test1 = test_analyze_and_save_preference()
        test2 = test_get_user_preference()
        test3 = test_analyze_without_saving()
        test4 = test_update_existing_preference()
        
        # Summary
        print("\n" + "="*50)
        print("Test Summary:")
        print(f"Test 1 (Analyze & Save): {'✓ PASS' if test1 else '✗ FAIL'}")
        print(f"Test 2 (Get Preference): {'✓ PASS' if test2 else '✗ FAIL'}")
        print(f"Test 3 (Analyze Only): {'✓ PASS' if test3 else '✗ FAIL'}")
        print(f"Test 4 (Update): {'✓ PASS' if test4 else '✗ FAIL'}")
        print("="*50)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to backend server")
        print("Please start the backend server first: python app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
