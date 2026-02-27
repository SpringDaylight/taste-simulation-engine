"""
Test script for User Preference API
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_save_user_preference():
    """Test saving user preference"""
    print("\n=== Test: Save User Preference ===")
    
    payload = {
        "user_id": "test_user_123",
        "preference_vector_json": {
            "emotion_scores": {
                "우울": 0.8,
                "따뜻": 0.6,
                "긴장": 0.3
            },
            "narrative_traits": {
                "성장": 0.7,
                "관계": 0.8,
                "복수": 0.2
            },
            "direction_mood": {
                "잔잔": 0.7,
                "빠른": 0.3
            },
            "character_relationship": {
                "가족": 0.8,
                "친구": 0.6
            },
            "ending_preference": {
                "happy": 0.6,
                "open": 0.3,
                "bittersweet": 0.7
            }
        },
        "persona_code": "MELANCHOLIC_ROMANTIC",
        "boost_tags": ["우울", "따뜻", "성장", "관계"],
        "dislike_tags": ["폭력", "공포"],
        "penalty_tags": []
    }
    
    response = requests.post(f"{BASE_URL}/api/user-preferences", json=payload)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 201


def test_get_user_preference():
    """Test getting user preference"""
    print("\n=== Test: Get User Preference ===")
    
    user_id = "test_user_123"
    response = requests.get(f"{BASE_URL}/api/user-preferences/{user_id}")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_check_exists():
    """Test checking if preference exists"""
    print("\n=== Test: Check Preference Exists ===")
    
    user_id = "test_user_123"
    response = requests.get(f"{BASE_URL}/api/user-preferences/{user_id}/exists")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_update_user_preference():
    """Test updating user preference"""
    print("\n=== Test: Update User Preference ===")
    
    payload = {
        "user_id": "test_user_123",
        "preference_vector_json": {
            "emotion_scores": {
                "우울": 0.9,  # Updated
                "따뜻": 0.7,  # Updated
                "긴장": 0.2
            },
            "narrative_traits": {
                "성장": 0.8,  # Updated
                "관계": 0.9,  # Updated
                "복수": 0.1
            },
            "direction_mood": {
                "잔잔": 0.8,
                "빠른": 0.2
            },
            "character_relationship": {
                "가족": 0.9,
                "친구": 0.7
            },
            "ending_preference": {
                "happy": 0.5,
                "open": 0.4,
                "bittersweet": 0.8
            }
        },
        "persona_code": "MELANCHOLIC_ROMANTIC_V2",
        "boost_tags": ["우울", "따뜻", "성장", "관계", "가족"],  # Added "가족"
        "dislike_tags": ["폭력", "공포", "스릴러"],  # Added "스릴러"
        "penalty_tags": []
    }
    
    response = requests.post(f"{BASE_URL}/api/user-preferences", json=payload)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 201


def test_delete_user_preference():
    """Test deleting user preference"""
    print("\n=== Test: Delete User Preference ===")
    
    user_id = "test_user_123"
    response = requests.delete(f"{BASE_URL}/api/user-preferences/{user_id}")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 200


def test_get_nonexistent_preference():
    """Test getting non-existent preference"""
    print("\n=== Test: Get Non-existent Preference ===")
    
    user_id = "nonexistent_user"
    response = requests.get(f"{BASE_URL}/api/user-preferences/{user_id}")
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    return response.status_code == 404


if __name__ == "__main__":
    print("=" * 60)
    print("User Preference API Test Suite")
    print("=" * 60)
    
    tests = [
        ("Save User Preference", test_save_user_preference),
        ("Get User Preference", test_get_user_preference),
        ("Check Exists", test_check_exists),
        ("Update User Preference", test_update_user_preference),
        ("Get User Preference (After Update)", test_get_user_preference),
        ("Delete User Preference", test_delete_user_preference),
        ("Get Non-existent Preference", test_get_nonexistent_preference),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, "✓ PASS" if success else "✗ FAIL"))
        except Exception as e:
            print(f"Error: {e}")
            results.append((test_name, f"✗ ERROR: {e}"))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for test_name, result in results:
        print(f"{test_name}: {result}")
    
    passed = sum(1 for _, r in results if "PASS" in r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
