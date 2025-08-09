// 파일 경로: web/static/js/ai_model.js
// 코드명: AI 모델 관리 페이지 JavaScript (고급 토스트 적용)

// 전역 변수
let isTraining = false;
let statusInterval = null;
let selectedIndicators = {};
let trainingParams = {};

// 지표 정보 매핑 (새 지표 추가 및 재구성)
const indicatorInfo = {
    // 핵심 지표 (14개) - 원웨이 장 대응 특화
    'price': { name: '가격 데이터', columns: 3, essential: true, default: true },
    'macd': { name: 'MACD', columns: 3, essential: true, default: true },
    'rsi': { name: 'RSI', columns: 1, essential: true, default: true },
    'bb': { name: '볼린저밴드', columns: 2, essential: true, default: true },
    'atr': { name: 'ATR', columns: 1, essential: true, default: true },
    'volume': { name: '거래량', columns: 3, essential: true, default: true },
    'adx': { name: 'ADX', columns: 2, essential: true, default: true },
    'aroon': { name: 'Aroon', columns: 1, essential: true, default: true },
    'consecutive': { name: '연속 카운터', columns: 2, essential: true, default: true },
    'trend': { name: '다중 시간대', columns: 4, essential: true, default: true },
    'hhll': { name: 'HH/LL 카운터', columns: 3, essential: true, default: true },
    'zscore': { name: 'Z-score', columns: 2, essential: true, default: true },
    'market_structure': { name: 'Market Structure', columns: 2, essential: true, default: true },
    'trend_strength': { name: '추세 강도 점수', columns: 1, essential: true, default: true },
    
    // 선택적 지표 (7개)
    'sma': { name: 'SMA', columns: 2, essential: false, default: false },
    'ema': { name: 'EMA', columns: 3, essential: false, default: false },
    'stoch': { name: '스토캐스틱', columns: 2, essential: false, default: false },
    'williams': { name: 'Williams %R', columns: 1, essential: false, default: false },
    'mfi': { name: 'MFI', columns: 1, essential: false, default: false },
    'vwap': { name: 'VWAP', columns: 1, essential: false, default: false },
    'volatility': { name: '변동성', columns: 1, essential: false, default: false },
    
    // 고급 지표 (5개)
    'keltner': { name: 'Keltner Channel', columns: 4, essential: false, default: false },
    'donchian': { name: 'Donchian Channel', columns: 4, essential: false, default: false },
    'vpoc': { name: 'VPOC', columns: 2, essential: false, default: false },
    'order_flow': { name: 'Order Flow', columns: 1, essential: false, default: false },
    'pivot': { name: 'Pivot Points', columns: 4, essential: false, default: false }
};

// ============================================================================
// 페이지 초기화
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 AI 모델 관리 페이지 초기화');
    
    // Bootstrap 툴팁 초기화 (개선된 설정)
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'hover',  // 마우스 호버시에만 표시
            delay: { show: 100, hide: 100 },  // 0.1초 딜레이
            html: true  // HTML 허용
        });
    });
    
    // 초기 데이터 로드
    initializeIndicators();
    loadModels();
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
    
    // 지표 카드 전체 클릭 이벤트 (개선된 버전)
    document.querySelectorAll('.indicator-card').forEach(card => {
        card.addEventListener('click', function(e) {
            // 체크박스 직접 클릭은 제외
            if (e.target.type !== 'checkbox' && !e.target.classList.contains('form-check-input')) {
                e.preventDefault();
                e.stopPropagation();
                
                const checkbox = this.querySelector('.indicator-checkbox');
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    const indicator = checkbox.dataset.indicator;
                    selectedIndicators[indicator] = checkbox.checked;
                    updateSelectedCounts();
                }
            }
        });
    });
    
    // 지표 체크박스 이벤트 리스너
    document.querySelectorAll('.indicator-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const indicator = this.dataset.indicator;
            selectedIndicators[indicator] = this.checked;
            updateSelectedCounts();
        });
    });
}

// ============================================================================
// 지표 초기화
// ============================================================================

function initializeIndicators() {
    // 모든 지표의 초기 상태 설정
    Object.entries(indicatorInfo).forEach(([key, info]) => {
        const checkbox = document.getElementById(`indicator_${key}`);
        if (checkbox) {
            // default 값에 따라 초기 체크 상태 설정
            if (info.default) {
                checkbox.checked = true;
                selectedIndicators[key] = true;
            } else {
                selectedIndicators[key] = checkbox.checked;
            }
        }
    });
    
    updateSelectedCounts();
}

function updateSelectedCounts() {
    // 각 섹션별로 선택된 개수 계산
    let essentialCount = 0;
    let optionalCount = 0;
    let advancedCount = 0;
    let totalCount = 0;
    
    // 핵심 지표 (essential: true)
    const essentialKeys = ['price', 'macd', 'rsi', 'bb', 'atr', 'volume', 'adx', 'aroon', 
                          'consecutive', 'trend', 'hhll', 'zscore', 'market_structure', 'trend_strength'];
    
    // 선택적 지표
    const optionalKeys = ['sma', 'ema', 'stoch', 'williams', 'mfi', 'vwap', 'volatility'];
    
    // 고급 지표
    const advancedKeys = ['keltner', 'donchian', 'vpoc', 'order_flow', 'pivot'];
    
    essentialKeys.forEach(key => {
        if (selectedIndicators[key]) essentialCount++;
    });
    
    optionalKeys.forEach(key => {
        if (selectedIndicators[key]) optionalCount++;
    });
    
    advancedKeys.forEach(key => {
        if (selectedIndicators[key]) advancedCount++;
    });
    
    totalCount = essentialCount + optionalCount + advancedCount;
    
    // UI 업데이트
    const essentialElement = document.getElementById('essentialIndicatorCount');
    if (essentialElement) {
        essentialElement.textContent = `${essentialCount}개 선택`;
        // 색상 변경
        if (essentialCount === 0) {
            essentialElement.className = 'badge bg-secondary float-end';
        } else if (essentialCount < 10) {
            essentialElement.className = 'badge bg-warning float-end';
        } else {
            essentialElement.className = 'badge bg-info float-end';
        }
    }
    
    const optionalElement = document.getElementById('optionalIndicatorCount');
    if (optionalElement) {
        optionalElement.textContent = `${optionalCount}개 선택`;
        // 색상 변경
        if (optionalCount === 0) {
            optionalElement.className = 'badge bg-secondary float-end';
        } else {
            optionalElement.className = 'badge bg-info float-end';
        }
    }
    
    const advancedElement = document.getElementById('advancedIndicatorCount');
    if (advancedElement) {
        advancedElement.textContent = `${advancedCount}개 선택`;
        // 색상 변경
        if (advancedCount === 0) {
            advancedElement.className = 'badge bg-secondary float-end';
        } else {
            advancedElement.className = 'badge bg-info float-end';
        }
    }
    
    const totalElement = document.getElementById('totalSelectedCount');
    if (totalElement) {
        totalElement.textContent = `${totalCount}개 선택`;
        // 색상 변경
        if (totalCount === 0) {
            totalElement.className = 'badge bg-secondary ms-2';
        } else if (totalCount < 10) {
            totalElement.className = 'badge bg-warning ms-2';
        } else {
            totalElement.className = 'badge bg-primary ms-2';
        }
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
            showAdvancedToast('error', '로드 실패', '모델 목록 로드 실패');
        }
    } catch (error) {
        console.error('모델 로드 오류:', error);
        showAdvancedToast('error', '오류 발생', '모델 목록 로드 중 오류 발생');
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
        const accuracy = model.accuracy ? (model.accuracy * 100).toFixed(1) : 'N/A';
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
    
    console.log('Storage info:', info);
}

async function activateModel(modelName) {
    showConfirm(
        '모델 활성화',
        `${modelName} 모델을 활성화하시겠습니까?`,
        async (confirmed) => {
            if (!confirmed) return;
            
            try {
                const response = await fetch('/api/ai/models/activate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({model_name: modelName})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAdvancedToast('success', '활성화 완료', '모델이 활성화되었습니다');
                    loadModels();
                } else {
                    showAdvancedToast('error', '활성화 실패', data.error || '모델 활성화 실패');
                }
            } catch (error) {
                console.error('모델 활성화 오류:', error);
                showAdvancedToast('error', '오류 발생', '모델 활성화 중 오류 발생');
            }
        }
    );
}

async function deleteModel(modelName) {
    showConfirm(
        '모델 삭제',
        `${modelName} 모델을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.`,
        async (confirmed) => {
            if (!confirmed) return;
            
            try {
                const response = await fetch(`/api/ai/models/${modelName}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAdvancedToast('success', '삭제 완료', '모델이 삭제되었습니다');
                    loadModels();
                } else {
                    showAdvancedToast('error', '삭제 실패', data.error || '모델 삭제 실패');
                }
            } catch (error) {
                console.error('모델 삭제 오류:', error);
                showAdvancedToast('error', '오류 발생', '모델 삭제 중 오류 발생');
            }
        }
    );
}

async function cleanupModels() {
    showConfirm(
        '모델 정리',
        '오래된 모델들을 정리하시겠습니까?\n최근 5개 모델만 보관됩니다.',
        async (confirmed) => {
            if (!confirmed) return;
            
            try {
                const response = await fetch('/api/ai/models/cleanup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({keep_count: 5})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showAdvancedToast('success', '정리 완료', `${data.data.deleted_count}개 모델이 정리되었습니다`);
                    loadModels();
                } else {
                    showAdvancedToast('error', '정리 실패', data.error || '모델 정리 실패');
                }
            } catch (error) {
                console.error('모델 정리 오류:', error);
                showAdvancedToast('error', '오류 발생', '모델 정리 중 오류 발생');
            }
        }
    );
}

// ============================================================================
// 학습 관리
// ============================================================================

async function startTraining() {
    if (isTraining) {
        showAdvancedToast('warning', '경고', '이미 학습이 진행 중입니다');
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
        showAdvancedToast('error', '유효성 검사 실패', errors.join('<br>'), 5000);
        return;
    }
    
    // 선택된 지표 확인
    const selectedCount = Object.values(selectedIndicators).filter(v => v).length;
    if (selectedCount === 0) {
        showAdvancedToast('error', '지표 선택 필요', '최소 하나 이상의 지표를 선택해주세요');
        return;
    }
    
    // 선택된 지표 정보 생성
    const selectedIndicatorNames = Object.entries(selectedIndicators)
        .filter(([key, value]) => value)
        .map(([key, value]) => indicatorInfo[key]?.name || key)
        .join(', ');
    
    showConfirm(
        'AI 학습 시작',
        `학습을 시작하시겠습니까?\n\n선택된 지표: ${selectedCount}개\n(${selectedIndicatorNames})\n\n에폭: ${trainingParams.epochs}\n학습 기간: ${trainingParams.training_days}일`,
        async (confirmed) => {
            if (!confirmed) return;
            
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
                    showAdvancedToast('success', '학습 시작', 'AI 모델 학습을 시작했습니다');
                    
                    // UI 업데이트
                    document.getElementById('startTrainingBtn').disabled = true;
                    document.getElementById('stopTrainingBtn').disabled = false;
                    document.getElementById('trainingStatus').textContent = '학습 중';
                    document.getElementById('trainingStatus').className = 'badge bg-primary';
                    document.getElementById('trainingProgress').style.display = 'block';
                    
                    // 상태 모니터링 시작
                    startStatusMonitoring();
                    
                } else {
                    showAdvancedToast('error', '학습 시작 실패', data.error || '학습 시작 실패');
                }
            } catch (error) {
                console.error('학습 시작 오류:', error);
                showAdvancedToast('error', '오류 발생', '학습 시작 중 오류 발생');
            }
        }
    );
}

async function stopTraining() {
    if (!isTraining) {
        return;
    }
    
    showConfirm(
        '학습 중지',
        '학습을 중지하시겠습니까?',
        async (confirmed) => {
            if (!confirmed) return;
            
            try {
                const response = await fetch('/api/ai/training/stop', {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    isTraining = false;
                    showAdvancedToast('info', '학습 중지', 'AI 모델 학습을 중지했습니다');
                    
                    // UI 업데이트
                    document.getElementById('startTrainingBtn').disabled = false;
                    document.getElementById('stopTrainingBtn').disabled = true;
                    document.getElementById('trainingStatus').textContent = '중지됨';
                    document.getElementById('trainingStatus').className = 'badge bg-warning';
                    
                    // 상태 모니터링 중지
                    stopStatusMonitoring();
                    
                } else {
                    showAdvancedToast('error', '중지 실패', data.error || '학습 중지 실패');
                }
            } catch (error) {
                console.error('학습 중지 오류:', error);
                showAdvancedToast('error', '오류 발생', '학습 중지 중 오류 발생');
            }
        }
    );
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
            
            // 완료/실패 알림
            if (statusBadge.textContent === '완료') {
                showAdvancedToast('success', '학습 완료', 'AI 모델 학습이 완료되었습니다!', 5000);
            } else {
                showAdvancedToast('error', '학습 실패', 'AI 모델 학습이 실패했습니다.', 5000);
            }
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
    showConfirm(
        '파라미터 초기화',
        '모든 파라미터를 기본값으로 복원하시겠습니까?',
        (confirmed) => {
            if (!confirmed) return;
            
            document.getElementById('trainingDays').value = 365;
            document.getElementById('epochs').value = 100;
            document.getElementById('batchSize').value = 32;
            document.getElementById('learningRate').value = 0.001;
            document.getElementById('sequenceLength').value = 60;
            document.getElementById('validationSplit').value = 20;
            
            showAdvancedToast('info', '초기화 완료', '파라미터가 기본값으로 복원되었습니다');
        }
    );
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
            showAdvancedToast('success', '설정 업데이트', '스케줄 설정이 업데이트되었습니다');
            
            // 다음 학습 시간 업데이트
            if (data.data.next_training) {
                const nextTime = new Date(data.data.next_training);
                document.getElementById('nextTraining').textContent = nextTime.toLocaleString('ko-KR');
            }
        } else {
            showAdvancedToast('error', '업데이트 실패', data.error || '스케줄 설정 업데이트 실패');
        }
    } catch (error) {
        console.error('스케줄 설정 업데이트 오류:', error);
        showAdvancedToast('error', '오류 발생', '스케줄 설정 업데이트 중 오류 발생');
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

// ============================================================================
// 디버그 함수 (개발용)
// ============================================================================

window.debugAI = {
    getSelectedIndicators: () => selectedIndicators,
    getIndicatorInfo: () => indicatorInfo,
    getTrainingParams: () => trainingParams,
    getTrainingStatus: () => isTraining,
    reloadAll: () => {
        loadModels();
        initializeIndicators();
        loadTrainingStatus();
        loadScheduleSettings();
    }
};

console.log('💡 디버그 명령어:');
console.log('   debugAI.getSelectedIndicators() - 선택된 지표 확인');
console.log('   debugAI.getIndicatorInfo() - 지표 정보 확인');
console.log('   debugAI.getTrainingParams() - 학습 파라미터 확인');
console.log('   debugAI.reloadAll() - 전체 데이터 새로고침');