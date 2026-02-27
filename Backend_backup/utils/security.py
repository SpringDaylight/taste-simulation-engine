import re
from uuid import uuid4
from passlib.context import CryptContext


_pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def validate_password_policy(password: str) -> bool:
    if len(password) < 8 or len(password) > 20:
        return False

    has_lower = re.search(r"[a-z]", password) is not None
    has_upper = re.search(r"[A-Z]", password) is not None
    has_digit = re.search(r"\d", password) is not None
    has_special = re.search(r"[^\w]", password) is not None

    categories = sum([has_lower, has_upper, has_digit, has_special])
    return categories >= 2


def generate_user_pk() -> str:
    return f"user_{uuid4().hex}"
