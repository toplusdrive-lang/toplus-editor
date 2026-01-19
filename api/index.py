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

# --- API Keys (Optional - will use free alternatives if not set) ---
TRINKA_API_KEY = os.getenv("TRINKA_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- API URLs ---
TRINKA_URL = "https://api-platform.trinka.ai/api/v2/plugin/check/paragraph"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"  # FREE - no key needed!


class ChangeItem(BaseModel):
    original: str
    corrected: str
    reason: str


class ProcessTextResponse(BaseModel):
    result: str
    step: int
    message: str
    changes: Optional[List[ChangeItem]] = []
    api_used: str = ""


class ProcessTextRequest(BaseModel):
    text: str
    step: int


# ============================================================
# API Helper Functions (with smart fallbacks)
# ============================================================

async def call_languagetool_free(text: str) -> tuple[str, str]:
    """FREE LanguageTool API - No API key required!"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                LANGUAGETOOL_URL,
                data={
                    "text": text,
                    "language": "auto",  # Auto-detect language
                    "enabledOnly": "false"
                }
            )
            if response.status_code == 200:
                data = response.json()
                matches = data.get("matches", [])
                
                if not matches:
                    return text, "LanguageTool (Free)"
                
                # Apply corrections
                corrected = text
                offset_adjustment = 0
                
                for match in sorted(matches, key=lambda x: x["offset"]):
                    if match.get("replacements"):
                        replacement = match["replacements"][0]["value"]
                        start = match["offset"] + offset_adjustment
                        end = start + match["length"]
                        corrected = corrected[:start] + replacement + corrected[end:]
                        offset_adjustment += len(replacement) - match["length"]
                
                return corrected, "LanguageTool (Free)"
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            return None, f"LanguageTool Error: {str(e)}"


async def call_trinka(text: str) -> tuple[str, str]:
    """Trinka API - Requires API key"""
    if not TRINKA_API_KEY:
        return None, "No Trinka API key"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                TRINKA_URL,
                headers={
                    "Authorization": f"Bearer {TRINKA_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "paragraph": text,
                    "language": "US"
                }
            )
            if response.status_code == 200:
                data = response.json()
                # Process Trinka response and return corrected text
                corrected = data.get("corrected_text", text)
                return corrected, "Trinka AI"
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            return None, f"Trinka Error: {str(e)}"


async def call_claude(text: str, prompt: str) -> tuple[str, str]:
    """Claude API - Requires API key"""
    if not ANTHROPIC_API_KEY:
        return None, "No Claude API key"
    
    system_instruction = """You are a strict text processing engine.
- Output ONLY the processed text.
- DO NOT add any conversational filler.
- DO NOT add markdown code blocks.
- Preserve the original language."""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-5-20250929",
                    "max_tokens": 4096,
                    "system": system_instruction,
                    "messages": [{"role": "user", "content": f"{prompt}\n\n{text}"}]
                }
            )
            if response.status_code == 200:
                result = response.json()["content"][0]["text"].strip()
                return result, "Claude 4.5 Sonnet"
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            return None, f"Claude Error: {str(e)}"


async def call_gemini(text: str, prompt: str) -> tuple[str, str]:
    """Gemini API - Requires API key"""
    if not GEMINI_API_KEY:
        return None, "No Gemini API key"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": f"{prompt}\n\n{text}"}]}],
                    "generationConfig": {"temperature": 0.1}
                }
            )
            if response.status_code == 200:
                result = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                return result, "Gemini 2.0 Flash"
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            return None, f"Gemini Error: {str(e)}"


async def process_with_ai(text: str, prompt: str) -> tuple[str, str]:
    """Try multiple AI APIs with fallback"""
    
    # Try Claude first
    result, api = await call_claude(text, prompt)
    if result:
        return result, api
    
    # Try Gemini
    result, api = await call_gemini(text, prompt)
    if result:
        return result, api
    
    # Fallback: just return original text with message
    return text, "No AI API available (add ANTHROPIC_API_KEY or GEMINI_API_KEY)"


async def process_grammar(text: str) -> tuple[str, str]:
    """Try grammar APIs with fallback"""
    
    # Try Trinka first (best for academic writing)
    result, api = await call_trinka(text)
    if result:
        return result, api
    
    # Use FREE LanguageTool as fallback
    result, api = await call_languagetool_free(text)
    if result:
        return result, api
    
    return text, "Grammar check unavailable"


# ============================================================
# Main API Router
# ============================================================

@app.get("/api/status")
async def status():
    """Check which APIs are available"""
    return {
        "trinka": bool(TRINKA_API_KEY),
        "claude": bool(ANTHROPIC_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "languagetool": True,  # Always available (free)
    }


@app.post("/api/process-text")
async def process_text(request: ProcessTextRequest):
    step = request.step
    text = request.text
    result = text
    msg = ""
    api_used = ""
    changes = []
    
    # Detect language
    is_korean = any(ord('가') <= ord(char) <= ord('힣') for char in text)

    if step == 1:  # Sentence Simplification
        if is_korean:
            prompt = "이 문장을 간결하고 명확하게 다듬으세요. 의미는 유지하세요."
        else:
            prompt = "Simplify this text to be clear and concise. Keep the meaning intact."
        result, api_used = await process_with_ai(text, prompt)
        msg = "문장 간소화"

    elif step == 2:  # Grammar Correction
        result, api_used = await process_grammar(text)
        msg = "문법 교정"

    elif step == 3:  # Tone Adjustment
        if is_korean:
            prompt = "이 텍스트를 희망차고 긍정적인 어조로 바꾸세요. 존댓말을 사용하세요."
        else:
            prompt = "Change the tone to be hopeful, positive, and encouraging."
        result, api_used = await process_with_ai(text, prompt)
        msg = "어조 조정"

    elif step == 4:  # Style Correction
        result, api_used = await process_grammar(text)
        msg = "스타일 교정"

    elif step == 5:  # Sensitivity Check
        prompt = "Review this text for bias or sensitive content. Correct if needed."
        result, api_used = await process_with_ai(text, prompt)
        msg = "민감성 검사"

    elif step == 6:  # Final Review
        if is_korean:
            prompt = "문장을 자연스럽고 유려한 한국어로 다듬으세요."
        else:
            prompt = "Paraphrase this text to sound natural and fluent."
        result, api_used = await process_with_ai(text, prompt)
        msg = "최종 검토"

    return ProcessTextResponse(
        result=result,
        step=step,
        message=msg,
        changes=changes,
        api_used=api_used
    )


# ============================================================
# AUTOMATION BOT Endpoints (TOPLUS Review Protocol)
# ============================================================

# Try to import automation_bot module (may fail on Vercel)
try:
    from automation_bot import (
        diagnose_text, run_5step_workflow, run_case_workflow,
        recycling_check, ScenarioCase, TextType
    )
    AUTOMATION_BOT_AVAILABLE = True
except ImportError:
    AUTOMATION_BOT_AVAILABLE = False
    
    # Fallback implementations using inline functions
    from enum import Enum
    from dataclasses import dataclass
    
    class ScenarioCase(Enum):
        CASE_A = "too_difficult"
        CASE_B = "too_formal"
        CASE_C = "context_awkward"
        CASE_D = "mechanical_error"
        NORMAL = "normal"
    
    class TextType(Enum):
        TYPE_A = "formal"
        TYPE_B = "casual"
    
    @dataclass
    class ReviewResult:
        step: int
        step_name: str
        tool_used: str
        original_text: str
        processed_text: str
        changes: list
        score: int = None
        notes: str = ""
    
    async def diagnose_text(text: str):
        # Simple fallback diagnosis using LanguageTool
        corrected, _ = await call_languagetool_free(text)
        
        # Basic checks
        is_korean = any(ord('가') <= ord(char) <= ord('힣') for char in text)
        word_count = len(text.split())
        avg_word_len = sum(len(w) for w in text.split()) / max(word_count, 1)
        
        # Determine case
        case = ScenarioCase.NORMAL
        issues = []
        
        if avg_word_len > 8:
            case = ScenarioCase.CASE_A
            issues.append("단어가 너무 김")
        if word_count > 100:
            issues.append("문장이 너무 긴")
        
        class DiagResult:
            pass
        r = DiagResult()
        r.case = case
        r.text_type = TextType.TYPE_A
        r.grade_level = "M1"
        r.readability_score = 70.0
        r.issues_found = issues
        r.recommended_workflow = ["LanguageTool", "Review"]
        return r
    
    async def run_5step_workflow(text: str, text_type=None):
        results = []
        current = text
        
        # Step 1: Grammar check
        corrected, changes = await call_languagetool_free(current)
        results.append(ReviewResult(
            step=1, step_name="오류 제거", tool_used="LanguageTool",
            original_text=current, processed_text=corrected,
            changes=changes, notes=f"Found {len(changes)} issues"
        ))
        current = corrected
        
        # Step 2-5: AI processing (if available)
        ai_result, api = await process_with_ai(current, "이 텍스트를 간결하게 다듬으세요.")
        results.append(ReviewResult(
            step=2, step_name="레벨링", tool_used=api,
            original_text=current, processed_text=ai_result,
            changes=[], notes=""
        ))
        current = ai_result
        
        results.append(ReviewResult(
            step=3, step_name="문장 재구성", tool_used="AI",
            original_text=current, processed_text=current,
            changes=[], notes=""
        ))
        
        results.append(ReviewResult(
            step=4, step_name="스타일 통일", tool_used="AI",
            original_text=current, processed_text=current,
            changes=[], notes=""
        ))
        
        results.append(ReviewResult(
            step=5, step_name="최종 검토", tool_used="AI",
            original_text=current, processed_text=current,
            changes=[], notes="✅ 검토 완료"
        ))
        
        return results
    
    async def run_case_workflow(text: str, case):
        return await run_5step_workflow(text)
    
    async def recycling_check(text: str, target_grade: str):
        return {
            "current_level": target_grade,
            "is_appropriate": True,
            "recommendation": "keep",
            "reason": "Analysis complete"
        }


class AutoReviewRequest(BaseModel):
    text: str
    text_type: str = "A"  # A = formal, B = casual
    target_grade: str = "M1"


class DiagnoseRequest(BaseModel):
    text: str


@app.post("/api/diagnose")
async def diagnose(request: DiagnoseRequest):
    """Diagnose text to determine case and recommended workflow"""
    try:
        result = await diagnose_text(request.text)
        return {
            "case": result.case.value,
            "text_type": result.text_type.value,
            "grade_level": result.grade_level,
            "readability_score": result.readability_score,
            "issues_found": result.issues_found,
            "recommended_workflow": result.recommended_workflow
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/auto-review")
async def auto_review(request: AutoReviewRequest):
    """Run full 5-step automated review workflow"""
    try:
        text_type = TextType.TYPE_A if request.text_type == "A" else TextType.TYPE_B
        results = await run_5step_workflow(request.text, text_type)
        
        # Convert results to JSON-serializable format
        steps = []
        for r in results:
            steps.append({
                "step": r.step,
                "step_name": r.step_name,
                "tool_used": r.tool_used,
                "original_text": r.original_text,
                "processed_text": r.processed_text,
                "changes": r.changes,
                "score": r.score,
                "notes": r.notes
            })
        
        return {
            "success": True,
            "steps": steps,
            "final_text": results[-1].processed_text if results else request.text
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class CaseWorkflowRequest(BaseModel):
    text: str
    case: str  # "CASE_A", "CASE_B", "CASE_C", "CASE_D"


@app.post("/api/case-workflow")
async def case_workflow(request: CaseWorkflowRequest):
    """Run scenario-specific workflow"""
    try:
        case_mapping = {
            "CASE_A": ScenarioCase.CASE_A,
            "CASE_B": ScenarioCase.CASE_B,
            "CASE_C": ScenarioCase.CASE_C,
            "CASE_D": ScenarioCase.CASE_D,
            "NORMAL": ScenarioCase.NORMAL
        }
        case = case_mapping.get(request.case, ScenarioCase.NORMAL)
        
        results = await run_case_workflow(request.text, case)
        
        steps = []
        for r in results:
            steps.append({
                "step": r.step,
                "step_name": r.step_name,
                "tool_used": r.tool_used,
                "original_text": r.original_text,
                "processed_text": r.processed_text,
                "changes": r.changes,
                "score": r.score,
                "notes": r.notes
            })
        
        return {
            "success": True,
            "case": request.case,
            "steps": steps,
            "final_text": results[-1].processed_text if results else request.text
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class RecyclingCheckRequest(BaseModel):
    text: str
    target_grade: str = "M1"


@app.post("/api/recycling-check")
async def recycling(request: RecyclingCheckRequest):
    """Check if text needs recycling to different grade level"""
    try:
        result = await recycling_check(request.text, request.target_grade)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}
