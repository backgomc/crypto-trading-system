// 파일 경로: web/static/js/ai_model.js
// 코드명: AI 모델 관리 페이지 JavaScript (RemoteTrainer 연동)

// 전역 변수
let isTraining = false;
let statusInterval = null;
let selectedIndicators = {};
let trainingParams = {};

// ============================================================================
// 페이지 초기화
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 AI 모델 관리 페이지 초기화');
    
    // 초기 데이터 로드
    loadModels();
    loadIndicators();
    loadTrainingStatus();
    loadScheduleSettings();
    
    // 이벤트 리스너 등록
    initEventListeners();
    
    // 현재 시간 업데이트
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
});

// ============================================================================
// 이벤트 리스너
// ============================================================================

function initEventListeners() {
    // 학습 시작 버튼
    const startBtn = document.getElementById('startTrainingBtn');
    if (startBtn) {
        startBtn.addEventListener('click', startTraining);
    }
    
    // 학습 중지 버튼
    const stopBtn = document.getElementById('stopTrainingBtn');
    if (stopBtn) {
        stopBtn.addEventListener('click', stopTraining);
    }
    
    // 기본값 복원 버튼
    const resetBtn = document.getElementById('resetParametersBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetParameters);
    }
    
    // 자동 재학습 스위치
    const autoRetraining = document.getElementById('autoRetraining');
    if (autoRetraining) {
        autoRetraining.addEventListener('change', updateScheduleSettings);
    }
    
    // 재학습 간격 선택
    const retrainingInterval = document.getElementById('retrainingInterval');
    if (retrainingInterval) {
        retrainingInterval.addEventListener('change', updateScheduleSettings);
    }
    
    // 모델 정리 버튼
    const cleanupBtn = document.getElementById('cleanupModelsBtn');
    if (cleanupBtn) {
        cleanupBtn.addEventListener('click', cleanupModels);
    }
}

// ============================================================================
// 모델 관리
// ============================================================================

async function loadModels() {
    try {
        const response = await fetch('/api/ai/models');
        const data = await response.json();
        
        if (data.success) {
            displayModels(data.data.models);
            updateActiveModel(data.data.active_model);
            updateStorageInfo(data.data.storage_info);
        } else {
            showToast('모델 목록 로드 실패', 'error');
        }
    } catch (error) {
        console.error('모델 로드 오류:', error);
        showToast('모델 목록 로드 중 오류 발생', 'error');
    }
}

function displayModels(models) {
    const modelList = document.querySelector('.model-list');
    if (!modelList) return;
    
    if (models.length === 0) {
        modelList.innerHTML = `
            <div class="text-center p-4 text-muted">
                <i class="bi bi-inbox" style="font-size: 3rem;"></i>
                <p class="mt-2">학습된 모델이 없습니다</p>
            </div>
        `;
        return;
    }
    
    modelList.innerHTML = models.map(model => {
        const isActive = model.name === document.getElementById('activeModelName')?.textContent;
        const accuracy = (model.accuracy * 100).toFixed(1);
        const date = new Date(model.created_at).toLocaleDateString('ko-KR');
        const time = new Date(model.created_at).toLocaleTimeString('ko-KR', {hour: '2-digit', minute: '2-digit'});
        
        return `
            <div class="model-item ${isActive ? 'active' : ''}" data-model="${model.name}">
                <div class="model-info">
                    <div class="model-name">${model.name}</div>
                    <div class="model-meta">
                        <small>${date} ${time}</small>
                        <span class="accuracy">${accuracy}%</span>
                    </div>
                </div>
                <div class="model-actions">
                    ${isActive ? 
                        '<button class="btn btn-sm btn-success" disabled><i class="bi bi-check-circle"></i></button>' :
                        `<button class="btn btn-sm btn-outline-primary" onclick="activateModel('${model.name}')">
                            <i class="bi bi-play"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteModel('${model.name}')">
                            <i class="bi bi-trash"></i>
                        </button>`
                    }
                </div>
            </div>
        `;
    }).join('');
}

function updateActiveModel(modelName) {
    if (!modelName) return;
    
    const activeModelName = document.getElementById('activeModelName');
    const activeModelBadge = document.getElementById('activeModelBadge');
    
    if (activeModelName) {
        activeModelName.textContent = modelName;
    }
    
    if (activeModelBadge) {
        activeModelBadge.textContent = '활성';
        activeModelBadge.className = 'badge bg-success';
    }
}

function updateStorageInfo(info) {
    if (!info) return;
    
    const totalModels = document.getElementById('totalModels');
    const storageSize = document.getElementById('storageSize');
    
    if (totalModels) {
        totalModels.textContent = `${info.total_models}개`;
    }
    
    if (storageSize) {
        storageSize.textContent = `${info.storage_size_mb} MB`;
    }
}

async function activateModel(modelName) {
    if (!confirm(`${modelName} 모델을 활성화하시겠습니까?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/ai/models/activate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({model_name: modelName})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('모델이 활성화되었습니다', 'success');
            loadModels(); // 목록 새로고침
        } else {
            showToast(data.error || '모델 활성화 실패', 'error');
        }
    } catch (error) {
        console.error('모델 활성화 오류:', error);
        showToast('모델 활성화 중 오류 발생', 'error');
    }
}

async function deleteModel(modelName) {
    if (!confirm(`${modelName} 모델을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/ai/models/${modelName}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('모델이 삭제되었습니다', 'success');
            loadModels(); // 목록 새로고침
        } else {
            showToast(data.error || '모델 삭제 실패', 'error');
        }
    } catch (error) {
        console.error('모델 삭제 오류:', error);
        showToast('모델 삭제 중 오류 발생', 'error');
    }
}

async function cleanupModels() {
    if (!confirm('오래된 모델들을 정리하시겠습니까?\n최근 5개 모델만 보관됩니다.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/ai/models/cleanup', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({keep_count: 5})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`${data.data.deleted_count}개 모델이 정리되었습니다`, 'success');
            loadModels(); // 목록 새로고침
        } else {
            showToast(data.error || '모델 정리 실패', 'error');
        }
    } catch (error) {
        console.error('모델 정리 오류:', error);
        showToast('모델 정리 중 오류 발생', 'error');
    }
}

// ============================================================================
// 지표 관리
// ============================================================================

async function loadIndicators() {
    try {
        const response = await fetch('/api/ai/data/indicators');
        const data = await response.json();
        
        if (data.success) {
            displayIndicators(data.data.indicators);
        } else {
            showToast('지표 목록 로드 실패', 'error');
        }
    } catch (error) {
        console.error('지표 로드 오류:', error);
        showToast('지표 목록 로드 중 오류 발생', 'error');
    }
}

function displayIndicators(indicators) {
    const priceIndicators = document.getElementById('priceIndicators');
    const momentumIndicators = document.getElementById('momentumIndicators');
    const volumeIndicators = document.getElementById('volumeIndicators');
    const volatilityIndicators = document.getElementById('volatilityIndicators');
    
    // 지표 분류
    const categories = {
        price: ['price', 'sma', 'ema', 'bb'],
        momentum: ['macd', 'rsi', 'stoch', 'williams', 'adx', 'aroon'],
        volume: ['volume', 'mfi', 'vwap', 'cvd'],
        volatility: ['atr', 'volatility', 'consecutive', 'trend']
    };
    
    // 각 카테고리별로 표시
    Object.entries(categories).forEach(([category, indicatorKeys]) => {
        let container = null;
        
        switch(category) {
            case 'price': container = priceIndicators; break;
            case 'momentum': container = momentumIndicators; break;
            case 'volume': container = volumeIndicators; break;
            case 'volatility': container = volatilityIndicators; break;
        }
        
        if (!container) return;
        
        const html = indicatorKeys.map(key => {
            const indicator = indicators[key];
            if (!indicator) return '';
            
            const isEssential = indicator.is_essential;
            const isChecked = indicator.default_enabled;
            const isDisabled = isEssential; // 필수 지표는 비활성화
            
            selectedIndicators[key] = isChecked; // 초기값 설정
            
            return `
                <div class="form-check mb-2">
                    <input class="form-check-input indicator-checkbox" 
                           type="checkbox" 
                           id="indicator_${key}" 
                           data-indicator="${key}"
                           ${isChecked ? 'checked' : ''}
                           ${isDisabled ? 'disabled' : ''}>
                    <label class="form-check-label" for="indicator_${key}">
                        ${indicator.name}
                        ${isEssential ? '<span class="badge bg-info ms-1">필수</span>' : ''}
                        <small class="text-muted">(${indicator.column_count}개)</small>
                    </label>
                </div>
            `;
        }).join('');
        
        container.innerHTML = html;
    });
    
    // 체크박스 이벤트 리스너
    document.querySelectorAll('.indicator-checkbox:not(:disabled)').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const indicator = this.dataset.indicator;
            selectedIndicators[indicator] = this.checked;
            updateSelectedCount();
        });
    });
    
    updateSelectedCount();
}

function updateSelectedCount() {
    const totalCount = Object.keys(selectedIndicators).length;
    const selectedCount = Object.values(selectedIndicators).filter(v => v).length;
    
    const countElement = document.getElementById('selectedIndicatorCount');
    if (countElement) {
        countElement.textContent = `${selectedCount}/${totalCount}개 선택`;
    }
}

// ============================================================================
// 학습 관리
// ============================================================================

async function startTraining() {
    if (isTraining) {
        showToast('이미 학습이 진행 중입니다', 'warning');
        return;
    }
    
    // 파라미터 수집
    trainingParams = {
        training_days: parseInt(document.getElementById('trainingDays')?.value || 365),
        epochs: parseInt(document.getElementById('epochs')?.value || 100),
        batch_size: parseInt(document.getElementById('batchSize')?.value || 32),
        learning_rate: parseFloat(document.getElementById('learningRate')?.value || 0.001),
        sequence_length: parseInt(document.getElementById('sequenceLength')?.value || 60),
        validation_split: parseInt(document.getElementById('validationSplit')?.value || 20),
        interval: '15',
        symbol: 'BTCUSDT'
    };
    
    // 파라미터 유효성 검사
    const errors = validateTrainingParams(trainingParams);
    if (errors.length > 0) {
        showToast(errors.join('\n'), 'error');
        return;
    }
    
    // 선택된 지표 확인
    const selectedCount = Object.values(selectedIndicators).filter(v => v).length;
    if (selectedCount === 0) {
        showToast('최소 하나 이상의 지표를 선택해주세요', 'error');
        return;
    }
    
    if (!confirm(`학습을 시작하시겠습니까?\n\n선택된 지표: ${selectedCount}개\n에폭: ${trainingParams.epochs}\n학습 기간: ${trainingParams.training_days}일`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/ai/training/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                indicators: selectedIndicators,
                ...trainingParams
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            isTraining = true;
            showToast('AI 모델 학습을 시작했습니다', 'success');
            
            // UI 업데이트
            document.getElementById('startTrainingBtn').disabled = true;
            document.getElementById('stopTrainingBtn').disabled = false;
            document.getElementById('trainingStatus').textContent = '학습 중';
            document.getElementById('trainingStatus').className = 'badge bg-primary';
            document.getElementById('trainingProgress').style.display = 'block';
            
            // 상태 모니터링 시작
            startStatusMonitoring();
            
        } else {
            showToast(data.error || '학습 시작 실패', 'error');
        }
    } catch (error) {
        console.error('학습 시작 오류:', error);
        showToast('학습 시작 중 오류 발생', 'error');
    }
}

async function stopTraining() {
    if (!isTraining) {
        return;
    }
    
    if (!confirm('학습을 중지하시겠습니까?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/ai/training/stop', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            isTraining = false;
            showToast('AI 모델 학습을 중지했습니다', 'info');
            
            // UI 업데이트
            document.getElementById('startTrainingBtn').disabled = false;
            document.getElementById('stopTrainingBtn').disabled = true;
            document.getElementById('trainingStatus').textContent = '중지됨';
            document.getElementById('trainingStatus').className = 'badge bg-warning';
            
            // 상태 모니터링 중지
            stopStatusMonitoring();
            
        } else {
            showToast(data.error || '학습 중지 실패', 'error');
        }
    } catch (error) {
        console.error('학습 중지 오류:', error);
        showToast('학습 중지 중 오류 발생', 'error');
    }
}

async function loadTrainingStatus() {
    try {
        const response = await fetch('/api/ai/training/status');
        const data = await response.json();
        
        if (data.success) {
            updateTrainingStatus(data.data);
        }
    } catch (error) {
        console.error('학습 상태 로드 오류:', error);
    }
}

function updateTrainingStatus(status) {
    if (!status) return;
    
    // 학습 중 여부
    isTraining = status.is_training || false;
    
    // 버튼 상태
    document.getElementById('startTrainingBtn').disabled = isTraining;
    document.getElementById('stopTrainingBtn').disabled = !isTraining;
    
    // 상태 배지
    const statusBadge = document.getElementById('trainingStatus');
    if (statusBadge) {
        if (status.status === 'running') {
            statusBadge.textContent = '학습 중';
            statusBadge.className = 'badge bg-primary';
        } else if (status.status === 'completed') {
            statusBadge.textContent = '완료';
            statusBadge.className = 'badge bg-success';
        } else if (status.status === 'failed') {
            statusBadge.textContent = '실패';
            statusBadge.className = 'badge bg-danger';
        } else {
            statusBadge.textContent = '대기 중';
            statusBadge.className = 'badge bg-secondary';
        }
    }
    
    // 진행률 표시
    if (isTraining && status.total_epochs > 0) {
        document.getElementById('trainingProgress').style.display = 'block';
        
        // 전체 진행률
        const progress = (status.current_epoch / status.total_epochs) * 100;
        document.getElementById('overallProgress').style.width = progress + '%';
        document.getElementById('progressText').textContent = `${status.current_epoch}/${status.total_epochs} 에폭`;
        
        // 시간 정보
        if (status.start_time) {
            document.getElementById('startTime').textContent = new Date(status.start_time).toLocaleString('ko-KR');
        }
        
        if (status.elapsed_formatted) {
            document.getElementById('elapsedTime').textContent = status.elapsed_formatted;
        }
        
        // 메트릭
        if (status.accuracy) {
            document.getElementById('currentAccuracy').textContent = (status.accuracy * 100).toFixed(1) + '%';
        }
    } else {
        document.getElementById('trainingProgress').style.display = 'none';
    }
    
    // 학습 중이면 모니터링 시작
    if (isTraining && !statusInterval) {
        startStatusMonitoring();
    }
}

function startStatusMonitoring() {
    if (statusInterval) return;
    
    statusInterval = setInterval(async () => {
        await loadTrainingStatus();
        
        // 학습 완료 체크
        const statusBadge = document.getElementById('trainingStatus');
        if (statusBadge && (statusBadge.textContent === '완료' || statusBadge.textContent === '실패')) {
            stopStatusMonitoring();
            loadModels(); // 모델 목록 새로고침
        }
    }, 5000); // 5초마다 확인
}

function stopStatusMonitoring() {
    if (statusInterval) {
        clearInterval(statusInterval);
        statusInterval = null;
    }
}

function validateTrainingParams(params) {
    const errors = [];
    
    if (params.training_days < 30 || params.training_days > 1095) {
        errors.push('학습 기간은 30~1095일 사이여야 합니다');
    }
    
    if (params.epochs < 10 || params.epochs > 1000) {
        errors.push('에폭은 10~1000 사이여야 합니다');
    }
    
    if (params.batch_size < 8 || params.batch_size > 128) {
        errors.push('배치 크기는 8~128 사이여야 합니다');
    }
    
    if (params.learning_rate < 0.0001 || params.learning_rate > 0.1) {
        errors.push('학습률은 0.0001~0.1 사이여야 합니다');
    }
    
    return errors;
}

function resetParameters() {
    if (confirm('모든 파라미터를 기본값으로 복원하시겠습니까?')) {
        document.getElementById('trainingDays').value = 365;
        document.getElementById('epochs').value = 100;
        document.getElementById('batchSize').value = 32;
        document.getElementById('learningRate').value = 0.001;
        document.getElementById('sequenceLength').value = 60;
        document.getElementById('validationSplit').value = 20;
        
        showToast('파라미터가 기본값으로 복원되었습니다', 'info');
    }
}

// ============================================================================
// 스케줄 관리
// ============================================================================

async function loadScheduleSettings() {
    try {
        const response = await fetch('/api/ai/schedule');
        const data = await response.json();
        
        if (data.success) {
            const settings = data.data;
            
            // 자동 재학습 스위치
            const autoRetraining = document.getElementById('autoRetraining');
            if (autoRetraining) {
                autoRetraining.checked = settings.enabled;
            }
            
            // 재학습 간격
            const retrainingInterval = document.getElementById('retrainingInterval');
            if (retrainingInterval) {
                retrainingInterval.value = settings.interval;
            }
            
            // 다음 학습 시간
            const nextTraining = document.getElementById('nextTraining');
            if (nextTraining && settings.next_training) {
                const nextTime = new Date(settings.next_training);
                nextTraining.textContent = nextTime.toLocaleString('ko-KR');
            }
        }
    } catch (error) {
        console.error('스케줄 설정 로드 오류:', error);
    }
}

async function updateScheduleSettings() {
    const enabled = document.getElementById('autoRetraining').checked;
    const interval = parseInt(document.getElementById('retrainingInterval').value);
    
    try {
        const response = await fetch('/api/ai/schedule', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                enabled: enabled,
                interval: interval
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('스케줄 설정이 업데이트되었습니다', 'success');
            
            // 다음 학습 시간 업데이트
            if (data.data.next_training) {
                const nextTime = new Date(data.data.next_training);
                document.getElementById('nextTraining').textContent = nextTime.toLocaleString('ko-KR');
            }
        } else {
            showToast(data.error || '스케줄 설정 업데이트 실패', 'error');
        }
    } catch (error) {
        console.error('스케줄 설정 업데이트 오류:', error);
        showToast('스케줄 설정 업데이트 중 오류 발생', 'error');
    }
}

// ============================================================================
// 유틸리티 함수
// ============================================================================

function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    const currentTime = document.getElementById('currentTime');
    if (currentTime) {
        currentTime.textContent = timeString;
    }
}

function showToast(message, type = 'info') {
    // Bootstrap 토스트 또는 커스텀 알림 표시
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        // 토스트 컨테이너 생성
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const toastId = 'toast_' + Date.now();
    const bgClass = type === 'error' ? 'bg-danger' : 
                   type === 'success' ? 'bg-success' : 
                   type === 'warning' ? 'bg-warning' : 'bg-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0 mb-2" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    document.getElementById('toastContainer').insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {autohide: true, delay: 3000});
    toast.show();
    
    // 토스트 제거
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// ============================================================================
// 디버그 함수 (개발용)
// ============================================================================

window.debugAI = {
    getSelectedIndicators: () => selectedIndicators,
    getTrainingParams: () => trainingParams,
    getTrainingStatus: () => isTraining,
    reloadAll: () => {
        loadModels();
        loadIndicators();
        loadTrainingStatus();
        loadScheduleSettings();
    }
};

console.log('💡 디버그 명령어:');
console.log('   debugAI.getSelectedIndicators() - 선택된 지표 확인');
console.log('   debugAI.getTrainingParams() - 학습 파라미터 확인');
console.log('   debugAI.reloadAll() - 전체 데이터 새로고침');