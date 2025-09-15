"""
자연어를 SQL 쿼리로 변환하는 모듈
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
import requests

logger = logging.getLogger(__name__)

class NaturalLanguageToSQL:
    def __init__(self):
        """자연어-SQL 변환기 초기화"""
        logger.info("자연어-SQL 변환기 초기화 완료")
        
        # 데이터베이스 스키마 정의
        self.database_schema = {
            "reviews": {
                "columns": ["_id", "product_id", "user_id", "rating", "comment", "sentiment", "created_at"],
                "description": "리뷰 데이터"
            },
            "products": {
                "columns": ["_id", "name", "brand", "category", "price", "description", "created_at"],
                "description": "상품 데이터"
            },
            "orders": {
                "columns": ["_id", "user_id", "product_id", "quantity", "total_amount", "status", "created_at"],
                "description": "주문 데이터"
            },
            "buyers": {
                "columns": ["_id", "name", "email", "age", "gender", "created_at"],
                "description": "구매자 데이터"
            }
        }
        
        # 한국어 시간 표현 매핑
        self.time_mappings = {
            "오늘": 0,
            "어제": -1,
            "그제": -2,
            "이번주": "this_week",
            "지난주": "last_week",
            "이번달": "this_month",
            "지난달": "last_month",
            "올해": "this_year",
            "작년": "last_year"
        }
        
        # 감정 표현 매핑
        self.sentiment_mappings = {
            "긍정적": "positive",
            "부정적": "negative",
            "중립적": "neutral",
            "좋은": "positive",
            "나쁜": "negative",
            "불만": "negative",
            "만족": "positive"
        }

    def parse_natural_language(self, text: str) -> Dict[str, Any]:
        """자연어를 파싱하여 쿼리 요소 추출"""
        query_elements = {
            "collection": None,
            "filters": {},
            "projection": None,
            "sort": None,
            "limit": None,
            "aggregation": []
        }
        
        # 컬렉션 추론
        collection_keywords = {
            "리뷰": "reviews",
            "상품": "products", 
            "제품": "products",
            "고객": "customers",
            "사용자": "users",
            "주문": "orders",
            "판매": "sales"
        }
        
        for keyword, collection in collection_keywords.items():
            if keyword in text:
                query_elements["collection"] = collection
                break
        
        # 시간 필터 추출
        time_filter = self._extract_time_filter(text)
        if time_filter:
            query_elements["filters"].update(time_filter)
        
        # 감정 필터 추출
        sentiment_filter = self._extract_sentiment_filter(text)
        if sentiment_filter:
            query_elements["filters"].update(sentiment_filter)
        
        # 정렬 추출
        if "최신" in text or "최근" in text:
            query_elements["sort"] = {"created_at": -1}
        elif "오래된" in text:
            query_elements["sort"] = {"created_at": 1}
        
        # 제한 추출
        limit_match = re.search(r'(\d+)개', text)
        if limit_match:
            query_elements["limit"] = int(limit_match.group(1))
        
        # 집계 연산 추출
        if "개수" in text or "몇 개" in text:
            query_elements["aggregation"].append({"$count": "total"})
        elif "평균" in text:
            field = self._extract_numeric_field(text)
            if field:
                query_elements["aggregation"].append({
                    "$group": {
                        "_id": None,
                        "average": {"$avg": f"${field}"}
                    }
                })
        
        return query_elements

    def _extract_time_filter(self, text: str) -> Optional[Dict[str, Any]]:
        """시간 관련 필터 추출"""
        now = datetime.now()
        
        for korean_time, offset in self.time_mappings.items():
            if korean_time in text:
                if isinstance(offset, int):
                    # 일 단위
                    start_date = (now + timedelta(days=offset)).replace(hour=0, minute=0, second=0)
                    end_date = start_date + timedelta(days=1)
                    return {
                        "created_at": {
                            "$gte": start_date.isoformat(),
                            "$lt": end_date.isoformat()
                        }
                    }
                elif offset == "this_week":
                    start_date = now - timedelta(days=now.weekday())
                    start_date = start_date.replace(hour=0, minute=0, second=0)
                    return {
                        "created_at": {"$gte": start_date.isoformat()}
                    }
                elif offset == "last_week":
                    start_date = now - timedelta(days=now.weekday() + 7)
                    end_date = start_date + timedelta(days=7)
                    return {
                        "created_at": {
                            "$gte": start_date.replace(hour=0, minute=0, second=0).isoformat(),
                            "$lt": end_date.replace(hour=0, minute=0, second=0).isoformat()
                        }
                    }
                elif offset == "this_month":
                    start_date = now.replace(day=1, hour=0, minute=0, second=0)
                    return {
                        "created_at": {"$gte": start_date.isoformat()}
                    }
                elif offset == "last_month":
                    if now.month == 1:
                        start_date = now.replace(year=now.year-1, month=12, day=1, hour=0, minute=0, second=0)
                    else:
                        start_date = now.replace(month=now.month-1, day=1, hour=0, minute=0, second=0)
                    end_date = now.replace(day=1, hour=0, minute=0, second=0)
                    return {
                        "created_at": {
                            "$gte": start_date.isoformat(),
                            "$lt": end_date.isoformat()
                        }
                    }
        
        return None

    def _extract_sentiment_filter(self, text: str) -> Optional[Dict[str, Any]]:
        """감정 관련 필터 추출"""
        for sentiment_key, keywords in self.sentiment_mappings.items():
            for keyword in keywords:
                if keyword in text:
                    return {"sentiment": {"$in": keywords}}
        return None

    def _extract_numeric_field(self, text: str) -> Optional[str]:
        """수치 필드 추출"""
        numeric_keywords = {
            "가격": "price",
            "점수": "score",
            "평점": "rating",
            "금액": "amount"
        }
        
        for keyword, field in numeric_keywords.items():
            if keyword in text:
                return field
        return None

    def _load_model(self):
        """T5 모델을 필요할 때 로드"""
        if not self.model_loaded:
            try:
                logger.info("T5 모델 로딩 시작...")
                self.tokenizer = T5Tokenizer.from_pretrained(self.model_name)
                self.model = T5ForConditionalGeneration.from_pretrained(self.model_name)
                self.model.to(self.device)
                self.model_loaded = True
                logger.info(f"T5 모델 로드 완료: {self.device}")
            except Exception as e:
                logger.error(f"T5 모델 로드 실패: {e}")
                self.model_loaded = False
                raise

    def generate_query_with_t5(self, text: str) -> str:
        """T5 모델을 사용하여 쿼리 생성"""
        try:
            self._load_model()
            prompt = f"translate Korean to MongoDB query: {text}"
            
            inputs = self.tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)
            inputs = inputs.to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs, 
                    max_length=200,
                    num_beams=4,
                    temperature=0.7,
                    early_stopping=True
                )
            
            query = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return query
        except Exception as e:
            logger.error(f"T5 모델 쿼리 생성 실패: {e}")
            return f"규칙 기반 변환: {text}"

    def convert_to_mongodb_query(self, natural_language: str) -> Dict[str, Any]:
        """자연어를 MongoDB 쿼리로 변환"""
        try:
            # 1. 규칙 기반 파싱
            query_elements = self.parse_natural_language(natural_language)
            
            # 2. MongoDB 쿼리 구성
            mongodb_query = {
                "collection": query_elements["collection"] or "reviews",  # 기본 컬렉션
                "operation": "find",
                "filter": query_elements["filters"],
                "options": {}
            }
            
            if query_elements["projection"]:
                mongodb_query["options"]["projection"] = query_elements["projection"]
            
            if query_elements["sort"]:
                mongodb_query["options"]["sort"] = query_elements["sort"]
            
            if query_elements["limit"]:
                mongodb_query["options"]["limit"] = query_elements["limit"]
            
            if query_elements["aggregation"]:
                mongodb_query["operation"] = "aggregate"
                mongodb_query["pipeline"] = []
                if query_elements["filters"]:
                    mongodb_query["pipeline"].append({"$match": query_elements["filters"]})
                mongodb_query["pipeline"].extend(query_elements["aggregation"])
            
            return {
                "success": True,
                "query": mongodb_query,
                "natural_language": natural_language,
                "parsed_elements": query_elements
            }
            
        except Exception as e:
            logger.error(f"쿼리 변환 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "natural_language": natural_language
            }

# 싱글톤 인스턴스
nl_to_query_converter = None

def get_nl_to_query_converter():
    """싱글톤 변환기 인스턴스 반환"""
    global nl_to_query_converter
    if nl_to_query_converter is None:
        nl_to_query_converter = NaturalLanguageToQuery()
    return nl_to_query_converter