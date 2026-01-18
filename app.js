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
        this.outputText.innerHTML = `<div class="result-text">${result}</div>`;
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
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ToPlusEditor();
});
