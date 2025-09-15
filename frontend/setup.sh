#!/bin/bash

# NLP Analytics Platform Frontend 설치 스크립트
# 사용법: ./setup.sh

echo "🚀 NLP Analytics Platform Frontend 설치를 시작합니다..."
echo

# Node.js 버전 확인
echo "📋 시스템 요구사항 확인 중..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js가 설치되지 않았습니다."
    echo "   https://nodejs.org/ 에서 Node.js LTS 버전을 다운로드하여 설치해주세요."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm이 설치되지 않았습니다."
    echo "   Node.js와 함께 자동으로 설치되어야 합니다."
    exit 1
fi

NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)

echo "✅ Node.js 버전: $NODE_VERSION"
echo "✅ npm 버전: $NPM_VERSION"
echo

# 의존성 설치
echo "📦 의존성 패키지 설치 중..."
echo "   (2-3분 정도 소요될 수 있습니다)"
echo

if npm install; then
    echo "✅ 의존성 설치 완료!"
else
    echo "❌ 의존성 설치 실패. 다음을 시도해보세요:"
    echo "   npm cache clean --force"
    echo "   rm -rf node_modules package-lock.json"
    echo "   npm install"
    exit 1
fi

echo
echo "🎉 설치가 완료되었습니다!"
echo
echo "🚀 애플리케이션 실행 방법:"
echo "   npm start              # 개발 서버 실행"
echo "   npm run build          # 빌드 (배포용)"
echo
echo "🌐 실행 후 브라우저에서 접속:"
echo "   http://localhost:3000"
echo
echo "🔑 로그인 정보 (데모용):"
echo "   사번: 아무거나 (예: admin, test, emp001)"
echo "   비밀번호: 아무거나 (예: password, 123456)"
echo
echo "📖 자세한 사용법은 README.md를 참고하세요."
echo
echo