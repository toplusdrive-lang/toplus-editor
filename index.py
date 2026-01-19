from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class ProcessTextRequest(BaseModel):
    text: str
    step: int

class ProcessTextResponse(BaseModel):
    result: str
    step: int
    message: str

# 단계별 시스템 프롬프트
STEP_PROMPTS = {
    1: "당신은 문장 간소화 전문가입니다. 주어진 텍스트를 더 간결하고 명확하게 만들어주세요. 불필요한 수식어나 중복 표현을 제거하되, 원래 의미는 유지하세요. 수정된 텍스트만 출력하세요.",
    2: "당신은 한국어 문법 교정 전문가입니다. 주어진 텍스트의 맞춤법, 띄어쓰기, 문법 오류를 수정해주세요. 수정된 텍스트만 출력하세요.",
    3: "당신은 어조 조정 전문가입니다. 주어진 텍스트를 공식적이고 전문적인 어조로 변환해주세요. 수정된 텍스트만 출력하세요.",
    4: "당신은 문체 교정 전문가입니다. 주어진 텍스트의 문체를 일관되게 다듬어주세요. 수정된 텍스트만 출력하세요.",
    5: "당신은 민감성 검사 전문가입니다. 주어진 텍스트에서 부적절하거나 민감한 표현이 있다면 적절하게 수정해주세요. 문제가 없다면 원문을 그대로 출력하세요.",
    6: "당신은 최종 검토 전문가입니다. 주어진 텍스트를 최종 검토하여 자연스럽고 완성도 높은 문장으로 다듬어주세요. 수정된 텍스트만 출력하세요."
}

STEP_NAMES = {
    1: "문장 간소화", 2: "문법 교정", 3: "어조 조정",
    4: "스타일 교정", 5: "민감성 검사", 6: "최종 검토"
}

@app.get("/api/health")
async def health_check():
    has_key = "configured" if GEMINI_API_KEY else "not configured"
    return {"status": "healthy", "service": "TOPLUS Editor API", "gemini_api": has_key}

@app.post("/api/process-text")
async def process_text(request: ProcessTextRequest):
    if not 1 <= request.step <= 6:
        raise HTTPException(status_code=400, detail="Step must be between 1 and 6")
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # API 키가 없으면 Mock 처리
    if not GEMINI_API_KEY:
        processed = mock_process(request.text, request.step)
        return ProcessTextResponse(
            result=processed,
            step=request.step,
            message=f"{STEP_NAMES[request.step]} 완료 (Mock 모드 - API 키를 설정하세요)"
        )
    
    # Gemini API 호출
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{
                        "parts": [{
                            "text": f"{STEP_PROMPTS[request.step]}\n\n입력 텍스트:\n{request.text}"
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 2048
                    }
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Gemini API error: {response.text}")
            
            data = response.json()
            result_text = data["candidates"][0]["content"]["parts"][0]["text"]
            
            return ProcessTextResponse(
                result=result_text.strip(),
                step=request.step,
                message=f"{STEP_NAMES[request.step]} 완료 (Gemini 2.0)"
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Gemini API timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def mock_process(text: str, step: int) -> str:
    """API 키 없을 때 사용하는 Mock 처리"""
    if step == 1:
        return text.replace("매우 ", "").replace("정말 ", "").replace("아주 ", "")
    elif step == 2:
        return text.replace("되요", "돼요").replace("됬", "됐").replace("않됩", "안 됩")
    return text
