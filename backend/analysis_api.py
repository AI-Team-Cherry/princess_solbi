"""
GPT 기반 고급 분석 API
Reflection 구조를 사용한 완벽한 보고서 생성
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
import logging
import asyncio
import pandas as pd
from dotenv import load_dotenv

# 내부 모듈 import
from gpt_reflection_analyzer import GPTReflectionAnalyzer, AnalysisResult
from dynamic_schema_mongodb_analyzer import DynamicMongoDBAnalyzer

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)

# MongoDB 연결 설정
MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME") or os.getenv("DATABASE_NAME", "musinsa_db")

if not MONGODB_URI:
    MONGODB_URI = "mongodb+srv://musinsa:musinsa@cluster0.ed1m1eg.mongodb.net/musinsa?retryWrites=true&w=majority&appName=Cluster0"
    logger.warning("Using default MongoDB URI")

client = AsyncIOMotorClient(MONGODB_URI)
db: AsyncIOMotorDatabase = client[DB_NAME]

# 라우터 생성
router = APIRouter(prefix="/api", tags=["advanced-analysis"])

# 데이터 모델 정의
class AdvancedAnalysisRequest(BaseModel):
    question: str = Field(..., description="분석하고자 하는 질문")
    dataset_id: Optional[str] = Field(None, description="분석할 데이터셋 ID (선택)")
    collection_name: Optional[str] = Field(None, description="MongoDB 컬렉션 명 (선택)")
    use_reflection: bool = Field(True, description="Reflection 구조 사용 여부")
    max_reflections: int = Field(10, ge=1, le=15, description="최대 반복 횟수")
    target_score: float = Field(9.0, ge=7.0, le=10.0, description="목표 점수")

class AnalysisStatus(BaseModel):
    status: str
    progress: float
    current_step: int
    total_steps: int
    message: str
    estimated_time_remaining: Optional[float] = None

class AdvancedAnalysisResponse(BaseModel):
    analysis_id: str
    question: str
    final_report: str
    analysis_summary: Dict[str, Any]
    reflection_history: List[Dict[str, Any]]
    data_summary: str
    created_at: datetime
    execution_time: float

# 글로벌 변수
gpt_analyzer = None
mongodb_analyzer = None
analysis_cache = {}  # 분석 결과 캐시

async def get_analyzers():
    """분석기 인스턴스 가져오기 (의존성 주입)"""
    global gpt_analyzer, mongodb_analyzer
    
    if gpt_analyzer is None:
        gpt_analyzer = GPTReflectionAnalyzer()
    
    if mongodb_analyzer is None:
        # MongoDB 분석기 초기화
        mongodb_analyzer = DynamicMongoDBAnalyzer(
            connection_string=MONGODB_URI,
            db_name=DB_NAME
        )
    
    return gpt_analyzer, mongodb_analyzer

async def get_analysis_data(question: str, collection_name: Optional[str] = None, 
                           dataset_id: Optional[str] = None) -> pd.DataFrame:
    """분석용 데이터 가져오기"""
    try:
        # 데이터셋 ID가 제공된 경우
        if dataset_id:
            # 저장된 데이터셋에서 데이터 가져오기
            dataset = await db.datasets.find_one({"_id": dataset_id})
            if dataset and "data" in dataset:
                return pd.DataFrame(dataset["data"])
        
        # 컬렉션 명이 제공된 경우
        if collection_name:
            collection = db[collection_name]
            data = await collection.find({}).limit(1000).to_list(1000)
            # ObjectId를 문자열로 변환
            for item in data:
                if '_id' in item:
                    item['_id'] = str(item['_id'])
            return pd.DataFrame(data)
        
        # 질문 기반 자동 데이터 선택
        return await _get_smart_data_for_question(question)
        
    except Exception as e:
        logger.error(f"데이터 가져오기 실패: {e}")
        return pd.DataFrame()  # 빈 DataFrame 반환

async def _get_smart_data_for_question(question: str) -> pd.DataFrame:
    """질문에 따른 스마트 데이터 선택"""
    question_lower = question.lower()
    
    try:
        # 질문 유형에 따른 데이터 선택
        def convert_objectids(data_list):
            """ObjectId를 문자열로 변환"""
            for item in data_list:
                if '_id' in item:
                    item['_id'] = str(item['_id'])
                # 다른 ObjectId 필드들도 변환
                for key, value in item.items():
                    if hasattr(value, '__class__') and value.__class__.__name__ == 'ObjectId':
                        item[key] = str(value)
            return data_list

        if any(word in question_lower for word in ["리뷰", "평점", "만족", "부정", "긍정"]):
            # 리뷰 데이터
            data = await db.reviews.find({}).limit(500).to_list(500)
            return pd.DataFrame(convert_objectids(data))
        
        elif any(word in question_lower for word in ["매출", "판매", "주문", "구매"]):
            # 주문 데이터
            data = await db.orders.find({}).limit(500).to_list(500)
            return pd.DataFrame(convert_objectids(data))
        
        elif any(word in question_lower for word in ["상품", "제품", "브랜드", "카테고리"]):
            # 상품 데이터
            data = await db.products.find({}).limit(500).to_list(500)
            return pd.DataFrame(convert_objectids(data))
        
        else:
            # 기본적으로 리뷰 데이터 사용
            data = await db.reviews.find({}).limit(300).to_list(300)
            return pd.DataFrame(convert_objectids(data))
            
    except Exception as e:
        logger.error(f"스마트 데이터 선택 실패: {e}")
        # 목 데이터 반환
        return pd.DataFrame([
            {"_id": "샘플데이터1", "value": 100, "category": "A"},
            {"_id": "샘플데이터2", "value": 200, "category": "B"},
            {"_id": "샘플데이터3", "value": 150, "category": "C"}
        ])

@router.post("/analysis/advanced", response_model=Dict[str, str])
async def start_advanced_analysis(
    request: AdvancedAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """고급 분석 시작 (비동기)"""
    try:
        # 분석 ID 생성
        analysis_id = f"analysis_{int(datetime.now().timestamp() * 1000)}"
        
        # 초기 상태 설정
        analysis_cache[analysis_id] = {
            "status": "starting",
            "progress": 0.0,
            "current_step": 0,
            "total_steps": request.max_reflections,
            "message": "분석을 시작합니다...",
            "start_time": datetime.now(),
            "request": request
        }
        
        # 백그라운드에서 분석 실행
        background_tasks.add_task(
            _run_advanced_analysis,
            analysis_id,
            request
        )
        
        return {
            "analysis_id": analysis_id,
            "message": "분석이 시작되었습니다. 상태를 확인하려면 /api/analysis/status/{analysis_id}를 호출하세요."
        }
        
    except Exception as e:
        logger.error(f"고급 분석 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=f"분석 시작 실패: {str(e)}")

async def _run_advanced_analysis(analysis_id: str, request: AdvancedAnalysisRequest):
    """실제 분석 실행 (백그라운드)"""
    try:
        # 상태 업데이트
        analysis_cache[analysis_id]["status"] = "data_loading"
        analysis_cache[analysis_id]["message"] = "데이터를 불러오는 중..."
        analysis_cache[analysis_id]["progress"] = 10.0
        
        # 분석기 가져오기
        gpt_analyzer, mongodb_analyzer = await get_analyzers()
        
        # 데이터 가져오기
        data = await get_analysis_data(
            request.question,
            request.collection_name,
            request.dataset_id
        )
        
        # 상태 업데이트
        analysis_cache[analysis_id]["status"] = "analyzing"
        analysis_cache[analysis_id]["message"] = "GPT Reflection 분석 중..."
        analysis_cache[analysis_id]["progress"] = 20.0
        
        # GPT Reflection 분석 설정
        gpt_analyzer.max_reflections = request.max_reflections
        gpt_analyzer.target_score = request.target_score
        
        # 분석 실행
        if request.use_reflection:
            result = gpt_analyzer.analyze_with_reflection(request.question, data)
        else:
            # 단순 분석 (Reflection 없이)
            result = await _simple_gpt_analysis(request.question, data)
        
        # 결과 포맷팅
        formatted_result = gpt_analyzer.format_result_for_display(result)
        
        # 최종 결과 저장
        final_result = AdvancedAnalysisResponse(
            analysis_id=analysis_id,
            question=request.question,
            final_report=result.final_report,
            analysis_summary=formatted_result["analysis_summary"],
            reflection_history=formatted_result["reflection_history"],
            data_summary=result.data_summary,
            created_at=datetime.now(),
            execution_time=result.execution_time
        )
        
        # 상태 완료로 업데이트
        analysis_cache[analysis_id] = {
            "status": "completed",
            "progress": 100.0,
            "current_step": result.total_steps,
            "total_steps": request.max_reflections,
            "message": "분석이 완료되었습니다.",
            "result": final_result,
            "completion_time": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"분석 실행 실패: {e}")
        analysis_cache[analysis_id] = {
            "status": "failed",
            "progress": 0.0,
            "current_step": 0,
            "total_steps": request.max_reflections,
            "message": f"분석 실패: {str(e)}",
            "error": str(e)
        }

async def _simple_gpt_analysis(question: str, data: pd.DataFrame) -> AnalysisResult:
    """단순 GPT 분석 (Reflection 없이)"""
    from datetime import datetime
    import time
    
    start_time = time.time()
    
    # 데이터 요약
    data_summary = f"총 {len(data)}개 데이터 포인트"
    
    # 단순 분석 (Reflection Step 없이)
    gpt_analyzer, _ = await get_analyzers()
    analysis = gpt_analyzer._generate_initial_analysis(question, data_summary)
    
    execution_time = time.time() - start_time
    
    # AnalysisResult 객체 생성
    return AnalysisResult(
        question=question,
        final_report=analysis,
        reflection_steps=[],
        total_steps=1,
        execution_time=execution_time,
        final_score=8.0,  # 기본 점수
        data_summary=data_summary
    )

@router.get("/analysis/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """분석 상태 확인"""
    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="분석 ID를 찾을 수 없습니다.")
    
    cache_data = analysis_cache[analysis_id]
    
    status_response = {
        "analysis_id": analysis_id,
        "status": cache_data["status"],
        "progress": cache_data["progress"],
        "current_step": cache_data["current_step"],
        "total_steps": cache_data["total_steps"],
        "message": cache_data["message"]
    }
    
    # 완료된 경우 결과 포함
    if cache_data["status"] == "completed" and "result" in cache_data:
        status_response["result"] = cache_data["result"].dict()
    
    # 실패한 경우 에러 정보 포함
    if cache_data["status"] == "failed" and "error" in cache_data:
        status_response["error"] = cache_data["error"]
    
    return status_response

@router.get("/analysis/result/{analysis_id}", response_model=AdvancedAnalysisResponse)
async def get_analysis_result(analysis_id: str):
    """분석 결과 가져오기"""
    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="분석 ID를 찾을 수 없습니다.")
    
    cache_data = analysis_cache[analysis_id]
    
    if cache_data["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"분석이 아직 완료되지 않았습니다. 현재 상태: {cache_data['status']}"
        )
    
    if "result" not in cache_data:
        raise HTTPException(status_code=500, detail="분석 결과를 찾을 수 없습니다.")
    
    return cache_data["result"]

@router.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """분석 결과 삭제"""
    if analysis_id not in analysis_cache:
        raise HTTPException(status_code=404, detail="분석 ID를 찾을 수 없습니다.")
    
    del analysis_cache[analysis_id]
    
    return {"message": "분석 결과가 삭제되었습니다."}

@router.get("/analysis/list")
async def list_analyses():
    """모든 분석 목록 조회"""
    analyses = []
    
    for analysis_id, cache_data in analysis_cache.items():
        analysis_info = {
            "analysis_id": analysis_id,
            "status": cache_data["status"],
            "progress": cache_data["progress"],
            "start_time": cache_data.get("start_time"),
            "message": cache_data["message"]
        }
        
        # 요청 정보 추가
        if "request" in cache_data:
            analysis_info["question"] = cache_data["request"].question
        
        # 완료 시간 추가
        if "completion_time" in cache_data:
            analysis_info["completion_time"] = cache_data["completion_time"]
        
        analyses.append(analysis_info)
    
    return {"analyses": analyses}

@router.get("/analysis/health")
async def analysis_health_check():
    """분석 서비스 상태 확인"""
    try:
        # OpenAI API 키 확인
        openai_key = os.getenv("OPENAI_API_KEY")
        openai_available = bool(openai_key and openai_key.startswith("sk-"))
        
        # MongoDB 연결 확인
        await db.command("ping")
        mongodb_available = True
        
        # 분석기 초기화 확인
        try:
            gpt_analyzer, mongodb_analyzer = await get_analyzers()
            analyzers_available = True
        except Exception:
            analyzers_available = False
        
        return {
            "status": "healthy" if all([openai_available, mongodb_available, analyzers_available]) else "degraded",
            "services": {
                "openai_api": openai_available,
                "mongodb": mongodb_available,
                "analyzers": analyzers_available
            },
            "active_analyses": len(analysis_cache),
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now()
        }