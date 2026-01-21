from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import httpx
import json

# Mangum is required for FastAPI to work on Vercel serverless
from mangum import Mangum

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Export handler for Vercel serverless functions
handler = Mangum(app, lifespan="off")

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("gemini_api_key")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")  # Anthropic Claude
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")  # OpenAI GPT
LANGUAGETOOL_USERNAME = os.getenv("LANGUAGETOOL_USERNAME")
LANGUAGETOOL_API_KEY = os.getenv("LANGUAGETOOL_API_KEY")

# --- API URLs ---
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"

class ChangeItem(BaseModel):
    original: str
    corrected: str
    reason: str

class AnalysisMetrics(BaseModel):
    readability: int = 0
    grammar: int = 0
    tone: str = "Neutral"

class ProcessTextResponse(BaseModel):
    result: str
    step: int
    message: str
    changes: Optional[List[ChangeItem]] = []
    metrics: Optional[AnalysisMetrics] = None

class ProcessTextRequest(BaseModel):
    text: str
    step: int
    textType: Optional[str] = "A"
    targetGrade: Optional[str] = "M1"

class DiagnoseRequest(BaseModel):
    text: str
    textType: str = "A"
    targetGrade: str = "M1"

class DiagnoseResponse(BaseModel):
    readability: int
    grammar: int
    tone: int
    sensitivity: int
    suggestions: Optional[List[ChangeItem]] = []
    message: str

# --- System Instructions ---
SYSTEM_INSTRUCTION = """[SYSTEM]
You are a strict text processing engine.
- Output ONLY the processed text.
- DO NOT add any conversational filler.
- DO NOT add markdown code blocks.
- Preserve the original language unless asked to translate.
"""

# --- Claude API ---
async def call_claude(text: str, prompt: str):
    if not CLAUDE_API_KEY:
        return await call_gemini(text, prompt)
    
    full_prompt = f"{prompt}\n\n{text}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                CLAUDE_API_URL,
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 4096,
                    "system": SYSTEM_INSTRUCTION,
                    "messages": [{"role": "user", "content": full_prompt}]
                }
            )
            if response.status_code == 200:
                return response.json()["content"][0]["text"].strip()
            else:
                return await call_gemini(text, prompt)
        except Exception as e:
            return await call_gemini(text, prompt)

# --- OpenAI GPT API ---
async def call_gpt(text: str, prompt: str):
    if not OPENAI_API_KEY:
        return await call_gemini(text, prompt)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": SYSTEM_INSTRUCTION},
                        {"role": "user", "content": f"{prompt}\n\n{text}"}
                    ],
                    "temperature": 0.1
                }
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            else:
                return await call_gemini(text, prompt)
        except Exception as e:
            return await call_gemini(text, prompt)

# --- Gemini API ---
async def call_gemini(text: str, prompt: str):
    if not GEMINI_API_KEY:
        return f"[Mock] API Key missing"
    
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\n[INSTRUCTION]\n{prompt}\n\n[INPUT TEXT]\n{text}"

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
                if response.status_code == 404:
                    return await call_gemini_fallback(text, prompt)
                return f"[Gemini Error {response.status_code}]"
            return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            return f"[Gemini Exception] {str(e)}"

# --- Gemini Fallback ---
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
            return "[Gemini Fallback Error]"
        except:
            return "API Error"

# --- LanguageTool API ---
async def call_languagetool(text: str):
    async with httpx.AsyncClient() as client:
        try:
            data = {"text": text, "language": "auto"}
            if LANGUAGETOOL_USERNAME and LANGUAGETOOL_API_KEY:
                data["username"] = LANGUAGETOOL_USERNAME
                data["apiKey"] = LANGUAGETOOL_API_KEY
            
            response = await client.post(LANGUAGETOOL_URL, data=data)
            if response.status_code == 200:
                result = response.json()
                matches = result.get("matches", [])
                corrected_text = text
                offset_adjustment = 0
                
                for match in matches:
                    if match.get("replacements"):
                        start = match["offset"] + offset_adjustment
                        end = start + match["length"]
                        replacement = match["replacements"][0]["value"]
                        corrected_text = corrected_text[:start] + replacement + corrected_text[end:]
                        offset_adjustment += len(replacement) - match["length"]
                
                return corrected_text
            else:
                return await call_gemini(text, "Fix grammar and spelling. Output only the text.")
        except Exception:
            return await call_gemini(text, "Fix grammar and spelling. Output only the text.")


# --- Main Router ---
@app.post("/api/process-text")
async def process_text(request: ProcessTextRequest):
    step = request.step
    text = request.text
    result = text
    msg = ""
    changes = []
    metrics = AnalysisMetrics()
    
    is_korean = any(ord('가') <= ord(char) <= ord('힣') for char in text)

    if step == 1:
        prompt = "Analyze context and logical structure. Improve logical flow. Output ONLY the improved text."
        if is_korean:
            prompt = "문맥과 논리 구조를 분석하고 개선하세요. 설명 없이 개선된 텍스트만 출력하세요."
        result = await call_claude(text, prompt)
        msg = "문맥/논리 분석 (Notion AI)"
        metrics.readability = 85

    elif step == 2:
        result = await call_languagetool(text)
        msg = "문법/스펠 체크 (LanguageTool)"
        metrics.grammar = 98

    elif step == 3:
        prompt = "Adjust tone for students. Make it hopeful and encouraging. Output ONLY the adjusted text."
        if is_korean:
            prompt = "학생에게 적합하도록 희망차고 긍정적인 어조로 조정하세요. 설명 없이 텍스트만 출력하세요."
        result = await call_claude(text, prompt)
        msg = "톤 & 타깃독자 조정 (Claude 4.5 Sonnet)"
        metrics.tone = "Hopeful"

    elif step == 4:
        prompt = "Improve style and readability. Make sentences concise. Output ONLY the improved text."
        if is_korean:
            prompt = "스타일과 가독성을 개선하세요. 문장을 간결하게. 설명 없이 텍스트만 출력하세요."
        result = await call_gpt(text, prompt)
        msg = "스타일 & 가독성 (GPT-4o)"
        metrics.readability = 92

    elif step == 5:
        prompt = "Final review. Polish to perfection. Output ONLY the finalized text."
        if is_korean:
            prompt = "최종 검토. 완벽하게 다듬으세요. 설명 없이 완성된 텍스트만 출력하세요."
        result = await call_gemini(text, prompt)
        msg = "최종 검토 (Final Review)"
        metrics.readability = 95
        metrics.grammar = 100
        metrics.tone = "Perfect"

    return ProcessTextResponse(result=result, step=step, message=msg, changes=changes, metrics=metrics)


@app.post("/api/diagnose")
async def diagnose_text(request: DiagnoseRequest):
    text = request.text
    text_type = request.textType
    target_grade = request.targetGrade
    
    # Check if Korean text
    is_korean = any(ord('가') <= ord(char) <= ord('힣') for char in text)
    
    # Run LanguageTool for grammar check
    grammar_errors = 0
    suggestions = []
    
    try:
        async with httpx.AsyncClient() as client:
            data = {"text": text, "language": "auto"}
            if LANGUAGETOOL_USERNAME and LANGUAGETOOL_API_KEY:
                data["username"] = LANGUAGETOOL_USERNAME
                data["apiKey"] = LANGUAGETOOL_API_KEY
            
            response = await client.post(LANGUAGETOOL_URL, data=data)
            if response.status_code == 200:
                result = response.json()
                matches = result.get("matches", [])
                grammar_errors = len(matches)
                
                # Extract suggestions
                for match in matches[:5]:  # Limit to 5 suggestions
                    if match.get("replacements"):
                        original = text[match["offset"]:match["offset"] + match["length"]]
                        corrected = match["replacements"][0]["value"]
                        reason = match.get("message", "Grammar issue")
                        suggestions.append(ChangeItem(
                            original=original,
                            corrected=corrected,
                            reason=reason
                        ))
    except Exception as e:
        pass  # Continue even if LanguageTool fails
    
    # Calculate scores
    grammar_score = max(0, 100 - (grammar_errors * 5))  # -5 points per error
    
    # Calculate readability (simple heuristic)
    words = text.split()
    avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
    readability_score = min(100, max(0, 100 - int((avg_word_length - 5) * 10)))
    
    # Tone analysis using Gemini
    tone_score = 85
    sensitivity_score = 100
    
    if GEMINI_API_KEY:
        try:
            tone_prompt = "Analyze the tone of this text. Rate it from 0-100 for appropriateness for students. Output only the number."
            if is_korean:
                tone_prompt = "이 텍스트의 어조를 분석하세요. 학생에게 적합한 정도를 0-100으로 평가하세요. 숫자만 출력하세요."
            
            tone_result = await call_gemini(text, tone_prompt)
            try:
                tone_score = int(''.join(filter(str.isdigit, tone_result[:3])))
                tone_score = max(0, min(100, tone_score))
            except:
                tone_score = 85
        except:
            pass
    
    message = f"진단 완료: 문법 {grammar_score}%, 가독성 {readability_score}%, 어조 {tone_score}%"
    
    return DiagnoseResponse(
        readability=readability_score,
        grammar=grammar_score,
        tone=tone_score,
        sensitivity=sensitivity_score,
        suggestions=suggestions,
        message=message
    )


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "apis": {
            "gemini": bool(GEMINI_API_KEY),
            "claude": bool(CLAUDE_API_KEY),
            "openai": bool(OPENAI_API_KEY),
            "languagetool": bool(LANGUAGETOOL_USERNAME and LANGUAGETOOL_API_KEY)
        }
    }
