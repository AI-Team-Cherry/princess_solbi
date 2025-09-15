#!/bin/bash

# 🚀 서버 자동 시작 스크립트

echo "🚀 Dynamic MongoDB Analytics Platform 서버 시작"
echo "================================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 포트 사용 여부 확인
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 포트 사용 중
    else
        return 1  # 포트 사용 안함
    fi
}

# 백엔드 포트 확인 (8000)
if check_port 8000; then
    echo -e "${YELLOW}⚠️ 포트 8000이 이미 사용 중입니다.${NC}"
    echo -e "${CYAN}기존 프로세스를 종료하시겠습니까? (y/n): ${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}포트 8000 프로세스 종료 중...${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        echo -e "${RED}❌ 백엔드 서버를 시작할 수 없습니다.${NC}"
        exit 1
    fi
fi

# 프론트엔드 포트 확인 (3000)
if check_port 3000; then
    echo -e "${YELLOW}⚠️ 포트 3000이 이미 사용 중입니다.${NC}"
    echo -e "${CYAN}기존 프로세스를 종료하시겠습니까? (y/n): ${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}포트 3000 프로세스 종료 중...${NC}"
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        echo -e "${RED}❌ 프론트엔드 서버를 시작할 수 없습니다.${NC}"
        exit 1
    fi
fi

# PID 파일 경로
BACKEND_PID_FILE="backend.pid"
FRONTEND_PID_FILE="frontend.pid"

# 이전 PID 파일 정리
cleanup_pids() {
    if [ -f "$BACKEND_PID_FILE" ]; then
        local backend_pid=$(cat "$BACKEND_PID_FILE")
        kill $backend_pid 2>/dev/null || true
        rm -f "$BACKEND_PID_FILE"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE")
        kill $frontend_pid 2>/dev/null || true
        rm -f "$FRONTEND_PID_FILE"
    fi
}

# Ctrl+C 시그널 처리
cleanup() {
    echo -e "\n${YELLOW}🛑 서버 종료 중...${NC}"
    cleanup_pids
    echo -e "${GREEN}✅ 모든 서버가 종료되었습니다.${NC}"
    exit 0
}

trap cleanup INT TERM

echo -e "${CYAN}🔧 가상환경 활성화 중...${NC}"
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# 백엔드 서버 시작
echo -e "${PURPLE}⚙️ 백엔드 서버 시작 중...${NC}"
cd backend

python start_server.py &
BACKEND_PID=$!
echo $BACKEND_PID > "../$BACKEND_PID_FILE"

echo -e "${GREEN}✅ 백엔드 서버 시작됨 (PID: $BACKEND_PID)${NC}"
echo -e "${CYAN}   API 서버: http://localhost:8000${NC}"
echo -e "${CYAN}   API 문서: http://localhost:8000/docs${NC}"

cd ..

# 백엔드 서버가 준비될 때까지 대기
echo -e "${YELLOW}⏳ 백엔드 서버 초기화 대기 중...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ 백엔드 서버 준비 완료!${NC}"
        break
    fi
    sleep 2
    echo -n "."
done

# 프론트엔드 서버 시작
echo -e "\n${BLUE}🌐 프론트엔드 서버 시작 중...${NC}"
cd frontend

# 브라우저 자동 열기 방지
export BROWSER=none

npm start &
FRONTEND_PID=$!
echo $FRONTEND_PID > "../$FRONTEND_PID_FILE"

echo -e "${GREEN}✅ 프론트엔드 서버 시작됨 (PID: $FRONTEND_PID)${NC}"
echo -e "${CYAN}   웹 앱: http://localhost:3000${NC}"

cd ..

echo ""
echo -e "${PURPLE}🎉 모든 서버가 성공적으로 시작되었습니다!${NC}"
echo ""
echo -e "${CYAN}📍 접속 정보:${NC}"
echo -e "   • ${GREEN}웹 애플리케이션${NC}: http://localhost:3000"
echo -e "   • ${GREEN}API 서버${NC}: http://localhost:8000" 
echo -e "   • ${GREEN}API 문서${NC}: http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}🔐 테스트 계정:${NC}"
echo -e "   • ${GREEN}관리자${NC}: EMP001 / password123"
echo -e "   • ${GREEN}분석가${NC}: EMP002 / password123"
echo ""
echo -e "${BLUE}💡 브라우저에서 http://localhost:3000 으로 접속해보세요!${NC}"
echo ""
echo -e "${RED}⏹️ 서버 종료: Ctrl+C${NC}"
echo ""

# 프론트엔드가 준비될 때까지 대기 후 브라우저 열기
sleep 10
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:3000 >/dev/null 2>&1 &
elif command -v open > /dev/null; then
    open http://localhost:3000 >/dev/null 2>&1 &
elif command -v start > /dev/null; then
    start http://localhost:3000 >/dev/null 2>&1 &
fi

# 서버 실행 상태 유지
wait