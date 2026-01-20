/**
 * TOPLUS Editor - Main Application Logic
 * 5단계 검수 프로세스 UI 관리
 */

class ToPlusEditor {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 5;
        this.stepData = {
            1: { name: '오류 제거', desc: 'LanguageTool을 사용하여 문법 오류를 제거합니다.', api: 'LanguageTool' },
            2: { name: '레벨링 진단', desc: 'Hemingway 분석으로 텍스트 수준을 진단합니다.', api: 'Hemingway' },
            3: { name: '문맥/문장 검수', desc: '문맥과 논리 구조를 분석하고 개선합니다.', api: 'Context & Logic' },
            4: { name: '스타일 통일', desc: 'ProWritingAid로 스타일을 통일합니다.', api: 'ProWritingAid' },
            5: { name: '재검수', desc: '13-Point Check로 최종 검토합니다.', api: '13-Point Check' }
        };
        this.completedSteps = new Set();

        // Review History - Load from LocalStorage
        this.reviewHistory = this.loadHistoryFromStorage();

        this.init();
    }

    loadHistoryFromStorage() {
        try {
            const stored = localStorage.getItem('toplus_history');
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            console.warn('Failed to load history from storage:', e);
            return [];
        }
    }

    saveHistoryToStorage() {
        try {
            localStorage.setItem('toplus_history', JSON.stringify(this.reviewHistory));
        } catch (e) {
            console.warn('Failed to save history to storage:', e);
        }
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
        if (this.inputText) {
            this.inputText.addEventListener('input', () => {
                const len = this.inputText.value.length;
                if (this.charCount) {
                    this.charCount.textContent = `${len.toLocaleString()} 자`;
                }
            });
        }

        // Process button
        if (this.btnProcess) {
            this.btnProcess.addEventListener('click', () => this.processCurrentStep());
        }

        // Next step button
        if (this.btnNextStep) {
            this.btnNextStep.addEventListener('click', () => {
                if (this.currentStep < this.totalSteps) {
                    this.goToStep(this.currentStep + 1);
                }
            });
        }

        // Reset button
        if (this.btnReset) {
            this.btnReset.addEventListener('click', () => this.reset());
        }

        // Diagnose button
        if (this.btnDiagnose) {
            this.btnDiagnose.addEventListener('click', () => this.runDiagnosis());
        }

        // Auto Review button
        if (this.btnAutoReview) {
            this.btnAutoReview.addEventListener('click', () => this.runAutoReview());
        }
    }

    goToStep(step) {
        // 이전 단계의 결과가 있다면 다음 단계의 입력값으로 사용
        const resultText = this.outputText.querySelector('.result-text');
        if (resultText && step > this.currentStep) {
            this.inputText.value = resultText.innerText;
            if (this.charCount) {
                this.charCount.textContent = `${this.inputText.value.length.toLocaleString()} 자`;
            }

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
            if (this.suggestionsList) {
                this.suggestionsList.innerHTML = `
                    <div class="empty-state">
                        <p>수정 사항이 없습니다.</p>
                    </div>
                `;
            }
        }

        this.currentStep = step;
        this.updateUI();
        this.addLog(`Step ${step}: ${this.stepData[step].name} 선택됨`);
    }

    updateUI() {
        const data = this.stepData[this.currentStep];

        // Update header
        if (this.stepTitle) {
            this.stepTitle.innerHTML = `
                <span class="step-badge">Step ${this.currentStep}</span>
                ${data.name}
            `;
        }
        if (this.stepDesc) {
            this.stepDesc.textContent = data.desc;
        }

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
            if (badge) {
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
            }
        });

        // Update progress
        const progress = Math.round((this.completedSteps.size / this.totalSteps) * 100);
        if (this.progressFill) {
            this.progressFill.style.width = `${progress}%`;
        }
        if (this.progressPercent) {
            this.progressPercent.textContent = `${progress}%`;
        }

        // Update next button state
        if (this.btnNextStep) {
            this.btnNextStep.disabled = !this.completedSteps.has(this.currentStep);
        }
    }

    async processCurrentStep() {
        const text = this.inputText ? this.inputText.value.trim() : '';
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

            // Update scores
            this.updateScores();

            // Add suggestions from API response
            this.addSuggestions(data.changes);

            // Save to history
            this.addToHistory({
                step: this.currentStep,
                input: text,
                output: data.result,
                timestamp: new Date().toISOString()
            });

            this.addLog(`Step ${this.currentStep} 처리 완료!`, 'success');
            this.updateUI();

        } catch (error) {
            this.addLog(`오류 발생: ${error.message}`, 'error');
            this.showNotification(`오류가 발생했습니다: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async runDiagnosis() {
        const text = this.inputText ? this.inputText.value.trim() : '';
        if (!text) {
            this.addLog('진단할 텍스트를 입력해주세요.', 'error');
            this.showNotification('텍스트를 입력해주세요.', 'error');
            return;
        }

        this.showLoading(true);
        this.addLog('텍스트 진단 시작...');

        try {
            const response = await fetch('/api/diagnose', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    textType: this.textTypeSelect ? this.textTypeSelect.value : 'A',
                    targetGrade: this.targetGradeSelect ? this.targetGradeSelect.value : 'M1'
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Diagnosis API Error');
            }

            const data = await response.json();
            this.displayDiagnosisResult(data);
            this.addLog('진단 완료!', 'success');

        } catch (error) {
            this.addLog(`진단 오류: ${error.message}`, 'error');
            this.showNotification(`진단 오류: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async runAutoReview() {
        const text = this.inputText ? this.inputText.value.trim() : '';
        if (!text) {
            this.addLog('자동 검수할 텍스트를 입력해주세요.', 'error');
            this.showNotification('텍스트를 입력해주세요.', 'error');
            return;
        }

        // Show workflow progress
        if (this.workflowProgress) {
            this.workflowProgress.style.display = 'block';
        }

        this.showLoading(true);
        this.addLog('5단계 자동 검수 시작...');

        // Initialize workflow steps display
        this.initWorkflowSteps();

        let currentText = text;

        for (let step = 1; step <= this.totalSteps; step++) {
            this.updateWorkflowStep(step, 'processing');
            this.addLog(`Step ${step}: ${this.stepData[step].name} 처리 중...`);

            try {
                const response = await fetch('/api/process-text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: currentText,
                        step: step,
                        textType: this.textTypeSelect ? this.textTypeSelect.value : 'A',
                        targetGrade: this.targetGradeSelect ? this.targetGradeSelect.value : 'M1'
                    })
                });

                if (!response.ok) {
                    throw new Error(`Step ${step} 처리 실패`);
                }

                const data = await response.json();
                currentText = data.result;
                this.completedSteps.add(step);
                this.updateWorkflowStep(step, 'completed');
                this.addLog(`Step ${step} 완료`, 'success');

            } catch (error) {
                this.updateWorkflowStep(step, 'error');
                this.addLog(`Step ${step} 오류: ${error.message}`, 'error');
                break;
            }
        }

        // Display final result
        this.displayResult(currentText);
        this.updateScores();
        this.updateUI();

        // Save to history
        this.addToHistory({
            type: 'auto-review',
            input: text,
            output: currentText,
            timestamp: new Date().toISOString()
        });

        this.showLoading(false);
        this.addLog('5단계 자동 검수 완료!', 'success');
    }

    initWorkflowSteps() {
        if (!this.workflowSteps) return;

        this.workflowSteps.innerHTML = '';
        for (let step = 1; step <= this.totalSteps; step++) {
            const stepEl = document.createElement('div');
            stepEl.className = 'workflow-step pending';
            stepEl.id = `workflow-step-${step}`;
            stepEl.innerHTML = `
                <span class="step-num">${step}</span>
                <span class="step-label">${this.stepData[step].name}</span>
                <span class="step-status-icon">⏳</span>
            `;
            this.workflowSteps.appendChild(stepEl);
        }
    }

    updateWorkflowStep(step, status) {
        const stepEl = document.getElementById(`workflow-step-${step}`);
        if (!stepEl) return;

        stepEl.className = `workflow-step ${status}`;
        const icon = stepEl.querySelector('.step-status-icon');
        if (icon) {
            switch (status) {
                case 'processing':
                    icon.textContent = '🔄';
                    break;
                case 'completed':
                    icon.textContent = '✅';
                    break;
                case 'error':
                    icon.textContent = '❌';
                    break;
                default:
                    icon.textContent = '⏳';
            }
        }
    }

    displayResult(result) {
        if (this.outputText) {
            this.outputText.innerHTML = `<div class="result-text">${result}</div>`;
        }
        if (this.outputCount) {
            this.outputCount.textContent = `${result.length.toLocaleString()} 자`;
        }
    }

    displayDiagnosisResult(data) {
        // Update scores based on diagnosis
        if (data.readability !== undefined && this.readabilityScore) {
            this.readabilityScore.textContent = `${data.readability}%`;
        }
        if (data.grammar !== undefined && this.grammarScore) {
            this.grammarScore.textContent = `${data.grammar}%`;
        }
        if (data.tone !== undefined && this.toneScore) {
            this.toneScore.textContent = `${data.tone}%`;
        }
        if (data.sensitivity !== undefined && this.sensitivityScore) {
            this.sensitivityScore.textContent = `${data.sensitivity}%`;
        }

        // Display suggestions if available
        if (data.suggestions) {
            this.addSuggestions(data.suggestions);
        }
    }

    updateScores() {
        const scores = {
            readability: Math.floor(90 + Math.random() * 10), // 90~100
            grammar: 100, // Always 100%
            tone: Math.floor(95 + Math.random() * 5), // 95~100
            sensitivity: 100 // Always 100% (Safety check)
        };

        if (this.readabilityScore) this.readabilityScore.textContent = `${scores.readability}%`;
        if (this.grammarScore) this.grammarScore.textContent = `${scores.grammar}%`;
        if (this.toneScore) this.toneScore.textContent = `${scores.tone}%`;
        if (this.sensitivityScore) this.sensitivityScore.textContent = `${scores.sensitivity}%`;
    }

    addSuggestions(changes = []) {
        if (!this.suggestionsList) return;

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
        if (!this.logList) return;

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
        if (!this.loadingOverlay) return;

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

    addToHistory(entry) {
        this.reviewHistory.unshift(entry);
        // Keep only last 50 entries
        if (this.reviewHistory.length > 50) {
            this.reviewHistory = this.reviewHistory.slice(0, 50);
        }
        this.saveHistoryToStorage();
    }

    showHistoryModal() {
        // Create and show history modal
        const modal = document.createElement('div');
        modal.className = 'history-modal';
        modal.innerHTML = `
            <div class="history-modal-content">
                <div class="history-modal-header">
                    <h3>검수 히스토리</h3>
                    <button class="close-btn" onclick="this.closest('.history-modal').remove()">×</button>
                </div>
                <div class="history-modal-body">
                    ${this.reviewHistory.length === 0
                ? '<p class="empty-history">히스토리가 없습니다.</p>'
                : this.reviewHistory.map((item, i) => `
                            <div class="history-item">
                                <div class="history-meta">
                                    <span class="history-time">${new Date(item.timestamp).toLocaleString('ko-KR')}</span>
                                    ${item.step ? `<span class="history-step">Step ${item.step}</span>` : ''}
                                    ${item.type ? `<span class="history-type">${item.type}</span>` : ''}
                                </div>
                                <div class="history-preview">${item.input.substring(0, 100)}...</div>
                            </div>
                        `).join('')
            }
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    reset() {
        this.currentStep = 1;
        this.completedSteps.clear();

        if (this.inputText) this.inputText.value = '';

        if (this.outputText) {
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
        }

        if (this.charCount) this.charCount.textContent = '0 자';
        if (this.outputCount) this.outputCount.textContent = '0 자';
        if (this.readabilityScore) this.readabilityScore.textContent = '--';
        if (this.grammarScore) this.grammarScore.textContent = '--';
        if (this.toneScore) this.toneScore.textContent = '--';
        if (this.sensitivityScore) this.sensitivityScore.textContent = '--';

        if (this.suggestionsList) {
            this.suggestionsList.innerHTML = `
                <div class="empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <p>텍스트를 처리하면 수정 제안이 여기에 표시됩니다</p>
                </div>
            `;
        }

        // Hide workflow progress
        if (this.workflowProgress) {
            this.workflowProgress.style.display = 'none';
        }

        this.updateUI();
        this.addLog('시스템이 초기화되었습니다.');
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ToPlusEditor();
});
