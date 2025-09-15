#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 실행 스크립트 - 허깅페이스 모델 사용
"""

import os
import sys
import argparse

from config import HUGGINGFACE_MODEL, OUTPUT_DIR
from predictor import test_3class_custom
from csv_analyzer import analyze_csv_reviews
from mongodb_analyzer import analyze_mongodb_reviews

def setup_directories():
    """필요한 디렉토리 생성"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 디렉토리 생성: {OUTPUT_DIR}")

def test_model(text):
    """모델 테스트 실행"""
    print("🔍 모델 테스트 시작!")
    test_3class_custom(HUGGINGFACE_MODEL, text)

def analyze_csv(csv_path, text_column='text'):
    """CSV 파일 분석 실행"""
    print("📊 CSV 파일 분석 시작!")
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV 파일을 찾을 수 없습니다: {csv_path}")
        return None
    
    result_df = analyze_csv_reviews(
        csv_path=csv_path,
        model_name=HUGGINGFACE_MODEL,
        text_column=text_column
    )
    
    if result_df is not None:
        print("✅ CSV 분석 완료!")
        return result_df
    else:
        print("❌ CSV 분석 실패!")
        return None

def analyze_mongodb(connection_string, database_name, collection_name, 
                   limit=None, filter_query=None, text_field='text', 
                   update_existing=True, export_csv=True):
    """MongoDB 리뷰 분석 실행"""
    print("🗄️ MongoDB 리뷰 분석 시작!")
    
    success = analyze_mongodb_reviews(
        connection_string=connection_string,
        database_name=database_name,
        collection_name=collection_name,
        model_name=HUGGINGFACE_MODEL,
        limit=limit,
        filter_query=filter_query,
        text_field=text_field,
        update_existing=update_existing,
        export_csv=export_csv
    )
    
    if success:
        print("✅ MongoDB 분석 완료!")
        return True
    else:
        print("❌ MongoDB 분석 실패!")
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='3클래스 감정분석 시스템 (허깅페이스 모델)')
    parser.add_argument('--mode', choices=['test', 'analyze', 'mongodb'], required=True,
                       help='실행 모드: test(테스트), analyze(CSV분석), mongodb(MongoDB분석)')
    parser.add_argument('--text', type=str, help='테스트할 텍스트 (test 모드에서 사용)')
    parser.add_argument('--csv', type=str, help='분석할 CSV 파일 경로 (analyze 모드에서 사용)')
    parser.add_argument('--text-column', type=str, default='text', 
                       help='CSV에서 텍스트가 있는 컬럼명 (기본값: text)')
    parser.add_argument('--mongodb-uri', type=str, 
                       help='MongoDB 연결 문자열 (mongodb 모드에서 사용)')
    parser.add_argument('--database', type=str, default='musinsa_db',
                       help='MongoDB 데이터베이스명 (기본값: musinsa_db)')
    parser.add_argument('--collection', type=str, default='reviews',
                       help='MongoDB 컬렉션명 (기본값: reviews)')
    parser.add_argument('--limit', type=int, 
                       help='분석할 리뷰 수 제한 (기본값: 전체)')
    parser.add_argument('--text-field', type=str, default='text',
                       help='MongoDB에서 텍스트가 있는 필드명 (기본값: text)')
    parser.add_argument('--no-update', action='store_true',
                       help='MongoDB 업데이트 비활성화 (기본값: 업데이트)')
    parser.add_argument('--no-csv-export', action='store_true',
                       help='CSV 내보내기 비활성화 (기본값: 내보내기)')
    
    args = parser.parse_args()
    
    # 디렉토리 설정
    setup_directories()
    
    if args.mode == 'test':
        if not args.text:
            print("❌ 테스트할 텍스트를 지정해주세요 (--text 옵션)")
            sys.exit(1)
        test_model(args.text)
        
    elif args.mode == 'analyze':
        if not args.csv:
            print("❌ CSV 파일 경로를 지정해주세요 (--csv 옵션)")
            sys.exit(1)
        result = analyze_csv(args.csv, args.text_column)
        sys.exit(0 if result is not None else 1)
        
    elif args.mode == 'mongodb':
        if not args.mongodb_uri:
            print("❌ MongoDB 연결 문자열을 지정해주세요 (--mongodb-uri 옵션)")
            sys.exit(1)
        success = analyze_mongodb(
            connection_string=args.mongodb_uri,
            database_name=args.database,
            collection_name=args.collection,
            limit=args.limit,
            text_field=args.text_field,
            update_existing=not args.no_update,
            export_csv=not args.no_csv_export
        )
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    # 명령행 인수 없이 실행된 경우 대화형 모드
    if len(sys.argv) == 1:
        print("🎉 3클래스 감정분석 시스템 (허깅페이스 모델)")
        print("=" * 50)
        print("1. 텍스트 테스트")
        print("2. CSV 파일 분석")
        print("3. MongoDB 리뷰 분석")
        print("4. 종료")
        print("=" * 50)
        
        while True:
            try:
                choice = input("\n선택하세요 (1-4): ").strip()
                
                if choice == '1':
                    text = input("테스트할 텍스트를 입력하세요: ").strip()
                    if text:
                        test_model(text)
                    else:
                        print("❌ 텍스트를 입력해주세요.")
                        
                elif choice == '2':
                    csv_path = input("CSV 파일 경로를 입력하세요: ").strip()
                    text_column = input("텍스트 컬럼명 (기본값: text): ").strip() or 'text'
                    if csv_path:
                        result = analyze_csv(csv_path, text_column)
                        if result is not None:
                            print("\n✅ CSV 분석이 완료되었습니다!")
                        else:
                            print("\n❌ CSV 분석에 실패했습니다.")
                    else:
                        print("❌ CSV 파일 경로를 입력해주세요.")
                        
                elif choice == '3':
                    print("\n🗄️ MongoDB 리뷰 분석")
                    print("-" * 30)
                    mongodb_uri = input("MongoDB 연결 문자열을 입력하세요: ").strip()
                    database = input("데이터베이스명 (기본값: musinsa_db): ").strip() or 'musinsa_db'
                    collection = input("컬렉션명 (기본값: reviews): ").strip() or 'reviews'
                    limit_input = input("분석할 리뷰 수 제한 (기본값: 전체): ").strip()
                    limit = int(limit_input) if limit_input.isdigit() else None
                    text_field = input("텍스트 필드명 (기본값: text): ").strip() or 'text'
                    
                    if mongodb_uri:
                        success = analyze_mongodb(
                            connection_string=mongodb_uri,
                            database_name=database,
                            collection_name=collection,
                            limit=limit,
                            text_field=text_field,
                            update_existing=True,
                            export_csv=True
                        )
                        if success:
                            print("\n✅ MongoDB 분석이 완료되었습니다!")
                        else:
                            print("\n❌ MongoDB 분석에 실패했습니다.")
                    else:
                        print("❌ MongoDB 연결 문자열을 입력해주세요.")
                        
                elif choice == '4':
                    print("👋 프로그램을 종료합니다.")
                    break
                    
                else:
                    print("❌ 잘못된 선택입니다. 1-4 중에서 선택해주세요.")
                    
            except KeyboardInterrupt:
                print("\n👋 프로그램을 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류가 발생했습니다: {e}")
    else:
        # 명령행 인수가 있는 경우 파싱하여 실행
        main()