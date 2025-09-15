from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
import os
import uuid
from dotenv import load_dotenv
import logging
from utils.serializers import to_jsonable

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)

# MongoDB 연결 - 환경변수 또는 기본값 사용
MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME") or os.getenv("DATABASE_NAME", "musinsa_db")

if not MONGODB_URI:
    # 기본 MongoDB URL 사용 (환경변수가 설정되지 않은 경우)
    MONGODB_URI = "mongodb+srv://musinsa:musinsa@cluster0.ed1m1eg.mongodb.net/musinsa?retryWrites=true&w=majority&appName=Cluster0"
    logger.warning("Using default MongoDB URI")

client = AsyncIOMotorClient(MONGODB_URI)
db: AsyncIOMotorDatabase = client[DB_NAME]

# 라우터 생성
router = APIRouter(prefix="/api", tags=["datasets"])

# 민감정보 필드 화이트리스트
SENSITIVE_FIELDS = {
    "buyers.email",
    "buyers.phone", 
    "buyers.address",
    "buyers.postal_code",
    "users.password"
}

# 허용된 aggregation 연산자
ALLOWED_STAGES = {
    "$match", "$project", "$group", "$sort", "$limit", 
    "$lookup", "$unwind", "$addFields", "$count"
}

# Pydantic 모델들
class DateRange(BaseModel):
    from_date: Optional[str] = Field(None, alias="from")
    to_date: Optional[str] = Field(None, alias="to")

class JoinSpec(BaseModel):
    from_collection: str = Field(..., alias="from")
    local_field: Optional[str] = Field(None, alias="localField")
    foreign_field: Optional[str] = Field(None, alias="foreignField")
    pipeline: Optional[List[Dict[str, Any]]] = None

class QueryPreviewRequest(BaseModel):
    collection: str
    date_range: Optional[DateRange] = None
    filters: Optional[Dict[str, Any]] = None
    joins: Optional[List[JoinSpec]] = None
    limit: Optional[int] = Field(100, ge=1, le=5000)
    projection: Optional[List[str]] = None

class SaveDatasetRequest(BaseModel):
    name: str
    description: Optional[str] = None
    collection: str
    date_range: Optional[DateRange] = None
    filters: Optional[Dict[str, Any]] = None
    joins: Optional[List[JoinSpec]] = None
    limit: Optional[int] = Field(100, ge=1, le=5000)
    projection: Optional[List[str]] = None

class AnalysisRunRequest(BaseModel):
    dataset_id: str
    task: Optional[str] = Field("insight", pattern="^(insight|summary|topic|sentiment)$")
    options: Optional[Dict[str, Any]] = None

# 헬퍼 함수들
def sanitize_pipeline(pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """파이프라인 안전성 검증 및 민감정보 필터링"""
    sanitized = []
    
    for stage in pipeline:
        stage_type = list(stage.keys())[0] if stage else None
        
        # 허용된 스테이지만 통과
        if stage_type not in ALLOWED_STAGES:
            logger.warning(f"Blocked unauthorized stage: {stage_type}")
            continue
            
        # $where 및 JavaScript 표현식 차단
        stage_str = str(stage)
        if any(banned in stage_str.lower() for banned in ["$where", "function", "mapreduce", "$function"]):
            logger.warning(f"Blocked JavaScript expression in stage: {stage_type}")
            continue
            
        # $lookup 검증
        if stage_type == "$lookup":
            lookup_spec = stage["$lookup"]
            if "from" not in lookup_spec:
                continue
            # 조인 깊이 제한 (체인 길이)
            if isinstance(lookup_spec.get("pipeline"), list) and len(lookup_spec["pipeline"]) > 3:
                logger.warning("Blocked deep lookup pipeline")
                continue
                
        sanitized.append(stage)
    
    return sanitized

def remove_sensitive_fields(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """민감정보 필드 제거 또는 마스킹"""
    cleaned_data = []
    
    for doc in data:
        cleaned_doc = {}
        for key, value in doc.items():
            # 중첩 필드 처리
            if isinstance(value, dict):
                cleaned_value = {}
                for sub_key, sub_value in value.items():
                    field_path = f"{key}.{sub_key}"
                    if field_path in SENSITIVE_FIELDS:
                        cleaned_value[sub_key] = "***MASKED***"
                    else:
                        cleaned_value[sub_key] = sub_value
                cleaned_doc[key] = cleaned_value
            else:
                if key in SENSITIVE_FIELDS:
                    cleaned_doc[key] = "***MASKED***"
                else:
                    cleaned_doc[key] = value
        cleaned_data.append(cleaned_doc)
    
    return cleaned_data

def build_aggregation_pipeline(request: QueryPreviewRequest) -> List[Dict[str, Any]]:
    """요청 기반으로 aggregation 파이프라인 생성"""
    pipeline = []
    
    # 1. 날짜 필터
    match_stage = {}
    if request.date_range and (request.date_range.from_date or request.date_range.to_date):
        date_field_map = {
            "reviews": "review_created_at",
            "orders": "order_date",
            "product": "created_at"
        }
        date_field = date_field_map.get(request.collection, "created_at")
        
        date_filter = {}
        if request.date_range.from_date:
            try:
                date_filter["$gte"] = datetime.fromisoformat(request.date_range.from_date.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid from_date format: {request.date_range.from_date}")
        if request.date_range.to_date:
            try:
                date_filter["$lte"] = datetime.fromisoformat(request.date_range.to_date.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid to_date format: {request.date_range.to_date}")
        
        if date_filter:
            match_stage[date_field] = date_filter
    
    # 2. 추가 필터
    if request.filters:
        for field, condition in request.filters.items():
            if isinstance(condition, dict):
                # 연산자 변환
                transformed_condition = {}
                for op, value in condition.items():
                    if op == "eq":
                        transformed_condition = value
                    elif op == "ne":
                        transformed_condition["$ne"] = value
                    elif op == "gt":
                        transformed_condition["$gt"] = value
                    elif op == "gte":
                        transformed_condition["$gte"] = value
                    elif op == "lt":
                        transformed_condition["$lt"] = value
                    elif op == "lte":
                        transformed_condition["$lte"] = value
                    elif op == "contains":
                        transformed_condition["$regex"] = value
                        transformed_condition["$options"] = "i"
                match_stage[field] = transformed_condition
            else:
                match_stage[field] = condition
    
    if match_stage:
        pipeline.append({"$match": match_stage})
    
    # 3. 조인
    if request.joins:
        for join in request.joins:
            lookup_stage = {
                "$lookup": {
                    "from": join.from_collection,
                    "localField": join.local_field,
                    "foreignField": join.foreign_field,
                    "as": join.from_collection
                }
            }
            pipeline.append(lookup_stage)
            # 조인 결과 언와인드 (배열 -> 객체)
            pipeline.append({"$unwind": {"path": f"${join.from_collection}", "preserveNullAndEmptyArrays": True}})
    
    # 4. 프로젝션
    if request.projection:
        project_stage = {field: 1 for field in request.projection}
        project_stage["_id"] = 0  # _id는 기본적으로 제외
        pipeline.append({"$project": project_stage})
    
    # 5. 제한
    pipeline.append({"$limit": request.limit or 100})
    
    return sanitize_pipeline(pipeline)

# API 엔드포인트들
@router.post("/query/preview")
async def query_preview(request: QueryPreviewRequest):
    """데이터 미리보기 쿼리 실행"""
    try:
        logger.info(f"Preview request: collection={request.collection}, limit={request.limit}")
        
        # MongoDB 연결 테스트
        await db.command("ping")
        logger.info("MongoDB connection OK")
        # 컬렉션 존재 확인
        collections = await db.list_collection_names()
        if request.collection not in collections:
            raise HTTPException(status_code=404, detail=f"Collection '{request.collection}' not found")
        
        # 파이프라인 생성
        pipeline = build_aggregation_pipeline(request)
        
        # 전체 카운트 추정 (별도 파이프라인)
        count_pipeline = [p for p in pipeline if "$limit" not in p]
        count_pipeline.append({"$count": "total"})
        
        # 쿼리 실행
        logger.info(f"Executing preview query on {request.collection} with pipeline: {pipeline}")
        
        cursor = db[request.collection].aggregate(pipeline)
        data = await cursor.to_list(length=request.limit or 100)
        
        # 카운트 쿼리 (옵션)
        total_estimate = None
        if len(count_pipeline) <= 3:  # 간단한 쿼리만 카운트
            count_cursor = db[request.collection].aggregate(count_pipeline)
            count_result = await count_cursor.to_list(length=1)
            if count_result:
                total_estimate = count_result[0].get("total", 0)
        
        # 민감정보 제거
        cleaned_data = remove_sensitive_fields(data)
        
        # ObjectId 직렬화
        serialized_data = to_jsonable(cleaned_data)
        
        # 컬럼 추출
        columns = []
        if serialized_data:
            first_doc = serialized_data[0]
            columns = list(first_doc.keys())
        
        return {
            "columns": columns,
            "rows": serialized_data,
            "total_estimate": total_estimate
        }
        
    except Exception as e:
        logger.error(f"Query preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/datasets/save")
async def save_dataset(request: SaveDatasetRequest, user_id: str = "demo_user"):  # TODO: 실제 인증에서 가져오기
    """데이터셋 저장"""
    try:
        # 미리보기 쿼리 실행
        preview_request = QueryPreviewRequest(
            collection=request.collection,
            date_range=request.date_range,
            filters=request.filters,
            joins=request.joins,
            limit=min(request.limit or 100, 100),  # 미리보기는 최대 100개
            projection=request.projection
        )
        
        preview_result = await query_preview(preview_request)
        
        # 전체 행수 계산
        pipeline = build_aggregation_pipeline(preview_request)
        count_pipeline = [p for p in pipeline if "$limit" not in p]
        count_pipeline.append({"$count": "total"})
        
        count_cursor = db[request.collection].aggregate(count_pipeline)
        count_result = await count_cursor.to_list(length=1)
        row_count = count_result[0]["total"] if count_result else len(preview_result["rows"])
        
        # 데이터셋 문서 생성
        dataset_id = str(uuid.uuid4())
        dataset_doc = {
            "dataset_id": dataset_id,
            "user_id": user_id,
            "name": request.name,
            "description": request.description,
            "created_at": datetime.utcnow(),
            "source": {
                "db": DB_NAME,
                "collection": request.collection,
                "filters": request.filters or {},
                "date_range": {
                    "from": request.date_range.from_date if request.date_range else None,
                    "to": request.date_range.to_date if request.date_range else None
                },
                "limit": request.limit or 100,
                "projection": request.projection,
                "joins": [join.dict() for join in request.joins] if request.joins else []
            },
            "preview": preview_result["rows"][:20],  # 상위 20행만 저장
            "row_count": row_count,
            "storage": {
                "type": "inline",
                "location": None
            }
        }
        
        # MongoDB에 저장
        await db.saved_datasets.insert_one(dataset_doc)
        
        logger.info(f"Dataset saved: {dataset_id} by user {user_id}")
        
        return {"dataset_id": dataset_id}
        
    except Exception as e:
        logger.error(f"Save dataset error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/datasets/list")
async def list_datasets(
    q: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = "demo_user"  # TODO: 실제 인증에서 가져오기
):
    """저장된 데이터셋 목록 조회"""
    try:
        # 검색 조건
        filter_query = {}
        if q:
            filter_query["$or"] = [
                {"name": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}}
            ]
        
        # 전체 개수
        total = await db.saved_datasets.count_documents(filter_query)
        
        # 페이지네이션
        skip = (page - 1) * page_size
        
        # 쿼리 실행
        cursor = db.saved_datasets.find(filter_query).sort("created_at", -1).skip(skip).limit(page_size)
        datasets = await cursor.to_list(length=page_size)
        
        # 응답 포맷
        items = []
        for ds in datasets:
            items.append({
                "dataset_id": ds["dataset_id"],
                "name": ds["name"],
                "created_at": ds["created_at"].isoformat(),
                "row_count": ds["row_count"],
                "collection": ds["source"]["collection"],
                "user_id": ds["user_id"]
            })
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"List datasets error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """데이터셋 상세 정보 조회"""
    try:
        dataset = await db.saved_datasets.find_one({"dataset_id": dataset_id})
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # _id 제거
        dataset.pop("_id", None)
        
        # datetime 객체를 문자열로 변환
        if isinstance(dataset.get("created_at"), datetime):
            dataset["created_at"] = dataset["created_at"].isoformat()
        
        # ObjectId 직렬화 적용
        serialized_dataset = to_jsonable(dataset)
        
        return {
            "dataset_id": serialized_dataset["dataset_id"],
            "name": serialized_dataset["name"],
            "description": serialized_dataset.get("description"),
            "created_at": serialized_dataset["created_at"],
            "row_count": serialized_dataset["row_count"],
            "source": serialized_dataset["source"],
            "preview": serialized_dataset["preview"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get dataset error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))