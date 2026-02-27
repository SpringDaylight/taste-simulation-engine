"""
Test script for review API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_review_api():
    """Test review CRUD operations"""
    
    print("=" * 50)
    print("Testing Review API")
    print("=" * 50)
    
    # Test data
    user_id = "test_user_001"
    movie_id = 1
    
    # 1. Create a review
    print("\n1. Creating a review...")
    review_data = {
        "movie_id": movie_id,
        "rating": 4.5,
        "content": "정말 감동적인 영화였습니다. 스토리가 탄탄하고 연기도 훌륭했어요!"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/reviews?user_id={user_id}",
        json=review_data
    )
    
    if response.status_code == 201:
        review = response.json()
        review_id = review["id"]
        print(f"✓ Review created successfully (ID: {review_id})")
        print(f"  Rating: {review['rating']}")
        print(f"  User Nickname: {review.get('user_nickname', 'N/A')}")
        print(f"  Content: {review['content'][:50]}...")
    else:
        print(f"✗ Failed to create review: {response.status_code}")
        print(f"  Error: {response.text}")
        return
    
    # 2. Get the review
    print(f"\n2. Getting review {review_id}...")
    response = requests.get(f"{BASE_URL}/api/reviews/{review_id}")
    
    if response.status_code == 200:
        review = response.json()
        print(f"✓ Review retrieved successfully")
        print(f"  User Nickname: {review.get('user_nickname', 'N/A')}")
        print(f"  Likes: {review['likes_count']}")
        print(f"  Comments: {review['comments_count']}")
    else:
        print(f"✗ Failed to get review: {response.status_code}")
    
    # 3. Update the review
    print(f"\n3. Updating review {review_id}...")
    update_data = {
        "rating": 5.0,
        "content": "다시 봐도 정말 좋은 영화입니다. 최고예요!"
    }
    
    response = requests.put(
        f"{BASE_URL}/api/reviews/{review_id}",
        json=update_data
    )
    
    if response.status_code == 200:
        review = response.json()
        print(f"✓ Review updated successfully")
        print(f"  New rating: {review['rating']}")
        print(f"  New content: {review['content'][:50]}...")
    else:
        print(f"✗ Failed to update review: {response.status_code}")
    
    # 4. Add a like
    print(f"\n4. Adding a like to review {review_id}...")
    response = requests.post(
        f"{BASE_URL}/api/reviews/{review_id}/likes?user_id=test_user_002&is_like=true"
    )
    
    if response.status_code == 200:
        print(f"✓ Like added successfully")
    else:
        print(f"✗ Failed to add like: {response.status_code}")
    
    # 5. Add a comment
    print(f"\n5. Adding a comment to review {review_id}...")
    comment_data = {
        "content": "저도 이 영화 정말 좋아해요! 공감합니다."
    }
    
    response = requests.post(
        f"{BASE_URL}/api/reviews/{review_id}/comments?user_id=test_user_003",
        json=comment_data
    )
    
    if response.status_code == 201:
        comment = response.json()
        comment_id = comment["id"]
        print(f"✓ Comment added successfully (ID: {comment_id})")
        print(f"  Content: {comment['content']}")
    else:
        print(f"✗ Failed to add comment: {response.status_code}")
    
    # 6. Get comments
    print(f"\n6. Getting comments for review {review_id}...")
    response = requests.get(f"{BASE_URL}/api/reviews/{review_id}/comments")
    
    if response.status_code == 200:
        comments = response.json()
        print(f"✓ Retrieved {len(comments)} comment(s)")
        for comment in comments:
            nickname = comment.get('user_nickname', 'N/A')
            print(f"  - [{nickname}] {comment['content'][:50]}...")
    else:
        print(f"✗ Failed to get comments: {response.status_code}")
    
    # 7. Get movie reviews
    print(f"\n7. Getting all reviews for movie {movie_id}...")
    response = requests.get(f"{BASE_URL}/api/movies/{movie_id}/reviews")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Retrieved {result['total']} review(s)")
        for review in result['reviews']:
            nickname = review.get('user_nickname', 'N/A')
            print(f"  - [{nickname}] Rating: {review['rating']}, User: {review['user_id']}")
    else:
        print(f"✗ Failed to get movie reviews: {response.status_code}")
    
    # 8. Get user reviews
    print(f"\n8. Getting all reviews by user {user_id}...")
    response = requests.get(f"{BASE_URL}/api/users/me/reviews?user_id={user_id}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Retrieved {result['total']} review(s)")
        for review in result['reviews']:
            nickname = review.get('user_nickname', 'N/A')
            print(f"  - [{nickname}] Movie: {review['movie_id']}, Rating: {review['rating']}")
    else:
        print(f"✗ Failed to get user reviews: {response.status_code}")
    
    # 9. Delete the review
    print(f"\n9. Deleting review {review_id}...")
    response = requests.delete(f"{BASE_URL}/api/reviews/{review_id}")
    
    if response.status_code == 200:
        print(f"✓ Review deleted successfully")
    else:
        print(f"✗ Failed to delete review: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("Review API test completed!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        test_review_api()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server.")
        print("Please make sure the server is running at http://localhost:8000")
    except Exception as e:
        print(f"Error: {e}")
