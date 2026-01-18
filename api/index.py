import json
from typing import List, Optional

# ... (Previous imports)

class ChangeItem(BaseModel):
    original: str
    corrected: str
    reason: str

class ProcessTextResponse(BaseModel):
    result: str
    step: int
    message: str
    changes: Optional[List[ChangeItem]] = []

# --- Claude 도우미 함수 (범용 + JSON 모드 지원) ---
async def call_claude(text: str, system_instruction: str, json_mode: bool = False):
    if not ANTHROPIC_API_KEY:
        # 키 없으면 Mock 처리 (JSON 모드일 때는 Mock도 JSON 구조로)
        if json_mode:
            mock_resp = {
                "corrected": text,
                "changes": [{"original": "예시", "corrected": "예시", "reason": "API 키가 없어 교정되지 않았습니다."}]
            }
            return json.dumps(mock_resp, ensure_ascii=False)
        return await call_gemini(text, f"당신은 Claude 4.5 Sonnet입니다. {system_instruction}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            prompt = f"{system_instruction}\n\n입력 텍스트:\n{text}"
            if json_mode:
                prompt += "\n\n반드시 JSON 포맷으로만 응답하세요. 다른 말은 하지 마세요."

            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 2048,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            data = response.json()
            if response.status_code != 200:
                 raise Exception(f"Claude API Error: {data.get('error', {}).get('message')}")
            return data["content"][0]["text"].strip()
        except Exception as e:
             # 에러 시 fallback
            if json_mode:
                return json.dumps({"corrected": text, "changes": []})
            return f"[Claude Error] {str(e)}"

# ... (Previous Gemini/LT functions remain similar)

# --- 메인 라우터 ---
@app.post("/api/process-text")
async def process_text(request: ProcessTextRequest):
    step = request.step
    text = request.text
    result = text
    msg = ""
    changes = []

    if step == 1: # 문장 간소화 (Gemini 3.0 Pro)
        result = await call_gemini(text, "문장을 간결하고 명확하게 만드세요. 불필요한 수식어를 제거하되 핵심 의미는 유지하세요.")
        msg = "문장 간소화 (Gemini 3.0 Pro)"

    elif step == 2: # 문법 교정 (Claude 4.5 Sonnet - JSON 모드)
        prompt = """
        당신은 한국어 문법 교정 전문가입니다.
        주어진 텍스트의 맞춤법, 띄어쓰기, 문법 오류를 찾아 교정해주세요.
        응답은 반드시 다음 JSON 구조로 작성해야 합니다 (MarkDown 코드블럭 없이 순수 JSON만 반환):
        {
            "corrected": "교정된 전체 텍스트",
            "changes": [
                {
                    "original": "틀린 부분 (원문)",
                    "corrected": "고친 부분",
                    "reason": "오류 유형 및 설명"
                }
            ]
        }
        """
        raw_json = await call_claude(text, prompt, json_mode=True)
        try:
            # JSON 파싱 (혹시 모를 마크다운 제거)
            clean_json = raw_json.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            result = data.get("corrected", text)
            changes = data.get("changes", [])
        except Exception as e:
            # 파싱 실패 시 원본만 반환
            result = raw_json
            msg = f"문법 교정 (Claude 4.5 Sonnet) - 상세 분석 실패: {str(e)}"
        else:
            msg = "문법 교정 (Claude 4.5 Sonnet)"

    elif step == 3: # 어조 조정 (Claude 4.5 Sonnet)
        result = await call_claude(text, "다음 텍스트의 어조를 '격식 있고(Formal) 전문적인 어조'로 변경해줘. 의미는 유지하고 스타일만 바꿔서 텍스트만 출력해.", json_mode=False)
        msg = "어조 조정 (Claude 4.5 Sonnet)"

# ... (Rest steps remain same)

    return ProcessTextResponse(result=result, step=step, message=msg, changes=changes)

    elif step == 4: # 스타일 교정 (LanguageTool)
        result = await call_languagetool(text)
        msg = "스타일 교정 (LanguageTool API)"

    elif step == 5: # 민감성 검사 (Gemini 3.0 Pro)
        result = await call_gemini(text, "텍스트의 편향성, 차별적 표현, 민감한 내용을 검사하고 순화하세요.")
        msg = "민감성 검사 (Gemini 3.0 Pro)"

    elif step == 6: # 최종 검토 (QuillBot by Gemini)
        result = await call_gemini(text, "QuillBot 스타일: 문장을 가장 자연스럽고 유려한 한국어로 패러프레이징(재구성)하세요.")
        msg = "최종 검토 (QuillBot Style)"

    else:
        raise HTTPException(status_code=400, detail="Invalid step")

    return ProcessTextResponse(result=result, step=step, message=msg)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "TOPLUS Hybrid Engine (Gemini + Claude)"}
