import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pymongo import MongoClient
try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not available. AI features will be limited.")
import matplotlib
matplotlib.use('Agg')  # 비대화형 백엔드 사용으로 팝업 방지
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Any, Tuple, Optional, Set
import re
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import pickle
import logging
from functools import lru_cache
import hashlib

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FieldInfo:
    """필드 정보 클래스"""
    name: str
    data_type: str
    sample_values: List[Any] = field(default_factory=list)
    common_patterns: List[str] = field(default_factory=list)
    semantic_type: Optional[str] = None  # 'date', 'amount', 'id', 'text', 'category'
    confidence: float = 0.0

@dataclass
class CollectionSchema:
    """컬렉션 스키마 클래스"""
    name: str
    fields: Dict[str, FieldInfo] = field(default_factory=dict)
    document_count: int = 0
    sample_documents: List[Dict] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class DatabaseSchema:
    """데이터베이스 스키마 클래스"""
    name: str
    collections: Dict[str, CollectionSchema] = field(default_factory=dict)
    last_analyzed: datetime = field(default_factory=datetime.now)
    schema_hash: str = ""

class SchemaAnalyzer:
    """동적 스키마 분석기"""
    
    def __init__(self):
        self.semantic_patterns = {
            'date': [
                r'.*date.*', r'.*time.*', r'.*created.*', r'.*updated.*', 
                r'.*timestamp.*', r'.*at$', r'.*when.*'
            ],
            'amount': [
                r'.*amount.*', r'.*price.*', r'.*cost.*', r'.*total.*',
                r'.*sum.*', r'.*value.*', r'.*money.*', r'.*fee.*'
            ],
            'id': [
                r'.*_id$', r'^id$', r'.*identifier.*', r'.*uuid.*', r'.*key.*'
            ],
            'category': [
                r'.*category.*', r'.*type.*', r'.*class.*', r'.*group.*',
                r'.*status.*', r'.*state.*', r'.*level.*'
            ],
            'text': [
                r'.*text.*', r'.*description.*', r'.*comment.*', r'.*note.*',
                r'.*message.*', r'.*content.*', r'.*review.*'
            ],
            'score': [
                r'.*score.*', r'.*rating.*', r'.*rank.*', r'.*grade.*',
                r'.*sentiment.*', r'.*confidence.*'
            ]
        }
    
    def analyze_database_schema(self, db, sample_size: int = 100) -> DatabaseSchema:
        """데이터베이스 전체 스키마 분석"""
        logger.info(f"데이터베이스 '{db.name}' 스키마 분석 시작...")
        
        schema = DatabaseSchema(name=db.name)
        
        for collection_name in db.list_collection_names():
            logger.info(f"컬렉션 '{collection_name}' 분석 중...")
            collection_schema = self.analyze_collection_schema(
                db[collection_name], sample_size
            )
            schema.collections[collection_name] = collection_schema
        
        # 스키마 해시 생성 (변경 감지용)
        schema.schema_hash = self._generate_schema_hash(schema)
        
        logger.info(f"스키마 분석 완료: {len(schema.collections)}개 컬렉션")
        return schema
    
    def analyze_collection_schema(self, collection, sample_size: int = 100) -> CollectionSchema:
        """컬렉션 스키마 분석"""
        schema = CollectionSchema(
            name=collection.name,
            document_count=collection.count_documents({})
        )
        
        if schema.document_count == 0:
            return schema
        
        # 샘플 문서 수집
        sample_docs = list(collection.aggregate([
            {'$sample': {'size': min(sample_size, schema.document_count)}}
        ]))
        
        schema.sample_documents = sample_docs[:5]  # 처음 5개만 저장
        
        # 필드 분석
        field_stats = defaultdict(lambda: {
            'types': Counter(),
            'samples': [],
            'null_count': 0
        })
        
        for doc in sample_docs:
            self._analyze_document(doc, field_stats)
        
        # 필드 정보 생성
        for field_name, stats in field_stats.items():
            field_info = self._create_field_info(field_name, stats, len(sample_docs))
            schema.fields[field_name] = field_info
        
        return schema
    
    def _analyze_document(self, doc: Dict, field_stats: Dict, prefix: str = ""):
        """문서의 필드들을 재귀적으로 분석"""
        for key, value in doc.items():
            field_name = f"{prefix}.{key}" if prefix else key
            
            if value is None:
                field_stats[field_name]['null_count'] += 1
            else:
                # 데이터 타입 분석
                if isinstance(value, dict):
                    field_stats[field_name]['types']['object'] += 1
                    # 중첩 객체 분석
                    self._analyze_document(value, field_stats, field_name)
                elif isinstance(value, list):
                    field_stats[field_name]['types']['array'] += 1
                    if value and not isinstance(value[0], (dict, list)):
                        field_stats[field_name]['samples'].extend(value[:3])
                elif isinstance(value, datetime):
                    field_stats[field_name]['types']['datetime'] += 1
                    field_stats[field_name]['samples'].append(value)
                elif isinstance(value, (int, float)):
                    field_stats[field_name]['types']['number'] += 1
                    field_stats[field_name]['samples'].append(value)
                elif isinstance(value, str):
                    field_stats[field_name]['types']['string'] += 1
                    field_stats[field_name]['samples'].append(value)
                else:
                    field_stats[field_name]['types']['other'] += 1
    
    def _create_field_info(self, field_name: str, stats: Dict, total_docs: int) -> FieldInfo:
        """필드 정보 객체 생성"""
        # 가장 일반적인 데이터 타입 결정
        most_common_type = stats['types'].most_common(1)[0][0] if stats['types'] else 'unknown'
        
        # 샘플 값들 정리
        samples = list(set(stats['samples'][:10]))  # 중복 제거하고 최대 10개
        
        # 시맨틱 타입 추론
        semantic_type = self._infer_semantic_type(field_name, samples, most_common_type)
        
        # 신뢰도 계산
        type_confidence = stats['types'].most_common(1)[0][1] / total_docs if stats['types'] else 0
        semantic_confidence = self._calculate_semantic_confidence(semantic_type, field_name, samples)
        confidence = (type_confidence + semantic_confidence) / 2
        
        return FieldInfo(
            name=field_name,
            data_type=most_common_type,
            sample_values=samples,
            semantic_type=semantic_type,
            confidence=confidence
        )
    
    def _infer_semantic_type(self, field_name: str, samples: List[Any], data_type: str) -> Optional[str]:
        """필드의 시맨틱 타입 추론"""
        field_lower = field_name.lower()
        
        # 패턴 매칭으로 시맨틱 타입 찾기
        for semantic_type, patterns in self.semantic_patterns.items():
            for pattern in patterns:
                if re.match(pattern, field_lower):
                    return semantic_type
        
        # 샘플 값 기반 추론
        if data_type == 'datetime':
            return 'date'
        elif data_type == 'number' and samples:
            if any(isinstance(v, float) or (isinstance(v, int) and v > 1000) for v in samples):
                return 'amount'
            elif all(isinstance(v, int) and 0 <= v <= 10 for v in samples if isinstance(v, int)):
                return 'score'
        elif data_type == 'string' and samples:
            if all(len(str(v)) < 50 for v in samples):
                return 'category'
            else:
                return 'text'
        
        return None
    
    def _calculate_semantic_confidence(self, semantic_type: Optional[str], field_name: str, samples: List[Any]) -> float:
        """시맨틱 타입 추론의 신뢰도 계산"""
        if not semantic_type:
            return 0.0
        
        confidence = 0.5  # 기본값
        
        # 필드명 매칭 보너스
        field_lower = field_name.lower()
        if semantic_type in self.semantic_patterns:
            for pattern in self.semantic_patterns[semantic_type]:
                if re.match(pattern, field_lower):
                    confidence += 0.3
                    break
        
        # 샘플 값 일관성 보너스
        if samples and len(samples) > 1:
            if semantic_type == 'amount' and all(isinstance(v, (int, float)) for v in samples):
                confidence += 0.2
            elif semantic_type == 'score' and all(isinstance(v, int) and 0 <= v <= 10 for v in samples):
                confidence += 0.2
        
        return min(1.0, confidence)
    
    def _generate_schema_hash(self, schema: DatabaseSchema) -> str:
        """스키마 해시 생성 (변경 감지용)"""
        schema_str = ""
        for coll_name, coll_schema in sorted(schema.collections.items()):
            schema_str += f"{coll_name}:{coll_schema.document_count}:"
            for field_name, field_info in sorted(coll_schema.fields.items()):
                schema_str += f"{field_name}-{field_info.data_type}-{field_info.semantic_type};"
        
        return hashlib.md5(schema_str.encode()).hexdigest()


class DynamicQueryBuilder:
    """동적 쿼리 빌더"""
    
    def __init__(self, schema: DatabaseSchema):
        self.schema = schema
        self.field_mappings = self._build_field_mappings()
    
    def _build_field_mappings(self) -> Dict[str, Dict[str, List[str]]]:
        """시맨틱 타입별 필드 매핑 구축"""
        mappings = defaultdict(lambda: defaultdict(list))
        
        for coll_name, coll_schema in self.schema.collections.items():
            for field_name, field_info in coll_schema.fields.items():
                if field_info.semantic_type and field_info.confidence > 0.5:
                    mappings[coll_name][field_info.semantic_type].append(field_name)
        
        return dict(mappings)
    
    def infer_collection(self, nl_query: str) -> str:
        """자연어 쿼리에서 컬렉션 추론"""
        query_lower = nl_query.lower()
        
        # 키워드 기반 매칭
        collection_keywords = {
            'orders': ['주문', '구매', '매출', '판매', 'order', 'purchase', 'sale'],
            'product': ['상품', '제품', '아이템', 'product', 'item'],
            'buyers': ['구매자', '고객', '사용자', 'buyer', 'customer', 'user'],
            'reviews': ['리뷰', '평가', '후기', 'review', 'rating', 'feedback'],
            'sellers': ['판매자', '셀러', 'seller', 'vendor']
        }
        
        scores = {}
        for collection, keywords in collection_keywords.items():
            if collection in self.schema.collections:
                score = sum(1 for keyword in keywords if keyword in query_lower)
                if score > 0:
                    scores[collection] = score
        
        # 가장 높은 점수의 컬렉션 반환
        if scores:
            return max(scores, key=scores.get)
        
        # 기본값: 가장 큰 컬렉션
        return max(
            self.schema.collections.keys(),
            key=lambda x: self.schema.collections[x].document_count
        )
    
    def build_aggregation_pipeline(self, nl_query: str, collection_name: str, use_ai: bool = True) -> List[Dict]:
        """자연어 쿼리에서 MongoDB 집계 파이프라인 생성"""
        if use_ai:
            return self._build_ai_pipeline(nl_query, collection_name)
        else:
            return self._build_rule_based_pipeline(nl_query, collection_name)
    
    def _build_ai_pipeline(self, nl_query: str, collection_name: str) -> List[Dict]:
        """AI 기반 파이프라인 생성"""
        try:
            # 스키마 정보를 포함한 프롬프트 생성
            collection_schema = self.schema.collections[collection_name]
            schema_info = self._get_schema_context(collection_schema)
            
            prompt = f"""Convert the following natural language query to a MongoDB aggregation pipeline.

Task: Generate a valid MongoDB aggregation pipeline as a JSON array.

Collection: {collection_name}
Schema: {schema_info}
Natural Language Query: {nl_query}

Requirements:
1. Return only valid JSON array format
2. Use appropriate MongoDB operators ($match, $group, $sort, $limit, etc.)
3. Consider field types and relationships
4. Include proper Korean text handling for string fields

MongoDB aggregation pipeline:"""
            
            # AI 모델로 변환 (가능한 경우)
            if hasattr(self, 'text_generator') and self.text_generator:
                try:
                    response = self.text_generator(prompt, max_length=200, num_return_sequences=1)
                    pipeline_text = response[0]['generated_text'].replace(prompt, '').strip()
                    
                    # JSON 파싱 시도
                    import json
                    pipeline = json.loads(pipeline_text)
                    if isinstance(pipeline, list):
                        logger.info(f"AI 생성 파이프라인: {pipeline}")
                        return pipeline
                except Exception as e:
                    logger.warning(f"AI 파이프라인 생성 실패: {e}")
            
            # AI 실패시 향상된 규칙 기반 시스템 사용
            return self._build_enhanced_rule_pipeline(nl_query, collection_name)
            
        except Exception as e:
            logger.error(f"AI 파이프라인 생성 오류: {e}")
            return self._build_rule_based_pipeline(nl_query, collection_name)
    
    def _get_schema_context(self, collection_schema) -> str:
        """스키마 컨텍스트 생성"""
        fields = []
        for field_name, field_info in collection_schema.fields.items():
            fields.append(f"{field_name}: {field_info.data_type}")
        return "{ " + ", ".join(fields[:10]) + " }"
    
    def _build_enhanced_rule_pipeline(self, nl_query: str, collection_name: str) -> List[Dict]:
        """향상된 규칙 기반 파이프라인"""
        pipeline = []
        query_lower = nl_query.lower()
        field_map = self.field_mappings.get(collection_name, {})
        
        # 시간 범위 필터링
        if any(word in query_lower for word in ['이번 주', '이번달', '최근']):
            date_fields = field_map.get('date', [])
            if date_fields:
                from datetime import datetime, timedelta
                if '이번 주' in query_lower:
                    week_ago = datetime.now() - timedelta(weeks=1)
                elif '이번달' in query_lower:
                    month_ago = datetime.now() - timedelta(days=30)
                else:  # 최근
                    month_ago = datetime.now() - timedelta(days=7)
                    
                pipeline.append({
                    '$match': {
                        date_fields[0]: {'$gte': week_ago if '이번 주' in query_lower else month_ago}
                    }
                })
        
        # 집계 연산
        if any(word in query_lower for word in ['가장 많이', '베스트', 'top']):
            # 그룹화 및 정렬
            amount_fields = field_map.get('amount', [])
            if amount_fields:
                pipeline.extend([
                    {'$group': {
                        '_id': '$product_name' if 'product_name' in field_map else '$name',
                        'total': {'$sum': f'${amount_fields[0]}'}
                    }},
                    {'$sort': {'total': -1}},
                    {'$limit': 10}
                ])
            else:
                pipeline.extend([
                    {'$sort': {'order_date': -1} if 'order_date' in field_map else {'_id': -1}},
                    {'$limit': 20}
                ])
        else:
            # 기본: 최신 데이터
            date_fields = field_map.get('date', [])
            if date_fields:
                pipeline.append({'$sort': {date_fields[0]: -1}})
            pipeline.append({'$limit': 20})
        
        return pipeline
    
    def _build_rule_based_pipeline(self, nl_query: str, collection_name: str) -> List[Dict]:
        """기존 규칙 기반 파이프라인"""
        pipeline = []
        query_lower = nl_query.lower()
        
        collection_schema = self.schema.collections[collection_name]
        field_map = self.field_mappings.get(collection_name, {})
        
        # 1. Match 단계 구성
        match_conditions = self._build_match_conditions(nl_query, field_map)
        if match_conditions:
            pipeline.append({'$match': match_conditions})
        
        # 2. Group/Sort 단계 구성
        if any(word in query_lower for word in ['합계', '총', '전체']):
            pipeline.extend(self._build_sum_pipeline(field_map))
        elif any(word in query_lower for word in ['평균', 'average']):
            pipeline.extend(self._build_avg_pipeline(field_map))
        elif any(word in query_lower for word in ['순위', '탑', 'top', '상위']):
            pipeline.extend(self._build_top_pipeline(nl_query, field_map))
        elif any(word in query_lower for word in ['추세', '트렌드', 'trend']):
            pipeline.extend(self._build_trend_pipeline(field_map))
        else:
            # 기본: 최신 데이터
            date_fields = field_map.get('date', [])
            if date_fields:
                pipeline.append({'$sort': {date_fields[0]: -1}})
            pipeline.append({'$limit': 20})
        
        return pipeline
    
    def _build_match_conditions(self, nl_query: str, field_map: Dict[str, List[str]]) -> Dict:
        """매치 조건 구성"""
        conditions = {}
        
        # 날짜 조건
        date_fields = field_map.get('date', [])
        if date_fields:
            date_condition = self._extract_date_condition(nl_query)
            if date_condition:
                conditions[date_fields[0]] = date_condition
        
        # 카테고리 조건
        category_fields = field_map.get('category', [])
        if category_fields:
            category_condition = self._extract_category_condition(nl_query)
            if category_condition:
                conditions[category_fields[0]] = category_condition
        
        # 금액 조건
        amount_fields = field_map.get('amount', [])
        if amount_fields:
            amount_condition = self._extract_amount_condition(nl_query)
            if amount_condition:
                conditions[amount_fields[0]] = amount_condition
        
        return conditions
    
    def _extract_date_condition(self, nl_query: str) -> Optional[Dict]:
        """날짜 조건 추출"""
        # 날짜 패턴 매칭 (기존 로직 재사용)
        patterns = [
            (r'(\d{4})년\s*(\d{1,2})월', 'year_month'),
            (r'지난\s*(\d+)일', 'last_days'),
            (r'최근\s*(\d+)개월', 'last_months'),
        ]
        
        for pattern, pattern_type in patterns:
            match = re.search(pattern, nl_query)
            if match:
                return self._parse_date_pattern(match, pattern_type)
        
        return None
    
    def _parse_date_pattern(self, match, pattern_type: str) -> Dict:
        """날짜 패턴 파싱"""
        if pattern_type == 'year_month':
            year, month = int(match.group(1)), int(match.group(2))
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)
            return {'$gte': start_date, '$lt': end_date}
        elif pattern_type == 'last_days':
            days = int(match.group(1))
            start_date = datetime.now() - timedelta(days=days)
            return {'$gte': start_date}
        elif pattern_type == 'last_months':
            months = int(match.group(1))
            start_date = datetime.now() - timedelta(days=months * 30)
            return {'$gte': start_date}
        
        return {}
    
    def _extract_category_condition(self, nl_query: str) -> Optional[str]:
        """카테고리 조건 추출"""
        categories = ['아우터', '상의', '하의', '신발', '가방', '액세서리']
        query_lower = nl_query.lower()
        
        for category in categories:
            if category in query_lower:
                return category
        
        return None
    
    def _extract_amount_condition(self, nl_query: str) -> Optional[Dict]:
        """금액 조건 추출"""
        price_match = re.search(r'(\d+)만원?\s*(?:이상|이하|부터|까지)', nl_query)
        if price_match:
            price_value = int(price_match.group(1)) * 10000
            if '이상' in nl_query or '부터' in nl_query:
                return {'$gte': price_value}
            elif '이하' in nl_query or '까지' in nl_query:
                return {'$lte': price_value}
        
        return None
    
    def _build_sum_pipeline(self, field_map: Dict[str, List[str]]) -> List[Dict]:
        """합계 파이프라인 구성"""
        amount_fields = field_map.get('amount', [])
        if amount_fields:
            return [{
                '$group': {
                    '_id': None,
                    'total': {'$sum': f'${amount_fields[0]}'},
                    'count': {'$sum': 1}
                }
            }]
        return [{'$group': {'_id': None, 'count': {'$sum': 1}}}]
    
    def _build_avg_pipeline(self, field_map: Dict[str, List[str]]) -> List[Dict]:
        """평균 파이프라인 구성"""
        amount_fields = field_map.get('amount', [])
        if amount_fields:
            return [{
                '$group': {
                    '_id': None,
                    'average': {'$avg': f'${amount_fields[0]}'},
                    'count': {'$sum': 1}
                }
            }]
        return [{'$group': {'_id': None, 'count': {'$sum': 1}}}]
    
    def _build_top_pipeline(self, nl_query: str, field_map: Dict[str, List[str]]) -> List[Dict]:
        """상위 N개 파이프라인 구성"""
        # 제한 수 추출
        limit = 10
        num_match = re.search(r'(\d+)개', nl_query)
        if num_match:
            limit = int(num_match.group(1))
        
        # 그룹화 필드 결정
        category_fields = field_map.get('category', [])
        amount_fields = field_map.get('amount', [])
        
        if category_fields and amount_fields:
            return [
                {
                    '$group': {
                        '_id': f'${category_fields[0]}',
                        'total': {'$sum': f'${amount_fields[0]}'},
                        'count': {'$sum': 1}
                    }
                },
                {'$sort': {'total': -1}},
                {'$limit': limit}
            ]
        
        return [{'$sort': {'_id': -1}}, {'$limit': limit}]
    
    def _build_trend_pipeline(self, field_map: Dict[str, List[str]]) -> List[Dict]:
        """추세 분석 파이프라인 구성"""
        date_fields = field_map.get('date', [])
        amount_fields = field_map.get('amount', [])
        
        if date_fields:
            pipeline = [{
                '$group': {
                    '_id': {
                        'year': {'$year': f'${date_fields[0]}'},
                        'month': {'$month': f'${date_fields[0]}'}
                    },
                    'count': {'$sum': 1}
                }
            }]
            
            if amount_fields:
                pipeline[0]['$group']['total'] = {'$sum': f'${amount_fields[0]}'}
                pipeline[0]['$group']['avg'] = {'$avg': f'${amount_fields[0]}'}
            
            pipeline.append({'$sort': {'_id.year': 1, '_id.month': 1}})
            return pipeline
        
        return [{'$group': {'_id': None, 'count': {'$sum': 1}}}]


class DynamicMongoDBAnalyzer:
    """동적 MongoDB 자연어 분석기"""
    
    def __init__(self, connection_string: str, db_name: str):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.db_name = db_name
        
        # 스키마 분석기 초기화
        self.schema_analyzer = SchemaAnalyzer()
        self.schema = None
        self.query_builder = None
        
        # 스키마 캐시
        self.schema_cache_file = f"{db_name}_schema_cache.pkl"
        
        # 초기 스키마 분석
        self._initialize_schema()
        
        # LLM 모델 (선택적)
        self.llm_available = self._initialize_llm()
        
        logger.info(f"동적 MongoDB 분석기 초기화 완료!")
    
    def _initialize_schema(self):
        """스키마 초기화"""
        # 캐시된 스키마 로드 시도
        if os.path.exists(self.schema_cache_file):
            try:
                with open(self.schema_cache_file, 'rb') as f:
                    cached_schema = pickle.load(f)
                
                # 스키마 변경 확인
                current_hash = self._get_current_schema_hash()
                if cached_schema.schema_hash == current_hash:
                    self.schema = cached_schema
                    logger.info("캐시된 스키마 로드 성공")
                else:
                    logger.info("스키마 변경 감지, 재분석 필요")
                    self._analyze_and_cache_schema()
            except Exception as e:
                logger.error(f"스키마 캐시 로드 실패: {e}")
                self._analyze_and_cache_schema()
        else:
            self._analyze_and_cache_schema()
        
        # 쿼리 빌더 초기화
        self.query_builder = DynamicQueryBuilder(self.schema)
    
    def _analyze_and_cache_schema(self):
        """스키마 분석 및 캐시"""
        logger.info("데이터베이스 스키마 분석 중...")
        self.schema = self.schema_analyzer.analyze_database_schema(self.db)
        
        # 캐시 저장
        try:
            with open(self.schema_cache_file, 'wb') as f:
                pickle.dump(self.schema, f)
            logger.info("스키마 캐시 저장 완료")
        except Exception as e:
            logger.error(f"스키마 캐시 저장 실패: {e}")
    
    def _get_current_schema_hash(self) -> str:
        """현재 스키마 해시 생성"""
        schema_str = ""
        for collection_name in self.db.list_collection_names():
            count = self.db[collection_name].count_documents({})
            schema_str += f"{collection_name}:{count};"
        
        return hashlib.md5(schema_str.encode()).hexdigest()
    
    def _initialize_llm(self) -> bool:
        """LLM 모델 초기화"""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("transformers 라이브러리가 설치되지 않았습니다. 기본 모드로 동작합니다.")
            return False
            
        try:
            # 더 강력한 instruction-tuned 모델 사용 (NL2SQL에 최적화)
            model_name = "google/flan-t5-large"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self.text_generator = pipeline(
                "text2text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_length=1024,  # 더 긴 출력 허용
                device=-1  # CPU 사용 (GPU 메모리 절약)
            )
            return True
        except Exception as e:
            logger.warning(f"LLM 모델 로드 실패: {e}")
            return False
    
    def get_schema_info(self) -> Dict:
        """스키마 정보 반환"""
        info = {
            'database': self.schema.name,
            'collections': {},
            'last_analyzed': self.schema.last_analyzed.isoformat(),
            'schema_hash': self.schema.schema_hash
        }
        
        for coll_name, coll_schema in self.schema.collections.items():
            info['collections'][coll_name] = {
                'document_count': coll_schema.document_count,
                'fields': {}
            }
            
            for field_name, field_info in coll_schema.fields.items():
                info['collections'][coll_name]['fields'][field_name] = {
                    'data_type': field_info.data_type,
                    'semantic_type': field_info.semantic_type,
                    'confidence': field_info.confidence,
                    'sample_values': field_info.sample_values[:3]  # 처음 3개만
                }
        
        return info
    
    def refresh_schema(self):
        """스키마 강제 새로고침"""
        logger.info("스키마 강제 새로고침...")
        self._analyze_and_cache_schema()
        self.query_builder = DynamicQueryBuilder(self.schema)
        logger.info("스키마 새로고침 완료")
    
    def execute_query(self, nl_query: str, use_ai: bool = True) -> pd.DataFrame:
        """자연어 쿼리 실행"""
        try:
            # 컬렉션 추론
            collection_name = self.query_builder.infer_collection(nl_query)
            logger.info(f"추론된 컬렉션: {collection_name}")
            
            # 파이프라인 생성 (AI 모드 적용)
            pipeline = self.query_builder.build_aggregation_pipeline(nl_query, collection_name, use_ai and self.llm_available)
            logger.info(f"생성된 파이프라인 (AI: {use_ai and self.llm_available}): {pipeline}")
            
            # 쿼리 실행
            collection = self.db[collection_name]
            results = list(collection.aggregate(pipeline))
            
            return pd.DataFrame(results)
            
        except Exception as e:
            logger.error(f"쿼리 실행 오류: {e}")
            return pd.DataFrame()
    
    def execute_simple_query(self, nl_query: str) -> pd.DataFrame:
        """단순 키워드 매칭 기반 쿼리 실행"""
        try:
            logger.info(f"단순 쿼리 모드로 실행: '{nl_query}'")
            
            # 키워드 기반 컬렉션 매칭
            query_lower = nl_query.lower()
            
            # 컬렉션 이름 매칭
            matched_collection = None
            for coll_name in self.db.list_collection_names():
                if coll_name.lower() in query_lower or any(keyword in query_lower for keyword in [
                    '리뷰', '상품', '주문', '고객', '판매', 'review', 'product', 'order', 'customer', 'sale'
                ]):
                    # 간단한 매칭 로직
                    if 'review' in query_lower or '리뷰' in query_lower:
                        if 'review' in coll_name.lower():
                            matched_collection = coll_name
                            break
                    elif 'product' in query_lower or '상품' in query_lower:
                        if 'product' in coll_name.lower():
                            matched_collection = coll_name
                            break
                    elif 'order' in query_lower or '주문' in query_lower:
                        if 'order' in coll_name.lower():
                            matched_collection = coll_name
                            break
                    elif 'buyer' in query_lower or '고객' in query_lower:
                        if 'buyer' in coll_name.lower():
                            matched_collection = coll_name
                            break
                    elif 'seller' in query_lower or '판매' in query_lower:
                        if 'seller' in coll_name.lower():
                            matched_collection = coll_name
                            break
            
            # 기본값: 첫 번째 컬렉션
            if not matched_collection:
                collections = self.db.list_collection_names()
                matched_collection = collections[0] if collections else None
            
            if not matched_collection:
                return pd.DataFrame()
            
            # 단순 필터링 및 집계
            collection = self.db[matched_collection]
            
            # 숫자 키워드 감지
            limit_size = 100  # 기본 제한
            if '10' in query_lower:
                limit_size = 10
            elif '20' in query_lower:
                limit_size = 20
            elif '50' in query_lower:
                limit_size = 50
            
            # 기본 쿼리 (최신 데이터)
            pipeline = []
            
            # 정렬 키워드 감지
            if '최신' in query_lower or 'recent' in query_lower:
                # 날짜 필드 찾기
                sample_doc = collection.find_one()
                if sample_doc:
                    date_field = None
                    for field in ['created_at', 'date', 'timestamp', 'createdAt']:
                        if field in sample_doc:
                            date_field = field
                            break
                    if date_field:
                        pipeline.append({"$sort": {date_field: -1}})
            
            # 집계 키워드 감지
            if any(keyword in query_lower for keyword in ['합계', '총', '평균', 'total', 'sum', 'average']):
                # 간단한 집계
                pipeline.extend([
                    {"$group": {"_id": None, "count": {"$sum": 1}}},
                    {"$project": {"_id": 0, "total_count": "$count"}}
                ])
            else:
                pipeline.append({"$limit": limit_size})
            
            # 쿼리 실행
            cursor = collection.aggregate(pipeline)
            data = list(cursor)
            
            return pd.DataFrame(data) if data else pd.DataFrame()
            
        except Exception as e:
            logger.error(f"단순 쿼리 실행 오류: {e}")
            return pd.DataFrame()
    
    def analyze_query(self, nl_query: str, use_ai_mode: bool = True) -> Dict[str, Any]:
        """자연어 쿼리 종합 분석"""
        # 무조건 AI 모드 강제 사용
        use_ai_mode = True
        logger.info(f"쿼리 분석 시작: '{nl_query}' (AI 모드: {use_ai_mode} - 강제 활성화)")
        
        # 쿼리 실행 (항상 AI 모드)
        data = self.execute_query(nl_query, use_ai=True)
        processing_mode = "AI 자연어 처리 (강제 활성화)"
        
        # 기본 분석
        analysis = {
            'query': nl_query,
            'processing_mode': processing_mode,
            'use_ai_mode': use_ai_mode,
            'execution_time': datetime.now().isoformat(),
            'data_count': len(data),
            'data': data.to_dict('records') if not data.empty else [],
            'insights': [],
            'recommendations': []
        }
        
        if not data.empty:
            # 인사이트 생성 (무조건 AI 모드)
            analysis['insights'] = self._generate_insights(data, nl_query)
            analysis['recommendations'] = self._generate_recommendations(data, nl_query)
            
            # 시각화 (선택적)
            try:
                self._create_visualization(data, nl_query)
            except Exception as e:
                logger.warning(f"시각화 생성 실패: {e}")
        
        return analysis
    
    def _generate_insights(self, data: pd.DataFrame, query: str) -> List[str]:
        """AI 기반 인사이트 생성"""
        insights = []
        
        # 기본 통계
        insights.append(f"총 {len(data)}건의 데이터를 분석했습니다.")
        
        if data.empty:
            insights.append("조회된 데이터가 없습니다. 검색 조건을 다시 확인해보세요.")
            return insights
        
        # 숫자형 컬럼 분석
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col not in ['_id'] and len(data[col].dropna()) > 0:
                stats = data[col].describe()
                insights.append(f"{col}: 평균 {stats['mean']:.2f}, 최댓값 {stats['max']:.2f}, 최솟값 {stats['min']:.2f}")
        
        # AI 기반 패턴 분석
        if len(data) > 1:
            ai_insights = self._generate_ai_insights(data, query)
            insights.extend(ai_insights)
        
        # 추세 분석
        date_cols = data.select_dtypes(include=['datetime64']).columns
        if len(date_cols) > 0 and len(data) > 1:
            date_col = date_cols[0]
            data_sorted = data.sort_values(date_col)
            if len(numeric_cols) > 0:
                numeric_col = [c for c in numeric_cols if c != '_id'][0]
                if data_sorted[numeric_col].iloc[-1] > data_sorted[numeric_col].iloc[0]:
                    insights.append(f"{numeric_col}이(가) 시간에 따라 증가하는 추세를 보입니다.")
                else:
                    insights.append(f"{numeric_col}이(가) 시간에 따라 감소하는 추세를 보입니다.")
        
        return insights
    
    def _generate_ai_insights(self, data: pd.DataFrame, query: str) -> List[str]:
        """실제 AI 모델을 사용한 인사이트 생성"""
        insights = []
        
        if hasattr(self, 'text_generator') and self.text_generator:
            try:
                # 데이터 요약 생성
                summary = self._create_data_summary(data)
                
                prompt = f"""Analyze the following data and generate 3 key business insights in Korean.

Query: {query}
Data Summary: {summary}

Task: Generate exactly 3 actionable business insights based on the data analysis results. Each insight should be practical and specific.

Format your response as:
1. [First insight in Korean]
2. [Second insight in Korean] 
3. [Third insight in Korean]

Business Insights:"""
                
                response = self.text_generator(prompt, max_length=300, num_return_sequences=1)
                ai_text = response[0]['generated_text'].replace(prompt, '').strip()
                
                # AI 응답을 파싱하여 인사이트 추출
                ai_lines = [line.strip() for line in ai_text.split('\n') if line.strip()]
                for line in ai_lines[:3]:  # 최대 3개
                    if line and not line.startswith('인사이트'):
                        insights.append(f"AI 분석: {line}")
                
            except Exception as e:
                logger.warning(f"AI 인사이트 생성 실패: {e}")
                # Fallback: 규칙 기반 인사이트
                insights.append("데이터 패턴 분석을 통해 비즈니스 기회를 식별할 수 있습니다.")
        
        return insights
    
    def _create_data_summary(self, data: pd.DataFrame) -> str:
        """데이터 요약 생성"""
        summary_parts = []
        
        summary_parts.append(f"총 {len(data)}개 행")
        
        # 숫자형 컬럼 요약
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            for col in numeric_cols[:3]:  # 최대 3개만
                if col != '_id':
                    mean_val = data[col].mean()
                    summary_parts.append(f"{col} 평균: {mean_val:.2f}")
        
        # 범주형 컬럼 요약
        categorical_cols = data.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            for col in categorical_cols[:2]:  # 최대 2개만
                if col not in ['_id']:
                    unique_count = data[col].nunique()
                    summary_parts.append(f"{col}: {unique_count}개 고유값")
        
        return ", ".join(summary_parts)
    
    def _generate_simple_insights(self, data: pd.DataFrame, query: str) -> List[str]:
        """단순 모드 인사이트 생성"""
        insights = []
        
        insights.append(f"키워드 매칭으로 {len(data)}건의 데이터를 찾았습니다.")
        
        if len(data) > 0:
            # 기본 통계
            insights.append(f"데이터 조회가 완료되었습니다.")
            
            # 숫자형 컬럼이 있는 경우
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                insights.append(f"수치 데이터 {len(numeric_cols)}개 컬럼을 발견했습니다.")
            
            # 컬럼 수 정보
            insights.append(f"총 {len(data.columns)}개의 필드가 있습니다.")
        else:
            insights.append("일치하는 데이터를 찾지 못했습니다.")
        
        return insights
    
    def _generate_simple_recommendations(self, data: pd.DataFrame, query: str) -> List[str]:
        """단순 모드 추천사항 생성"""
        recommendations = []
        
        if len(data) == 0:
            recommendations.append("다른 키워드로 검색해보세요.")
            recommendations.append("AI 모드를 사용하면 더 정확한 검색이 가능합니다.")
        elif len(data) < 10:
            recommendations.append("더 많은 데이터를 보려면 검색 범위를 넓혀보세요.")
            recommendations.append("AI 모드로 전환하면 더 상세한 분석이 가능합니다.")
        else:
            recommendations.append("데이터 분석을 위해 AI 모드 사용을 권장합니다.")
            recommendations.append("특정 조건으로 필터링하려면 더 구체적인 키워드를 사용하세요.")
        
        return recommendations
    
    def _generate_recommendations(self, data: pd.DataFrame, query: str) -> List[str]:
        """추천사항 생성"""
        recommendations = []
        
        if len(data) == 0:
            recommendations.append("검색 조건을 넓혀서 더 많은 데이터를 확인해보세요.")
        elif len(data) < 10:
            recommendations.append("더 많은 데이터를 수집하여 분석의 정확도를 높이세요.")
        else:
            recommendations.append("충분한 데이터를 기반으로 신뢰할 수 있는 분석 결과입니다.")
        
        # 쿼리 타입별 추천
        if '트렌드' in query or '추세' in query:
            recommendations.append("시간별 패턴을 파악하여 예측 모델을 구축해보세요.")
        elif '비교' in query:
            recommendations.append("성과가 좋은 항목의 성공 요인을 다른 항목에 적용해보세요.")
        
        return recommendations
    
    def _create_visualization(self, data: pd.DataFrame, query: str):
        """시각화 생성"""
        if data.empty:
            return
        
        plt.figure(figsize=(12, 6))
        
        # 간단한 시각화
        if len(data.columns) >= 2:
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) >= 1:
                col = numeric_cols[0]
                if '_id' in data.columns and data['_id'].dtype == 'object':
                    plt.bar(range(len(data)), data[col])
                    plt.title(f'{query} - {col}')
                    plt.xticks(range(len(data)), data['_id'], rotation=45)
                else:
                    data[col].plot()
                    plt.title(f'{query} - {col}')
                
                plt.tight_layout()
                # plt.show() 제거: 팝업 방지
    
    def suggest_queries(self) -> List[str]:
        """스키마 기반 쿼리 제안"""
        suggestions = []
        
        for coll_name, coll_schema in self.schema.collections.items():
            # 컬렉션별 기본 쿼리
            suggestions.append(f"{coll_name} 컬렉션의 전체 현황을 보여주세요")
            
            # 시맨틱 타입별 쿼리 제안
            field_types = defaultdict(list)
            for field_name, field_info in coll_schema.fields.items():
                if field_info.semantic_type and field_info.confidence > 0.7:
                    field_types[field_info.semantic_type].append(field_name)
            
            if field_types.get('amount'):
                suggestions.append(f"{coll_name}의 총 금액을 계산해주세요")
                suggestions.append(f"{coll_name}의 평균 금액을 알려주세요")
            
            if field_types.get('date'):
                suggestions.append(f"{coll_name}의 월별 추세를 분석해주세요")
            
            if field_types.get('category'):
                suggestions.append(f"{coll_name}의 카테고리별 현황을 보여주세요")
        
        return suggestions[:10]  # 상위 10개만


# 사용 예시
def main():
    # 동적 분석기 초기화
    connection_string = "mongodb+srv://musinsa:musinsa@cluster0.ed1m1eg.mongodb.net/musinsa?retryWrites=true&w=majority&appName=Cluster0"
    analyzer = DynamicMongoDBAnalyzer(connection_string, "musinsa_db")
    
    # 스키마 정보 확인
    print("=== 데이터베이스 스키마 정보 ===")
    schema_info = analyzer.get_schema_info()
    print(f"데이터베이스: {schema_info['database']}")
    print(f"마지막 분석: {schema_info['last_analyzed']}")
    
    for coll_name, coll_info in schema_info['collections'].items():
        print(f"\n컬렉션: {coll_name} ({coll_info['document_count']}개 문서)")
        for field_name, field_info in list(coll_info['fields'].items())[:5]:
            print(f"  {field_name}: {field_info['data_type']} ({field_info.get('semantic_type', 'unknown')})")
    
    # 쿼리 제안
    print("\n=== 추천 쿼리 ===")
    suggestions = analyzer.suggest_queries()
    for i, suggestion in enumerate(suggestions[:5], 1):
        print(f"{i}. {suggestion}")
    
    # 예시 쿼리 실행
    print("\n=== 쿼리 실행 예시 ===")
    test_query = "총 주문 금액은 얼마인가요?"
    result = analyzer.analyze_query(test_query)
    
    print(f"쿼리: {result['query']}")
    print(f"결과 건수: {result['data_count']}")
    for insight in result['insights']:
        print(f"인사이트: {insight}")


if __name__ == "__main__":
    main()