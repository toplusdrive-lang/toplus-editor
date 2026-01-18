"""
TOPLUS Editor - AI 서비스 연동 모듈
Stage 03: OpenAI, Trinka, LanguageTool API 통합
"""

import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class AIServices:
    """AI 서비스 통합 클래스"""
    
    def __init__(self):
        self.openai_key = OPENAI_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def step1_simplify(self, text: str) -> str:
        """Step 1: 문장 간소화 (GPT-4o)"""
        if not self.openai_key:
            # API 키 없으면 간단한 로컬 처리
            result = text.replace("매우 ", "").replace("정말 ", "").replace("아주 ", "")
            return result
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 문장 간소화 전문가입니다. 주어진 텍스트를 더 간결하고 명확하게 만들어주세요. 원래 의미는 유지하면서 불필요한 수식어나 중복 표현을 제거하세요."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.3
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenAI API 오류: {e}")
            return text
    
    async def step2_grammar_trinka(self, text: str) -> str:
        """Step 2: 문법 교정 (Trinka API)"""
        # Trinka API 연동 예시 - 실제 API 키 필요
        # 임시로 로컬 처리
        result = text.replace("되요", "돼요").replace("됬", "됐")
        return result
    
    async def step3_tone_adjustment(self, text: str) -> str:
        """Step 3: 어조 조정 (Wordtune - GPT-4o 대체)"""
        if not self.openai_key:
            return text
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 문장 어조 조정 전문가입니다. 주어진 텍스트를 공식적이고 전문적인 어조로 변환해주세요."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.3
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"어조 조정 오류: {e}")
            return text
    
    async def step4_style_languagetool(self, text: str) -> str:
        """Step 4: 스타일 교정 (LanguageTool API)"""
        try:
            response = await self.client.post(
                "https://api.languagetool.org/v2/check",
                data={
                    "text": text,
                    "language": "ko"
                }
            )
            data = response.json()
            # 수정 제안 적용
            result = text
            for match in reversed(data.get("matches", [])):
                if match.get("replacements"):
                    offset = match["offset"]
                    length = match["length"]
                    replacement = match["replacements"][0]["value"]
                    result = result[:offset] + replacement + result[offset + length:]
            return result
        except Exception as e:
            print(f"LanguageTool API 오류: {e}")
            return text
    
    async def step5_sensitivity_check(self, text: str) -> str:
        """Step 5: 민감성 검사 (GPT-4o)"""
        if not self.openai_key:
            return text
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 텍스트 민감성 검사 전문가입니다. 주어진 텍스트에서 부적절하거나 민감한 표현이 있는지 검사하고, 있다면 적절한 대안을 제시해주세요. 문제가 없다면 원문을 그대로 반환하세요."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.2
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"민감성 검사 오류: {e}")
            return text
    
    async def step6_final_review(self, text: str) -> str:
        """Step 6: 최종 검토 (QuillBot - GPT-4o 대체)"""
        if not self.openai_key:
            return text
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 최종 텍스트 검토 전문가입니다. 주어진 텍스트를 최종 검토하여 자연스럽고 완성도 높은 문장으로 다듬어주세요."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.3
                }
            )
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"최종 검토 오류: {e}")
            return text
    
    async def process_step(self, text: str, step: int) -> str:
        """단계별 처리 라우터"""
        processors = {
            1: self.step1_simplify,
            2: self.step2_grammar_trinka,
            3: self.step3_tone_adjustment,
            4: self.step4_style_languagetool,
            5: self.step5_sensitivity_check,
            6: self.step6_final_review
        }
        
        processor = processors.get(step)
        if processor:
            return await processor(text)
        return text


# 싱글톤 인스턴스
ai_services = AIServices()
