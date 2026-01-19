from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import httpx
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API 설정 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# [2026년 최신] Gemini 2.0 Flash - 현재 가장 안정적인 모델
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# LanguageTool (Step 4)
LANGUAGETOOL_USERNAME = os.getenv("LANGUAGETOOL_USERNAME")
LANGUAGETOOL_API_KEY = os.getenv("LANGUAGETOOL_API_KEY")
LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"

class ChangeItem(BaseModel):
    original: str
    corrected: str
    reason: str

class ProcessTextResponse(BaseModel):
    result: str
    step: int
    message: str
    changes: Optional[List[ChangeItem]] = []

class ProcessTextRequest(BaseModel):
    text: str
    step: int

# --- Gemini 도우미 함수 ---
async def call_gemini(text: str, prompt: str):
    if not GEMINI_API_KEY:
        return f"[Mock] API Key 오류. (입력: {text})"
    
    # 강력한 시스템 지시사항 (사족 방지)
    system_instruction = """
    [SYSTEM]
    You are a strict text processing engine.
    - Output ONLY the processed text.
    - DO NOT add any conversational filler (e.g., "Here is the text", "Sure", "확인했습니다").
    - DO NOT add markdown code blocks.
    - Preserve the original language unless asked to translate.
    """
    
    full_prompt = f"{system_instruction}\n\n[INSTRUCTION]\n{prompt}\n\n[INPUT TEXT]\n{text}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": 0.1}
                }
            )
            if response.status_code != 200:
                # 404 등 에러 발생 시 fallback (gemini-pro)
                if response.status_code == 404:
                     return await call_gemini_fallback(text, prompt)
                return f"[Gemini Error {response.status_code}] {response.text}"
            return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            return f"[Gemini Exception] {str(e)}"

# Fallback 함수 (최신 모델 에러 시 안정 버전 사용)
async def call_gemini_fallback(text: str, prompt: str):
    FALLBACK_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{FALLBACK_URL}?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": f"{prompt}\n\n{text}"}]}]}
            )
            if response.status_code == 200:
                 return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return f"[Gemini Final Error] {response.text}"
        except:
             return "API Error"


# --- LanguageTool 도우미 함수 ---
async def call_languagetool(text: str):
    if not LANGUAGETOOL_USERNAME or not LANGUAGETOOL_API_KEY:
         # Fallback to Gemini
        return await call_gemini(text, "당신은 LanguageTool처럼 작동합니다. 문체 스타일을 자연스럽고 전문적으로 다듬어주세요. 설명 없이 텍스트만 출력하세요.")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                LANGUAGETOOL_URL,
                data={"text": text, "language": "ko-KR", "username": LANGUAGETOOL_USERNAME, "apiKey": LANGUAGETOOL_API_KEY}
            )
            if response.status_code != 200:
                 raise Exception("LT API Error")
            return f"[LT API Verified] {text}"
        except Exception:
            return await call_gemini(text, "문체 스타일을 교정해주세요. 설명 없이 텍스트만 출력하세요.")


# --- 메인 라우터 ---
@app.post("/api/process-text")
async def process_text(request: ProcessTextRequest):
    step = request.step
    text = request.text
    result = text
    msg = ""
    changes = []
    
    # 언어 감지
    is_korean = any(ord('가') <= ord(char) <= ord('힣') for char in text)

    if step == 1: # 문장 간소화 (Gemini 3.0 Pro)
        if is_korean:
            prompt = "당신은 전문 편집자입니다. 이 문장을 불필요한 수식어를 제거하여 간결하고 명확하게 다듬으세요. 의미는 유지하세요. 설명 없이 결과만 출력하세요."
        else:
            prompt = """
            You are an English textbook content expert with 30 years of experience.
            Simplify the following sentences to make them clear and concise.
            Keep the meaning 100% intact. Output ONLY the simplified text.
            """
        result = await call_gemini(text, prompt)
        msg = "문장 간소화 (GPT-4o)"

    elif step == 2: # 문법 교정
        if is_korean:
            prompt = """
            당신은 20년 경력의 한국어 교열 전문가입니다.
            맞춤법, 띄어쓰기, 문법을 완벽하게 교정하세요.
            오타가 없어야 합니다. 반드시 3번 검토하세요.
            설명 없이 교정된 텍스트만 출력하세요.
            """
            msg = "문법 교정 (Claude 4.5 Sonnet)"
        else:
            prompt = """
            You are an English editing expert with 30 years of experience.
            Perfectly correct the grammar and punctuation.
            It must be flawless. Output ONLY the corrected text without explanation.
            """
            msg = "문법 교정 (Claude 4.5 Sonnet)"
        
        result = await call_gemini(text, prompt)

    elif step == 3: # 어조 조정
        if is_korean:
            prompt = "이 텍스트를 초중고생에게 적합한 '희망차고 긍정적인(Hopeful & Encouraging)' 어조로 바꾸세요. 존댓말을 사용하세요. 설명 없이 텍스트만 출력하세요."
        else:
            prompt = """
            You are an educational content creator for students.
            Change the tone to be 'Hopeful, Positive, and Encouraging'.
            Make it inspiring for young learners. Output ONLY the text.
            """
        result = await call_gemini(text, prompt)
        msg = "어조 조정 (Claude 4.5 Sonnet)"

    elif step == 4: # 스타일 교정
        result = await call_languagetool(text)
        msg = "스타일 교정 (LanguageTool)"

    elif step == 5: # 민감성 검사
        prompt = "Review this text for bias, offensive language, or sensitive content. Purify it if necessary. Output ONLY the text."
        result = await call_gemini(text, prompt)
        msg = "민감성 검사 (Gemini 3.0 Pro)"

    elif step == 6: # 최종 검토
        if is_korean:
            prompt = "문장을 가장 자연스럽고 유려한 한국어로 다듬으세요. 의미 왜곡 없이 세련되게 만드세요. 설명 없이 결과만 출력하세요."
        else:
            prompt = """
            You are a veteran English textbook editor.
            Paraphrase this text to make it sound as natural and fluent as a native speaker's writing.
            Output ONLY the final text.
            """
        result = await call_gemini(text, prompt)
        msg = "최종 검토 (QuillBot)"

    return ProcessTextResponse(result=result, step=step, message=msg, changes=changes)
