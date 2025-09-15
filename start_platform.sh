#!/bin/bash

# 🚀 Dynamic MongoDB Analytics Platform 시작 스크립트

echo "🚀 Dynamic MongoDB Analytics Platform 시작"
echo "================================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 현재 디렉토리 확인
CURRENT_DIR=$(pwd)
echo -e "${BLUE}현재 디렉토리: $CURRENT_DIR${NC}"

# 필요한 디렉토리 존재 확인
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ 오류: backend 또는 frontend 디렉토리를 찾을 수 없습니다.${NC}"
    echo -e "${YELLOW}nlp-analytics-platform 디렉토리에서 실행해주세요.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 프로젝트 구조 확인 완료${NC}"
echo ""

# Python 가상환경 확인 및 생성
echo -e "${CYAN}🐍 Python 환경 설정 중...${NC}"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}가상환경을 생성합니다...${NC}"
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 가상환경 생성 완료${NC}"
    else
        echo -e "${RED}❌ 가상환경 생성 실패${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ 기존 가상환경 발견${NC}"
fi

# 가상환경 활성화
echo -e "${YELLOW}가상환경 활성화 중...${NC}"
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# 백엔드 의존성 설치 및 확인
echo -e "${CYAN}📦 백엔드 의존성 설치 중...${NC}"
cd backend

# requirements.txt 존재 확인
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt를 찾을 수 없습니다.${NC}"
    exit 1
fi

# 패키지 설치
echo -e "${YELLOW}백엔드 패키지 설치 중... (시간이 걸릴 수 있습니다)${NC}"
pip install -r requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 백엔드 의존성 설치 완료${NC}"
else
    echo -e "${RED}❌ 백엔드 의존성 설치 실패${NC}"
    exit 1
fi

# 환경 변수 파일 확인
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚙️ .env 파일을 생성합니다...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ .env 파일 생성 완료${NC}"
        echo -e "${CYAN}💡 .env 파일에서 MongoDB URL 등을 설정해주세요.${NC}"
    else
        echo -e "${YELLOW}⚠️ .env 파일이 없습니다. 기본값으로 실행합니다.${NC}"
    fi
fi

cd ..

# 프론트엔드 의존성 설치 및 확인
echo -e "${CYAN}🌐 프론트엔드 의존성 설치 중...${NC}"
cd frontend

# package.json 존재 확인
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ package.json을 찾을 수 없습니다.${NC}"
    exit 1
fi

# Node.js 및 npm 확인
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm이 설치되어 있지 않습니다.${NC}"
    echo -e "${YELLOW}Node.js를 먼저 설치해주세요: https://nodejs.org/${NC}"
    exit 1
fi

# 패키지 설치
echo -e "${YELLOW}프론트엔드 패키지 설치 중... (시간이 걸릴 수 있습니다)${NC}"
npm install --silent

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 프론트엔드 의존성 설치 완료${NC}"
else
    echo -e "${RED}❌ 프론트엔드 의존성 설치 실패${NC}"
    exit 1
fi

cd ..

echo ""
echo -e "${PURPLE}🎉 모든 설정이 완료되었습니다!${NC}"
echo ""
echo -e "${CYAN}🚀 서버를 시작하려면 다음 명령을 실행하세요:${NC}"
echo ""
echo -e "${GREEN}1️⃣ 백엔드 서버 시작:${NC}"
echo -e "   cd backend"
echo -e "   python start_server.py"
echo ""
echo -e "${GREEN}2️⃣ 프론트엔드 서버 시작 (새 터미널에서):${NC}"
echo -e "   cd frontend" 
echo -e "   npm start"
echo ""
echo -e "${BLUE}📍 접속 주소:${NC}"
echo -e "   • 프론트엔드: ${CYAN}http://localhost:3000${NC}"
echo -e "   • 백엔드 API: ${CYAN}http://localhost:8000${NC}"
echo -e "   • API 문서: ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}🔐 테스트 계정:${NC}"
echo -e "   • 관리자: ${GREEN}EMP001${NC} / ${GREEN}password123${NC}"
echo -e "   • 분석가: ${GREEN}EMP002${NC} / ${GREEN}password123${NC}"
echo ""
echo -e "${PURPLE}================================================${NC}"
echo -e "${CYAN}💡 자동으로 서버를 시작하려면 './run_servers.sh'를 실행하세요!${NC}"