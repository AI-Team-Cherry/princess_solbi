"""
한국어 자연어를 SQL 쿼리로 변환하는 모듈
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

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

    def convert_to_sql(self, natural_language: str) -> Dict[str, Any]:
        """자연어를 SQL 쿼리로 변환"""
        try:
            # 1. 자연어 파싱
            parsed_elements = self.parse_natural_language(natural_language)
            
            # 2. SQL 쿼리 생성
            sql_query = self.build_sql_query(parsed_elements)
            
            return {
                "success": True,
                "sql": sql_query,
                "natural_language": natural_language,
                "parsed_elements": parsed_elements
            }
            
        except Exception as e:
            logger.error(f"SQL 변환 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "natural_language": natural_language
            }

    def parse_natural_language(self, text: str) -> Dict[str, Any]:
        """자연어를 파싱하여 SQL 쿼리 요소 추출"""
        query_elements = {
            "table": None,
            "select": [],
            "where": [],
            "order_by": None,
            "limit": None,
            "aggregate": None
        }
        
        # 테이블 추론
        table_keywords = {
            "리뷰": "reviews",
            "상품": "products", 
            "제품": "products",
            "고객": "buyers",
            "구매자": "buyers",
            "사용자": "buyers",
            "주문": "orders"
        }
        
        for keyword, table in table_keywords.items():
            if keyword in text:
                query_elements["table"] = table
                break
        
        # 기본 테이블이 없으면 reviews로 설정
        if not query_elements["table"]:
            query_elements["table"] = "reviews"
        
        # SELECT 절 추출
        if "출력" in text or "보여줘" in text or "조회" in text:
            query_elements["select"] = ["*"]
        elif "개수" in text or "몇 개" in text:
            query_elements["aggregate"] = "COUNT"
            query_elements["select"] = ["COUNT(*) as count"]
        elif "평균" in text:
            query_elements["aggregate"] = "AVG"
            field = self._extract_numeric_field(text)
            if field:
                query_elements["select"] = [f"AVG({field}) as average"]
        else:
            query_elements["select"] = ["*"]  # 기본값
        
        # WHERE 절 추출
        where_conditions = []
        
        # 시간 필터
        time_condition = self._extract_time_condition(text)
        if time_condition:
            where_conditions.append(time_condition)
        
        # 감정 필터
        sentiment_condition = self._extract_sentiment_condition(text)
        if sentiment_condition:
            where_conditions.append(sentiment_condition)
        
        query_elements["where"] = where_conditions
        
        # ORDER BY 추출
        if "최신" in text or "최근" in text:
            query_elements["order_by"] = "created_at DESC"
        elif "오래된" in text:
            query_elements["order_by"] = "created_at ASC"
        
        # LIMIT 추출
        limit_match = re.search(r'(\d+)개', text)
        if limit_match:
            query_elements["limit"] = int(limit_match.group(1))
        
        return query_elements

    def _extract_time_condition(self, text: str) -> Optional[str]:
        """시간 관련 WHERE 조건 추출"""
        now = datetime.now()
        
        for korean_time, offset in self.time_mappings.items():
            if korean_time in text:
                if isinstance(offset, int):
                    # 일 단위
                    target_date = (now + timedelta(days=offset)).strftime('%Y-%m-%d')
                    return f"DATE(created_at) = '{target_date}'"
                elif offset == "this_week":
                    start_date = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
                    return f"created_at >= '{start_date}'"
                elif offset == "last_week":
                    start_date = (now - timedelta(days=now.weekday() + 7)).strftime('%Y-%m-%d')
                    end_date = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
                    return f"created_at >= '{start_date}' AND created_at < '{end_date}'"
                elif offset == "this_month":
                    start_date = now.replace(day=1).strftime('%Y-%m-%d')
                    return f"created_at >= '{start_date}'"
                elif offset == "last_month":
                    if now.month == 1:
                        start_date = now.replace(year=now.year-1, month=12, day=1).strftime('%Y-%m-%d')
                        end_date = now.replace(day=1).strftime('%Y-%m-%d')
                    else:
                        start_date = now.replace(month=now.month-1, day=1).strftime('%Y-%m-%d')
                        end_date = now.replace(day=1).strftime('%Y-%m-%d')
                    return f"created_at >= '{start_date}' AND created_at < '{end_date}'"
        
        return None

    def _extract_sentiment_condition(self, text: str) -> Optional[str]:
        """감정 관련 WHERE 조건 추출"""
        for korean_sentiment, english_sentiment in self.sentiment_mappings.items():
            if korean_sentiment in text:
                return f"sentiment = '{english_sentiment}'"
        return None

    def _extract_numeric_field(self, text: str) -> Optional[str]:
        """수치 필드 추출"""
        numeric_keywords = {
            "가격": "price",
            "점수": "rating",
            "평점": "rating",
            "금액": "total_amount",
            "수량": "quantity"
        }
        
        for keyword, field in numeric_keywords.items():
            if keyword in text:
                return field
        return "rating"  # 기본값

    def build_sql_query(self, elements: Dict[str, Any]) -> str:
        """파싱된 요소들로 SQL 쿼리 생성"""
        # SELECT 절
        select_clause = "SELECT " + ", ".join(elements["select"])
        
        # FROM 절
        from_clause = f"FROM {elements['table']}"
        
        # WHERE 절
        where_clause = ""
        if elements["where"]:
            where_clause = "WHERE " + " AND ".join(elements["where"])
        
        # ORDER BY 절
        order_clause = ""
        if elements["order_by"]:
            order_clause = f"ORDER BY {elements['order_by']}"
        
        # LIMIT 절
        limit_clause = ""
        if elements["limit"]:
            limit_clause = f"LIMIT {elements['limit']}"
        
        # SQL 쿼리 조합
        sql_parts = [select_clause, from_clause]
        if where_clause:
            sql_parts.append(where_clause)
        if order_clause:
            sql_parts.append(order_clause)
        if limit_clause:
            sql_parts.append(limit_clause)
        
        return " ".join(sql_parts) + ";"

    def convert_sql_to_mongodb(self, sql_query: str, elements: Dict[str, Any]) -> Dict[str, Any]:
        """SQL 쿼리를 MongoDB 쿼리로 변환 (백엔드 호환성을 위해)"""
        mongodb_query = {
            "collection": elements["table"],
            "operation": "aggregate" if elements["aggregate"] else "find",
            "filter": {},
            "options": {}
        }
        
        # WHERE 조건을 MongoDB 필터로 변환
        if elements["where"]:
            for condition in elements["where"]:
                if "sentiment =" in condition:
                    sentiment_value = condition.split("'")[1]
                    mongodb_query["filter"]["sentiment"] = sentiment_value
                elif "DATE(created_at)" in condition:
                    date_value = condition.split("'")[1]
                    mongodb_query["filter"]["created_at"] = {
                        "$gte": f"{date_value}T00:00:00",
                        "$lt": f"{date_value}T23:59:59"
                    }
                elif "created_at >=" in condition and "created_at <" in condition:
                    # 범위 조건 처리
                    parts = condition.split(" AND ")
                    start_date = parts[0].split("'")[1]
                    end_date = parts[1].split("'")[1]
                    mongodb_query["filter"]["created_at"] = {
                        "$gte": f"{start_date}T00:00:00",
                        "$lt": f"{end_date}T00:00:00"
                    }
                elif "created_at >=" in condition:
                    date_value = condition.split("'")[1]
                    mongodb_query["filter"]["created_at"] = {
                        "$gte": f"{date_value}T00:00:00"
                    }
        
        # ORDER BY
        if elements["order_by"]:
            if "DESC" in elements["order_by"]:
                field = elements["order_by"].replace(" DESC", "")
                mongodb_query["options"]["sort"] = {field: -1}
            elif "ASC" in elements["order_by"]:
                field = elements["order_by"].replace(" ASC", "")
                mongodb_query["options"]["sort"] = {field: 1}
        
        # LIMIT
        if elements["limit"]:
            mongodb_query["options"]["limit"] = elements["limit"]
        
        # Aggregation pipeline for COUNT/AVG
        if elements["aggregate"]:
            mongodb_query["pipeline"] = []
            if mongodb_query["filter"]:
                mongodb_query["pipeline"].append({"$match": mongodb_query["filter"]})
            
            if elements["aggregate"] == "COUNT":
                mongodb_query["pipeline"].append({"$count": "total"})
            elif elements["aggregate"] == "AVG":
                field = self._extract_numeric_field("")  # Use default
                mongodb_query["pipeline"].append({
                    "$group": {
                        "_id": None,
                        "average": {"$avg": f"${field}"}
                    }
                })
        
        return mongodb_query

# 싱글톤 인스턴스
nl_to_sql_converter = None

def get_nl_to_sql_converter():
    """싱글톤 변환기 인스턴스 반환"""
    global nl_to_sql_converter
    if nl_to_sql_converter is None:
        nl_to_sql_converter = NaturalLanguageToSQL()
    return nl_to_sql_converter