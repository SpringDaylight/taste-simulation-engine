import os
import sys
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Mock DB config
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_backend.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Monkeypatch JSONB for SQLite compatibility
import sqlalchemy.dialects.postgresql
from sqlalchemy import JSON
sqlalchemy.dialects.postgresql.JSONB = JSON

# We need to rely on 'app' import.
# Since psycopg2 is installed, 'from app import app' should work.
# The 'db.py' might try to create an engine, but connection is lazy.
try:
    from app import app
    from db import get_db, Base
    from models import User
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Override the get_db dependency to use our SQLite session
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create tables in SQLite
Base.metadata.create_all(bind=engine)

# Seed demo user
def seed_user():
    db = TestingSessionLocal()
    try:
        if not db.query(User).filter_by(id="user_demo").first():
            print("Seeding user_demo...")
            user = User(
                id="user_demo", 
                name="Demo User", 
                level=1, 
                exp=0, 
                popcorn=100,
                main_flavor="Sweet",
                stage="Egg"
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

seed_user()

client = TestClient(app)

def test_endpoints():
    print("\n------------------------------------------------")
    print("Testing Backend Integration (Gamification API)")
    print("------------------------------------------------")

    # 1. Test Home
    print("GET /api/home")
    response = client.get("/api/home")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.text}")
    assert response.status_code == 200

    # 2. Test Inventory
    print("\nGET /api/inventory")
    response = client.get("/api/inventory")
    print(f"Status: {response.status_code}")
    assert response.status_code == 200

    print("\n✅ Success! All backend integration tests passed.")

if __name__ == "__main__":
    try:
        test_endpoints()
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
