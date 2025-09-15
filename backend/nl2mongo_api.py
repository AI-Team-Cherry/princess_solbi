from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
import logging
import json
import re
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import asyncio

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)

# MongoDB 연결 - 환경변수 또는 기본값 사용
MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME") or os.getenv("DATABASE_NAME", "musinsa_db")
MODEL_ID = os.getenv("MODEL_ID", "kakaocorp/kanana-nano-2.1b-instruct")

if not MONGODB_URI:
    MONGODB_URI = "mongodb+srv://musinsa:musinsa@cluster0.ed1m1eg.mongodb.net/musinsa?retryWrites=true&w=majority&appName=Cluster0"
    logger.warning("Using default MongoDB URI")

client = AsyncIOMotorClient(MONGODB_URI, unicode_decode_error_handler="ignore")
db: AsyncIOMotorDatabase = client[DB_NAME]

# 라우터 생성
router = APIRouter(prefix="/api", tags=["nl2mongo"])

# Pydantic 모델들
class NL2MongoRequest(BaseModel):
    query: str = Field(..., min_length=1, description="한국어 자연어 질의")
    limit: Optional[int] = Field(100, ge=1, le=5000, description="결과 제한")

class NL2AnalysisRequest(BaseModel):
    dataset_id: str = Field(..., description="분석할 데이터셋 ID")
    query: str = Field(..., min_length=1, description="한국어 분석 요청")

# MongoDB 스키마 정보 (실제 musinsa_db 스키마 반영)
SCHEMA_INFO = {
    "collections": {
        "reviews": {
            "fields": [
                "product_id", "user_id", "score", "text", 
                "review_created_at",  # str: 'YYYY-MM-DD'
                "overall_sentiment",  # str: 긍정/부정/중립
                "quality_sentiment", "delivery_sentiment", "price_sentiment", 
                "design_sentiment", "size_sentiment", "texture_sentiment", 
                "color_sentiment", "package_sentiment", "silhouette_sentiment", 
                "comfort_sentiment", "material_sentiment"
            ],
            "description": "상품 리뷰 데이터",
            "date_fields": ["review_created_at"],
            "date_format": "%Y-%m-%d"
        },
        "orders": {
            "fields": [
                "order_id", "buyer_id", "seller_id", "brand_name",
                "product_id", "quantity", "price", "total_amount", 
                "order_date"  # str: 'YYYY-MM-DD'
            ],
            "description": "주문 데이터", 
            "date_fields": ["order_date"],
            "date_format": "%Y-%m-%d"
        },
        "product": {
            "fields": [
                "product_id", "name", "brand", "category_l1", "gender", 
                "price", "rating_avg", "reviews_count"
            ],
            "description": "상품 정보",
            "date_fields": []
        },
        "buyers": {
            "fields": ["buyer_id", "gender", "age", "marketing_opt_in"],
            "description": "구매자 정보 (민감정보 제외)",
            "sensitive_fields": ["email", "phone", "address", "postal_code"]
        },
        "sellers": {
            "fields": ["seller_id", "brand_name", "categories"],
            "description": "판매자 정보",
            "sensitive_fields": ["email"]
        },
        "users": {
            "fields": ["emp_no", "team"],
            "description": "사용자 정보",
            "sensitive_fields": ["password"]
        },
        "review_image_path": {
            "fields": ["product_id", "user_id", "review_index", "image_name"],
            "description": "리뷰 이미지 경로",
            "date_fields": []
        },
        "image_path_with_vec": {
            "fields": ["product_id", "image_file", "image_vector"],
            "description": "이미지 벡터 데이터",
            "date_fields": []
        }
    }
}

# 허용된 MongoDB 연산자
ALLOWED_OPERATORS = {
    "$match", "$project", "$group", "$sort", "$limit", "$lookup", "$unwind", 
    "$addFields", "$count", "$sample", "$skip", "$facet"
}

# LLM 서비스 클래스
class NL2MongoLLMService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self.initialized = False
        
    async def initialize(self):
        """LLM 모델 초기화"""
        if not self.initialized:
            try:
                logger.info(f"Loading NL2Mongo LLM model: {MODEL_ID}")
                self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
                self.model = AutoModelForCausalLM.from_pretrained(
                    MODEL_ID,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    low_cpu_mem_usage=True
                )
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model.to(self.device)
                
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                    
                self.initialized = True
                logger.info(f"NL2Mongo LLM model loaded successfully on {self.device}")
            except Exception as e:
                logger.error(f"Failed to load NL2Mongo LLM model: {str(e)}")
                self.model = "dummy"
                self.initialized = True
                
    def create_nl2mongo_prompt(self, query: str) -> str:
        """자연어를 MongoDB 파이프라인으로 변환하는 프롬프트 생성"""
        schema_text = ""
        for collection, info in SCHEMA_INFO["collections"].items():
            fields = [f for f in info["fields"] if f not in info.get("sensitive_fields", [])]
            schema_text += f"- {collection}: {', '.join(fields)}\n"
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""너는 **MongoDB 전문가이자 UI 보조 시스템**이다.
**데이터셋 추출 페이지는 자연어 입력을 중심으로 동작**한다.
사용자가 한국어로 질의하면 이를 **MongoDB Aggregation Pipeline(JSON)**으로 변환해야 한다.

단, 쿼리를 만들기 위해 **필수 조건이 불완전하거나 모호**하다면,
옆 패널에서 사용자가 직접 보완할 수 있도록 **선택 후보 옵션(missing_options)**을 함께 반환한다.

## 출력 형식
항상 **단일 JSON 객체**만 출력한다. (코드블록 금지, 설명 금지)

{{
  "pipeline": [...],
  "missing_options": [
    {{
      "field": "string",
      "description": "string",
      "candidates": ["값1", "값2", "값3"]
    }}
  ]
}}

## 공통 규칙
* pipeline은 **유효한 MongoDB Aggregation Pipeline(JSON 배열)**이어야 한다.
* $limit이 없으면 자동으로 100을 포함하고, 최대 5000을 넘지 않는다.
* **민감정보는 절대 포함하지 않는다.** 금지 필드:
  - buyers.email, buyers.phone, buyers.address, buyers.postal_code
  - users.password, sellers.email
* **날짜 비교가 필요하면 반드시 문자열 날짜를 Date로 변환**하라:
  예) {{"$addFields": {{"_asDate": {{"$dateFromString": {{"dateString": "$review_created_at", "format": "%Y-%m-%d"}}}}}}}}
* "이번 달/지난 주" 같은 기간은 ISODate 범위로 변환 ({{{{month_start}}}}, {{{{month_end}}}} 템플릿 사용)
* 모호한 요청: pipeline에는 broad match, missing_options에 세부 후보 제시

## 실제 스키마 (musinsa_db)
### reviews
주요 필드: product_id, user_id, score, text, review_created_at (str: 'YYYY-MM-DD'), 
overall_sentiment (긍정/부정/중립), quality_sentiment, delivery_sentiment, price_sentiment,
design_sentiment, size_sentiment, texture_sentiment, color_sentiment, package_sentiment

### orders  
주요 필드: order_id, buyer_id, seller_id, brand_name, product_id, quantity, price, 
total_amount, order_date (str: 'YYYY-MM-DD')

### product
주요 필드: product_id, name, brand, category_l1, gender, price, rating_avg, reviews_count

### buyers (PII 금지: email, phone, address, postal_code)
주요 필드: buyer_id, gender, age, marketing_opt_in

### sellers (PII 금지: email)
주요 필드: seller_id, brand_name, categories

## 조인 힌트
* reviews.product_id ↔ product.product_id
* orders.product_id ↔ product.product_id  
* orders.buyer_id ↔ buyers.buyer_id (PII 금지)

## missing_options 권장 후보
* 감성 세부: "전체 부정", "품질 관련 부정", "배송 관련 부정", "가격 관련 부정", "디자인 관련 부정"
* 기간: "최근 7일", "이번 달", "지난 달", "최근 3개월"
* 평점: "별점 4 이상", "별점 4.5 이상", "별점 5점만"
* 카테고리: "상의/스웨트", "하의/데님", "신발", "가방", "액세서리"

현재 날짜: {current_date}
한국어 질의: "{query}"

JSON 응답:"""
        
        return prompt
    
    async def generate_pipeline(self, query: str) -> Dict[str, Any]:
        """자연어 쿼리를 MongoDB 파이프라인으로 변환"""
        if not self.initialized:
            await self.initialize()
            
        prompt = self.create_nl2mongo_prompt(query)
        
        if self.model == "dummy":
            return self._generate_dummy_pipeline(query)
            
        try:
            inputs = self.tokenizer.encode(prompt, return_tensors="pt", truncate=True, max_length=1024).to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=512,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response_text = response[len(prompt):].strip()
            
            # JSON 추출 및 파싱
            parsed_response = self._extract_and_validate_response(response_text)
            pipeline = parsed_response["pipeline"]
            missing_options = parsed_response["missing_options"]
            
            return {
                "success": True,
                "pipeline": pipeline,
                "collection": self._infer_collection(query),
                "explanation": self._generate_explanation(query, pipeline),
                "missing_options": missing_options
            }
            
        except Exception as e:
            logger.error(f"LLM pipeline generation error: {str(e)}")
            return self._generate_dummy_pipeline(query)
    
    def _extract_and_validate_response(self, text: str) -> Dict[str, Any]:
        """텍스트에서 JSON 응답 추출 및 검증"""
        # JSON 객체 패턴 찾기
        json_pattern = r'\{.*?\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                response = json.loads(match)
                if isinstance(response, dict) and "pipeline" in response:
                    # 파이프라인 안전성 검증
                    pipeline = response.get("pipeline", [])
                    if isinstance(pipeline, list):
                        validated_pipeline = self._validate_pipeline_safety(pipeline)
                        if validated_pipeline:
                            return {
                                "pipeline": validated_pipeline,
                                "missing_options": response.get("missing_options", [])
                            }
            except json.JSONDecodeError:
                continue
        
        # JSON이 없으면 기본 응답 반환
        return {
            "pipeline": [{"$match": {}}, {"$limit": 100}],
            "missing_options": []
        }
    
    def _validate_pipeline_safety(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """파이프라인 안전성 검증"""
        validated = []
        
        for stage in pipeline:
            if not isinstance(stage, dict):
                continue
                
            stage_ops = list(stage.keys())
            if not stage_ops:
                continue
                
            stage_op = stage_ops[0]
            
            # 허용된 연산자만 통과
            if stage_op not in ALLOWED_OPERATORS:
                logger.warning(f"Blocked unauthorized operation: {stage_op}")
                continue
            
            # $where 및 JavaScript 차단
            stage_str = str(stage)
            if any(banned in stage_str.lower() for banned in ["$where", "function", "mapreduce", "$javascript"]):
                logger.warning(f"Blocked JavaScript in stage: {stage_op}")
                continue
            
            # 민감정보 필드 제거
            cleaned_stage = self._remove_sensitive_fields(stage)
            validated.append(cleaned_stage)
        
        # 기본 limit 추가
        has_limit = any("$limit" in str(stage) for stage in validated)
        if not has_limit:
            validated.append({"$limit": 100})
            
        return validated
    
    def _remove_sensitive_fields(self, stage: Dict[str, Any]) -> Dict[str, Any]:
        """민감정보 필드 제거"""
        sensitive_patterns = ["email", "phone", "address", "postal_code", "password"]
        stage_str = json.dumps(stage)
        
        for pattern in sensitive_patterns:
            if pattern in stage_str.lower():
                logger.warning(f"Removed sensitive field pattern: {pattern}")
                # 간단한 제거 (실제로는 더 정교한 처리 필요)
                stage_str = re.sub(rf'["\'].*{pattern}.*["\']', '""', stage_str, flags=re.IGNORECASE)
        
        try:
            return json.loads(stage_str)
        except:
            return stage
    
    def _infer_collection(self, query: str) -> str:
        """질의에서 컬렉션 추론"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["리뷰", "평점", "후기", "댓글"]):
            return "reviews"
        elif any(word in query_lower for word in ["주문", "구매", "결제", "매출"]):
            return "orders"
        elif any(word in query_lower for word in ["상품", "제품", "브랜드", "카테고리"]):
            return "product"
        elif any(word in query_lower for word in ["구매자", "고객", "사용자"]):
            return "buyers"
        else:
            return "reviews"  # 기본값
    
    def _generate_explanation(self, query: str, pipeline: List[Dict[str, Any]]) -> str:
        """파이프라인 설명 생성"""
        explanations = []
        
        for stage in pipeline:
            stage_op = list(stage.keys())[0] if stage else ""
            
            if stage_op == "$match":
                explanations.append("조건에 맞는 문서 필터링")
            elif stage_op == "$project":
                explanations.append("필요한 필드만 선택")
            elif stage_op == "$group":
                explanations.append("데이터 그룹화 및 집계")
            elif stage_op == "$sort":
                explanations.append("결과 정렬")
            elif stage_op == "$limit":
                limit_val = stage.get("$limit", 100)
                explanations.append(f"상위 {limit_val}개 결과만 반환")
            elif stage_op == "$lookup":
                explanations.append("다른 컬렉션과 조인")
        
        return " → ".join(explanations) if explanations else "기본 데이터 조회"
    
    def _generate_dummy_pipeline(self, query: str) -> Dict[str, Any]:
        """폴백용 더미 파이프라인 생성"""
        query_lower = query.lower()
        
        # 간단한 키워드 기반 파이프라인 생성
        pipeline = []
        match_stage = {}
        missing_options = []
        
        # 날짜 필드 처리를 위한 addFields 단계
        needs_date_conversion = False
        date_field = None
        
        # 컬렉션별 날짜 필드 결정
        if "리뷰" in query_lower or "후기" in query_lower:
            date_field = "review_created_at"
            needs_date_conversion = True
        elif "주문" in query_lower or "매출" in query_lower:
            date_field = "order_date" 
            needs_date_conversion = True
            
        # 감성 분석 관련 (유연한 매칭 + 평점 기반 추론)
        if "부정" in query_lower or "나쁜" in query_lower:
            # 감성 필드가 없을 수도 있으니 평점 기반으로도 매칭
            match_stage["$or"] = [
                {"overall_sentiment": {"$in": ["부정", "부정적", "negative", "NEG", "Negative"]}},
                {"score": {"$lte": 2}}  # 평점 2점 이하도 부정으로 간주
            ]
            missing_options.append({
                "field": "sentiment_detail",
                "description": "부정적인 리뷰의 구체적인 범주를 선택하세요",
                "candidates": ["전체 부정", "품질 관련 부정", "배송 관련 부정", "가격 관련 부정", "디자인 관련 부정", "사이즈 관련 부정", "색상 관련 부정"]
            })
        elif "긍정" in query_lower or "좋은" in query_lower:
            match_stage["$or"] = [
                {"overall_sentiment": {"$in": ["긍정", "긍정적", "positive", "POS", "Positive"]}},
                {"score": {"$gte": 4}}  # 평점 4점 이상도 긍정으로 간주
            ]
        
        # 평점 조건
        if "높은" in query_lower and "평점" in query_lower:
            match_stage["score"] = {"$gte": 4}
            missing_options.append({
                "field": "score_threshold", 
                "description": "'높은' 평점의 기준을 선택하세요",
                "candidates": ["별점 4 이상", "별점 4.5 이상", "별점 5점만"]
            })
        
        # 날짜 조건 확인 및 처리
        has_date = any(word in query_lower for word in ["이번달", "이번 달", "지난달", "지난 주", "최근"])
        
        # 파이프라인에 날짜 변환 단계 추가 (조건부 변환)
        if needs_date_conversion and date_field:
            pipeline.append({
                "$addFields": {
                    "_asDate": {
                        "$cond": [
                            {"$eq": [{"$type": f"${date_field}"}, "string"]},
                            {
                                "$dateFromString": {
                                    "dateString": f"${date_field}",
                                    "format": "%Y-%m-%d"
                                }
                            },
                            f"${date_field}"
                        ]
                    }
                }
            })
            
            # 날짜 기반 매치 조건
            if "이번달" in query_lower or "이번 달" in query_lower:
                now = datetime.now()
                start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_of_month = (start_of_month.replace(month=start_of_month.month + 1) if start_of_month.month < 12 
                              else start_of_month.replace(year=start_of_month.year + 1, month=1)) - timedelta(days=1)
                match_stage["_asDate"] = {
                    "$gte": start_of_month,
                    "$lte": end_of_month
                }
                
        if not has_date and needs_date_conversion:
            missing_options.append({
                "field": "date_range", 
                "description": "기간이 지정되지 않았습니다. 범위를 선택하세요",
                "candidates": ["최근 7일", "이번 달", "지난 달", "최근 3개월"]
            })
        
        # 카테고리 관련
        if "카테고리" in query_lower or "범주" in query_lower:
            missing_options.append({
                "field": "category_l1",
                "description": "카테고리를 선택하세요",
                "candidates": ["상의/스웨트", "하의/데님", "신발", "가방", "액세서리"]
            })
        
        # 매치 조건이 있으면 추가
        if match_stage:
            pipeline.append({"$match": match_stage})
        
        # _asDate 필드 제거 (출력에서 숨김)
        if needs_date_conversion:
            pipeline.append({
                "$project": {
                    "_asDate": 0
                }
            })
            
        pipeline.append({"$limit": 100})
        
        return {
            "success": True,
            "pipeline": pipeline,
            "collection": self._infer_collection(query),
            "explanation": f"'{query}' 조건으로 데이터 조회",
            "missing_options": missing_options
        }

# LLM 서비스 인스턴스
nl2mongo_llm = NL2MongoLLMService()

# API 엔드포인트들
@router.post("/nl2mongo")
async def convert_nl_to_mongo(request: NL2MongoRequest):
    """자연어를 MongoDB 파이프라인으로 변환"""
    try:
        logger.info(f"NL2Mongo request: {request.query}")
        
        # LLM으로 파이프라인 생성
        result = await nl2mongo_llm.generate_pipeline(request.query)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail="파이프라인 생성에 실패했습니다")
        
        pipeline = result["pipeline"]
        collection = result["collection"]
        
        # MongoDB에서 실행하여 미리보기 생성
        try:
            # 컬렉션 존재 확인
            collections = await db.list_collection_names()
            if collection not in collections:
                collection = "reviews"  # 기본값으로 폴백
            
            # 파이프라인 실행
            cursor = db[collection].aggregate(pipeline)
            preview_data = await cursor.to_list(length=min(request.limit or 100, 200))
            
            # ObjectId를 문자열로 변환 및 인코딩 문제 해결
            for doc in preview_data:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                
                # 텍스트 필드 인코딩 문제 해결
                for key, value in doc.items():
                    if isinstance(value, bytes):
                        try:
                            doc[key] = value.decode("utf-8", errors="ignore")
                        except:
                            doc[key] = str(value)
                    elif isinstance(value, str):
                        # 이미 문자열이면 그대로 유지
                        doc[key] = value
            
            # 전체 카운트 추정
            count_pipeline = [stage for stage in pipeline if "$limit" not in str(stage)]
            if count_pipeline:
                count_cursor = db[collection].aggregate(count_pipeline + [{"$count": "total"}])
                count_result = await count_cursor.to_list(length=1)
                total_count = count_result[0]["total"] if count_result else len(preview_data)
            else:
                total_count = len(preview_data)
            
            return {
                "success": True,
                "pipeline": pipeline,
                "collection": collection,
                "explanation": result["explanation"],
                "preview": preview_data,
                "total_count": total_count,
                "query_interpretation": f"'{request.query}' → MongoDB 파이프라인 변환 완료",
                "missing_options": result.get("missing_options", [])
            }
            
        except Exception as db_error:
            logger.error(f"MongoDB execution error: {str(db_error)}")
            
            # DB 에러 시에도 파이프라인은 반환
            return {
                "success": True,
                "pipeline": pipeline,
                "collection": collection,
                "explanation": result["explanation"],
                "preview": [],
                "total_count": 0,
                "query_interpretation": f"'{request.query}' → 파이프라인 생성됨 (실행 에러: {str(db_error)})"
            }
            
    except Exception as e:
        logger.error(f"NL2Mongo error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"자연어 변환 중 오류 발생: {str(e)}")

@router.get("/nl2mongo/examples")
async def get_nl2mongo_examples():
    """자연어 쿼리 예시 제공"""
    return {
        "examples": [
            {
                "query": "이번달 부정 리뷰 보여줘",
                "description": "이번 달에 작성된 평점 2점 이하 리뷰 조회"
            },
            {
                "query": "10만원 이상 주문만 보여줘",
                "description": "주문 금액이 10만원 이상인 주문들 조회"
            },
            {
                "query": "브랜드별 평균 평점 높은 순으로 정렬",
                "description": "브랜드별로 평균 리뷰 점수를 계산하고 내림차순 정렬"
            },
            {
                "query": "여성 상품 중 가격대별 개수",
                "description": "여성 대상 상품들을 가격대별로 그룹핑하여 개수 집계"
            },
            {
                "query": "최근 일주일 주문량 많은 상품 TOP 10",
                "description": "지난 7일간 주문량이 많은 상품 상위 10개 조회"
            }
        ]
    }