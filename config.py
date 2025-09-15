#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
설정 파일 - 허깅페이스 모델 사용
"""

import os

# 기본 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 허깅페이스 모델 설정
HUGGINGFACE_MODEL = "solbi12/ecommers_fasion_fine_tuned_3class_model"

# 라벨 정보
LABEL_NAMES = ["부정", "중립", "긍정"]

# 패션 속성 목록 (실제 학습 데이터에서 추출된 속성들)
FASHION_ASPECTS = [
    "착용감", "디자인", "가격", "품질", "크기", "소재", "배송", "색상",
    "스타일", "사이즈", "핏", "편안함", "내구성", "재질", "포장"
]

# 출력 파일 설정
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# 디렉토리 생성
os.makedirs(OUTPUT_DIR, exist_ok=True)