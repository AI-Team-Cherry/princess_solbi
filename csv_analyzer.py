#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV 분석 모듈 - 허깅페이스 모델 사용
"""

import pandas as pd
import os
from tqdm.auto import tqdm

from config import FASHION_ASPECTS, OUTPUT_DIR
from predictor import ThreeClassPredictor, load_huggingface_model, find_relevant_aspects_with_model

def analyze_csv_reviews(csv_path, model_name, output_path=None, text_column='text'):
    """
    CSV 파일의 리뷰들을 전체 감정분석 + 속성별 감정분석하여 결과 저장

    Args:
        csv_path: 입력 CSV 파일 경로
        model_name: 허깅페이스 모델명
        output_path: 출력 CSV 파일 경로 (None이면 자동 생성)
        text_column: 리뷰 텍스트가 있는 컬럼명
    """

    # 모델 로드
    model, tokenizer = load_huggingface_model(model_name)
    if not model:
        return None

    predictor = ThreeClassPredictor(model, tokenizer)

    # CSV 파일 읽기
    print(f"📁 CSV 파일 로딩: {csv_path}")
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
    except:
        try:
            df = pd.read_csv(csv_path, encoding='cp949')  # 윈도우 인코딩
        except:
            df = pd.read_csv(csv_path, encoding='euc-kr')  # 한글 인코딩

    print(f"📊 총 리뷰 수: {len(df)}")
    print(f"📋 기존 컬럼: {list(df.columns)}")

    if text_column not in df.columns:
        print(f"❌ '{text_column}' 컬럼을 찾을 수 없습니다.")
        print(f"사용 가능한 컬럼: {list(df.columns)}")
        return None

    # 전체 감정분석 컬럼들
    df['전체감정예측'] = ''
    df['전체예측신뢰도'] = 0.0
    df['전체부정확률'] = 0.0
    df['전체중립확률'] = 0.0
    df['전체긍정확률'] = 0.0

    # 속성별 감정분석 컬럼들 (동적으로 생성)
    df['감지된_속성들'] = ''  # 모델이 감지한 속성들의 리스트
    df['속성_개수'] = 0      # 감지된 속성 개수

    for aspect in FASHION_ASPECTS:
        df[f'{aspect}_언급여부'] = False
        df[f'{aspect}_감정'] = ''
        df[f'{aspect}_신뢰도'] = 0.0
        df[f'{aspect}_부정확률'] = 0.0
        df[f'{aspect}_중립확률'] = 0.0
        df[f'{aspect}_긍정확률'] = 0.0

    # 각 리뷰에 대해 감정분석 수행
    print("🔍 리뷰 전체 및 속성별 감정분석 수행 중...")
    print("💡 모델이 알아서 관련 속성을 찾아서 분석합니다 (키워드 방식 대신)")

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="감정분석"):
        text = row[text_column]

        # 1. 전체 감정분석
        overall_result = predictor.predict(text, aspect="전체")
        df.at[idx, '전체감정예측'] = overall_result['prediction']
        df.at[idx, '전체예측신뢰도'] = round(overall_result['confidence'], 4)
        df.at[idx, '전체부정확률'] = round(overall_result['probabilities']['부정'], 4)
        df.at[idx, '전체중립확률'] = round(overall_result['probabilities']['중립'], 4)
        df.at[idx, '전체긍정확률'] = round(overall_result['probabilities']['긍정'], 4)

        # 2. 모델이 자동으로 관련 속성 찾기
        relevant_aspects = find_relevant_aspects_with_model(text, predictor)

        # 감지된 속성들 정보 저장
        detected_aspects = list(relevant_aspects.keys())
        df.at[idx, '감지된_속성들'] = ', '.join(detected_aspects) if detected_aspects else '없음'
        df.at[idx, '속성_개수'] = len(detected_aspects)

        # 각 속성별로 결과 저장
        for aspect in FASHION_ASPECTS:
            if aspect in relevant_aspects:
                # 해당 속성이 모델에 의해 감지된 경우
                aspect_data = relevant_aspects[aspect]
                df.at[idx, f'{aspect}_언급여부'] = True
                df.at[idx, f'{aspect}_감정'] = aspect_data['prediction']
                df.at[idx, f'{aspect}_신뢰도'] = round(aspect_data['confidence'], 4)
                df.at[idx, f'{aspect}_부정확률'] = round(aspect_data['probabilities']['부정'], 4)
                df.at[idx, f'{aspect}_중립확률'] = round(aspect_data['probabilities']['중립'], 4)
                df.at[idx, f'{aspect}_긍정확률'] = round(aspect_data['probabilities']['긍정'], 4)
            else:
                # 해당 속성이 감지되지 않은 경우
                df.at[idx, f'{aspect}_언급여부'] = False
                df.at[idx, f'{aspect}_감정'] = '언급없음'
                df.at[idx, f'{aspect}_신뢰도'] = 0.0
                df.at[idx, f'{aspect}_부정확률'] = 0.0
                df.at[idx, f'{aspect}_중립확률'] = 0.0
                df.at[idx, f'{aspect}_긍정확률'] = 0.0

    # 결과 통계
    prediction_counts = df['전체감정예측'].value_counts()
    print(f"\n📊 전체 감정 예측 결과 분포:")
    for sentiment, count in prediction_counts.items():
        percentage = (count / len(df)) * 100
        print(f"  {sentiment}: {count}개 ({percentage:.1f}%)")

    # 평균 신뢰도
    avg_confidence = df['전체예측신뢰도'].mean()
    print(f"📈 평균 예측 신뢰도: {avg_confidence:.3f}")

    # 모델 기반 속성 감지 통계
    avg_aspects_per_review = df['속성_개수'].mean()
    print(f"\n🤖 모델 기반 속성 감지 결과:")
    print(f"  평균 리뷰당 감지된 속성 수: {avg_aspects_per_review:.1f}개")

    print(f"\n🏷️ 속성별 감지 통계 (모델 기준):")
    for aspect in FASHION_ASPECTS:
        mentioned_count = df[f'{aspect}_언급여부'].sum()
        percentage = (mentioned_count / len(df)) * 100
        print(f"  {aspect}: {mentioned_count}개 ({percentage:.1f}%)")

        if mentioned_count > 0:
            # 해당 속성이 감지된 경우의 감정 분포
            aspect_sentiments = df[df[f'{aspect}_언급여부'] == True][f'{aspect}_감정'].value_counts()
            print(f"    └ ", end="")
            for sentiment, count in aspect_sentiments.items():
                print(f"{sentiment}: {count}개, ", end="")
            print()

    # 출력 파일 경로 설정
    if output_path is None:
        base_name = os.path.splitext(os.path.basename(csv_path))[0]
        output_path = os.path.join(OUTPUT_DIR, f"{base_name}_with_ai_sentiment_analysis.csv")

    # 결과 저장
    df.to_csv(output_path, index=False, encoding='utf-8-sig')  # 엑셀에서 한글 깨짐 방지
    print(f"✅ 분석 완료! 결과 저장: {output_path}")

    # 추가된 컬럼 정보
    extra_cols = 2  # 감지된_속성들, 속성_개수
    total_new_columns = 5 + extra_cols + (len(FASHION_ASPECTS) * 6)  # 전체 5개 + 추가 2개 + 속성별 6개씩
    print(f"\n📋 추가된 컬럼 (총 {total_new_columns}개):")
    print("🌐 전체 감정분석 (5개):")
    print("  1. 전체감정예측")
    print("  2. 전체예측신뢰도")
    print("  3. 전체부정확률")
    print("  4. 전체중립확률")
    print("  5. 전체긍정확률")

    print("\n🤖 AI 속성 감지 정보 (2개):")
    print("  6. 감지된_속성들")
    print("  7. 속성_개수")

    print(f"\n🏷️ 속성별 감정분석 ({len(FASHION_ASPECTS)}개 속성 × 6개 = {len(FASHION_ASPECTS) * 6}개):")
    for i, aspect in enumerate(FASHION_ASPECTS, 8):
        print(f"  {aspect}: {aspect}_언급여부, {aspect}_감정, {aspect}_신뢰도, {aspect}_부정확률, {aspect}_중립확률, {aspect}_긍정확률")

    return df