"""
FastAPI 서버 시작 스크립트
개발 및 프로덕션 환경을 위한 설정
"""

import uvicorn
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

if __name__ == "__main__":
    # 환경 변수에서 설정 읽기
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    reload = os.getenv("RELOAD", "true").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info")
    
    print("🚀 Dynamic MongoDB Analytics API 서버 시작")
    print(f"📍 주소: http://{host}:{port}")
    print(f"🔧 디버그 모드: {debug}")
    print(f"🔄 자동 재시작: {reload}")
    print(f"📊 로그 레벨: {log_level}")
    print()
    print("📖 API 문서:")
    print(f"   - Swagger UI: http://localhost:{port}/docs")
    print(f"   - ReDoc: http://localhost:{port}/redoc")
    print()
    print("🧪 테스트 사용자:")
    print("   - ID: admin, PW: admin123 (관리자)")
    print("   - ID: user001, PW: user123 (분석가)")
    print()
    
    # 서버 시작
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )