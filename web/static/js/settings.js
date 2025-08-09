// 파일 경로: web/static/js/settings.js
// 코드명: 설정 페이지 전용 로직 (Promise 기반 확인 모달)

// ============================================================================
// 전역 변수
// ============================================================================

let currentConfig = {};
let isLoading = false;

// ============================================================================
// 페이지 초기화
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🛠️ 설정 페이지 초기화 시작');
    
    loadConfig();
    initEventListeners();
    
    console.log('✅ 설정 페이지 초기화 완료');
});

// ============================================================================
// 설정 로드 및 저장
// ============================================================================

async function loadConfig() {
    try {
        showLoading(true);
        console.log('🔄 설정 로드 시작...');
        
        const result = await apiCall('/api/config');
        
        if (result.success && result.data && result.data.config) {
            currentConfig = result.data.config;
            console.log('✅ 설정 로드 성공:', currentConfig);
            
            populateForm(currentConfig);
            updateStatusDisplay();
        } else {
            throw new Error('설정 데이터 형식이 올바르지 않습니다.');
        }
        
    } catch (error) {
        console.error('❌ 설정 로드 실패:', error);
        showAdvancedToast('error', '로드 실패', '설정을 불러오는데 실패했습니다: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function saveSettings() {
    if (isLoading) return;

    try {
        if (!validateForm()) {
            return;
        }

        showLoading(true);
        console.log('💾 설정 저장 시작...');
        
        const formData = collectFormData();
        const result = await apiCall('/api/config', 'PUT', formData);
        
        if (result.success) {
            currentConfig = result.data.config;
            updateStatusDisplay();
            showAdvancedToast('success', '저장 완료', result.message || '설정이 성공적으로 저장되었습니다.');
            console.log('✅ 설정 저장 완료');
        } else {
            throw new Error(result.error || '설정 저장에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('❌ 설정 저장 실패:', error);
        showAdvancedToast('error', '저장 실패', '설정 저장 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function resetSettings() {
    if (isLoading) return;

    // Promise 기반 확인 모달
    const confirmed = await confirmReset();
    if (!confirmed) {
        return;
    }

    try {
        showLoading(true);
        console.log('🔄 설정 초기화 시작...');
        
        const result = await apiCall('/api/config/reset', 'POST');
        
        if (result.success) {
            currentConfig = result.data.config;
            populateForm(currentConfig);
            updateStatusDisplay();
            showAdvancedToast('success', '초기화 완료', result.message || '모든 설정이 기본값으로 복원되었습니다.');
            console.log('✅ 설정 초기화 완료');
        } else {
            throw new Error(result.error || '설정 초기화에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('❌ 설정 초기화 실패:', error);
        showAdvancedToast('error', '초기화 실패', '설정 초기화 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// ============================================================================
// 프리셋 관리
// ============================================================================

async function applyPreset(presetType) {
    if (isLoading) return;

    const presetNames = {
        conservative: '보수적',
        balanced: '균형',
        aggressive: '공격적'
    };

    // Promise 기반 확인 모달
    const confirmed = await confirmPreset(presetNames[presetType]);
    if (!confirmed) {
        return;
    }

    try {
        showLoading(true);
        console.log(`🎯 ${presetType} 프리셋 적용 시작...`);
        
        const result = await apiCall(`/api/config/preset/${presetType}`, 'POST');
        
        if (result.success) {
            currentConfig = result.data.config;
            populateForm(currentConfig);
            updateStatusDisplay();
            showAdvancedToast('success', '프리셋 적용', result.message || `${presetNames[presetType]} 설정이 적용되었습니다.`);
            console.log(`✅ ${presetType} 프리셋 적용 완료`);
        } else {
            throw new Error(result.error || '프리셋 적용에 실패했습니다.');
        }
        
    } catch (error) {
        console.error(`❌ ${presetType} 프리셋 적용 실패:`, error);
        showAdvancedToast('error', '프리셋 실패', '프리셋 적용 실패: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// ============================================================================
// 폼 데이터 처리
// ============================================================================

function populateForm(config) {
    console.log('📝 폼 데이터 적용 시작:', config);
    
    // 매매 설정 (trading)
    if (config.trading) {
        const t = config.trading;
        setElementValue('demo_mode', String(t.demo_mode !== false));
        setElementValue('virtual_balance', t.virtual_balance || 10000);
        setElementValue('initial_position_size', t.initial_position_size || 0.05);
        setElementValue('adjustment_size', t.adjustment_size || 0.01);
        setElementValue('base_threshold', t.base_threshold || 1000);
        setElementValue('consecutive_threshold', t.consecutive_threshold || 4);
        setElementValue('adaptive_threshold_enabled', t.adaptive_threshold_enabled !== false);
        setElementValue('volatility_window', t.volatility_window || 20);
        setElementValue('loop_delay', t.loop_delay || 60);
    }

    // AI 설정 (ai)
    if (config.ai) {
        const a = config.ai;
        setElementValue('ai_enabled', a.enabled !== false);
        setElementValue('main_interval', a.main_interval || '15');
        setElementValue('training_days', a.training_days || 365);
        setElementValue('retrain_interval_days', a.retrain_interval_days || 14);
    }

    // 리스크 설정 (risk)
    if (config.risk) {
        const r = config.risk;
        setElementValue('max_loss_percent', r.max_loss_percent || 5.0);
        setElementValue('daily_trade_limit', r.daily_trade_limit || 10);
        setElementValue('max_position_size', r.max_position_size || 0.5);
        setElementValue('emergency_stop_enabled', r.emergency_stop_enabled !== false);
        setElementValue('consecutive_loss_limit', r.consecutive_loss_limit || 3);
        setElementValue('cooldown_minutes', r.cooldown_minutes || 30);
    }

    // 알림 설정 (notifications)
    if (config.notifications) {
        const n = config.notifications;
        setElementValue('telegram_enabled', n.telegram_enabled !== false);
        setElementValue('email_enabled', n.email_enabled || false);
        setElementValue('frequency', n.frequency || 'all');
        setElementValue('profit_threshold_krw', n.profit_threshold_krw || 1000);
    }
    
    console.log('✅ 폼 데이터 적용 완료');
}

function collectFormData() {
    const formData = {
        config: {
            trading: {
                demo_mode: getElementValue('demo_mode') === 'true',
                virtual_balance: getElementValue('virtual_balance'),
                symbol: "BTCUSDT",
                initial_position_size: getElementValue('initial_position_size'),
                adjustment_size: getElementValue('adjustment_size'),
                base_threshold: getElementValue('base_threshold'),
                consecutive_threshold: getElementValue('consecutive_threshold'),
                adaptive_threshold_enabled: getElementValue('adaptive_threshold_enabled'),
                volatility_window: getElementValue('volatility_window'),
                loop_delay: getElementValue('loop_delay')
            },
            ai: {
                enabled: getElementValue('ai_enabled'),
                main_interval: getElementValue('main_interval'),
                training_days: getElementValue('training_days'),
                retrain_interval_days: getElementValue('retrain_interval_days'),
                timeframes: ["1", "5", "15", "60"]
            },
            risk: {
                max_loss_percent: getElementValue('max_loss_percent'),
                daily_trade_limit: getElementValue('daily_trade_limit'),
                max_position_size: getElementValue('max_position_size'),
                emergency_stop_enabled: getElementValue('emergency_stop_enabled'),
                consecutive_loss_limit: getElementValue('consecutive_loss_limit'),
                cooldown_minutes: getElementValue('cooldown_minutes')
            },
            notifications: {
                telegram_enabled: getElementValue('telegram_enabled'),
                email_enabled: getElementValue('email_enabled'),
                frequency: getElementValue('frequency'),
                profit_threshold_krw: getElementValue('profit_threshold_krw')
            }
        }
    };
    
    console.log('📊 수집된 폼 데이터:', formData);
    return formData;
}

// ============================================================================
// 유효성 검사
// ============================================================================

function validateForm() {
    const errors = [];

    // 필수 필드 검사
    const requiredFields = [
        'virtual_balance', 'initial_position_size', 'adjustment_size',
        'base_threshold', 'consecutive_threshold', 'volatility_window', 'loop_delay',
        'training_days', 'retrain_interval_days',
        'max_loss_percent', 'daily_trade_limit', 'max_position_size',
        'consecutive_loss_limit', 'cooldown_minutes', 'profit_threshold_krw'
    ];

    for (const fieldId of requiredFields) {
        const element = document.getElementById(fieldId);
        if (!element || !element.value || isNaN(parseFloat(element.value))) {
            const label = element ? element.closest('.col-md-6, .col-md-12')?.querySelector('label')?.textContent || fieldId : fieldId;
            errors.push(`${label}은(는) 필수 입력값입니다.`);
        }
    }

    // 범위 검사
    const rangeChecks = [
        { id: 'virtual_balance', min: 1000, max: 1000000, name: '가상 잔고' },
        { id: 'initial_position_size', min: 0.001, max: 1, name: '초기 포지션 크기' },
        { id: 'adjustment_size', min: 0.001, max: 0.1, name: '조정 크기' },
        { id: 'base_threshold', min: 100, max: 10000, name: '기본 임계값' },
        { id: 'consecutive_threshold', min: 2, max: 10, name: '연속 신호 기준' },
        { id: 'volatility_window', min: 5, max: 100, name: '변동성 윈도우' },
        { id: 'loop_delay', min: 10, max: 300, name: '루프 간격' },
        { id: 'training_days', min: 30, max: 1095, name: 'AI 학습 기간' },
        { id: 'retrain_interval_days', min: 1, max: 30, name: '모델 재훈련 간격' },
        { id: 'max_loss_percent', min: 1.0, max: 20.0, name: '최대 손실 한도' },
        { id: 'daily_trade_limit', min: 1, max: 100, name: '일일 거래 한도' },
        { id: 'max_position_size', min: 0.01, max: 2.0, name: '포지션 크기 상한' },
        { id: 'consecutive_loss_limit', min: 2, max: 10, name: '연속 손실 제한' },
        { id: 'cooldown_minutes', min: 5, max: 120, name: '쿨다운 시간' },
        { id: 'profit_threshold_krw', min: 100, max: 100000, name: '수익 알림 기준' }
    ];

    for (const check of rangeChecks) {
        const element = document.getElementById(check.id);
        if (element && element.value) {
            const value = parseFloat(element.value);
            if (value < check.min || value > check.max) {
                errors.push(`${check.name}은(는) ${check.min}~${check.max} 범위 내에서 입력해주세요.`);
            }
        }
    }

    if (errors.length > 0) {
        showAdvancedToast('error', '유효성 검사 실패', errors.join('<br>'), 5000);
        return false;
    }

    return true;
}

// ============================================================================
// 상태 관리
// ============================================================================

function updateStatusDisplay() {
    const configStatus = document.getElementById('configStatus');
    const lastSaved = document.getElementById('lastSaved');
    
    if (configStatus) {
        configStatus.textContent = '저장됨';
        configStatus.className = 'badge bg-success';
    }
    
    if (lastSaved) {
        lastSaved.textContent = formatTime();
    }
}

function markAsChanged() {
    const configStatus = document.getElementById('configStatus');
    if (configStatus) {
        configStatus.textContent = '변경됨';
        configStatus.className = 'badge bg-warning';
    }
}

// ============================================================================
// 이벤트 리스너
// ============================================================================

function initEventListeners() {
    // 실시간 유효성 검사
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateNumberField(this);
        });
    });

    // 설정 변경 감지
    const formElements = document.querySelectorAll('input, select');
    formElements.forEach(element => {
        element.addEventListener('change', markAsChanged);
    });

    // 키보드 단축키 (Ctrl+S로 저장)
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            saveSettings();
        }
    });

    // 페이지 이탈 시 경고
    window.addEventListener('beforeunload', function(e) {
        const configStatus = document.getElementById('configStatus');
        if (configStatus && configStatus.textContent === '변경됨') {
            e.preventDefault();
            e.returnValue = '저장하지 않은 설정 변경사항이 있습니다. 페이지를 떠나시겠습니까?';
        }
    });
}

// ============================================================================
// 가져오기/내보내기
// ============================================================================

function exportSettings() {
    const formData = collectFormData();
    const filename = `nhbot_settings_${new Date().toISOString().slice(0, 10)}.json`;
    downloadJSON(formData.config, filename);
}

function importSettings() {
    uploadJSON(function(settings) {
        populateForm(settings);
        markAsChanged();
        showAdvancedToast('info', '설정 가져오기', '설정을 가져왔습니다. 저장 버튼을 눌러 적용하세요.');
    });
}

// ============================================================================
// 디버그 함수들
// ============================================================================

function showDebugInfo() {
    debugLog('현재 설정', currentConfig);
    debugLog('폼 데이터', collectFormData());
    debugLog('로딩 상태', isLoading);
}

// 전역 함수로 노출 (개발용)
window.debugSettings = showDebugInfo;
window.exportSettings = exportSettings;
window.importSettings = importSettings;

console.log('🚀 Settings.js 로드 완료');