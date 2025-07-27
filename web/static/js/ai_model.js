// 파일 경로: web/static/js/ai_model.js
// 코드명: AI 모델 관리 페이지 전용 로직

// ============================================================================
// 전역 변수
// ============================================================================

let trainingInterval = null;
let startTimestamp = null;
let isTraining = false;

// ============================================================================
// 페이지 초기화
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🤖 AI 모델 관리 페이지 초기화');
    
    initTimeUpdate();
    loadCurrentModel();
    loadModelHistory();
    loadTrainingParams();
    
    console.log('✅ AI 모델 페이지 초기화 완료');
});

// ============================================================================
// 시간 업데이트
// ============================================================================

function initTimeUpdate() {
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
}

function updateCurrentTime() {
    const now = new Date();
    const timeString = formatDateTime(now);
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        timeElement.textContent = timeString;
    }
}

// ============================================================================
// AI 모델 정보 로드
// ============================================================================

async function loadCurrentModel() {
    try {
        const result = await apiCall('/api/ai/model/current');
        if (result.success && result.data) {
            updateActiveModelDisplay(result.data);
        }
    } catch (error) {
        console.error('현재 모델 정보 로드 실패:', error);
    }
}

async function loadModelHistory() {
    try {
        const result = await apiCall('/api/ai/model/history');
        if (result.success && result.data) {
            updateModelHistoryDisplay(result.data);
        }
    } catch (error) {
        console.error('모델 히스토리 로드 실패:', error);
    }
}

function updateActiveModelDisplay(modelData) {
    const modelNameEl = document.querySelector('.active-model-info .model-name strong');
    const accuracyEl = document.querySelector('.stat-item .value.text-success');
    const dateEl = document.querySelectorAll('.stat-item .value')[1];
    
    if (modelNameEl) modelNameEl.textContent = modelData.name || 'model_unknown';
    if (accuracyEl) accuracyEl.textContent = `${(modelData.accuracy * 100).toFixed(1)}%`;
    if (dateEl) dateEl.textContent = formatDate(modelData.created_at);
}

function updateModelHistoryDisplay(models) {
    const modelList = document.querySelector('.model-list');
    if (!modelList) return;
    
    modelList.innerHTML = '';
    
    models.forEach((model, index) => {
        const isActive = index === 0;
        const modelItem = createModelItem(model, isActive);
        modelList.appendChild(modelItem);
    });
}

function createModelItem(model, isActive) {
    const div = document.createElement('div');
    div.className = `model-item ${isActive ? 'active' : ''}`;
    
    div.innerHTML = `
        <div class="model-info">
            <div class="model-name">${model.name}</div>
            <div class="model-meta">
                <small>${formatDateTime(model.created_at)}</small>
                <span class="accuracy">${(model.accuracy * 100).toFixed(1)}%</span>
            </div>
        </div>
        <div class="model-actions">
            ${isActive ? 
                '<button class="btn btn-sm btn-success" disabled><i class="bi bi-check-circle"></i></button>' :
                `<button class="btn btn-sm btn-outline-primary" onclick="activateModel('${model.name}')"><i class="bi bi-play"></i></button>
                 <button class="btn btn-sm btn-outline-danger" onclick="deleteModel('${model.name}')"><i class="bi bi-trash"></i></button>`
            }
        </div>
    `;
    
    return div;
}

// ============================================================================
// 학습 파라미터 관리
// ============================================================================

async function loadTrainingParams() {
    try {
        const result = await apiCall('/api/ai/training/params');
        if (result.success && result.data) {
            populateTrainingParams(result.data);
        }
    } catch (error) {
        console.error('학습 파라미터 로드 실패:', error);
        setDefaultTrainingParams();
    }
}

function populateTrainingParams(params) {
    setElementValue('trainingDays', params.training_days || 365);
    setElementValue('epochs', params.epochs || 100);
    setElementValue('batchSize', params.batch_size || 32);
    setElementValue('learningRate', params.learning_rate || 0.001);
    setElementValue('sequenceLength', params.sequence_length || 60);
    setElementValue('validationSplit', params.validation_split || 20);
    
    // 지표 선택 상태
    const indicators = params.indicators || {};
    Object.keys(indicators).forEach(key => {
        setElementValue(`indicator_${key}`, indicators[key]);
    });
}

function setDefaultTrainingParams() {
    setElementValue('trainingDays', 365);
    setElementValue('epochs', 100);
    setElementValue('batchSize', 32);
    setElementValue('learningRate', 0.001);
    setElementValue('sequenceLength', 60);
    setElementValue('validationSplit', 20);
    
    // 모든 지표 기본 선택
    document.querySelectorAll('input[id^="indicator_"]').forEach(checkbox => {
        checkbox.checked = true;
    });
}

function collectTrainingParams() {
    return {
        training_days: getElementValue('trainingDays'),
        epochs: getElementValue('epochs'),
        batch_size: getElementValue('batchSize'),
        learning_rate: getElementValue('learningRate'),
        sequence_length: getElementValue('sequenceLength'),
        validation_split: getElementValue('validationSplit'),
        indicators: collectSelectedIndicators()
    };
}

function collectSelectedIndicators() {
    const indicators = {};
    document.querySelectorAll('input[id^="indicator_"]').forEach(checkbox => {
        const key = checkbox.id.replace('indicator_', '');
        indicators[key] = checkbox.checked;
    });
    return indicators;
}

// ============================================================================
// 학습 제어
// ============================================================================

async function startTraining() {
    if (isTraining) return;
    
    try {
        showLoading(true);
        
        const params = collectTrainingParams();
        const result = await apiCall('/api/ai/training/start', 'POST', params);
        
        if (result.success) {
            isTraining = true;
            updateTrainingUI(true);
            startTrainingMonitor();
            showToast('success', 'AI 모델 학습을 시작했습니다.');
        } else {
            throw new Error(result.error || '학습 시작에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('학습 시작 실패:', error);
        showToast('error', '학습 시작 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function stopTraining() {
    if (!isTraining) return;
    
    if (!confirmAction('진행 중인 학습을 중지하시겠습니까?', '학습 중지')) {
        return;
    }
    
    try {
        showLoading(true);
        
        const result = await apiCall('/api/ai/training/stop', 'POST');
        
        if (result.success) {
            isTraining = false;
            updateTrainingUI(false);
            stopTrainingMonitor();
            showToast('warning', 'AI 모델 학습을 중지했습니다.');
        } else {
            throw new Error(result.error || '학습 중지에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('학습 중지 실패:', error);
        showToast('error', '학습 중지 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function updateTrainingUI(training) {
    const startBtn = document.getElementById('startTrainingBtn');
    const stopBtn = document.getElementById('stopTrainingBtn');
    const status = document.getElementById('trainingStatus');
    const progressDiv = document.getElementById('trainingProgress');
    
    if (startBtn) startBtn.disabled = training;
    if (stopBtn) stopBtn.disabled = !training;
    
    if (status) {
        if (training) {
            status.textContent = '학습 중';
            status.className = 'badge bg-primary';
        } else {
            status.textContent = '대기 중';
            status.className = 'badge bg-secondary';
        }
    }
    
    if (progressDiv) {
        progressDiv.style.display = training ? 'block' : 'none';
    }
    
    if (training) {
        startTimestamp = Date.now();
        const startTimeEl = document.getElementById('startTime');
        if (startTimeEl) {
            startTimeEl.textContent = formatDateTime(new Date());
        }
    }
}

// ============================================================================
// 학습 모니터링
// ============================================================================

function startTrainingMonitor() {
    if (trainingInterval) {
        clearInterval(trainingInterval);
    }
    
    trainingInterval = setInterval(async () => {
        try {
            const result = await apiCall('/api/ai/training/status');
            if (result.success && result.data) {
                updateTrainingProgress(result.data);
                
                if (result.data.status === 'completed' || result.data.status === 'failed') {
                    stopTrainingMonitor();
                    isTraining = false;
                    updateTrainingUI(false);
                    
                    if (result.data.status === 'completed') {
                        showToast('success', 'AI 모델 학습이 완료되었습니다!');
                        loadCurrentModel();
                        loadModelHistory();
                    } else {
                        showToast('error', '학습 중 오류가 발생했습니다.');
                    }
                }
            }
        } catch (error) {
            console.error('학습 상태 조회 실패:', error);
        }
    }, 2000); // 2초마다 상태 확인
}

function stopTrainingMonitor() {
    if (trainingInterval) {
        clearInterval(trainingInterval);
        trainingInterval = null;
    }
}

function updateTrainingProgress(data) {
    // 전체 진행률
    const overallProgress = document.getElementById('overallProgress');
    const progressText = document.getElementById('progressText');
    
    if (overallProgress && data.current_epoch && data.total_epochs) {
        const progress = (data.current_epoch / data.total_epochs) * 100;
        overallProgress.style.width = progress + '%';
        overallProgress.textContent = `${progress.toFixed(1)}%`;
    }
    
    if (progressText && data.current_epoch && data.total_epochs) {
        progressText.textContent = `${data.current_epoch}/${data.total_epochs} 에폭`;
    }
    
    // 에폭 진행률
    const epochProgress = document.getElementById('epochProgress');
    const epochText = document.getElementById('epochText');
    
    if (epochProgress && data.current_batch && data.total_batches) {
        const progress = (data.current_batch / data.total_batches) * 100;
        epochProgress.style.width = progress + '%';
        epochProgress.textContent = `${progress.toFixed(1)}%`;
    }
    
    if (epochText && data.current_batch && data.total_batches) {
        epochText.textContent = `${data.current_batch}/${data.total_batches} 배치`;
    }
    
    // 메트릭 업데이트
    if (data.metrics) {
        const currentLoss = document.getElementById('currentLoss');
        const currentAccuracy = document.getElementById('currentAccuracy');
        const valLoss = document.getElementById('valLoss');
        
        if (currentLoss) currentLoss.textContent = data.metrics.loss?.toFixed(4) || '-';
        if (currentAccuracy) currentAccuracy.textContent = data.metrics.accuracy ? `${(data.metrics.accuracy * 100).toFixed(1)}%` : '-';
        if (valLoss) valLoss.textContent = data.metrics.val_loss?.toFixed(4) || '-';
    }
    
    // 경과 시간 업데이트
    if (startTimestamp) {
        const elapsed = Date.now() - startTimestamp;
        const elapsedTimeEl = document.getElementById('elapsedTime');
        if (elapsedTimeEl) {
            elapsedTimeEl.textContent = formatElapsedTime(elapsed);
        }
        
        // 예상 완료 시간
        if (data.current_epoch && data.total_epochs && elapsed > 0) {
            const estimatedTotal = (elapsed / data.current_epoch) * data.total_epochs;
            const remaining = estimatedTotal - elapsed;
            const estimatedTimeEl = document.getElementById('estimatedTime');
            if (estimatedTimeEl && remaining > 0) {
                const completionTime = new Date(Date.now() + remaining);
                estimatedTimeEl.textContent = formatTime(completionTime);
            }
        }
    }
}

// ============================================================================
// 모델 관리
// ============================================================================

async function activateModel(modelName) {
    if (!confirmAction(`${modelName} 모델을 활성화하시겠습니까?`, '모델 활성화')) {
        return;
    }
    
    try {
        showLoading(true);
        
        const result = await apiCall(`/api/ai/model/activate/${modelName}`, 'POST');
        
        if (result.success) {
            showToast('success', `${modelName} 모델이 활성화되었습니다.`);
            loadCurrentModel();
            loadModelHistory();
        } else {
            throw new Error(result.error || '모델 활성화에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('모델 활성화 실패:', error);
        showToast('error', '모델 활성화 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function deleteModel(modelName) {
    if (!confirmAction(`${modelName} 모델을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`, '모델 삭제')) {
        return;
    }
    
    try {
        showLoading(true);
        
        const result = await apiCall(`/api/ai/model/delete/${modelName}`, 'DELETE');
        
        if (result.success) {
            showToast('success', `${modelName} 모델이 삭제되었습니다.`);
            loadModelHistory();
        } else {
            throw new Error(result.error || '모델 삭제에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('모델 삭제 실패:', error);
        showToast('error', '모델 삭제 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function cleanupModels() {
    if (!confirmAction('오래된 모델들을 정리하시겠습니까?\n(최근 5개 모델만 보관)', '모델 정리')) {
        return;
    }
    
    try {
        showLoading(true);
        
        const result = await apiCall('/api/ai/model/cleanup', 'POST');
        
        if (result.success) {
            showToast('success', '오래된 모델들이 정리되었습니다.');
            loadModelHistory();
        } else {
            throw new Error(result.error || '모델 정리에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('모델 정리 실패:', error);
        showToast('error', '모델 정리 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// ============================================================================
// 파라미터 관리
// ============================================================================

function resetParameters() {
    if (!confirmAction('모든 파라미터를 기본값으로 복원하시겠습니까?', '파라미터 초기화')) {
        return;
    }
    
    setDefaultTrainingParams();
    showToast('success', '파라미터가 기본값으로 복원되었습니다.');
}

async function saveTrainingParams() {
    try {
        const params = collectTrainingParams();
        const result = await apiCall('/api/ai/training/params', 'PUT', params);
        
        if (result.success) {
            showToast('success', '학습 파라미터가 저장되었습니다.');
        } else {
            throw new Error(result.error || '파라미터 저장에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('파라미터 저장 실패:', error);
        showToast('error', '파라미터 저장 실패: ' + error.message);
    }
}

// ============================================================================
// 자동 학습 스케줄러
// ============================================================================

async function updateAutoRetraining() {
    try {
        const enabled = getElementValue('autoRetraining');
        const interval = getElementValue('retrainingInterval');
        
        const result = await apiCall('/api/ai/schedule', 'PUT', {
            enabled: enabled,
            interval: parseInt(interval)
        });
        
        if (result.success) {
            showToast('success', '자동 학습 스케줄이 업데이트되었습니다.');
            updateNextTrainingTime(result.data.next_training);
        }
        
    } catch (error) {
        console.error('스케줄 업데이트 실패:', error);
        showToast('error', '스케줄 업데이트 실패: ' + error.message);
    }
}

function updateNextTrainingTime(nextTime) {
    const nextTrainingEl = document.getElementById('nextTraining');
    if (nextTrainingEl && nextTime) {
        nextTrainingEl.textContent = formatDateTime(new Date(nextTime));
    }
}

// ============================================================================
// 유틸리티 함수들
// ============================================================================

function formatElapsedTime(milliseconds) {
    const hours = Math.floor(milliseconds / 3600000);
    const minutes = Math.floor((milliseconds % 3600000) / 60000);
    const seconds = Math.floor((milliseconds % 60000) / 1000);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR');
}

// ============================================================================
// 이벤트 리스너
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // 자동 학습 설정 변경 감지
    const autoRetrainingCheckbox = document.getElementById('autoRetraining');
    const retrainingIntervalSelect = document.getElementById('retrainingInterval');
    
    if (autoRetrainingCheckbox) {
        autoRetrainingCheckbox.addEventListener('change', updateAutoRetraining);
    }
    
    if (retrainingIntervalSelect) {
        retrainingIntervalSelect.addEventListener('change', updateAutoRetraining);
    }
    
    // 파라미터 변경 시 자동 저장 (디바운스)
    let saveTimeout;
    document.querySelectorAll('#trainingDays, #epochs, #batchSize, #learningRate, #sequenceLength, #validationSplit').forEach(input => {
        input.addEventListener('change', () => {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(saveTrainingParams, 1000);
        });
    });
});

// 페이지 종료 시 정리
window.addEventListener('beforeunload', function() {
    if (trainingInterval) {
        clearInterval(trainingInterval);
    }
});

console.log('🚀 AI Model.js 로드 완료');