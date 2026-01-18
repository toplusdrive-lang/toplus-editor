"""
TOPLUS Editor - FastAPI Backend Server
텍스트 검수 프로세스를 위한 API 서버
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

# FastAPI 앱 생성
app = FastAPI(
    title="TOPLUS Editor API",
    description="6단계 텍스트 검수 프로세스 API",
    version="1.0.0"
)

# CORS 설정 - 모든 도메인 허용 (개발 환경)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)


# 요청/응답 모델 정의
class ProcessTextRequest(BaseModel):
    text: str
    step: int  # 1-6 단계


class ProcessTextResponse(BaseModel):
    result: str
    step: int
    message: str


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "TOPLUS Editor API"}


# 텍스트 처리 엔드포인트
@app.post("/api/process-text", response_model=ProcessTextResponse)
async def process_text(request: ProcessTextRequest):
    """
    텍스트를 받아 해당 단계의 처리를 수행합니다.
    
    - step 1: 문장 간소화 (GPT-4o)
    - step 2: 문법 교정 (Trinka)
    - step 3: 어조 조정 (Wordtune)
    - step 4: 스타일 교정 (LanguageTool)
    - step 5: 민감성 검사 (GPT-4o)
    - step 6: 최종 검토 (QuillBot)
    """
    
    if not 1 <= request.step <= 6:
        raise HTTPException(status_code=400, detail="Step must be between 1 and 6")
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # 임시 구현 - 나중에 각 단계별 AI 로직으로 교체
    step_names = {
        1: "문장 간소화",
        2: "문법 교정",
        3: "어조 조정",
        4: "스타일 교정",
        5: "민감성 검사",
        6: "최종 검토"
    }
    
    # 임시 처리 로직
    processed_text = request.text
    
    # Step 1: 간단한 간소화 예시
    if request.step == 1:
        processed_text = processed_text.replace("매우 ", "")
        processed_text = processed_text.replace("정말 ", "")
        processed_text = processed_text.replace("아주 ", "")
    
    # Step 2: 간단한 문법 교정 예시
    elif request.step == 2:
        processed_text = processed_text.replace("되요", "돼요")
        processed_text = processed_text.replace("됬", "됐")
        processed_text = processed_text.replace("않됩", "안 됩")
    
    return ProcessTextResponse(
        result=f"Processing for step {request.step}: {processed_text}",
        step=request.step,
        message=f"{step_names[request.step]} 처리 완료"
    )


# 서버 실행
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
