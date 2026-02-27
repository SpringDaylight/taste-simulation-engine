# API 응답 포맷
import json

def success(data: dict, status: int = 200) -> dict:
    return {
        "statusCode": status,
        "body": json.dumps(data, ensure_ascii=False)
    }

def error(message: str, status: int = 400) -> dict:
    return {
        "statusCode": status,
        "body": json.dumps({"error": message}, ensure_ascii=False)
    }
