from bson import ObjectId
from datetime import datetime
from typing import Any, Dict, List, Union

def to_jsonable(obj: Any) -> Any:
    """
    재귀적으로 MongoDB 객체들을 JSON 직렬화 가능한 형태로 변환
    
    Args:
        obj: 변환할 객체 (dict, list, ObjectId 등)
        
    Returns:
        JSON 직렬화 가능한 객체
    """
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: to_jsonable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_jsonable(item) for item in obj]
    elif isinstance(obj, set):
        return [to_jsonable(item) for item in obj]
    else:
        return obj