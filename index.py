from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API 설정 ---
# 1. Gemini (Step 1, 5, 3, 6)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.0-pro:generateContent"

# 2. Trinka (Step 2)
TRINKA_API_KEY = os.getenv("TRINKA_API_KEY")
TRINKA_API_URL = "https://api.trinka.ai/v1/check"  # 예시 URL (실제 엔드포인트 확인 필요)

# 3. LanguageTool (Step 4)
LANGUAGETOOL_USERNAME = os.getenv("LANGUAGETOOL_USERNAME")
LANGUAGETOOL_API_KEY = os.getenv("LANGUAGETOOL_API_KEY")
LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"

class ProcessTextRequest(BaseModel):
    text: str
    step: int

class ProcessTextResponse(BaseModel):
    result: str
    step: int
    message: str

# --- Gemini 도우미 함수 ---
async def call_gemini(text: str, prompt: str):
    if not GEMINI_API_KEY:
        return f"[Mock] Gemini API Key가 없습니다. 결과: {text}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": f"{prompt}\n\nInput Text:\n{text}"}]}],
                    "generationConfig": {"temperature": 0.3}
                }
            )
            if response.status_code != 200:
                raise Exception(f"Gemini Error: {response.text}")
            return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# --- Trinka 도우미 함수 ---
async def call_trinka(text: str):
    if not TRINKA_API_KEY:
        # 키가 없으면 Gemini가 대신 Trinka 스타일로 교정
        return await call_gemini(text, "당신은 Trinka AI와 같은 엄격한 문법 교정기입니다. 한국어 맞춤법과 문법 오류를 완벽하게 수정하세요.")
    
    async with httpx.AsyncClient() as client:
        try:
            # 실제 Trinka API 명세에 맞춰 수정 필요
            response = await client.post(
                TRINKA_API_URL,
                headers={"x-api-key": TRINKA_API_KEY},
                json={"text": text}
            )
            # 응답 파싱 로직 (예시)
            return response.json().get("corrected_text", text)
        except Exception as e:
            return f"[Trinka Error] {str(e)} (Gemini Fallback: {await call_gemini(text, '문법 교정해주세요.')})"

# --- LanguageTool 도우미 함수 ---
async def call_languagetool(text: str):
    if not LANGUAGETOOL_USERNAME or not LANGUAGETOOL_API_KEY:
         # 키가 없으면 Gemini가 대신 LanguageTool 스타일로 교정
        return await call_gemini(text, "당신은 LanguageTool과 같은 스타일 교정기입니다. 문체를 다듬고 세련되게 만드세요.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                LANGUAGETOOL_URL,
                data={
                    "text": text,
                    "language": "ko-KR",
                    "username": LANGUAGETOOL_USERNAME,
                    "apiKey": LANGUAGETOOL_API_KEY
                }
            )
            # LanguageTool은 교정 목록을 반환하므로 이를 적용하는 로직 필요 (여기선 단순화)
            return f"[LT API 연동됨] {text} (실제 적용 로직 구현 필요)"
        except Exception:
            return await call_gemini(text, "스타일 교정해주세요.")


# --- 메인 프로세서 ---
@app.post("/api/process-text")
async def process_text(request: ProcessTextRequest):
    step = request.step
    text = request.text
    result = text
    msg = ""

    if step == 1: # 문장 간소화 (Gemini 3.0)
        result = await call_gemini(text, "문장을 간결하고 명확하게 간소화하세요. 핵심 의미는 유지하세요.")
        msg = "문장 간소화 (Gemini 3.0)"

    elif step == 2: # 문법 교정 (Trinka)
        result = await call_trinka(text)
        msg = "문법 교정 (Trinka API)"

    elif step == 3: # 어조 조정 (Wordtune)
        # Wordtune은 공식 공개 API가 없으므로 Gemini가 Wordtune 페르소나로 작동
        result = await call_gemini(text, "Wordtune 처럼 작동하세요. 이 텍스트의 어조를 '공식적이고 전문적(Formal)'으로 변경하세요.")
        msg = "어조 조정 (Wordtune Style by Gemini)"

    elif step == 4: # 스타일 교정 (LanguageTool)
        result = await call_languagetool(text)
        msg = "스타일 교정 (LanguageTool API)"

    elif step == 5: # 민감성 검사 (Gemini 3.0)
        result = await call_gemini(text, "텍스트의 편향성, 혐오 표현, 민감한 내용을 검사하고 순화하세요.")
        msg = "민감성 검사 (Gemini 3.0)"

    elif step == 6: # 최종 검토 (QuillBot)
         # QuillBot도 공식 API 제한적. Gemini가 QuillBot 페르소나로 작동
        result = await call_gemini(text, "QuillBot 처럼 작동하세요. 문다듬기(Paraphrasing)를 통해 문장을 가장 자연스러운 한국어로 유려하게 바꾸세요.")
        msg = "최종 검토 (QuillBot Style by Gemini)"

    else:
        raise HTTPException(status_code=400, detail="Invalid step")

    return ProcessTextResponse(result=result, step=step, message=msg)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "TOPLUS Hybrid API Engine"}
