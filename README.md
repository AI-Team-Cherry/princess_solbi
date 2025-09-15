# 3클래스 감정분석 시스템 (허깅페이스 모델)

이 프로젝트는 사전 학습된 허깅페이스 모델을 사용하여 패션 리뷰 데이터를 대상으로 한 3클래스 감정분석(긍정/중립/부정) 시스템입니다.

## 🚀 주요 기능

- **3클래스 감정분석**: 긍정, 중립, 부정으로 리뷰 분류
- **속성별 분석**: 디자인, 가격, 품질 등 15개 패션 속성별 감정 분석
- **AI 기반 속성 감지**: 키워드 방식이 아닌 모델이 자동으로 관련 속성 감지
- **CSV 파일 분석**: 대량의 리뷰 데이터를 일괄 처리
- **MongoDB 연동**: 데이터베이스에서 리뷰를 가져와 분석 후 다시 저장
- **허깅페이스 모델**: 사전 학습된 모델을 바로 사용 가능

## 📁 프로젝트 구조

```
final_project/
├── main.py                 # 메인 실행 스크립트
├── config.py              # 설정 파일
├── predictor.py            # 예측 모듈
├── csv_analyzer.py         # CSV 분석 모듈
├── mongodb_analyzer.py     # MongoDB 분석 모듈
├── huggingface_model.py    # 허깅페이스 모델 사용 예제
├── requirements.txt        # 의존성 패키지 목록
├── README.md              # 프로젝트 설명서
└── output/                # 분석 결과 출력 디렉토리
```

## 🛠️ 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 허깅페이스 모델 정보

- **모델명**: `solbi12/ecommers_fasion_fine_tuned_3class_model`
- **성능**: 평균 신뢰도 0.921
- **학습 데이터**: 15,322개 샘플
- **감정 분포**: 긍정 70.2%, 중립 24.5%, 부정 5.2%

## 🎯 사용법

### 대화형 모드

```bash
python main.py
```

메뉴에서 원하는 기능을 선택하세요:
1. 텍스트 테스트
2. CSV 파일 분석
3. 종료

### 명령행 모드

#### 1. 텍스트 테스트
```bash
python main.py --mode test --text "배송이 빠르고 품질도 좋아요"
```

#### 2. CSV 파일 분석
```bash
python main.py --mode analyze --csv "reviews.csv" --text-column "text"
```

#### 3. MongoDB 리뷰 분석
```bash
# 기본 MongoDB 분석
python main.py --mode mongodb --mongodb-uri "mongodb://localhost:27017/"

# 원격 MongoDB 분석 (제한된 수)
python main.py --mode mongodb --mongodb-uri "mongodb+srv://user:pass@cluster.mongodb.net/" --limit 1000

# 특정 조건으로 필터링
python main.py --mode mongodb --mongodb-uri "mongodb://localhost:27017/" --database "my_db" --collection "reviews"
```

#### 4. 허깅페이스 모델 직접 사용
```bash
# 간단한 테스트
python huggingface_model.py

# 대화형 테스트
python huggingface_model.py interactive
```

## 🗄️ MongoDB 연동 과정

### 1. 전체 프로세스 개요

MongoDB 연동은 다음과 같은 단계로 진행됩니다:

```
MongoDB 연결 → 리뷰 데이터 가져오기 → 감성분석 수행 → MongoDB에 저장 → CSV 내보내기
```

### 2. 단계별 상세 과정

#### 2.1 MongoDB 연결
```python
# 연결 문자열 예시
mongodb://localhost:27017/                    # 로컬 MongoDB
mongodb+srv://user:pass@cluster.mongodb.net/  # MongoDB Atlas (클라우드)
```

#### 2.2 리뷰 데이터 가져오기
```python
# 기본 쿼리 (전체 리뷰)
reviews = collection.find()

# 필터링 쿼리 예시
reviews = collection.find({
    "score": {"$gte": 3},           # 평점 3점 이상
    "text": {"$exists": True},      # 텍스트 필드 존재
    "created_at": {"$gte": "2024-01-01"}  # 2024년 이후
})
```

#### 2.3 감성분석 수행
각 리뷰에 대해 다음 정보가 추가됩니다:

**전체 감정분석:**
- `overall_prediction`: 부정/중립/긍정
- `overall_confidence`: 예측 신뢰도
- `overall_negative_prob`: 부정 확률
- `overall_neutral_prob`: 중립 확률
- `overall_positive_prob`: 긍정 확률

**속성별 감정분석:**
- `detected_aspects`: 감지된 속성 목록
- `aspect_count`: 감지된 속성 개수
- `aspect_analysis`: 각 속성별 상세 분석

#### 2.4 MongoDB에 저장
```python
# 기존 문서 업데이트
collection.update_one(
    {"_id": review_id},
    {"$set": {"sentiment_analysis": analysis_result}}
)
```

#### 2.5 CSV 내보내기
분석 결과를 CSV 파일로 내보내어 추가 분석이나 시각화에 활용할 수 있습니다.

### 3. 사용 예시

#### 3.1 대화형 모드
```bash
python main.py
# 메뉴에서 "3. MongoDB 리뷰 분석" 선택
# 연결 정보 입력 후 자동으로 전체 프로세스 실행
```

#### 3.2 명령행 모드
```bash
# 로컬 MongoDB 전체 분석
python main.py --mode mongodb --mongodb-uri "mongodb://localhost:27017/"

# 원격 MongoDB 제한 분석
python main.py --mode mongodb \
  --mongodb-uri "mongodb+srv://user:pass@cluster.mongodb.net/" \
  --limit 1000 \
  --database "musinsa_db" \
  --collection "reviews"
```

### 4. MongoDB 문서 구조

#### 4.1 원본 리뷰 문서
```json
{
  "_id": ObjectId("..."),
  "product_id": "12345",
  "user_id": "user123",
  "score": 5,
  "text": "배송이 빠르고 품질도 좋아요",
  "created_at": "2024-01-15"
}
```

#### 4.2 분석 후 리뷰 문서
```json
{
  "_id": ObjectId("..."),
  "product_id": "12345",
  "user_id": "user123",
  "score": 5,
  "text": "배송이 빠르고 품질도 좋아요",
  "created_at": "2024-01-15",
  "sentiment_analysis": {
    "overall_prediction": "긍정",
    "overall_confidence": 0.921,
    "overall_negative_prob": 0.012,
    "overall_neutral_prob": 0.067,
    "overall_positive_prob": 0.921,
    "detected_aspects": ["배송", "품질"],
    "aspect_count": 2,
    "analyzed_at": "2024-01-20T10:30:00",
    "aspect_analysis": {
      "배송": {
        "mentioned": true,
        "sentiment": "긍정",
        "confidence": 0.945,
        "negative_prob": 0.008,
        "neutral_prob": 0.047,
        "positive_prob": 0.945
      },
      "품질": {
        "mentioned": true,
        "sentiment": "긍정",
        "confidence": 0.892,
        "negative_prob": 0.015,
        "neutral_prob": 0.093,
        "positive_prob": 0.892
      }
    }
  }
}
```

### 5. 고급 사용법

#### 5.1 필터링 쿼리 사용
```python
# 특정 조건의 리뷰만 분석
filter_query = {
    "score": {"$gte": 4},           # 4점 이상 리뷰만
    "text": {"$regex": "배송"}      # "배송"이 포함된 리뷰만
}
```

#### 5.2 배치 처리
```python
# 대용량 데이터를 위한 배치 처리
analyzer.analyze_reviews(model_name, reviews, batch_size=50)
```

#### 5.3 에러 처리
```python
# 연결 실패 시 자동 재시도
# 분석 실패 시 해당 리뷰 건너뛰기
# 부분 완료 시 재시작 가능
```

## 📊 분석 결과

### 전체 감정분석 결과
- **전체감정예측**: 부정/중립/긍정
- **전체예측신뢰도**: 예측 신뢰도 (0-1)
- **전체부정확률/중립확률/긍정확률**: 각 클래스별 확률

### 속성별 감정분석 결과
각 패션 속성(디자인, 가격, 품질 등)에 대해:
- **{속성}_언급여부**: 해당 속성이 언급되었는지 여부
- **{속성}_감정**: 해당 속성에 대한 감정 (부정/중립/긍정)
- **{속성}_신뢰도**: 해당 속성 감정 예측 신뢰도
- **{속성}_부정확률/중립확률/긍정확률**: 각 클래스별 확률

### AI 속성 감지 정보
- **감지된_속성들**: 모델이 감지한 관련 속성 목록
- **속성_개수**: 감지된 속성의 개수

## 🔧 설정 변경

`config.py` 파일에서 다음 설정을 변경할 수 있습니다:

- **허깅페이스 모델**: `HUGGINGFACE_MODEL`
- **출력 디렉토리**: `OUTPUT_DIR`
- **패션 속성 목록**: `FASHION_ASPECTS`

## 📈 성능 지표

학습된 모델의 성능:
- **평균 예측 신뢰도**: 0.921
- **감정 분포**: 긍정 70.2%, 중립 24.5%, 부정 5.2%
- **평균 속성 감지 수**: 리뷰당 14.6개

## 🚨 주의사항

1. **GPU 사용**: CUDA가 설치된 환경에서 더 빠른 예측이 가능합니다.
2. **메모리 요구사항**: 대용량 데이터 처리 시 충분한 RAM이 필요합니다.
3. **데이터 형식**: CSV 파일의 텍스트 컬럼명을 정확히 지정해야 합니다.
4. **네트워크 연결**: 첫 실행 시 허깅페이스에서 모델을 다운로드합니다.

## 🐛 문제 해결

### 일반적인 오류

1. **모델 로드 실패**
   - 인터넷 연결 확인
   - 허깅페이스 모델명 확인

2. **CSV 파일 읽기 실패**
   - 파일 경로 확인
   - 텍스트 컬럼명 확인
   - 파일 인코딩 확인 (UTF-8, CP949, EUC-KR 지원)

3. **메모리 부족**
   - 배치 크기 줄이기
   - 더 작은 데이터셋으로 테스트

## 📞 지원

문제가 발생하면 다음을 확인해주세요:
1. Python 버전 (3.8 이상 권장)
2. 의존성 패키지 설치 상태
3. 인터넷 연결 상태
4. GPU/CPU 메모리 사용량

## 📄 라이선스

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다.