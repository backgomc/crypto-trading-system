// 파일 경로: web/static/js/common.js
// 코드명: 공통 API 호출 및 유틸리티 함수 (AI 모델 스타일 토스트 추가)

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
        
        // ✅ 401 에러 처리 개선
        if (response.status === 401) {
            // HTML 응답일 수도 있으므로 안전하게 처리
            try {
                const result = await response.json();
                if (result.code === 'AUTH_REQUIRED' || result.code === 'SESSION_EXPIRED') {
                    showSessionExpiredModal();
                    return;
                }
            } catch (jsonError) {
                // JSON 파싱 실패 시에도 세션 만료로 처리
                showSessionExpiredModal();
                return;
            }
        }
        
        // ✅ JSON 응답 안전하게 파싱
        let result;
        try {
            result = await response.json();
        } catch (jsonError) {
            // JSON이 아닌 응답(HTML 등)인 경우
            throw new Error(`서버 응답 형식 오류 (HTTP ${response.status})`);
        }

        if (!response.ok) {
            throw new Error(result.error || `HTTP ${response.status}: 요청 처리 중 오류가 발생했습니다.`);
        }

        return result;
    } catch (error) {
        console.error('API 호출 오류:', error);
        showAdvancedToast('error', '오류', error.message || '네트워크 오류가 발생했습니다.');
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
// 고급 토스트 알림 시스템 (AI 모델 페이지 스타일)
// ============================================================================

function showAdvancedToast(type, title, message, duration = 3000) {
    // 토스트 컨테이너가 없으면 생성
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
        document.body.appendChild(container);
    }
    
    // 토스트 ID 생성
    const toastId = 'toast-' + Date.now();
    
    // 아이콘 설정
    const icons = {
        success: 'bi-check-circle-fill',
        error: 'bi-exclamation-triangle-fill',
        warning: 'bi-exclamation-circle-fill',
        info: 'bi-info-circle-fill'
    };
    
    // 현재 시간
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    
    // 토스트 HTML 생성
    const toastHtml = `
        <div id="${toastId}" class="toast toast-${type}" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="false">
            <div class="toast-header">
                <i class="bi ${icons[type]} me-2"></i>
                <strong class="me-auto">${title}</strong>
                <small>${timeStr}</small>
                <button type="button" class="btn-close btn-close-white" onclick="hideAdvancedToast('${toastId}')"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // 토스트 추가
    container.insertAdjacentHTML('beforeend', toastHtml);
    
    // Bootstrap 토스트 인스턴스 생성 및 표시
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // 자동 제거
    if (duration > 0) {
        setTimeout(() => {
            hideAdvancedToast(toastId);
        }, duration);
    }
}

function hideAdvancedToast(toastId) {
    const toastElement = document.getElementById(toastId);
    if (toastElement) {
        // 숨김 애니메이션 추가
        toastElement.classList.add('hiding');
        
        // 애니메이션 후 제거
        setTimeout(() => {
            const toast = bootstrap.Toast.getInstance(toastElement);
            if (toast) {
                toast.dispose();
            }
            toastElement.remove();
        }, 300);
    }
}

// ============================================================================
// 기존 토스트 함수 (하위 호환성) - 고급 토스트로 리다이렉트
// ============================================================================

function showToast(type, message, duration = 3000) {
    // 제목 자동 설정
    const titles = {
        success: '성공',
        error: '오류',
        warning: '경고',
        info: '정보'
    };
    
    showAdvancedToast(type, titles[type] || '알림', message, duration);
}

// ============================================================================
// 부트스트랩 모달 확인창
// ============================================================================

function showConfirm(title, message, callback) {
    // 모달이 없으면 생성
    if (!document.getElementById('confirmModal')) {
        createConfirmModal();
    }
    
    document.getElementById('confirmModalTitle').textContent = title;
    
    // 줄바꿈을 <br>로 변환하여 HTML로 삽입
    const modalBody = document.getElementById('confirmModalBody');
    modalBody.innerHTML = message.replace(/\n/g, '<br>');
    
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const okBtn = document.getElementById('confirmModalOk');
    
    // 기존 이벤트 제거 후 새로 추가
    okBtn.replaceWith(okBtn.cloneNode(true));
    document.getElementById('confirmModalOk').onclick = function() {
        modal.hide();
        callback(true);
    };
    
    modal.show();
}

function createConfirmModal() {
    const modalHtml = `
        <div class="modal fade" id="confirmModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content bg-dark">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-white" id="confirmModalTitle">확인</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-white" id="confirmModalBody">
                        정말 실행하시겠습니까?
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>
                        <button type="button" class="btn btn-primary" id="confirmModalOk">확인</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// ============================================================================
// 설정 관련 확인 모달 (settings.js에서 사용)
// ============================================================================

function confirmReset() {
    return new Promise((resolve) => {
        showConfirm(
            '설정 초기화',
            '모든 설정을 기본값으로 복원하시겠습니까?\n현재 설정은 모두 삭제됩니다.',
            (confirmed) => resolve(confirmed)
        );
    });
}

function confirmPreset(presetName) {
    return new Promise((resolve) => {
        showConfirm(
            '프리셋 적용',
            `${presetName} 설정을 적용하시겠습니까?\n현재 설정이 변경됩니다.`,
            (confirmed) => resolve(confirmed)
        );
    });
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
// 시간 업데이트 함수 (모든 페이지 공통)
// ============================================================================

function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    // ID가 currentTime인 span 요소만 업데이트 (아이콘 보존)
    const currentTimeSpan = document.getElementById('currentTime');
    if (currentTimeSpan) {
        currentTimeSpan.textContent = timeString;
    }
    
    // 기존 방식도 유지 (다른 페이지 호환성)
    const timeElements = document.querySelectorAll('.current-time');
    timeElements.forEach(el => {
        if (el && !el.querySelector('#currentTime')) {
            el.textContent = timeString;
        }
    });
}

// 시간 업데이트 자동 시작
function startTimeUpdates() {
    updateTime(); // 즉시 1회 실행
    setInterval(updateTime, 1000); // 1초마다 반복
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
        
        showAdvancedToast('success', '파일 다운로드', '파일이 다운로드되었습니다.');
        return true;
    } catch (error) {
        showAdvancedToast('error', '다운로드 실패', '파일 다운로드에 실패했습니다.');
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
                showAdvancedToast('success', '파일 업로드', '파일을 성공적으로 불러왔습니다.');
            } catch (error) {
                showAdvancedToast('error', '업로드 실패', '파일 형식이 올바르지 않습니다.');
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
    
    // 시간 업데이트 시작
    startTimeUpdates();
    
    // 전역 에러 핸들러
    window.addEventListener('error', function(e) {
        console.error('전역 오류:', e.error);
    });
    
    // API 상태 체크 (선택적)
    debugAPI();
});

// ============================================================================
// 세션 관리 함수들
// ============================================================================

/**
 * 세션 만료 모달 표시
 */
function showSessionExpiredModal() {
    // 세션 만료 모달이 없으면 생성
    if (!document.getElementById('sessionExpiredModal')) {
        createSessionExpiredModal();
    }
    
    const modal = new bootstrap.Modal(document.getElementById('sessionExpiredModal'), {
        backdrop: 'static',
        keyboard: false
    });
    modal.show();
}

function createSessionExpiredModal() {
    const modalHtml = `
        <div class="modal fade" id="sessionExpiredModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content bg-dark">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-white">
                            <i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>세션 만료
                        </h5>
                    </div>
                    <div class="modal-body text-white">
                        세션이 만료되었습니다. 다시 로그인해주세요.
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-primary" onclick="handleSessionExpired()">
                            로그인 페이지로 이동
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 세션 만료 확인 처리
 */
function handleSessionExpired() {
    window.location.href = '/login?message=session_expired';
}

/**
 * 중복 로그인 확인 모달 표시
 */
function showDuplicateLoginModal() {
    // 중복 로그인 모달이 없으면 생성
    if (!document.getElementById('duplicateLoginModal')) {
        createDuplicateLoginModal();
    }
    
    const modal = new bootstrap.Modal(document.getElementById('duplicateLoginModal'), {
        backdrop: 'static',
        keyboard: false
    });
    modal.show();
}

function createDuplicateLoginModal() {
    const modalHtml = `
        <div class="modal fade" id="duplicateLoginModal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content bg-dark">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-white">
                            <i class="bi bi-exclamation-circle-fill text-warning me-2"></i>중복 로그인 감지
                        </h5>
                    </div>
                    <div class="modal-body text-white">
                        다른 기기에서 이미 로그인된 상태입니다.
                        계속 진행하시면 다른 기기의 세션이 종료됩니다.
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-secondary" onclick="cancelLogin()">취소</button>
                        <button type="button" class="btn btn-primary" onclick="confirmLogin()">
                            강제 로그인
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 로그인 취소
 */
function cancelLogin() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('duplicateLoginModal'));
    modal.hide();
    // 로그인 폼 초기화
    const loginForm = document.querySelector('#loginForm');
    if (loginForm) {
        loginForm.reset();
    }
}

/**
 * 강제 로그인 확인
 */
function confirmLogin() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('duplicateLoginModal'));
    modal.hide();
    
    // 강제 로그인 플래그 설정 후 폼 제출
    const loginForm = document.querySelector('#loginForm');
    if (loginForm) {
        const forceInput = document.createElement('input');
        forceInput.type = 'hidden';
        forceInput.name = 'force_login';
        forceInput.value = 'true';
        loginForm.appendChild(forceInput);
        loginForm.submit();
    }
}