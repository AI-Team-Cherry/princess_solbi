# 🚀 NLP Analytics Platform - Dataset & Analysis Edition

**MongoDB 기반 데이터셋 추출 및 고급 분석 플랫폼**

## ✨ 새로운 주요 기능

### 📊 데이터셋 추출
- MongoDB 컬렉션에서 기간/조건 기반 데이터 추출
- 실시간 미리보기 및 필터링
- 안전한 데이터셋 저장 및 관리
- 민감정보 자동 마스킹

### 🤖 고급 분석 (LLM/RAG)
- 저장된 데이터셋 기반 AI 분석
- 인사이트 도출, 데이터 요약, 주제 분석, 감성 분석
- 자동 시각화 및 차트 생성
- 참조 문서 및 출처 링크 제공

### 🛡️ 보안 및 안전성
- MongoDB Aggregation 화이트리스트 정책
- 민감정보(이메일, 전화번호, 주소 등) 자동 필터링
- 쿼리 복잡도 제한 및 성능 최적화

## 🏗️ 시스템 구조

```
📁 nlp-analytics-platform/
├── 🌐 frontend/                    # React + TypeScript
│   ├── src/
│   │   ├── pages/                  # 페이지 컴포넌트
│   │   ├── services/               # API 서비스
│   │   └── types/                  # TypeScript 타입
│   └── package.json
│
├── ⚙️ backend/                      # FastAPI + Python
│   ├── app.py                      # 메인 API 서버
│   ├── dynamic_schema_mongodb_analyzer.py  # 핵심 분석 엔진
│   ├── requirements.txt
│   └── start_server.py
│
└── 📚 docs/                        # 문서
```

## 🚦 빠른 시작

### 1️⃣ 백엔드 서버 시작

```bash
cd backend

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 MongoDB URL 등 설정

# 서버 시작
python start_server.py
```

### 2️⃣ 프론트엔드 시작

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 시작
npm start
```

### 3️⃣ 접속 및 테스트

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

**테스트 계정**:
- 관리자: `EMP001` / `password123`
- 분석가: `EMP002` / `password123`

## 🔧 환경 설정

### 백엔드 환경 변수 (.env)
```env
# MongoDB 연결 설정
MONGODB_URI=mongodb+srv://your-connection-string
MONGODB_URL=mongodb+srv://your-connection-string
DB_NAME=musinsa_db
DATABASE_NAME=musinsa_db
USER_DATABASE_NAME=nlp_platform_users

# LLM 설정
MODEL_ID=kakaobrain/kogpt
# MODEL_ID=kakaocorp/kanana-nano-2.1b-instruct

# 벡터 DB 설정 (옵션)
VECTOR_INDEX_NAME=vector_search
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# JWT 설정
JWT_SECRET=your-secret-key-here-change-in-production

# 서버 설정
HOST=0.0.0.0
PORT=8000
DEBUG=true

# 보안 설정
MAX_QUERY_RESULTS=5000
QUERY_TIMEOUT=30
MAX_AGGREGATION_STAGES=10
```

### 프론트엔드 환경 변수 (.env.local)
```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_APP_NAME=Dynamic MongoDB Analytics Platform
```

## 🎯 핵심 기능

### 1. 데이터셋 추출 워크플로우
```
1️⃣ 컬렉션 선택 (reviews, orders, product)
2️⃣ 기간 및 필터 조건 설정
3️⃣ 조인 옵션 선택 (필요시)
4️⃣ 실시간 미리보기 확인
5️⃣ 데이터셋 저장 및 메타데이터 관리
```

### 2. 고급 분석 워크플로우
```
1️⃣ 저장된 데이터셋 목록에서 선택
2️⃣ 분석 유형 선택 (인사이트/요약/주제/감성)
3️⃣ LLM 기반 분석 실행
4️⃣ 분석 결과 + 차트 + 참조 문서 표시
5️⃣ CSV 다운로드 및 결과 저장
```

### 3. 안전 가드 시스템
- 🔒 **화이트리스트 정책**: $match, $project, $group 등만 허용
- 🚫 **JavaScript 차단**: $where, function, mapReduce 금지
- 👤 **민감정보 보호**: 이메일, 전화번호, 주소 자동 마스킹
- ⏱️ **성능 최적화**: 쿼리 제한(기본 100, 최대 5,000)

## 📚 API 문서

### 인증 API
- `POST /api/auth/login` - 로그인
- `GET /api/auth/me` - 현재 사용자 정보
- `POST /api/auth/logout` - 로그아웃

### 데이터셋 API
- `POST /api/query/preview` - 데이터 미리보기
- `POST /api/datasets/save` - 데이터셋 저장
- `GET /api/datasets/list` - 데이터셋 목록 조회
- `GET /api/datasets/{id}` - 데이터셋 상세 정보

### 분석 API  
- `POST /api/analysis/run` - AI 기반 분석 실행
- `GET /api/analysis/status` - 분석 서비스 상태

### 시스템 API (기존 유지)
- `GET /api/schema/info` - 스키마 정보
- `POST /api/schema/refresh` - 스키마 새로고침
- `GET /api/queries/suggestions` - 쿼리 제안

## 🔥 주요 개선사항

### 기존 "자연어 처리/ML 고급 분석" vs 새 "데이터셋 추출/고급 분석"

| 기능 | 기존 | 새 시스템 | 개선점 |
|------|------|----------|--------|
| 데이터 접근 | 🔴 직접 쿼리 | ✅ 안전한 데이터셋 추출 | 보안성 ↑ |
| 분석 과정 | 🔴 일회성 | ✅ 저장/재사용 가능 | 효율성 ↑ |
| 민감정보 보호 | 🔴 수동 관리 | ✅ 자동 마스킹 | 안전성 ↑ |
| LLM 활용 | 🔴 제한적 | ✅ 전문 분석 모듈 | 분석 품질 ↑ |
| 시각화 | 🔴 기본 차트 | ✅ 동적 차트 생성 | 사용자 경험 ↑ |

## 🛠️ 기술 스택

### Frontend
- **React 18** + **TypeScript**
- **Material-UI (MUI)** - 디자인 시스템  
- **React-Vega** - 데이터 시각화
- **Axios** - API 통신

### Backend  
- **FastAPI** - 고성능 API 서버
- **Motor** - 비동기 MongoDB 드라이버  
- **PyMongo** - MongoDB 동기 드라이버
- **Transformers** - AI/ML 모델
- **JWT** - 인증 시스템

### AI/ML
- **HuggingFace Transformers** - LLM 모델 허브
- **kakaobrain/kogpt** - 한국어 생성형 LLM
- **Sentence Transformers** - 텍스트 임베딩
- **NumPy/Pandas** - 데이터 처리 및 통계

## 🚀 배포 가이드

### Docker 배포
```bash
# 백엔드
cd backend
docker build -t nlp-backend .
docker run -p 8000:8000 nlp-backend

# 프론트엔드  
cd frontend
docker build -t nlp-frontend .
docker run -p 3000:3000 nlp-frontend
```

### 클라우드 배포
- **AWS**: ECS + ALB
- **Azure**: Container Instances
- **Google Cloud**: Cloud Run

## 📊 성능 지표

- **쿼리 응답 시간**: 평균 2-5초
- **스키마 분석 시간**: 초기 10-30초, 이후 캐시 활용
- **동시 사용자**: 최대 100명 (기본 설정)
- **지원 데이터**: MongoDB 컬렉션 무제한

## 🤝 사용 시나리오

### 비즈니스 분석가
```
"이번 분기 매출이 작년 대비 얼마나 증가했나요?"
"고객 연령대별 구매 패턴을 분석해주세요"
"재고가 부족한 상품들을 찾아주세요"
```

### 마케팅 팀
```  
"캠페인 효과를 측정해주세요"
"지역별 브랜드 선호도를 보여주세요"
"리뷰 감성이 부정적인 상품을 찾아주세요"
```

### 개발팀
```
"API 응답 시간 추이를 분석해주세요"
"에러 로그 패턴을 찾아주세요" 
"사용자 활동 통계를 보여주세요"
```

## 🔮 향후 계획

### Phase 2 (Q1 2024)
- 🤖 **GPT 연동**: OpenAI API 통합으로 더 자연스러운 대화
- 📱 **모바일 앱**: React Native 기반 모바일 버전
- 🔔 **실시간 알림**: 스키마 변경/이상치 감지 알림

### Phase 3 (Q2 2024)  
- 🌐 **다국어 지원**: 영어, 중국어, 일본어 지원
- 📈 **고급 분석**: 머신러닝 기반 예측 분석
- 🔐 **엔터프라이즈 보안**: SAML/LDAP 통합

## 🏆 차별화 포인트

1. **🔄 완전 자동화**: 스키마 변경에 대한 수동 개입 불필요
2. **🧠 지능형 추론**: AI 기반 필드 의미 파악
3. **⚡ 고성능**: 캐싱과 최적화된 쿼리 생성  
4. **🎯 한국어 특화**: 국내 기업 환경에 최적화
5. **📊 즉시 시각화**: 분석과 동시에 차트 생성

## 📞 지원 및 문의

- **이슈 리포팅**: GitHub Issues
- **기술 문의**: 개발팀 연락처
- **기능 요청**: Feature Request 템플릿 활용

---

**🎉 이제 MongoDB 스키마가 아무리 변해도 걱정없는 분석 플랫폼을 경험해보세요!**