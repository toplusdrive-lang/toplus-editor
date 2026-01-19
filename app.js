/**
 * TOPLUS Editor - Main Application Logic
 * 5단계 검수 프로세스 UI 관리
 */


class ToPlusEditor {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 5;
        this.stepData = {
            1: { name: '문맥/논리 분석', desc: '텍스트의 문맥과 논리 구조를 분석하고 개선합니다.', api: 'Notion AI' },
            2: { name: '문법/스펠 체크', desc: '문법 오류와 맞춤법을 자동으로 교정합니다.', api: 'LanguageTool' },
            3: { name: '톤 & 타깃독자 조정', desc: '문맥에 맞는 적절한 어조로 조정합니다.', api: 'Claude 4.5 Sonnet' },
            4: { name: '스타일 & 가독성', desc: '가독성과 스타일을 개선합니다.', api: 'GPT-4o' },
            5: { name: '최종 검토', desc: '모든 단계를 거친 최종 결과를 검토합니다.', api: 'Final Review' }
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
