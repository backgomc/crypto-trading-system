// 파일 경로: web/static/js/common.js
// 코드명: 공통 API 호출 및 유틸리티 함수

// ============================================================================
// API 호출 함수
// ============================================================================

async function apiCall(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || `HTTP ${response.status}: 요청 처리 중 오류가 발생했습니다.`);
        }

        return result;
    } catch (error) {
        console.error('API 호출 오류:', error);
        showToast('error', error.message || '네트워크 오류가 발생했습니다.');
        throw error;
    }
}

// ============================================================================
// 로딩 및 UI 상태 관리
// ============================================================================

function showLoading(show, overlayId = 'loadingOverlay') {
    const overlay = document.getElementById(overlayId);
    if (overlay) {
        if (show) {
            overlay.classList.remove('d-none');
        } else {
            overlay.classList.add('d-none');
        }
    }
    
    // 버튼 비활성화/활성화
    const buttons = document.querySelectorAll('button[onclick]');
    buttons.forEach(btn => {
        btn.disabled = show;
    });
}

// ============================================================================
// 토스트 알림 시스템
// ============================================================================

function showToast(type, message, duration = 3000) {
    const container = document.getElementById('alertContainer') || createAlertContainer();
    const alertClass = type === 'error' ? 'alert-danger' : 'alert-success';
    const iconClass = type === 'error' ? 'bi-exclamation-triangle' : 'bi-check-circle';
    
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="bi ${iconClass} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    container.innerHTML = alertHtml;
    
    if (duration > 0) {
        setTimeout(() => {
            const alert = container.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, duration);
    }
}

function createAlertContainer() {
    const container = document.createElement('div');
    container.id = 'alertContainer';
    container.style.position = 'fixed';
    container.style.top = '20px';
    container.style.right = '20px';
    container.style.zIndex = '9999';
    container.style.maxWidth = '400px';
    document.body.appendChild(container);
    return container;
}

// ============================================================================
// 폼 유틸리티 함수들
// ============================================================================

function setElementValue(id, value) {
    const element = document.getElementById(id);
    if (!element) {
        console.warn(`⚠️ 요소를 찾을 수 없습니다: ${id}`);
        return;
    }

    if (element.type === 'checkbox') {
        element.checked = Boolean(value);
    } else if (element.type === 'select-one') {
        element.value = String(value);
    } else {
        element.value = value;
    }
}

function getElementValue(id) {
    const element = document.getElementById(id);
    if (!element) {
        console.warn(`⚠️ 요소를 찾을 수 없습니다: ${id}`);
        return null;
    }

    if (element.type === 'checkbox') {
        return element.checked;
    } else if (element.type === 'number') {
        return parseFloat(element.value) || 0;
    } else {
        return element.value;
    }
}

// ============================================================================
// 유효성 검사 함수들
// ============================================================================

function validateNumberField(input) {
    const min = parseFloat(input.min);
    const max = parseFloat(input.max);
    const value = parseFloat(input.value);
    
    if (input.value && (value < min || value > max)) {
        input.classList.add('is-invalid');
        
        // 기존 에러 메시지 제거
        const existingError = input.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
        
        // 에러 메시지 추가
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = `${min}~${max} 범위 내에서 입력해주세요.`;
        input.parentNode.appendChild(errorDiv);
        return false;
    } else {
        input.classList.remove('is-invalid');
        const errorDiv = input.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
        return true;
    }
}

function validateAllNumberFields() {
    const numberInputs = document.querySelectorAll('input[type="number"]');
    let allValid = true;
    
    numberInputs.forEach(input => {
        if (!validateNumberField(input)) {
            allValid = false;
        }
    });
    
    return allValid;
}

// ============================================================================
// 확인 대화상자 함수들
// ============================================================================

function confirmAction(message, title = '확인') {
    return confirm(`${title}\n\n${message}`);
}

function confirmReset() {
    return confirmAction(
        '모든 설정을 기본값으로 복원하시겠습니까?\n현재 설정은 모두 삭제됩니다.',
        '설정 초기화'
    );
}

function confirmPreset(presetName) {
    return confirmAction(
        `${presetName} 설정을 적용하시겠습니까?\n현재 설정이 변경됩니다.`,
        '프리셋 적용'
    );
}

// ============================================================================
// 시간 포맷팅 함수들
// ============================================================================

function formatDateTime(date = new Date()) {
    return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatTime(date = new Date()) {
    return date.toLocaleString('ko-KR', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ============================================================================
// 파일 다운로드 함수들
// ============================================================================

function downloadJSON(data, filename) {
    try {
        const dataStr = JSON.stringify(data, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = filename;
        link.click();
        
        showToast('success', '파일이 다운로드되었습니다.');
        return true;
    } catch (error) {
        showToast('error', '파일 다운로드에 실패했습니다.');
        return false;
    }
}

function uploadJSON(callback) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                callback(data);
                showToast('success', '파일을 성공적으로 불러왔습니다.');
            } catch (error) {
                showToast('error', '파일 형식이 올바르지 않습니다.');
            }
        };
        reader.readAsText(file);
    };
    
    input.click();
}

// ============================================================================
// 디버그 함수들
// ============================================================================

function debugLog(title, data) {
    console.log(`🔍 ${title}:`, data);
}

function debugAPI() {
    console.log('🌐 API 상태:');
    console.log('  - 기본 URL:', window.location.origin);
    console.log('  - 현재 페이지:', window.location.pathname);
}

// ============================================================================
// 전역 초기화
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Common.js 로드 완료');
    
    // 전역 에러 핸들러
    window.addEventListener('error', function(e) {
        console.error('전역 오류:', e.error);
    });
    
    // API 상태 체크 (선택적)
    debugAPI();
});