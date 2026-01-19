# TOPLUS Editor - 변경 히스토리 (CHANGELOG)

> 마지막 업데이트: 2026-01-19

---

## 📅 2026-01-19

### 🚀 [v2.0.0] TOPLUS Automation Bot 추가

#### 새로운 기능
1. **5단계 자동 검수 워크플로우**
   - Step 1: 오류 제거 (LanguageTool)
   - Step 2: 레벨링 진단 (Hemingway 스타일)
   - Step 3: 문장 재구성 (QuillBot/Wordtune 시뮬레이션)
   - Step 4: 스타일 통일 (ProWritingAid 시뮬레이션)
   - Step 5: 재검수 (13-Point Checklist)

2. **4가지 시나리오 케이스 처리**
   - Case A: 학년 대비 너무 어려움 → 간소화
   - Case B: 어조가 너무 딱딱함 → 캐주얼하게 조정
   - Case C: 필수 어휘 후 문맥 어색 → 재구성
   - Case D: 기계적 오류 의심 → 심층 문법 검사

3. **새로운 API 엔드포인트**
   - `POST /api/diagnose` - 텍스트 진단
   - `POST /api/auto-review` - 5단계 자동 검수
   - `POST /api/case-workflow` - 케이스별 워크플로우
   - `POST /api/recycling-check` - 학년 수준 리사이클링 체크

4. **UI 업데이트**
   - 🤖 자동 검수 섹션 추가
   - 지문 유형 선택 (A: 정숙성, B: 생동감)
   - 대상 학년 선택 (초3 ~ 고3)
   - 워크플로우 진행 상황 실시간 표시

#### 수정된 파일
| 파일 | 변경 내용 |
|------|----------|
| `api/automation_bot.py` | 🆕 새 파일 - 자동화 봇 엔진 (500+ lines) |
| `api/index.py` | 4개 API 엔드포인트 추가, fallback 함수 포함 |
| `index.html` | 자동 검수 UI 섹션 추가 |
| `editor.css` | 자동 검수 스타일 추가 (200+ lines) |
| `app.js` | `diagnoseText()`, `runAutoReview()` 메서드 추가 |

---

### 🐛 [v1.1.1] 버그 수정

#### 수정된 문제
1. **JSON Parse Error 수정**
   - 문제: Vercel에서 `automation_bot` 모듈 import 실패
   - 원인: Vercel Python 런타임에서 상대 import 문제
   - 해결: `try-except`로 import 감싸고 fallback 함수 구현

#### 커밋 히스토리
```
fc8e0dc fix: add fallback for automation_bot import on Vercel
1c95be7 feat: Update UI and add new features
f453c23 fix: relative import for Vercel compatibility
af5a451 feat: add TOPLUS Automation Bot with 5-step workflow and scenario cases
0f350ba feat: multi-API support with free LanguageTool fallback
3092748 refactor: switch from Gemini to Claude (Sonnet 4.5) API
```

---

### 🔄 [v1.1.0] Multi-API 지원

#### 변경 내용
1. **API 전환**: Gemini → Claude Sonnet 4.5
2. **무료 LanguageTool 통합** (API 키 불필요!)
3. **Smart Fallback 시스템**
   - 1순위: Trinka (키 있을 때)
   - 2순위: LanguageTool (무료)
   - 3순위: Claude/Gemini (키 있을 때)

---

## 🔧 환경 변수 (Optional)

| 변수명 | 용도 | 필수 여부 |
|--------|------|----------|
| `ANTHROPIC_API_KEY` | Claude API | 선택 |
| `GEMINI_API_KEY` | Gemini API | 선택 |
| `TRINKA_API_KEY` | Trinka API | 선택 |

> 💡 환경 변수 없이도 **LanguageTool (무료)**로 기본 동작합니다!

---

## 📁 프로젝트 구조

```
toplus-editor/
├── api/
│   ├── index.py          # 메인 API (FastAPI)
│   └── automation_bot.py # 자동화 봇 엔진
├── index.html            # 메인 페이지
├── app.js                # 프론트엔드 로직
├── styles.css            # 기본 스타일
├── editor.css            # 에디터 스타일
├── panel.css             # 패널 스타일
├── vercel.json           # Vercel 설정
└── requirements.txt      # Python 의존성
```

---

## 🔗 참고 링크

- **배포 URL**: https://toplus-editor.vercel.app/
- **GitHub**: https://github.com/toplusdrive-lang/toplus-editor
- **TOPLUS Review Protocol**: 2026.01.19 버전 기준
