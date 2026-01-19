"""
TOPLUS Automation Bot Engine
Based on TOPLUS Review Protocol (2026.01.19)

5-Step Workflow + 4 Scenario Cases + 13-Point Review
"""

import httpx
import os
import re
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


# ============================================================
# Configuration
# ============================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TRINKA_API_KEY = os.getenv("TRINKA_API_KEY")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
LANGUAGETOOL_URL = "https://api.languagetool.org/v2/check"


# ============================================================
# Enums & Data Classes
# ============================================================

class ScenarioCase(Enum):
    CASE_A = "too_difficult"      # 학년 대비 너무 어려움
    CASE_B = "too_formal"         # 어조가 너무 딱딱함
    CASE_C = "context_awkward"    # 필수 어휘 후 문맥 어색
    CASE_D = "mechanical_error"   # 기계적 오류 의심
    NORMAL = "normal"             # 일반 처리


class TextType(Enum):
    TYPE_A = "formal"    # 지문 A: 정숙성, 명료성 (Clarity)
    TYPE_B = "casual"    # 지문 B: 생동감, 이목 (Engagement)


@dataclass
class ReviewResult:
    step: int
    step_name: str
    tool_used: str
    original_text: str
    processed_text: str
    changes: List[Dict]
    score: Optional[int] = None
    notes: str = ""


@dataclass
class DiagnosisResult:
    case: ScenarioCase
    text_type: TextType
    grade_level: str
    readability_score: float
    issues_found: List[str]
    recommended_workflow: List[str]


# ============================================================
# AI Helper Functions
# ============================================================

async def call_ai(prompt: str, text: str) -> str:
    """Call available AI API (Claude first, then Gemini)"""
    
    system = """You are a strict text editing engine for educational content.
CRITICAL RULES:
1. Output ONLY the processed text. No polite introductions or explanations.
2. CONTEXT IS KING: Ensure the result makes logical sense. Do not produce sentences that are grammatically correct but semantically nonsense.
3. If the input is broken or nonsensical, fix it to be meaningful based on context.
4. Preserve the core meaning absolutely while improving clarity."""
    
    # Try Claude first
    if ANTHROPIC_API_KEY:
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
                        "system": system,
                        "messages": [{"role": "user", "content": f"{prompt}\n\n{text}"}]
                    }
                )
                if response.status_code == 200:
                    return response.json()["content"][0]["text"].strip()
            except:
                pass
    
    # Try Gemini
    if GEMINI_API_KEY:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                    json={
                        "contents": [{"parts": [{"text": f"{system}\n\n{prompt}\n\n{text}"}]}],
                        "generationConfig": {"temperature": 0.1}
                    }
                )
                if response.status_code == 200:
                    return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except:
                pass
    
    # Return original if no AI available
    return text


async def call_languagetool(text: str) -> Tuple[str, List[Dict]]:
    """Free LanguageTool API for grammar checking"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                LANGUAGETOOL_URL,
                data={"text": text, "language": "auto"}
            )
            if response.status_code == 200:
                data = response.json()
                matches = data.get("matches", [])
                
                changes = []
                corrected = text
                offset_adj = 0
                
                for match in sorted(matches, key=lambda x: x["offset"]):
                    if match.get("replacements"):
                        replacement = match["replacements"][0]["value"]
                        original = corrected[match["offset"] + offset_adj:match["offset"] + offset_adj + match["length"]]
                        
                        changes.append({
                            "original": original,
                            "corrected": replacement,
                            "reason": match.get("message", "Grammar correction")
                        })
                        
                        start = match["offset"] + offset_adj
                        end = start + match["length"]
                        corrected = corrected[:start] + replacement + corrected[end:]
                        offset_adj += len(replacement) - match["length"]
                
                return corrected, changes
        except:
            pass
    
    return text, []


# ============================================================
# Tool Simulations (AI-Powered)
# ============================================================

async def simulate_hemingway(text: str) -> Tuple[str, int, str]:
    """Simulate Hemingway Editor - Readability analysis"""
    prompt = """Analyze this text like the Hemingway Editor:
1. Calculate approximate grade level (1-12)
2. Identify complex sentences
3. Simplify if grade level > 6
4. FOR KOREAN TEXT: Aggressively shorten sentences. Remove all redundant adjectives and adverbs. Make it direct.
5. LOGIC CHECK: Ensure the simplified text makes sense. If the original text was broken (e.g. "Look ants"), correct it to be grammatical (e.g. "Look at the ants").

Output format:
GRADE_LEVEL: [number]
NOTES: [brief analysis]
SIMPLIFIED_TEXT: [the improved text]"""
    
    result = await call_ai(prompt, text)
    
    # Parse result
    grade_match = re.search(r'GRADE_LEVEL:\s*(\d+)', result)
    grade = int(grade_match.group(1)) if grade_match else 6
    
    notes_match = re.search(r'NOTES:\s*(.+?)(?=SIMPLIFIED_TEXT:|$)', result, re.DOTALL)
    notes = notes_match.group(1).strip() if notes_match else ""
    
    text_match = re.search(r'SIMPLIFIED_TEXT:\s*(.+)$', result, re.DOTALL)
    simplified = text_match.group(1).strip() if text_match else text
    
    return simplified, grade, notes


async def simulate_quillbot(text: str, mode: str = "standard") -> str:
    """Simulate QuillBot - Paraphrasing"""
    mode_prompts = {
        "standard": "Paraphrase this text clearly. Fix any logical errors. FOR KOREAN: Use formal, standard written style (문어체). Remove ambiguity.",
        "simple": "Simplify this text. For Korean, reduce length by 30-50%. Ensure the result makes logical sense.",
        "formal": "Make this text more formal and academic. Ensure logical flow.",
        "fluency": "Make this text more natural and fluent. Fix non-native phrasing.",
        "freeze_words": "Paraphrase but keep key vocabulary words unchanged."
    }
    
    prompt = mode_prompts.get(mode, mode_prompts["standard"])
    return await call_ai(prompt, text)


async def simulate_wordtune(text: str, style: str = "casual") -> str:
    """Simulate Wordtune - Tone & Style adjustment"""
    style_prompts = {
        "casual": "Rewrite this text in a casual, friendly tone. Like talking to a friend.",
        "formal": "Rewrite this text in a formal, professional tone.",
        "engaging": "Rewrite this text to be more engaging and dynamic. Add energy!",
        "casual_spices": """Rewrite this text to be lively, fun, and engaging.
1. FOR KOREAN: Use a friendly, enthusiastic tone (polite '해요' style). Add emotion and vitality to the sentences.
2. Make it sound like a popular blog post or storyteller.
3. Don't be stiff. Be creative!"""
    }
    
    prompt = style_prompts.get(style, style_prompts["casual"])
    return await call_ai(prompt, text)


async def simulate_prowritingaid(text: str) -> Tuple[str, List[str]]:
    """Simulate ProWritingAid - Deep style analysis"""
    prompt = """Analyze and improve this text like ProWritingAid:
1. Check for style consistency
2. Identify logical flow issues
3. Check sensitivity/bias
4. Improve sentence variety

Output format:
ISSUES: [comma-separated list of issues found]
IMPROVED_TEXT: [the corrected text]"""
    
    result = await call_ai(prompt, text)
    
    issues_match = re.search(r'ISSUES:\s*(.+?)(?=IMPROVED_TEXT:|$)', result, re.DOTALL)
    issues = [i.strip() for i in issues_match.group(1).split(',')] if issues_match else []
    
    text_match = re.search(r'IMPROVED_TEXT:\s*(.+)$', result, re.DOTALL)
    improved = text_match.group(1).strip() if text_match else text
    
    return improved, issues


# ============================================================
# Diagnosis System
# ============================================================

async def diagnose_text(text: str) -> DiagnosisResult:
    """Diagnose text to determine case and workflow"""
    
    prompt = """Analyze this educational text and diagnose issues:

1. Grade Level: What school grade is this appropriate for? (E1-E6, M1-M3, H1-H3)
2. Readability Score: 1-100 (100 = very easy)
3. Text Type: Is this formal (A) or casual (B)?
4. Issues Found: List any problems
5. Case: Which scenario applies?
   - CASE_A: Too difficult for target grade
   - CASE_B: Tone too formal/stiff for casual content
   - CASE_C: Required vocabulary makes context awkward
   - CASE_D: Mechanical errors (grammar, punctuation)
   - NORMAL: No major issues

Output as JSON:
{
    "grade_level": "M1",
    "readability_score": 75,
    "text_type": "A",
    "issues": ["sentence too long", "difficult vocabulary"],
    "case": "CASE_A"
}"""
    
    result = await call_ai(prompt, text)
    
    # Try to parse JSON from result
    import json
    try:
        # Find JSON in response
        json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {}
    except:
        data = {}
    
    case_mapping = {
        "CASE_A": ScenarioCase.CASE_A,
        "CASE_B": ScenarioCase.CASE_B,
        "CASE_C": ScenarioCase.CASE_C,
        "CASE_D": ScenarioCase.CASE_D,
        "NORMAL": ScenarioCase.NORMAL
    }
    
    case = case_mapping.get(data.get("case", "NORMAL"), ScenarioCase.NORMAL)
    text_type = TextType.TYPE_A if data.get("text_type") == "A" else TextType.TYPE_B
    
    # Determine workflow based on case
    workflows = {
        ScenarioCase.CASE_A: ["Hemingway", "QuillBot(Simple)", "Review"],
        ScenarioCase.CASE_B: ["Wordtune(Casual)", "LanguageTool"],
        ScenarioCase.CASE_C: ["QuillBot(FreezeWords)", "ProWritingAid"],
        ScenarioCase.CASE_D: ["LanguageTool", "Manual Review"],
        ScenarioCase.NORMAL: ["LanguageTool", "Hemingway", "QuillBot", "ProWritingAid", "Review"]
    }
    
    return DiagnosisResult(
        case=case,
        text_type=text_type,
        grade_level=data.get("grade_level", "M1"),
        readability_score=float(data.get("readability_score", 50)),
        issues_found=data.get("issues", []),
        recommended_workflow=workflows[case]
    )


# ============================================================
# Main Workflow Engine
# ============================================================

async def run_5step_workflow(text: str, text_type: TextType = TextType.TYPE_A) -> List[ReviewResult]:
    """Run the full 5-step TOPLUS workflow"""
    results = []
    current_text = text
    
    # Step 1: 오류 제거 (LanguageTool)
    corrected, changes = await call_languagetool(current_text)
    results.append(ReviewResult(
        step=1,
        step_name="오류 제거",
        tool_used="LanguageTool",
        original_text=current_text,
        processed_text=corrected,
        changes=changes,
        notes=f"Found {len(changes)} grammar issues"
    ))
    current_text = corrected
    
    # Step 2: 레벨링 진단 (Hemingway)
    simplified, grade, notes = await simulate_hemingway(current_text)
    results.append(ReviewResult(
        step=2,
        step_name="레벨링 진단",
        tool_used="Hemingway",
        original_text=current_text,
        processed_text=simplified,
        changes=[],
        score=grade,
        notes=f"Grade Level: {grade}. {notes}"
    ))
    current_text = simplified
    
    # Step 3: 문장 재구성 (QuillBot/Wordtune)
    if text_type == TextType.TYPE_A:
        # Formal: Use QuillBot standard
        paraphrased = await simulate_quillbot(current_text, "standard")
        tool = "QuillBot (Standard)"
    else:
        # Casual: Use Wordtune casual
        paraphrased = await simulate_wordtune(current_text, "casual_spices")
        tool = "Wordtune (Casual+Spices)"
    
    results.append(ReviewResult(
        step=3,
        step_name="문맥/문장 검수",
        tool_used=tool,
        original_text=current_text,
        processed_text=paraphrased,
        changes=[]
    ))
    current_text = paraphrased
    
    # Step 4: 스타일 통일 (ProWritingAid)
    styled, issues = await simulate_prowritingaid(current_text)
    results.append(ReviewResult(
        step=4,
        step_name="스타일 통일",
        tool_used="ProWritingAid",
        original_text=current_text,
        processed_text=styled,
        changes=[],
        notes=f"Issues: {', '.join(issues) if issues else 'None'}"
    ))
    current_text = styled
    
    # Step 5: 재검수 (13-Point Check)
    final, checklist = await run_13point_check(current_text)
    results.append(ReviewResult(
        step=5,
        step_name="재검수 (13-Point)",
        tool_used="13-Point Checklist",
        original_text=current_text,
        processed_text=final,
        changes=[],
        notes=checklist
    ))
    
    return results


async def run_13point_check(text: str) -> Tuple[str, str]:
    """Run the 13-point review checklist"""
    prompt = """Review this text against our 13-point checklist:

1. Grammar accuracy
2. Spelling
3. Punctuation
4. Sentence structure
5. Vocabulary appropriateness
6. Tone consistency
7. Logical flow
8. Clarity
9. Conciseness
10. Cultural sensitivity
11. Age appropriateness
12. Engagement level
13. Educational value

For each point, mark ✅ if pass or ❌ if needs work.
Then provide the final corrected text.

Output format:
CHECKLIST:
1. Grammar: ✅
2. Spelling: ✅
...

FINAL_TEXT: [corrected text]"""
    
    result = await call_ai(prompt, text)
    
    checklist_match = re.search(r'CHECKLIST:\s*(.+?)(?=FINAL_TEXT:|$)', result, re.DOTALL)
    checklist = checklist_match.group(1).strip() if checklist_match else "Checklist completed"
    
    text_match = re.search(r'FINAL_TEXT:\s*(.+)$', result, re.DOTALL)
    final = text_match.group(1).strip() if text_match else text
    
    return final, checklist


async def run_case_workflow(text: str, case: ScenarioCase) -> List[ReviewResult]:
    """Run scenario-specific workflow"""
    results = []
    current_text = text
    
    if case == ScenarioCase.CASE_A:
        # Too difficult: Hemingway → QuillBot(Simple) → Review
        simplified, grade, notes = await simulate_hemingway(current_text)
        results.append(ReviewResult(
            step=1, step_name="레벨링 진단", tool_used="Hemingway",
            original_text=current_text, processed_text=simplified,
            changes=[], score=grade, notes=notes
        ))
        current_text = simplified
        
        simple = await simulate_quillbot(current_text, "simple")
        results.append(ReviewResult(
            step=2, step_name="간소화", tool_used="QuillBot (Simple)",
            original_text=current_text, processed_text=simple,
            changes=[]
        ))
        current_text = simple
        
    elif case == ScenarioCase.CASE_B:
        # Too formal: Wordtune(Casual) → LanguageTool
        casual = await simulate_wordtune(current_text, "casual_spices")
        results.append(ReviewResult(
            step=1, step_name="어조 조정", tool_used="Wordtune (Casual+Spices)",
            original_text=current_text, processed_text=casual,
            changes=[]
        ))
        current_text = casual
        
        corrected, changes = await call_languagetool(current_text)
        results.append(ReviewResult(
            step=2, step_name="문법 검사", tool_used="LanguageTool",
            original_text=current_text, processed_text=corrected,
            changes=changes
        ))
        
    elif case == ScenarioCase.CASE_C:
        # Context awkward: QuillBot(FreezeWords) → ProWritingAid
        paraphrased = await simulate_quillbot(current_text, "freeze_words")
        results.append(ReviewResult(
            step=1, step_name="문장 재구성", tool_used="QuillBot (Freeze Words)",
            original_text=current_text, processed_text=paraphrased,
            changes=[]
        ))
        current_text = paraphrased
        
        styled, issues = await simulate_prowritingaid(current_text)
        results.append(ReviewResult(
            step=2, step_name="스타일 통일", tool_used="ProWritingAid",
            original_text=current_text, processed_text=styled,
            changes=[], notes=', '.join(issues)
        ))
        
    elif case == ScenarioCase.CASE_D:
        # Mechanical errors: LanguageTool → Manual flag
        corrected, changes = await call_languagetool(current_text)
        results.append(ReviewResult(
            step=1, step_name="기계적 오류 수정", tool_used="LanguageTool",
            original_text=current_text, processed_text=corrected,
            changes=changes,
            notes="⚠️ Recommend native speaker review (3차 감수)"
        ))
    
    else:  # NORMAL
        results = await run_5step_workflow(current_text)
    
    return results


# ============================================================
# Recycling Strategy (리사이클링 루프)
# ============================================================

async def recycling_check(text: str, target_grade: str = "M1") -> Dict:
    """Check if text needs recycling to different grade level"""
    
    prompt = f"""Analyze this text for grade appropriateness.
Target grade: {target_grade}

If too difficult → suggest moving to higher grade DB
If too easy → suggest moving to lower grade DB
If appropriate → keep current

Output as JSON:
{{
    "current_level": "M2",
    "target_level": "{target_grade}",
    "is_appropriate": true/false,
    "recommendation": "keep/move_up/move_down",
    "reason": "explanation"
}}"""
    
    result = await call_ai(prompt, text)
    
    try:
        import json
        json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    return {
        "current_level": target_grade,
        "is_appropriate": True,
        "recommendation": "keep",
        "reason": "Unable to analyze"
    }
