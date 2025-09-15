#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB 분석 모듈 - 허깅페이스 모델 사용
"""

import pandas as pd
from pymongo import MongoClient
from tqdm.auto import tqdm
import os
from datetime import datetime

from config import FASHION_ASPECTS, OUTPUT_DIR
from predictor import ThreeClassPredictor, load_huggingface_model, find_relevant_aspects_with_model

class MongoDBAnalyzer:
    """MongoDB 리뷰 감성분석 클래스"""
    
    def __init__(self, connection_string, database_name, collection_name):
        """
        MongoDB 연결 설정
        
        Args:
            connection_string: MongoDB 연결 문자열
            database_name: 데이터베이스 이름
            collection_name: 컬렉션 이름
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        
    def connect(self):
        """MongoDB 연결"""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            print("✅ MongoDB 연결 성공!")
            return True
        except Exception as e:
            print(f"❌ MongoDB 연결 실패: {e}")
            return False
    
    def disconnect(self):
        """MongoDB 연결 해제"""
        if self.client:
            self.client.close()
            print("🔌 MongoDB 연결 해제")
    
    def get_reviews(self, limit=None, filter_query=None):
        """
        리뷰 데이터 가져오기
        
        Args:
            limit: 가져올 리뷰 수 (None이면 전체)
            filter_query: 필터 쿼리 (예: {"score": {"$gte": 3}})
        
        Returns:
            리뷰 데이터 리스트
        """
        try:
            query = filter_query or {}
            cursor = self.collection.find(query)
            
            if limit:
                cursor = cursor.limit(limit)
            
            reviews = list(cursor)
            print(f"📊 총 {len(reviews)}개의 리뷰를 가져왔습니다.")
            return reviews
        except Exception as e:
            print(f"❌ 리뷰 데이터 가져오기 실패: {e}")
            return []
    
    def analyze_reviews(self, model_name, reviews, text_field='text', batch_size=100):
        """
        리뷰들에 대해 감성분석 수행
        
        Args:
            model_name: 허깅페이스 모델명
            reviews: 리뷰 데이터 리스트
            text_field: 텍스트 필드명
            batch_size: 배치 크기
        
        Returns:
            분석 결과가 포함된 리뷰 데이터
        """
        # 모델 로드
        model, tokenizer = load_huggingface_model(model_name)
        if not model:
            return []
        
        predictor = ThreeClassPredictor(model, tokenizer)
        
        print(f"🔍 {len(reviews)}개 리뷰에 대한 감성분석 시작...")
        
        # 각 리뷰에 대해 분석
        for i, review in enumerate(tqdm(reviews, desc="감성분석")):
            text = review.get(text_field, '')
            
            if not text:
                continue
            
            # 1. 전체 감정분석
            overall_result = predictor.predict(text, aspect="전체")
            review['sentiment_analysis'] = {
                'overall_prediction': overall_result['prediction'],
                'overall_confidence': round(overall_result['confidence'], 4),
                'overall_negative_prob': round(overall_result['probabilities']['부정'], 4),
                'overall_neutral_prob': round(overall_result['probabilities']['중립'], 4),
                'overall_positive_prob': round(overall_result['probabilities']['긍정'], 4)
            }
            
            # 2. 속성별 감정분석
            relevant_aspects = find_relevant_aspects_with_model(text, predictor)
            
            # 감지된 속성들 정보
            detected_aspects = list(relevant_aspects.keys())
            review['sentiment_analysis']['detected_aspects'] = detected_aspects
            review['sentiment_analysis']['aspect_count'] = len(detected_aspects)
            
            # 각 속성별로 결과 저장
            aspect_analysis = {}
            for aspect in FASHION_ASPECTS:
                if aspect in relevant_aspects:
                    aspect_data = relevant_aspects[aspect]
                    aspect_analysis[aspect] = {
                        'mentioned': True,
                        'sentiment': aspect_data['prediction'],
                        'confidence': round(aspect_data['confidence'], 4),
                        'negative_prob': round(aspect_data['probabilities']['부정'], 4),
                        'neutral_prob': round(aspect_data['probabilities']['중립'], 4),
                        'positive_prob': round(aspect_data['probabilities']['긍정'], 4)
                    }
                else:
                    aspect_analysis[aspect] = {
                        'mentioned': False,
                        'sentiment': 'not_mentioned',
                        'confidence': 0.0,
                        'negative_prob': 0.0,
                        'neutral_prob': 0.0,
                        'positive_prob': 0.0
                    }
            
            review['sentiment_analysis']['aspect_analysis'] = aspect_analysis
            
            # 분석 시간 추가
            review['sentiment_analysis']['analyzed_at'] = datetime.now().isoformat()
        
        print("✅ 감성분석 완료!")
        return reviews
    
    def save_analyzed_reviews(self, reviews, update_existing=True):
        """
        분석된 리뷰를 MongoDB에 저장
        
        Args:
            reviews: 분석된 리뷰 데이터
            update_existing: 기존 문서 업데이트 여부
        """
        if not reviews:
            print("❌ 저장할 리뷰 데이터가 없습니다.")
            return False
        
        try:
            updated_count = 0
            inserted_count = 0
            
            for review in tqdm(reviews, desc="MongoDB 저장"):
                review_id = review.get('_id')
                
                if update_existing and review_id:
                    # 기존 문서 업데이트
                    result = self.collection.update_one(
                        {'_id': review_id},
                        {'$set': {'sentiment_analysis': review['sentiment_analysis']}}
                    )
                    if result.modified_count > 0:
                        updated_count += 1
                else:
                    # 새 문서 삽입
                    self.collection.insert_one(review)
                    inserted_count += 1
            
            print(f"✅ MongoDB 저장 완료!")
            print(f"   업데이트: {updated_count}개")
            print(f"   삽입: {inserted_count}개")
            return True
            
        except Exception as e:
            print(f"❌ MongoDB 저장 실패: {e}")
            return False
    
    def export_to_csv(self, reviews, output_path=None):
        """
        분석된 리뷰를 CSV로 내보내기
        
        Args:
            reviews: 분석된 리뷰 데이터
            output_path: 출력 파일 경로
        """
        if not reviews:
            print("❌ 내보낼 리뷰 데이터가 없습니다.")
            return False
        
        try:
            # DataFrame으로 변환
            df_data = []
            for review in reviews:
                row = {
                    'review_id': str(review.get('_id', '')),
                    'text': review.get('text', ''),
                    'score': review.get('score', ''),
                    'user_id': review.get('user_id', ''),
                    'product_id': review.get('product_id', ''),
                    'review_created_at': review.get('review_created_at', '')
                }
                
                # 감성분석 결과 추가
                if 'sentiment_analysis' in review:
                    sa = review['sentiment_analysis']
                    row.update({
                        'overall_prediction': sa.get('overall_prediction', ''),
                        'overall_confidence': sa.get('overall_confidence', 0),
                        'overall_negative_prob': sa.get('overall_negative_prob', 0),
                        'overall_neutral_prob': sa.get('overall_neutral_prob', 0),
                        'overall_positive_prob': sa.get('overall_positive_prob', 0),
                        'detected_aspects': ', '.join(sa.get('detected_aspects', [])),
                        'aspect_count': sa.get('aspect_count', 0),
                        'analyzed_at': sa.get('analyzed_at', '')
                    })
                    
                    # 속성별 분석 결과 추가
                    if 'aspect_analysis' in sa:
                        for aspect in FASHION_ASPECTS:
                            aspect_data = sa['aspect_analysis'].get(aspect, {})
                            row.update({
                                f'{aspect}_mentioned': aspect_data.get('mentioned', False),
                                f'{aspect}_sentiment': aspect_data.get('sentiment', ''),
                                f'{aspect}_confidence': aspect_data.get('confidence', 0),
                                f'{aspect}_negative_prob': aspect_data.get('negative_prob', 0),
                                f'{aspect}_neutral_prob': aspect_data.get('neutral_prob', 0),
                                f'{aspect}_positive_prob': aspect_data.get('positive_prob', 0)
                            })
                
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            
            # 출력 파일 경로 설정
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(OUTPUT_DIR, f"mongodb_analyzed_reviews_{timestamp}.csv")
            
            # CSV 저장
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"✅ CSV 내보내기 완료: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ CSV 내보내기 실패: {e}")
            return False

def analyze_mongodb_reviews(connection_string, database_name, collection_name, 
                          model_name, limit=None, filter_query=None, 
                          text_field='text', update_existing=True, export_csv=True):
    """
    MongoDB 리뷰 감성분석 전체 프로세스
    
    Args:
        connection_string: MongoDB 연결 문자열
        database_name: 데이터베이스 이름
        collection_name: 컬렉션 이름
        model_name: 허깅페이스 모델명
        limit: 가져올 리뷰 수 (None이면 전체)
        filter_query: 필터 쿼리
        text_field: 텍스트 필드명
        update_existing: 기존 문서 업데이트 여부
        export_csv: CSV 내보내기 여부
    """
    analyzer = MongoDBAnalyzer(connection_string, database_name, collection_name)
    
    try:
        # 1. MongoDB 연결
        if not analyzer.connect():
            return False
        
        # 2. 리뷰 데이터 가져오기
        reviews = analyzer.get_reviews(limit=limit, filter_query=filter_query)
        if not reviews:
            print("❌ 가져올 리뷰 데이터가 없습니다.")
            return False
        
        # 3. 감성분석 수행
        analyzed_reviews = analyzer.analyze_reviews(model_name, reviews, text_field)
        if not analyzed_reviews:
            print("❌ 감성분석에 실패했습니다.")
            return False
        
        # 4. MongoDB에 저장
        if not analyzer.save_analyzed_reviews(analyzed_reviews, update_existing):
            print("❌ MongoDB 저장에 실패했습니다.")
            return False
        
        # 5. CSV 내보내기 (선택사항)
        if export_csv:
            analyzer.export_to_csv(analyzed_reviews)
        
        print("🎉 MongoDB 리뷰 감성분석 전체 프로세스 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 전체 프로세스 실행 중 오류: {e}")
        return False
    finally:
        analyzer.disconnect()
