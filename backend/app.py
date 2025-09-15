"""
FastAPI 기반 동적 MongoDB 분석 백엔드
NLP Analytics Platform과 연동
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import jwt
import os
from pymongo import MongoClient
from bson import ObjectId

# 동적 MongoDB 분석기 임포트
import sys
sys.path.append('..')
from dynamic_schema_mongodb_analyzer import DynamicMongoDBAnalyzer
from ml_analyzer import MLAnalyzer
from nl_to_sql import get_nl_to_sql_converter

# 새로운 API 라우터 임포트
from dataset_api import router as dataset_router
from analysis_api import router as analysis_router
from nl2mongo_api import router as nl2mongo_router
from nl2analysis_api import router as nl2analysis_router

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Dynamic MongoDB Analytics API",
    description="기업용 자연어 데이터 분석 플랫폼 백엔드",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 새로운 라우터 등록
app.include_router(dataset_router)
app.include_router(analysis_router)
app.include_router(nl2mongo_router)
app.include_router(nl2analysis_router)

# 보안 설정
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-here")
JWT_ALGORITHM = "HS256"

# MongoDB ObjectId를 JSON 직렬화 가능한 형태로 변환하는 유틸리티 함수
def convert_objectid_to_str(data):
    """ObjectId를 문자열로 변환하는 재귀 함수"""
    if isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, dict):
        return {key: convert_objectid_to_str(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectid_to_str(item) for item in data]
    else:
        return data

# MongoDB 연결 설정
MONGODB_URL = "mongodb+srv://musinsa:musinsa@cluster0.ed1m1eg.mongodb.net/musinsa?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "musinsa_db"
USER_DATABASE_NAME = "nlp_platform_users"

# 글로벌 변수
analyzer = None
ml_analyzer = None
user_client = None
user_db = None

# 데이터 모델 정의
class LoginRequest(BaseModel):
    emp_no: str
    password: str

class QueryRequest(BaseModel):
    query: str
    use_ai_mode: bool = True  # True: AI 모델 사용, False: 단순 SQL 모드
    save_analysis: bool = True
    tags: List[str] = []

class MLAnalysisRequest(BaseModel):
    analysis_type: str  # clustering, prediction, timeseries, anomaly, segmentation
    collection_name: str
    parameters: Dict[str, Any] = {}
    save_analysis: bool = True
    tags: List[str] = []

class AnalysisResponse(BaseModel):
    id: Optional[str] = None
    query: str
    execution_time: str
    data_count: int
    insights: List[str]
    recommendations: List[str]
    visualizations: List[Dict] = []
    confidence_score: float = 0.0
    
class User(BaseModel):
    emp_no: str
    name: str = ""
    team: str
    role: str = "user"

class Analysis(BaseModel):
    id: Optional[str] = None
    user_id: str
    query: str
    result: Dict[str, Any]
    tags: List[str] = []
    is_shared: bool = False
    created_at: datetime
    updated_at: datetime

# 초기화 함수
def initialize_services():
    """서비스 초기화"""
    global analyzer, ml_analyzer, user_client, user_db
    
    try:
        # MongoDB 분석기 초기화
        logger.info("MongoDB 분석기 초기화 중...")
        analyzer = DynamicMongoDBAnalyzer(MONGODB_URL, DATABASE_NAME)
        logger.info("MongoDB 분석기 초기화 완료!")
        
        # ML 분석기 초기화
        logger.info("ML 분석기 초기화 중...")
        ml_analyzer = MLAnalyzer()
        logger.info("ML 분석기 초기화 완료!")
        
        # 사용자 DB 초기화
        user_client = MongoClient(MONGODB_URL)
        user_db = user_client[USER_DATABASE_NAME]
        
        # 기본 사용자 생성 (개발용)
        create_default_users()
        
        logger.info("서비스 초기화 완료!")
        
    except Exception as e:
        logger.error(f"서비스 초기화 실패: {e}")
        raise

def create_default_users():
    """사용자 데이터 생성 - 실제 MongoDB 구조에 맞춤"""
    users_collection = user_db.users
    
    # 기존 사용자 수 확인
    user_count = users_collection.count_documents({})
    logger.info(f"기존 사용자 수: {user_count}명")
    
    # 실제 MongoDB 구조에 맞는 사용자 데이터 생성
    default_users = [
        {
            "emp_no": "admin",
            "password": "admin123",
            "team": "AI",
            "name": "관리자"
        },
        {
            "emp_no": "user001",
            "password": "user123",
            "team": "데이터분석팀",
            "name": "사용자1"
        }
    ]
    
    for user in default_users:
        if not users_collection.find_one({"emp_no": user["emp_no"]}):
            users_collection.insert_one(user)
            logger.info(f"사용자 생성: {user['emp_no']}")

# JWT 토큰 관련 함수
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT 토큰 검증"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        emp_no: str = payload.get("sub")
        if emp_no is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 유효하지 않습니다"
            )
        return emp_no
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않습니다"
        )

def get_current_user(emp_no: str = Depends(verify_token)):
    """현재 사용자 정보 조회"""
    user = user_db.users.find_one({"emp_no": emp_no})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    return user

# API 엔드포인트

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화"""
    initialize_services()

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Dynamic MongoDB Analytics API",
        "version": "2.0.0",
        "status": "running",
        "analyzer_available": analyzer is not None,
        "ml_analyzer_available": ml_analyzer is not None
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    try:
        # MongoDB 연결 확인
        schema_info = analyzer.get_schema_info() if analyzer else None
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "mongodb_analyzer": analyzer is not None,
                "ml_analyzer": ml_analyzer is not None,
                "user_db": user_db is not None,
                "schema_collections": len(schema_info['collections']) if schema_info else 0
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# 인증 관련 엔드포인트
@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """사용자 로그인"""
    try:
        user = user_db.users.find_one({"emp_no": request.emp_no})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다"
            )
        
        if request.password != user["password"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="비밀번호가 일치하지 않습니다"
            )
        
        # JWT 토큰 생성
        access_token = create_access_token(
            data={"sub": user["emp_no"]},
            expires_delta=timedelta(hours=24)
        )
        
        # 역할 결정 (admin은 관리자, 나머지는 user)
        role = "admin" if user["emp_no"] == "admin" else "user"
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "employee_id": user["emp_no"],  # 프론트엔드 호환성을 위해
                "emp_no": user["emp_no"],
                "name": user.get("name", user["emp_no"]),
                "department": user.get("team", ""),
                "team": user.get("team", ""),
                "role": role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다"
        )

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """현재 사용자 정보 조회"""
    # 역할 결정 (admin은 관리자, 나머지는 user)
    role = "admin" if current_user["emp_no"] == "admin" else "user"
    
    return {
        "employee_id": current_user["emp_no"],  # 프론트엔드 호환성을 위해
        "emp_no": current_user["emp_no"],
        "name": current_user.get("name", current_user["emp_no"]),
        "department": current_user.get("team", ""),
        "team": current_user.get("team", ""),
        "role": role
    }

@app.post("/api/auth/logout")
async def logout():
    """로그아웃 (클라이언트에서 토큰 제거)"""
    return {"message": "로그아웃되었습니다"}

# 스키마 및 시스템 정보 엔드포인트
@app.get("/api/schema/info")
async def get_schema_info(current_user: dict = Depends(get_current_user)):
    """스키마 정보 조회"""
    try:
        if not analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="분석 서비스가 초기화되지 않았습니다"
            )
        
        schema_info = analyzer.get_schema_info()
        return schema_info
        
    except Exception as e:
        logger.error(f"스키마 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스키마 정보를 가져올 수 없습니다"
        )

@app.post("/api/schema/refresh")
async def refresh_schema(current_user: dict = Depends(get_current_user)):
    """스키마 강제 새로고침"""
    try:
        if not analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="분석 서비스가 초기화되지 않았습니다"
            )
        
        # 관리자만 스키마 새로고침 가능
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다"
            )
        
        analyzer.refresh_schema()
        schema_info = analyzer.get_schema_info()
        
        return {
            "message": "스키마가 성공적으로 새로고침되었습니다",
            "schema_info": schema_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스키마 새로고침 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스키마 새로고침 중 오류가 발생했습니다"
        )

@app.get("/api/queries/suggestions")
async def get_query_suggestions(current_user: dict = Depends(get_current_user)):
    """스키마 기반 쿼리 제안"""
    try:
        if not analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="분석 서비스가 초기화되지 않았습니다"
            )
        
        suggestions = analyzer.suggest_queries()
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"쿼리 제안 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="쿼리 제안을 가져올 수 없습니다"
        )

# 분석 관련 엔드포인트
@app.post("/api/query", response_model=AnalysisResponse)
async def process_query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """자연어 쿼리 처리"""
    try:
        if not analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="분석 서비스가 초기화되지 않았습니다"
            )
        
        logger.info(f"사용자 {current_user['emp_no']}의 쿼리 처리: {request.query} (AI 모드: {request.use_ai_mode})")
        
        # 동적 분석 실행
        result = analyzer.analyze_query(request.query, request.use_ai_mode)
        
        # ObjectId를 문자열로 변환
        result = convert_objectid_to_str(result)
        
        # 분석 결과 저장
        analysis_id = None
        if request.save_analysis:
            analysis_doc = {
                "user_id": current_user["emp_no"],
                "query": request.query,
                "result": result,
                "tags": request.tags,
                "is_shared": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            analysis_result = user_db.analyses.insert_one(analysis_doc)
            analysis_id = str(analysis_result.inserted_id)
        
        # 시각화 데이터 생성 (간단한 예시)
        visualizations = []
        if result['data'] and len(result['data']) > 0:
            # Vega-Lite 스펙 생성
            viz_data = result['data'][:20]  # 최대 20개 데이터만
            
            if len(viz_data) > 1 and '_id' in viz_data[0]:
                # 막대 차트 생성
                viz_spec = {
                    "mark": "bar",
                    "data": {"values": viz_data},
                    "encoding": {
                        "x": {"field": "_id", "type": "nominal", "title": "항목"},
                        "y": {"field": "count" if "count" in viz_data[0] else "total", 
                              "type": "quantitative", "title": "값"}
                    },
                    "title": f"분석 결과: {request.query}",
                    "width": 600,
                    "height": 400
                }
                visualizations.append(viz_spec)
        
        # 응답 생성
        response = AnalysisResponse(
            id=analysis_id,
            query=result['query'],
            execution_time=result['execution_time'],
            data_count=result['data_count'],
            insights=result['insights'],
            recommendations=result['recommendations'],
            visualizations=visualizations,
            confidence_score=0.85  # 기본값
        )
        
        return response
        
    except Exception as e:
        logger.error(f"쿼리 처리 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"쿼리 처리 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/api/analyses/my")
async def get_my_analyses(
    skip: int = 0, 
    limit: int = 50, 
    current_user: dict = Depends(get_current_user)
):
    """내 분석 목록 조회"""
    try:
        analyses = list(user_db.analyses.find(
            {"user_id": current_user["emp_no"]},
            {"result.data": 0}  # 데이터는 제외하고 메타데이터만
        ).sort("created_at", -1).skip(skip).limit(limit))
        
        # ObjectId를 문자열로 변환
        for analysis in analyses:
            analysis["id"] = str(analysis["_id"])
            del analysis["_id"]
        
        total_count = user_db.analyses.count_documents({"user_id": current_user["emp_no"]})
        
        return {
            "analyses": analyses,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"내 분석 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 목록을 가져올 수 없습니다"
        )

@app.get("/api/analyses/shared")
async def get_shared_analyses(skip: int = 0, limit: int = 50):
    """공유 분석 목록 조회"""
    try:
        analyses = list(user_db.analyses.find(
            {"is_shared": True},
            {"result.data": 0}
        ).sort("created_at", -1).skip(skip).limit(limit))
        
        for analysis in analyses:
            analysis["id"] = str(analysis["_id"])
            del analysis["_id"]
            
            # 사용자 이름 추가
            user = user_db.users.find_one({"emp_no": analysis["user_id"]})
            if user:
                analysis["user_name"] = user.get("name", "Unknown")
                analysis["user_department"] = user.get("department", "Unknown")
        
        total_count = user_db.analyses.count_documents({"is_shared": True})
        
        return {
            "analyses": analyses,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"공유 분석 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="공유 분석 목록을 가져올 수 없습니다"
        )

@app.get("/api/analyses/{analysis_id}")
async def get_analysis_detail(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """분석 상세 조회"""
    try:
        
        analysis = user_db.analyses.find_one({"_id": ObjectId(analysis_id)})
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="분석을 찾을 수 없습니다"
            )
        
        # 소유자이거나 공유된 분석만 조회 가능
        if (analysis["user_id"] != current_user["emp_no"] and 
            not analysis.get("is_shared", False)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="접근 권한이 없습니다"
            )
        
        # ObjectId를 문자열로 변환
        analysis = convert_objectid_to_str(analysis)
        analysis["id"] = analysis.pop("_id", str(analysis.get("_id", "")))
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 상세 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 상세 정보를 가져올 수 없습니다"
        )

@app.put("/api/analyses/{analysis_id}")
async def update_analysis(
    analysis_id: str, 
    update_data: dict, 
    current_user: dict = Depends(get_current_user)
):
    """분석 수정"""
    try:
        
        # 소유자 확인
        analysis = user_db.analyses.find_one({"_id": ObjectId(analysis_id)})
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="분석을 찾을 수 없습니다"
            )
        
        if analysis["user_id"] != current_user["emp_no"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="수정 권한이 없습니다"
            )
        
        # 수정 가능한 필드만 업데이트
        allowed_fields = ["tags", "is_shared"]
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
        update_fields["updated_at"] = datetime.now()
        
        user_db.analyses.update_one(
            {"_id": ObjectId(analysis_id)},
            {"$set": update_fields}
        )
        
        return {"message": "분석이 성공적으로 수정되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 수정 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 수정 중 오류가 발생했습니다"
        )

@app.delete("/api/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str, current_user: dict = Depends(get_current_user)):
    """분석 삭제"""
    try:
        
        # 소유자 확인
        analysis = user_db.analyses.find_one({"_id": ObjectId(analysis_id)})
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="분석을 찾을 수 없습니다"
            )
        
        if analysis["user_id"] != current_user["emp_no"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="삭제 권한이 없습니다"
            )
        
        user_db.analyses.delete_one({"_id": ObjectId(analysis_id)})
        
        return {"message": "분석이 성공적으로 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 삭제 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 삭제 중 오류가 발생했습니다"
        )

# 대시보드 데이터 엔드포인트
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """대시보드 통계 데이터"""
    try:
        # 사용자의 분석 통계
        total_analyses = user_db.analyses.count_documents({"user_id": current_user["emp_no"]})
        shared_analyses = user_db.analyses.count_documents({
            "user_id": current_user["emp_no"],
            "is_shared": True
        })
        
        # 최근 분석들
        recent_analyses = list(user_db.analyses.find(
            {"user_id": current_user["emp_no"]},
            {"query": 1, "created_at": 1, "result.data_count": 1}
        ).sort("created_at", -1).limit(5))
        
        for analysis in recent_analyses:
            analysis["id"] = str(analysis["_id"])
            del analysis["_id"]
        
        # 인기 분석 (공유된 분석 중)
        popular_analyses = list(user_db.analyses.find(
            {"is_shared": True},
            {"query": 1, "user_id": 1, "created_at": 1}
        ).sort("created_at", -1).limit(5))
        
        for analysis in popular_analyses:
            analysis["id"] = str(analysis["_id"])
            del analysis["_id"]
            
            # 사용자 이름 추가
            user = user_db.users.find_one({"emp_no": analysis["user_id"]})
            if user:
                analysis["user_name"] = user.get("name", "Unknown")
        
        return {
            "user_stats": {
                "total_analyses": total_analyses,
                "shared_analyses": shared_analyses,
                "department": current_user["department"],
                "role": current_user["role"]
            },
            "recent_analyses": recent_analyses,
            "popular_analyses": popular_analyses
        }
        
    except Exception as e:
        logger.error(f"대시보드 통계 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대시보드 데이터를 가져올 수 없습니다"
        )

# ML 분석 엔드포인트
@app.post("/api/ml/analyze")
async def process_ml_analysis(request: MLAnalysisRequest, current_user: dict = Depends(get_current_user)):
    """머신러닝 기반 데이터 분석"""
    try:
        if not analyzer or not ml_analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="분석 서비스가 초기화되지 않았습니다"
            )
        
        logger.info(f"사용자 {current_user['emp_no']}의 ML 분석 요청: {request.analysis_type} on {request.collection_name}")
        
        # MongoDB에서 데이터 가져오기
        import pandas as pd
        data_client = MongoClient(MONGODB_URL)
        db = data_client[DATABASE_NAME]
        
        if request.collection_name not in db.list_collection_names():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"컬렉션 '{request.collection_name}'을 찾을 수 없습니다"
            )
        
        collection = db[request.collection_name]
        
        # 데이터 샘플링 (성능 고려)
        sample_size = request.parameters.get('sample_size', 1000)
        
        # MongoDB 데이터를 DataFrame으로 변환
        cursor = collection.aggregate([{"$sample": {"size": sample_size}}])
        data_list = list(cursor)
        
        if not data_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="분석할 데이터가 없습니다"
            )
        
        # pandas DataFrame 생성
        data = pd.json_normalize(data_list)
        
        # ML 분석 실행
        ml_result = ml_analyzer.analyze_data(
            data=data,
            analysis_type=request.analysis_type,
            **request.parameters
        )
        
        # 에러 체크
        if "error" in ml_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ml_result["error"]
            )
        
        # 분석 결과 저장
        analysis_id = None
        if request.save_analysis:
            analysis_doc = {
                "user_id": current_user["emp_no"],
                "query": f"ML 분석: {request.analysis_type} on {request.collection_name}",
                "result": {
                    "type": "ml_analysis",
                    "analysis_type": request.analysis_type,
                    "collection": request.collection_name,
                    "data_count": len(data_list),
                    "ml_result": ml_result,
                    "parameters": request.parameters
                },
                "tags": request.tags + ["ML", request.analysis_type],
                "is_shared": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            analysis_result = user_db.analyses.insert_one(analysis_doc)
            analysis_id = str(analysis_result.inserted_id)
        
        # 시각화 데이터 추가 (분석 유형에 따라)
        visualizations = []
        
        if request.analysis_type == "clustering" and "visualization_data" in ml_result:
            viz_data = ml_result["visualization_data"]
            viz_spec = {
                "mark": {"type": "circle", "size": 100, "opacity": 0.7},
                "data": {
                    "values": [
                        {"x": point[0], "y": point[1], "cluster": cluster}
                        for point, cluster in zip(viz_data["points"], viz_data["clusters"])
                    ]
                },
                "encoding": {
                    "x": {"field": "x", "type": "quantitative", "title": "PC1"},
                    "y": {"field": "y", "type": "quantitative", "title": "PC2"},
                    "color": {"field": "cluster", "type": "nominal", "title": "클러스터"}
                },
                "title": f"고객 클러스터링 결과 ({ml_result.get('n_clusters', 'N')}개 그룹)",
                "width": 600,
                "height": 400
            }
            visualizations.append(viz_spec)
        
        elif request.analysis_type == "timeseries" and "time_series_data" in ml_result:
            ts_data = ml_result["time_series_data"]
            viz_spec = {
                "mark": "line",
                "data": {
                    "values": [
                        {"date": date, "value": value}
                        for date, value in zip(ts_data["dates"], ts_data["values"])
                    ]
                },
                "encoding": {
                    "x": {"field": "date", "type": "temporal", "title": "날짜"},
                    "y": {"field": "value", "type": "quantitative", "title": "값"}
                },
                "title": f"시계열 분석: {request.collection_name}",
                "width": 800,
                "height": 400
            }
            visualizations.append(viz_spec)
        
        # 응답 생성
        response = {
            "id": analysis_id,
            "analysis_type": request.analysis_type,
            "collection": request.collection_name,
            "data_count": len(data_list),
            "ml_result": ml_result,
            "visualizations": visualizations,
            "created_at": datetime.now().isoformat()
        }
        
        data_client.close()
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ML 분석 처리 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML 분석 처리 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/api/ml/methods")
async def get_ml_methods():
    """지원하는 ML 분석 방법 목록"""
    return {
        "methods": {
            "clustering": {
                "name": "고객 클러스터링 분석",
                "description": "K-means를 사용한 고객 세분화",
                "parameters": {
                    "n_clusters": {"type": "int", "default": 5, "description": "클러스터 수"}
                }
            },
            "prediction": {
                "name": "매출 예측 분석", 
                "description": "Random Forest를 사용한 매출 예측",
                "parameters": {
                    "target_col": {"type": "str", "description": "예측 대상 컬럼"},
                    "days_ahead": {"type": "int", "default": 30, "description": "예측 기간(일)"}
                }
            },
            "timeseries": {
                "name": "시계열 분석",
                "description": "트렌드 및 계절성 분석", 
                "parameters": {
                    "date_col": {"type": "str", "description": "날짜 컬럼"},
                    "value_col": {"type": "str", "description": "값 컬럼"}
                }
            },
            "anomaly": {
                "name": "이상치 탐지",
                "description": "Isolation Forest를 사용한 이상치 탐지",
                "parameters": {
                    "method": {"type": "str", "default": "isolation", "options": ["isolation", "statistical"]}
                }
            }
        }
    }

@app.get("/api/ml/collections")
async def get_collections_for_ml(current_user: dict = Depends(get_current_user)):
    """ML 분석 가능한 컬렉션 목록"""
    try:
        if not analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="분석 서비스가 초기화되지 않았습니다"
            )
        
        collections = []
        
        # MongoDB에서 직접 컬렉션 목록 가져오기 (더 빠름)
        for collection_name in analyzer.db.list_collection_names():
            # 실제 MongoDB 컬렉션에서 필드 정보 가져오기
            actual_collection = analyzer.db[collection_name]
            sample_doc = actual_collection.find_one()
            
            if sample_doc:
                all_fields = list(sample_doc.keys())
                
                # 수치형 필드 식별
                numeric_fields = []
                for field, value in sample_doc.items():
                    if isinstance(value, (int, float)) and field != '_id':
                        numeric_fields.append(field)
                
                # 최소 1개의 수치형 필드가 있는 컬렉션만 포함
                if len(numeric_fields) > 0:
                    # count_documents 대신 estimated_document_count 사용 (훨씬 빠름)
                    doc_count = actual_collection.estimated_document_count()
                    collections.append({
                        "name": collection_name,
                        "document_count": doc_count,
                        "numeric_fields": numeric_fields,
                        "sample_fields": [f for f in all_fields if f != '_id'][:10]
                    })
        
        return {"collections": collections}
        
    except Exception as e:
        logger.error(f"ML 컬렉션 목록 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="컬렉션 목록을 가져올 수 없습니다"
        )

# 자연어 쿼리 변환 관련 모델
class NaturalLanguageQueryRequest(BaseModel):
    query: str
    ai_mode: bool = False
    collection: Optional[str] = None

class NaturalLanguageQueryResponse(BaseModel):
    success: bool
    query: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    natural_language: str
    parsed_elements: Optional[Dict[str, Any]] = None

@app.post("/api/nl/convert-query", response_model=NaturalLanguageQueryResponse)
async def convert_natural_language_to_query(
    request: NaturalLanguageQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """자연어를 MongoDB 쿼리로 변환"""
    try:
        if request.ai_mode:
            # AI 모드 ON: 기존 방식 사용
            # TODO: 기존 AI 분석 로직
            return NaturalLanguageQueryResponse(
                success=False,
                error="AI 모드는 아직 구현되지 않았습니다",
                natural_language=request.query
            )
        else:
            # AI 모드 OFF: 한국어 자연어-SQL 변환
            nl_converter = get_nl_to_sql_converter()
            result = nl_converter.convert_to_sql(request.query)
            
            if result["success"]:
                # SQL을 MongoDB 쿼리로 변환
                mongodb_query = nl_converter.convert_sql_to_mongodb(result["sql"], result["parsed_elements"])
                return NaturalLanguageQueryResponse(
                    success=True,
                    query=mongodb_query,
                    natural_language=result["natural_language"],
                    parsed_elements=result["parsed_elements"]
                )
            else:
                return NaturalLanguageQueryResponse(
                    success=False,
                    error=result["error"],
                    natural_language=result["natural_language"]
                )
                
    except Exception as e:
        logger.error(f"자연어 쿼리 변환 오류: {e}")
        return NaturalLanguageQueryResponse(
            success=False,
            error=str(e),
            natural_language=request.query
        )

@app.post("/api/nl/search", response_model=NaturalLanguageQueryResponse)
async def natural_language_search(
    request: NaturalLanguageQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """자연어 검색 실행"""
    try:
        if not analyzer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="분석 서비스가 초기화되지 않았습니다"
            )
        
        if request.ai_mode:
            # AI 모드 ON: 기존 방식 사용
            # TODO: 기존 AI 분석 로직
            return NaturalLanguageQueryResponse(
                success=False,
                error="AI 모드는 아직 구현되지 않았습니다",
                natural_language=request.query
            )
        else:
            # AI 모드 OFF: 한국어 자연어-SQL 변환 후 실행
            nl_converter = get_nl_to_sql_converter()
            sql_result = nl_converter.convert_to_sql(request.query)
            
            if not sql_result["success"]:
                return NaturalLanguageQueryResponse(
                    success=False,
                    error=sql_result["error"],
                    natural_language=request.query
                )
            
            # SQL을 MongoDB 쿼리로 변환
            conversion_result = {
                "success": True,
                "query": nl_converter.convert_sql_to_mongodb(sql_result["sql"], sql_result["parsed_elements"]),
                "natural_language": sql_result["natural_language"],
                "parsed_elements": sql_result["parsed_elements"]
            }
            
            if not conversion_result["success"]:
                return NaturalLanguageQueryResponse(
                    success=False,
                    error=conversion_result["error"],
                    natural_language=request.query
                )
            
            # MongoDB 쿼리 실행
            query_info = conversion_result["query"]
            collection_name = query_info["collection"]
            
            if collection_name not in analyzer.db.list_collection_names():
                return NaturalLanguageQueryResponse(
                    success=False,
                    error=f"컬렉션 '{collection_name}'을 찾을 수 없습니다",
                    natural_language=request.query
                )
            
            collection = analyzer.db[collection_name]
            
            if query_info["operation"] == "find":
                # find 연산
                cursor = collection.find(
                    query_info["filter"],
                    **query_info.get("options", {})
                )
                results = []
                for doc in cursor:
                    doc["_id"] = str(doc["_id"])  # ObjectId를 문자열로 변환
                    results.append(doc)
                
                return NaturalLanguageQueryResponse(
                    success=True,
                    query=conversion_result["query"],
                    results=results[:100],  # 최대 100개 결과 반환
                    natural_language=request.query,
                    parsed_elements=conversion_result["parsed_elements"]
                )
            
            elif query_info["operation"] == "aggregate":
                # aggregate 연산
                pipeline = query_info.get("pipeline", [])
                results = list(collection.aggregate(pipeline))
                
                for doc in results:
                    if "_id" in doc and isinstance(doc["_id"], ObjectId):
                        doc["_id"] = str(doc["_id"])
                
                return NaturalLanguageQueryResponse(
                    success=True,
                    query=conversion_result["query"],
                    results=results,
                    natural_language=request.query,
                    parsed_elements=conversion_result["parsed_elements"]
                )
            
            else:
                return NaturalLanguageQueryResponse(
                    success=False,
                    error=f"지원하지 않는 연산: {query_info['operation']}",
                    natural_language=request.query
                )
                
    except Exception as e:
        logger.error(f"자연어 검색 실행 오류: {e}")
        return NaturalLanguageQueryResponse(
            success=False,
            error=str(e),
            natural_language=request.query
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )