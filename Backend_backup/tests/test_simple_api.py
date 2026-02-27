"""
Simple API test to debug 500 error
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Step 0: Create a test user first
print("=== Step 0: Create Test User ===")
user_payload = {
    "user_id": "test_api_user",
    "email": "test_api@example.com",
    "password": "testpassword123",
    "name": "Test User"
}

try:
    response = requests.post(f"{BASE_URL}/api/auth/signup", json=user_payload)
    print(f"User Creation Status: {response.status_code}")
    if response.status_code == 201:
        print("✓ Test user created")
        user_data = response.json()
        test_user_id = user_data.get("id") or user_data.get("user", {}).get("id")
        print(f"User ID: {test_user_id}")
    elif response.status_code == 400:
        print("User already exists, continuing...")
        # Try to get existing user ID - use a known user from your DB
        test_user_id = "user_1210b58d1b2d4645bb2c8411bc67c172"  # Use an existing user ID
    else:
        print(f"Failed to create user: {response.text}")
        test_user_id = "user_1210b58d1b2d4645bb2c8411bc67c172"  # Fallback to existing user
except Exception as e:
    print(f"Error creating user: {e}")
    test_user_id = "user_1210b58d1b2d4645bb2c8411bc67c172"  # Fallback to existing user

print(f"\nUsing user_id: {test_user_id}\n")

# Test 1: Simple preference creation
print("=== Test 1: Create User Preference ===")
payload = {
    "user_id": test_user_id,
    "preference_vector_json": {
        "emotion_scores": {"우울": 0.5},
        "narrative_traits": {"성장": 0.5},
        "direction_mood": {"잔잔": 0.5},
        "character_relationship": {"가족": 0.5},
        "ending_preference": {"happy": 0.5, "open": 0.3, "bittersweet": 0.2}
    },
    "boost_tags": ["우울", "성장"],
    "dislike_tags": [],
    "penalty_tags": []
}

print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

try:
    response = requests.post(f"{BASE_URL}/api/user-preferences", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Text: {response.text[:500]}")
    
    if response.status_code == 201:
        print("✓ SUCCESS")
        result = response.json()
        print(f"Created: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print("✗ FAILED")
        
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 2: Get the created preference
print("\n=== Test 2: Get User Preference ===")
try:
    response = requests.get(f"{BASE_URL}/api/user-preferences/{test_user_id}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ SUCCESS")
        result = response.json()
        print(f"Retrieved: {json.dumps(result, indent=2, ensure_ascii=False)}")
    else:
        print(f"✗ FAILED: {response.text}")
        
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 3: Delete the preference
print("\n=== Test 3: Delete User Preference ===")
try:
    response = requests.delete(f"{BASE_URL}/api/user-preferences/{test_user_id}")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✓ SUCCESS")
    else:
        print(f"✗ FAILED: {response.text}")
        
except Exception as e:
    print(f"✗ ERROR: {e}")
