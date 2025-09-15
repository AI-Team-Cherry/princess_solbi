# NLP Analytics Platform Frontend

기업용 자연어 데이터 분석 플랫폼의 프론트엔드입니다. 직원들이 자연어로 데이터를 질의하고 분석 결과를 시각화하여 공유할 수 있는 웹 애플리케이션입니다.

## 📋 목차

- [주요 기능](#주요-기능)
- [필수 조건](#필수-조건)
- [설치 및 실행](#설치-및-실행)
- [사용법](#사용법)
- [프로젝트 구조](#프로젝트-구조)
- [기술 스택](#기술-스택)
- [문제 해결](#문제-해결)

## 🌟 주요 기능

### 🔐 사용자 관리

- 사번 기반 로그인 시스템 (데모용: 아무 사번/비밀번호로 로그인 가능)
- 사용자 프로필 관리

### 🗣️ 자연어 데이터 분석

- **한국어 자연어 질의 처리** (예: "일별 매출 추이를 보여줘")
- **실시간 데이터 시각화** (Vega-Lite 차트)
- **차트 종류 변경** (막대/선/면적/원형/산점도)
- **색상 테마 선택** 및 **투명도 조절**
- **목업 데이터**로 백엔드 없이도 완전 동작

### 📊 분석 결과 관리

- 개인 분석 히스토리 저장
- 분석 결과 편집 및 태그 관리
- 분석 결과 공유 및 재활용

### ⚙️ 설정 페이지

- 테마 변경 (라이트/다크/시스템)
- 알림 설정 (이메일/푸시/분석 완료 등)
- 언어 설정 (한국어/영어/일본어)
- 프로필 정보 관리

## 💻 필수 조건

실행하기 전에 다음 프로그램들이 설치되어 있어야 합니다:

### Node.js 설치

1. **Windows/Mac 사용자**:

   - [Node.js 공식 웹사이트](https://nodejs.org/)에서 LTS 버전 다운로드
   - 설치 프로그램 실행 (기본 설정으로 설치)

2. **Linux 사용자**:

   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install nodejs npm

   # CentOS/RHEL
   sudo yum install nodejs npm
   ```

### 설치 확인

터미널/명령 프롬프트에서 다음 명령어로 설치 확인:

```bash
node --version    # v18.0.0 이상
npm --version     # 8.0.0 이상
```

## 🚀 설치 및 실행

### 1단계: 프로젝트 다운로드

```bash
# Git으로 다운로드하는 경우
git clone [프로젝트 URL]
cd nlp-analytics-platform/frontend

# 또는 압축 파일을 받은 경우
unzip nlp-analytics-frontend.zip
cd frontend
```

### 2단계: 의존성 설치

```bash
npm install
```

⏳ **설치 시간**: 2-3분 정도 소요될 수 있습니다.

### 3단계: 개발 서버 실행

```bash
npm start
```

### 4단계: 브라우저에서 접속

- 자동으로 브라우저가 열리며 `http://localhost:3000`으로 이동합니다
- 수동으로 접속하려면: 브라우저 주소창에 `http://localhost:3000` 입력

## 🔧 기타 실행 명령어

### 빌드 (배포용)

```bash
npm run build
```

- `build/` 폴더에 최적화된 파일들이 생성됩니다
- 웹서버에 배포할 때 사용합니다

### 빌드된 파일 실행

```bash
# 방법 1: Python이 설치되어 있는 경우
cd build
python -m http.server 8000
# 브라우저에서 http://localhost:8000 접속

# 방법 2: serve 패키지 사용
npx serve -s build
```

## 🎯 사용법

### 로그인

1. 브라우저에서 `http://localhost:3000` 접속
2. **사번**: 아무거나 입력 (예: `admin`, `emp001`, `test` 등)
3. **비밀번호**: 아무거나 입력 (예: `password`, `123456` 등)
4. **로그인** 버튼 클릭

> 💡 **데모 모드**: 백엔드 없이 동작하므로 아무 사번/비밀번호로도 로그인됩니다!

### 자연어 검색

1. **좌측 메뉴**에서 **"자연어 검색"** 클릭
2. **질문 입력** (예시):
   - "일별 매출 추이를 보여줘"
   - "제품별 매출 현황을 분석해줘"
   - "고객 세그먼트를 분석해줘"
3. **분석하기** 버튼 클릭
4. **차트와 분석 결과** 확인
5. **"시각화 옵션"** 패널에서 차트 종류/색상 변경 가능

### 테마 변경

1. **우측 상단 프로필** 클릭
2. **"설정"** 선택
3. **테마 설정**에서 원하는 모드 선택:
   - 🌕 **라이트 모드**: 밝고 깔끔한 스타일
   - 🌑 **다크 모드**: 개발자가 좋아하는 어둡고 세련된 스타일
   - 🔄 **시스템 설정**: OS 설정에 따라 자동 변경

## 📁 프로젝트 구조

```
frontend/
├── public/                 # 정적 파일들
│   ├── index.html         # 메인 HTML
│   └── favicon.ico        # 파비콘
├── src/                   # 소스 코드
│   ├── components/        # 재사용 컴포넌트
│   │   └── Layout/        # 레이아웃 컴포넌트
│   ├── contexts/          # React Context
│   │   ├── AuthContext.tsx      # 인증 관리
│   │   └── ThemeContext.tsx     # 테마 관리
│   ├── pages/             # 페이지 컴포넌트
│   │   ├── LoginPage.tsx        # 로그인 페이지
│   │   ├── DashboardPage.tsx    # 대시보드
│   │   ├── SearchPage.tsx       # 자연어 검색
│   │   ├── MyPage.tsx           # 마이페이지
│   │   ├── SettingsPage.tsx     # 설정 페이지
│   │   └── ...
│   ├── services/          # API 서비스 (목업)
│   │   ├── auth.ts              # 인증 API
│   │   └── analytics.ts         # 분석 API
│   ├── types/             # TypeScript 타입
│   └── App.tsx            # 메인 앱 컴포넌트
├── package.json           # 프로젝트 설정
└── README.md              # 이 파일
```

## 🛠️ 기술 스택

### Frontend Framework

- **React 19.1.1** + **TypeScript**
- **React Router 7.8.2** (라우팅)

### UI Framework

- **Material-UI (MUI) 7.3.2** (커스터마이징)
- **Material Icons** (아이콘)

### Data Visualization

- **Vega-Lite 5.16.0** (차트 라이브러리)
- **React-Vega 7.6.0** (React 연동)

### State Management

- **React Context API** (전역 상태 관리)
- **useState/useEffect** (지역 상태 관리)

### HTTP Client

- **Axios 1.11.0** (API 통신, 현재는 목업 데이터)

## 🔍 문제 해결

### 포트 3000이 이미 사용 중인 경우

```bash
# 포트를 사용하는 프로세스 종료 (Linux/Mac)
lsof -ti:3000 | xargs kill -9

# 또는 다른 포트 사용
PORT=3001 npm start
```

### node_modules 관련 오류

```bash
# 의존성 재설치
rm -rf node_modules package-lock.json
npm install
```

### 빌드 오류가 발생하는 경우

```bash
# 캐시 정리 후 재설치
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
npm start
```

### 브라우저에서 "Cannot GET /" 오류

- 개발 서버가 제대로 시작되었는지 확인
- `http://localhost:3000` 주소가 정확한지 확인
- 방화벽이나 안티바이러스가 차단하지 않는지 확인

### Windows에서 실행 권한 오류

- PowerShell을 **관리자 권한**으로 실행
- 또는 명령 프롬프트(cmd) 사용

## 📞 지원

문제가 발생하거나 질문이 있으시면:

1. **콘솔 로그** 확인 (F12 → Console 탭)
2. **터미널 오류 메시지** 확인
3. **Node.js 버전** 확인 (`node --version`)

---
