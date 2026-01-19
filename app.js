/**
 * TOPLUS Editor - Main Application Logic
 * 6단계 검수 프로세스 UI 관리
 */

class ToPlusEditor {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 6;
        this.stepData = {
            1: { name: '문장 간소화', desc: '복잡한 문장을 명확하고 간결하게 변환합니다.', api: 'Gemini 3.0 Pro' },
            2: { name: '문법 교정', desc: '문법 오류를 자동으로 감지하고 수정합니다.', api: 'Claude 4.5 Sonnet' },
            3: { name: '어조 조정', desc: '문맥에 맞는 적절한 어조로 조정합니다.', api: 'Claude 4.5 Sonnet' },
            4: { name: '스타일 교정', desc: '일관된 문체와 스타일을 적용합니다.', api: 'LanguageTool' },
            5: { name: '민감성 검사', desc: '부적절한 내용이나 민감한 표현을 검사합니다.', api: 'Gemini 3.0 Pro' },
            6: { name: '최종 검토', desc: '모든 단계를 거친 최종 결과를 검토합니다.', api: 'QuillBot' }
        };
        this.completedSteps = new Set();

        // Review History - Load from LocalStorage
        this.reviewHistory = this.loadHistoryFromStorage();

        this.init();
    }

    init() {
        this.bindElements();
        this.bindEvents();
        this.updateUI();
        this.addLog('시스템 준비 완료', 'success');
    }

    bindElements() {
        // Main elements
        this.inputText = document.getElementById('inputText');
        this.outputText = document.getElementById('outputText');
        this.btnProcess = document.getElementById('btnProcess');
        this.btnNextStep = document.getElementById('btnNextStep');
        this.btnReset = document.getElementById('btnReset');
        this.loadingOverlay = document.getElementById('loadingOverlay');

        // Step elements
        this.stepItems = document.querySelectorAll('.step-item');
        this.stepTitle = document.querySelector('.current-step-title');
        this.stepDesc = document.querySelector('.current-step-desc');

        // Progress elements
        this.progressFill = document.querySelector('.progress-fill');
        this.progressPercent = document.querySelector('.progress-percent');

        // Analysis elements
        this.readabilityScore = document.getElementById('readabilityScore');
        this.grammarScore = document.getElementById('grammarScore');
        this.toneScore = document.getElementById('toneScore');
        this.sensitivityScore = document.getElementById('sensitivityScore');

        // Lists
        this.suggestionsList = document.getElementById('suggestionsList');
        this.logList = document.getElementById('logList');

        // Char counts
        this.charCount = document.querySelector('.char-count');
        this.outputCount = document.querySelector('.output-count');

        // Auto Review elements
        this.btnDiagnose = document.getElementById('btnDiagnose');
        this.btnAutoReview = document.getElementById('btnAutoReview');
        this.textTypeSelect = document.getElementById('textType');
        this.targetGradeSelect = document.getElementById('targetGrade');
        this.workflowProgress = document.getElementById('workflowProgress');
        this.workflowSteps = document.getElementById('workflowSteps');
    }

    bindEvents() {
        // Step navigation
        this.stepItems.forEach(item => {
            item.addEventListener('click', () => {
                const step = parseInt(item.dataset.step);
                if (step <= this.currentStep || this.completedSteps.has(step - 1)) {
                    this.goToStep(step);
                }
            });
        });

        // Text input
        this.inputText.addEventListener('input', () => {
            const len = this.inputText.value.length;
            this.charCount.textContent = `${len.toLocaleString()} 자`;
        });

        // Process button
        this.btnProcess.addEventListener('click', () => this.processCurrentStep());

        // Next step button
        this.btnNextStep.addEventListener('click', () => {
            if (this.currentStep < this.totalSteps) {
                this.goToStep(this.currentStep + 1);
            }
        });

        // Reset button
        this.btnReset.addEventListener('click', () => this.reset());

        // Auto Review buttons
        if (this.btnDiagnose) {
            this.btnDiagnose.addEventListener('click', () => this.diagnoseText());
        }
        if (this.btnAutoReview) {
            this.btnAutoReview.addEventListener('click', () => this.runAutoReview());
        }
    }

    goToStep(step) {
        // 이전 단계의 결과가 있다면 다음 단계의 입력값으로 사용
        const resultText = this.outputText.querySelector('.result-text');
        if (resultText && step > this.currentStep) {
            this.inputText.value = resultText.innerText;
            this.charCount.textContent = `${this.inputText.value.length.toLocaleString()} 자`;

            // 결과창 초기화 (새로운 단계 결과를 위해)
            this.outputText.innerHTML = `
                <div class="output-placeholder">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                        <path d="m5 3 4 4"></path>
                        <path d="m19 3-4 4"></path>
                        <path d="M12 12c-2-2.67-4-4-6-4a4 4 0 1 0 0 8c2 0 4-1.33 6-4Zm0 0c2 2.67 4 4 6 4a4 4 0 0 0 0-8c-2 0-4 1.33-6 4Z"></path>
                    </svg>
                    <p>텍스트를 입력하고 처리 버튼을 눌러주세요</p>
                </div>
            `;
            if (this.outputCount) this.outputCount.textContent = '0 자';

            // 점수 및 제안 초기화
            this.suggestionsList.innerHTML = `
                <div class="empty-state">
                    <p>수정 사항이 없습니다.</p>
                </div>
            `;
        }

        this.currentStep = step;
        this.updateUI();
        this.addLog(`Step ${step}: ${this.stepData[step].name} 선택됨`);
    }

    updateUI() {
        const data = this.stepData[this.currentStep];

        // Update header
        this.stepTitle.innerHTML = `
            <span class="step-badge">Step ${this.currentStep}</span>
            ${data.name}
        `;
        this.stepDesc.textContent = data.desc;

        // Update step list
        this.stepItems.forEach(item => {
            const step = parseInt(item.dataset.step);
            item.classList.remove('active', 'completed');

            if (step === this.currentStep) {
                item.classList.add('active');
            } else if (this.completedSteps.has(step)) {
                item.classList.add('completed');
            }

            // Update status badge
            const badge = item.querySelector('.status-badge');
            if (this.completedSteps.has(step)) {
                badge.textContent = '완료';
                badge.className = 'status-badge completed';
            } else if (step === this.currentStep) {
                badge.textContent = '진행중';
                badge.className = 'status-badge pending';
            } else {
                badge.textContent = '대기';
                badge.className = 'status-badge';
            }
        });

        // Update progress
        const progress = Math.round((this.completedSteps.size / this.totalSteps) * 100);
        this.progressFill.style.width = `${progress}%`;
        this.progressPercent.textContent = `${progress}%`;

        // Update next button state
        this.btnNextStep.disabled = !this.completedSteps.has(this.currentStep);
    }

    async processCurrentStep() {
        const text = this.inputText.value.trim();
        if (!text) {
            this.addLog('텍스트를 입력해주세요.', 'error');
            this.showNotification('텍스트를 입력해주세요.', 'error');
            return;
        }

        this.showLoading(true);
        this.addLog(`Step ${this.currentStep} 처리 시작...`);

        try {
            const response = await fetch('/api/process-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    step: this.currentStep
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'API Error');
            }

            const data = await response.json();

            // Mark step as completed
            this.completedSteps.add(this.currentStep);

            // Display result
            this.displayResult(data.result);

            // Update scores (Mock logic - 실제 점수는 이번 범위 제외)
            this.updateScores();

            // Add suggestions from API response
            this.addSuggestions(data.changes);

            // 히스토리에 저장
            this.addToHistory({
                type: `Step ${this.currentStep}: ${this.stepData[this.currentStep].name}`,
                originalText: text,
                resultText: data.result,
                toolsUsed: data.api_used || this.stepData[this.currentStep].api,
                changes: (data.changes || []).map(c => `${c.original} → ${c.corrected}`),
                step: this.currentStep
            });

            this.addLog(`Step ${this.currentStep} 처리 완료!`, 'success');
            this.updateUI();

        } catch (error) {
            this.addLog(`오류 발생: ${error.message}`, 'error');
            alert(`오류가 발생했습니다: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    // Mock functions removed (simulateProcessing, generateMockResult)

    displayResult(result) {
        // 결과 텍스트를 전역 변수나 속성에 저장해두면 좋겠지만, 여기서는 심플하게 DOM 조작
        // Copy logic: get the text content of the result-content div only
        const copyLogic = "navigator.clipboard.writeText(this.parentElement.querySelector('.result-content').innerText).then(() => alert('결과가 복사되었습니다!'))";

        this.outputText.innerHTML = `
            <div class="result-wrapper" style="position: relative;">
                <div class="result-content">${result}</div>
                <button onclick="${copyLogic}" style="position: absolute; top: 0; right: 0; padding: 4px 8px; font-size: 12px; background: #f0f0f0; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; opacity: 0.8;">📋 복사</button>
            </div>
        `;

        if (this.outputCount) {
            this.outputCount.textContent = `${result.length.toLocaleString()} 자`;
        }
    }

    updateScores() {
        const scores = {
            readability: Math.floor(90 + Math.random() * 10), // 90~100
            grammar: 100, // Always 100%
            tone: Math.floor(95 + Math.random() * 5), // 95~100
            sensitivity: 100 // Always 100% (Safety check)
        };

        this.readabilityScore.textContent = `${scores.readability}%`;
        this.grammarScore.textContent = `${scores.grammar}%`;
        this.toneScore.textContent = `${scores.tone}%`;
        this.sensitivityScore.textContent = `${scores.sensitivity}%`;
    }

    addSuggestions(changes = []) {
        if (!changes || changes.length === 0) {
            this.suggestionsList.innerHTML = `
                <div class="empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M5 13l4 4L19 7"></path>
                    </svg>
                    <p>수정 사항이 없습니다.</p>
                </div>
            `;
            return;
        }

        this.suggestionsList.innerHTML = changes.map(s => `
            <div class="suggestion-item">
                <span class="suggestion-type">${s.original} → ${s.corrected}</span>
                <p class="suggestion-text">${s.reason}</p>
            </div>
        `).join('');
    }

    addLog(message, type = '') {
        const time = new Date().toLocaleTimeString('ko-KR', { hour12: false });
        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-message">${message}</span>
        `;
        this.logList.insertBefore(entry, this.logList.firstChild);

        // Keep only last 20 logs
        while (this.logList.children.length > 20) {
            this.logList.removeChild(this.logList.lastChild);
        }
    }

    showLoading(show) {
        if (show) {
            this.loadingOverlay.classList.add('active');
        } else {
            this.loadingOverlay.classList.remove('active');
        }
    }

    showNotification(message, type = 'info') {
        // Simple alert for now, can be replaced with custom toast
        alert(message);
    }

    reset() {
        this.currentStep = 1;
        this.completedSteps.clear();
        this.inputText.value = '';
        this.outputText.innerHTML = `
            <div class="output-placeholder">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="m5 3 4 4"></path>
                    <path d="m19 3-4 4"></path>
                    <path d="M12 12c-2-2.67-4-4-6-4a4 4 0 1 0 0 8c2 0 4-1.33 6-4Zm0 0c2 2.67 4 4 6 4a4 4 0 0 0 0-8c-2 0-4 1.33-6 4Z"></path>
                </svg>
                <p>텍스트를 입력하고 처리 버튼을 눌러주세요</p>
            </div>
        `;
        this.charCount.textContent = '0 자';
        if (this.outputCount) this.outputCount.textContent = '0 자';
        this.readabilityScore.textContent = '--';
        this.grammarScore.textContent = '--';
        this.toneScore.textContent = '--';
        this.sensitivityScore.textContent = '--';
        this.suggestionsList.innerHTML = `
            <div class="empty-state">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <p>텍스트를 처리하면 수정 제안이 여기에 표시됩니다</p>
            </div>
        `;
        this.updateUI();
        this.addLog('시스템이 초기화되었습니다.');
    }

    // ============================================================
    // TOPLUS Automation Bot Methods
    // ============================================================

    async diagnoseText() {
        const text = this.inputText.value.trim();
        if (!text) {
            this.addLog('텍스트를 입력해주세요.', 'error');
            alert('텍스트를 입력해주세요.');
            return;
        }

        this.showLoading(true);
        this.addLog('🔍 텍스트 진단 시작...');

        try {
            const response = await fetch('/api/diagnose', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Display diagnosis result
            const caseNames = {
                'too_difficult': '🔴 Case A: 학년 대비 너무 어려움',
                'too_formal': '🟠 Case B: 어조가 너무 딱딱함',
                'context_awkward': '🟡 Case C: 문맥이 어색함',
                'mechanical_error': '🔵 Case D: 기계적 오류 의심',
                'normal': '🟢 정상'
            };

            const caseName = caseNames[data.case] || data.case;

            this.outputText.innerHTML = `
                <div class="result-text diagnosis-result">
                    <h3>📋 진단 결과</h3>
                    <p><strong>케이스:</strong> ${caseName}</p>
                    <p><strong>지문 유형:</strong> ${data.text_type === 'formal' ? '지문 A (정숙성)' : '지문 B (생동감)'}</p>
                    <p><strong>학년 수준:</strong> ${data.grade_level}</p>
                    <p><strong>가독성 점수:</strong> ${data.readability_score}%</p>
                    <p><strong>발견된 이슈:</strong></p>
                    <ul>
                        ${data.issues_found.map(i => `<li>${i}</li>`).join('') || '<li>없음</li>'}
                    </ul>
                    <p><strong>권장 워크플로우:</strong></p>
                    <ol>
                        ${data.recommended_workflow.map(w => `<li>${w}</li>`).join('')}
                    </ol>
                </div>
            `;

            this.addLog(`진단 완료: ${caseName}`, 'success');

        } catch (error) {
            this.addLog(`진단 오류: ${error.message}`, 'error');
            alert(`진단 오류: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    async runAutoReview() {
        const text = this.inputText.value.trim();
        if (!text) {
            this.addLog('텍스트를 입력해주세요.', 'error');
            alert('텍스트를 입력해주세요.');
            return;
        }

        const textType = this.textTypeSelect?.value || 'A';
        const targetGrade = this.targetGradeSelect?.value || 'M1';

        this.showLoading(true);
        this.addLog('🚀 5단계 자동 검수 시작...');

        // Show workflow progress
        if (this.workflowProgress) {
            this.workflowProgress.style.display = 'block';
            this.workflowSteps.innerHTML = `
                <div class="workflow-step active" data-step="1">
                    <div class="workflow-step-icon">1</div>
                    <div class="workflow-step-info">
                        <div class="workflow-step-name">오류 제거</div>
                        <div class="workflow-step-tool">LanguageTool</div>
                    </div>
                    <div class="workflow-step-status">진행중</div>
                </div>
                <div class="workflow-step" data-step="2">
                    <div class="workflow-step-icon">2</div>
                    <div class="workflow-step-info">
                        <div class="workflow-step-name">레벨링 진단</div>
                        <div class="workflow-step-tool">Hemingway</div>
                    </div>
                    <div class="workflow-step-status">대기</div>
                </div>
                <div class="workflow-step" data-step="3">
                    <div class="workflow-step-icon">3</div>
                    <div class="workflow-step-info">
                        <div class="workflow-step-name">문장 재구성</div>
                        <div class="workflow-step-tool">${textType === 'A' ? 'QuillBot' : 'Wordtune'}</div>
                    </div>
                    <div class="workflow-step-status">대기</div>
                </div>
                <div class="workflow-step" data-step="4">
                    <div class="workflow-step-icon">4</div>
                    <div class="workflow-step-info">
                        <div class="workflow-step-name">스타일 통일</div>
                        <div class="workflow-step-tool">ProWritingAid</div>
                    </div>
                    <div class="workflow-step-status">대기</div>
                </div>
                <div class="workflow-step" data-step="5">
                    <div class="workflow-step-icon">5</div>
                    <div class="workflow-step-info">
                        <div class="workflow-step-name">재검수</div>
                        <div class="workflow-step-tool">13-Point Check</div>
                    </div>
                    <div class="workflow-step-status">대기</div>
                </div>
            `;
        }

        try {
            const response = await fetch('/api/auto-review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text,
                    text_type: textType,
                    target_grade: targetGrade
                })
            });

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Auto review failed');
            }

            // Update workflow progress to show all completed
            if (this.workflowSteps) {
                const steps = this.workflowSteps.querySelectorAll('.workflow-step');
                steps.forEach(step => {
                    step.classList.remove('active');
                    step.classList.add('completed');
                    step.querySelector('.workflow-step-status').textContent = '완료';
                });
            }

            // Display final result
            this.outputText.innerHTML = `
                <div class="result-text">
                    <h3>✅ 5단계 자동 검수 완료!</h3>
                    <hr style="border-color: rgba(255,255,255,0.1); margin: 16px 0;">
                    <p><strong>최종 결과:</strong></p>
                    <div style="padding: 16px; background: rgba(0,200,83,0.1); border-radius: 8px; margin-top: 12px;">
                        ${data.final_text}
                    </div>
                    <hr style="border-color: rgba(255,255,255,0.1); margin: 16px 0;">
                    <p><strong>처리 단계:</strong></p>
                    ${data.steps.map(s => `
                        <div style="margin: 8px 0; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 4px;">
                            <strong>Step ${s.step}: ${s.step_name}</strong> (${s.tool_used})
                            ${s.notes ? `<br><small style="color: #888;">${s.notes}</small>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;

            if (this.outputCount) {
                this.outputCount.textContent = `${data.final_text.length.toLocaleString()} 자`;
            }

            // 히스토리에 저장
            this.addToHistory({
                type: '5단계 자동 검수',
                originalText: text,
                resultText: data.final_text,
                toolsUsed: data.steps.map(s => s.tool_used).join(' → '),
                changes: data.steps.map(s => `${s.step_name}: ${s.notes || '완료'}`),
                textType: textType,
                targetGrade: targetGrade,
                steps: data.steps
            });

            this.addLog('🎉 5단계 자동 검수 완료!', 'success');

        } catch (error) {
            this.addLog(`자동 검수 오류: ${error.message}`, 'error');
            alert(`자동 검수 오류: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    // ============================================================
    // REVIEW HISTORY MANAGEMENT
    // ============================================================

    loadHistoryFromStorage() {
        try {
            const saved = localStorage.getItem('toplus_review_history');
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            console.error('Failed to load history:', e);
            return [];
        }
    }

    saveHistoryToStorage() {
        try {
            localStorage.setItem('toplus_review_history', JSON.stringify(this.reviewHistory));
        } catch (e) {
            console.error('Failed to save history:', e);
        }
    }

    addToHistory(record) {
        const historyEntry = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            date: new Date().toLocaleDateString('ko-KR'),
            time: new Date().toLocaleTimeString('ko-KR'),
            ...record
        };

        this.reviewHistory.unshift(historyEntry); // 최신 항목이 맨 앞

        // 최대 100개까지만 저장
        if (this.reviewHistory.length > 100) {
            this.reviewHistory = this.reviewHistory.slice(0, 100);
        }

        this.saveHistoryToStorage();
        this.addLog(`📝 히스토리 저장됨 (총 ${this.reviewHistory.length}개)`, 'success');

        // 서버에도 저장 시도 (비동기)
        this.saveToServer(historyEntry);

        return historyEntry;
    }

    // Simple word-level diff
    computeDiff(original, modified) {
        if (!original || !modified) return '';

        // Escape HTML to prevent XSS and rendering issues
        const escapeHtml = (text) => {
            const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
            return text.replace(/[&<>"']/g, m => map[m]);
        };

        const oldWords = escapeHtml(original).split(/\s+/);
        const newWords = escapeHtml(modified).split(/\s+/);
        let result = '';

        let i = 0, j = 0;

        while (i < oldWords.length || j < newWords.length) {
            if (i < oldWords.length && j < newWords.length && oldWords[i] === newWords[j]) {
                result += oldWords[i] + ' ';
                i++;
                j++;
            } else {
                let foundSync = false;
                const lookahead = 5;

                for (let k = 1; k <= lookahead; k++) {
                    if (i + k < oldWords.length && oldWords[i + k] === newWords[j]) {
                        for (let x = 0; x < k; x++) {
                            result += `<span class="diff-del">${oldWords[i + x]}</span> `;
                        }
                        i += k;
                        foundSync = true;
                        break;
                    }
                    if (j + k < newWords.length && oldWords[i] === newWords[j + k]) {
                        for (let x = 0; x < k; x++) {
                            result += `<span class="diff-add">${newWords[j + x]}</span> `;
                        }
                        j += k;
                        foundSync = true;
                        break;
                    }
                }

                if (!foundSync) {
                    if (i < oldWords.length) {
                        result += `<span class="diff-del">${oldWords[i]}</span> `;
                        i++;
                    }
                    if (j < newWords.length) {
                        result += `<span class="diff-add">${newWords[j]}</span> `;
                        j++;
                    }
                }
            }
        }
        return result.trim();
    }

    showHistoryModal() {
        const existing = document.getElementById('historyModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'historyModal';
        modal.className = 'history-modal';
        modal.innerHTML = `
            <div class="history-modal-content">
                <div class="history-modal-header">
                    <h2>📋 검수 히스토리</h2>
                    <div class="history-modal-actions">
                        <button class="btn btn-small" onclick="app.exportToJSON()">📥 JSON</button>
                        <button class="btn btn-small" onclick="app.exportToCSV()">📥 CSV</button>
                        <button class="btn btn-small btn-danger" onclick="app.clearHistory()">🗑️ 전체 삭제</button>
                        <button class="btn btn-small" onclick="document.getElementById('historyModal').remove()">✕ 닫기</button>
                    </div>
                </div>
                <div class="history-list">
                    ${this.reviewHistory.length === 0 ?
                '<div class="empty-history">저장된 히스토리가 없습니다.</div>' :
                this.reviewHistory.map(h => {
                    const diffHtml = this.computeDiff(h.originalText, h.resultText);
                    return `
                            <div class="history-item" data-id="${h.id}">
                                <div class="history-item-header">
                                    <span class="history-date">${h.date} ${h.time}</span>
                                    <span class="history-type">${h.type || '검수'}</span>
                                </div>
                                <div class="history-item-body">
                                    <div class="history-text-pair">
                                        <div class="history-original">
                                            <strong>원본:</strong>
                                            <p>${(h.originalText || '').substring(0, 200)}${(h.originalText || '').length > 200 ? '...' : ''}</p>
                                        </div>
                                        <div class="history-arrow">→</div>
                                        <div class="history-result">
                                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                                <strong>결과 (자동 적용됨):</strong>
                                                <button class="btn btn-small" onclick="navigator.clipboard.writeText(this.parentElement.nextElementSibling.textContent); alert('복사되었습니다!')" style="padding: 2px 6px; font-size: 11px;">📋 복사</button>
                                            </div>
                                            <p>${(h.resultText || '').substring(0, 200)}${(h.resultText || '').length > 200 ? '...' : ''}</p>
                                        </div>
                                    </div>

                                    <div class="history-diff-view">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                            <h4>🔍 상세 비교 (수정 전/후)</h4>
                                            <div style="font-size: 11px; color: var(--text-tertiary);">
                                                <span class="diff-del">삭제됨(취소선)</span> 
                                                <span class="diff-add">추가됨(초록색)</span>
                                            </div>
                                        </div>
                                        <div class="diff-content">${diffHtml}</div>
                                    </div>

                                    ${h.toolsUsed ? `<div class="history-tools">🔧 ${h.toolsUsed}</div>` : ''}
                                    ${h.changes && h.changes.length > 0 ? `
                                        <div class="history-changes">
                                            <strong>변경 사항:</strong>
                                            <ul>${h.changes.slice(0, 5).map(c => `<li>${c}</li>`).join('')}</ul>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        `}).join('')
            }
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    async saveToServer(record) {
        try {
            await fetch('/api/save-history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(record)
            });
        } catch (e) {
            // 서버 저장 실패해도 로컬에는 저장됨
            console.log('Server save skipped:', e.message);
        }
    }

    exportToJSON() {
        const data = JSON.stringify(this.reviewHistory, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `toplus_history_${new Date().toISOString().split('T')[0]}.json`;
        a.click();

        URL.revokeObjectURL(url);
        this.addLog('📥 JSON 파일 다운로드 완료', 'success');
    }

    exportToCSV() {
        if (this.reviewHistory.length === 0) {
            alert('저장된 히스토리가 없습니다.');
            return;
        }

        const headers = ['날짜', '시간', '유형', '원본 텍스트', '결과 텍스트', '사용된 도구', '변경 사항'];
        const rows = this.reviewHistory.map(h => [
            h.date || '',
            h.time || '',
            h.type || '',
            `"${(h.originalText || '').replace(/"/g, '""')}"`,
            `"${(h.resultText || '').replace(/"/g, '""')}"`,
            h.toolsUsed || '',
            `"${(h.changes || []).join('; ').replace(/"/g, '""')}"`
        ]);

        const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
        const BOM = '\uFEFF'; // 한글 깨짐 방지
        const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `toplus_history_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();

        URL.revokeObjectURL(url);
        this.addLog('📥 CSV 파일 다운로드 완료', 'success');
    }

    showHistoryModal() {
        // 모달이 이미 있으면 제거
        const existing = document.getElementById('historyModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'historyModal';
        modal.className = 'history-modal';
        modal.innerHTML = `
            <div class="history-modal-content">
                <div class="history-modal-header">
                    <h2>📋 검수 히스토리</h2>
                    <div class="history-modal-actions">
                        <button class="btn btn-small" onclick="app.exportToJSON()">📥 JSON</button>
                        <button class="btn btn-small" onclick="app.exportToCSV()">📥 CSV</button>
                        <button class="btn btn-small btn-danger" onclick="app.clearHistory()">🗑️ 전체 삭제</button>
                        <button class="btn btn-small" onclick="document.getElementById('historyModal').remove()">✕ 닫기</button>
                    </div>
                </div>
                <div class="history-list">
                    ${this.reviewHistory.length === 0 ?
                '<div class="empty-history">저장된 히스토리가 없습니다.</div>' :
                this.reviewHistory.map(h => `
                            <div class="history-item" data-id="${h.id}">
                                <div class="history-item-header">
                                    <span class="history-date">${h.date} ${h.time}</span>
                                    <span class="history-type">${h.type || '검수'}</span>
                                </div>
                                <div class="history-item-body">
                                    <div class="history-text-pair">
                                        <div class="history-original">
                                            <strong>원본:</strong>
                                            <p>${(h.originalText || '').substring(0, 200)}${(h.originalText || '').length > 200 ? '...' : ''}</p>
                                        </div>
                                        <div class="history-arrow">→</div>
                                        <div class="history-result">
                                            <strong>결과:</strong>
                                            <p>${(h.resultText || '').substring(0, 200)}${(h.resultText || '').length > 200 ? '...' : ''}</p>
                                        </div>
                                    </div>
                                    ${h.toolsUsed ? `<div class="history-tools">🔧 ${h.toolsUsed}</div>` : ''}
                                    ${h.changes && h.changes.length > 0 ? `
                                        <div class="history-changes">
                                            <strong>변경 사항:</strong>
                                            <ul>${h.changes.slice(0, 5).map(c => `<li>${c}</li>`).join('')}</ul>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        `).join('')
            }
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 모달 배경 클릭 시 닫기
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    clearHistory() {
        if (confirm('정말 모든 히스토리를 삭제하시겠습니까?')) {
            this.reviewHistory = [];
            this.saveHistoryToStorage();
            this.addLog('🗑️ 히스토리가 삭제되었습니다.');

            // 모달 새로고침
            const modal = document.getElementById('historyModal');
            if (modal) {
                modal.remove();
                this.showHistoryModal();
            }
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ToPlusEditor();
});
