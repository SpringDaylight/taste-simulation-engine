import json
from typing import Any, Dict

# JSON Schema 검증
def validate_request(schema_name: str, body: Any) -> Dict[str, Any]:
    """
    JSON Schema 검증 (구현은 단순 타입 체크)
    """
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be JSON object") from exc

    if not isinstance(body, dict):
        raise ValueError("Request body must be JSON object")

    return body