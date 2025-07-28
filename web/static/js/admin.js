// 파일 경로: web/static/js/admin.js
// 코드명: 관리자 페이지 JavaScript 로직

// 전역 변수
let isLoading = false;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 관리자 페이지 로드 완료');
    
    // 실시간 시간 업데이트
    updateTime();
    setInterval(updateTime, 1000);
    
    // 페이지 로드 애니메이션
    animateCards();
});

// API 호출 헬퍼 함수
async function apiCall(url, method = 'GET', data = null) {
    if (isLoading) return null;
    
    isLoading = true;
    showLoading(true);
    
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
            throw new Error(result.error || '요청 처리 중 오류가 발생했습니다.');
        }

        return result;
        
    } catch (error) {
        console.error('API 호출 오류:', error);
        showToast('error', error.message || '네트워크 오류가 발생했습니다.');
        return null;
        
    } finally {
        isLoading = false;
        showLoading(false);
    }
}

// 로딩 상태 표시
function showLoading(show) {
    // 전체 화면 로딩 오버레이는 common.js에서 구현 예정
    const buttons = document.querySelectorAll('button');
    buttons.forEach(btn => {
        btn.disabled = show;
    });
}

// 토스트 알림 (common.js와 동일)
function showToast(type, message) {
    // 임시 alert (나중에 토스트로 교체)
    const icon = type === 'error' ? '❌' : '✅';
    alert(`${icon} ${message}`);
}

// 시간 업데이트
function updateTime() {
    const now = new Date();
    const timeElements = document.querySelectorAll('.current-time');
    const timeString = now.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    
    timeElements.forEach(el => {
        if (el) el.textContent = timeString;
    });
}

// 카드 애니메이션
function animateCards() {
    const cards = document.querySelectorAll('.stats-card, .main-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.6s ease-out';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// ============================================================================
// 사용자 관리 함수들
// ============================================================================

// 사용자 목록 새로고침
async function refreshUsers() {
    showToast('info', '사용자 목록을 새로고침합니다...');
    
    // 페이지 새로고침 (임시)
    setTimeout(() => {
        location.reload();
    }, 500);
}

// 새 사용자 추가
async function addUser() {
    const username = prompt('새 사용자명을 입력하세요:');
    if (!username) return;
    
    const password = prompt('초기 비밀번호를 입력하세요:');
    if (!password) return;
    
    const email = prompt('이메일 주소를 입력하세요 (선택):');
    const isAdmin = confirm('관리자 권한을 부여하시겠습니까?');
    
    const data = {
        username: username.trim(),
        password: password,
        email: email?.trim() || '',
        is_admin: isAdmin
    };
    
    const result = await apiCall('/api/admin/user', 'POST', data);
    if (result) {
        showToast('success', result.message);
        setTimeout(() => location.reload(), 1000);
    }
}

// 사용자 편집
function editUser(userId, username, isActive, isAdmin) {
    // 모달 필드 채우기
    document.getElementById('editUserId').value = userId;
    document.getElementById('editUsername').value = username;
    document.getElementById('editIsActive').checked = isActive;
    document.getElementById('editIsAdmin').checked = isAdmin;
    
    // 모달 열기
    const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
    modal.show();
}

// 사용자 변경사항 저장
async function saveUserChanges() {
    const userId = document.getElementById('editUserId').value;
    const isActive = document.getElementById('editIsActive').checked;
    const isAdmin = document.getElementById('editIsAdmin').checked;
    
    const data = {
        is_active: isActive,
        is_admin: isAdmin
    };
    
    const result = await apiCall(`/api/admin/user/${userId}`, 'PUT', data);
    if (result) {
        showToast('success', result.message);
        
        // 모달 닫기
        const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
        modal.hide();
        
        setTimeout(() => location.reload(), 1000);
    }
}

// 비밀번호 리셋
function resetPassword(userId, username) {
    // 모달 필드 채우기
    document.getElementById('resetUserId').value = userId;
    document.getElementById('resetUsername').value = username;
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
    
    // 모달 열기
    const modal = new bootstrap.Modal(document.getElementById('resetPasswordModal'));
    modal.show();
}

// 비밀번호 리셋 저장
async function savePasswordReset() {
    const userId = document.getElementById('resetUserId').value;
    const username = document.getElementById('resetUsername').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // 유효성 검사
    if (!newPassword) {
        showToast('error', '새 비밀번호를 입력하세요.');
        return;
    }
    
    if (newPassword.length < 6) {
        showToast('error', '비밀번호는 최소 6자 이상이어야 합니다.');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showToast('error', '비밀번호가 일치하지 않습니다.');
        return;
    }
    
    if (!confirm(`사용자 '${username}'의 비밀번호를 변경하시겠습니까?`)) {
        return;
    }
    
    const data = {
        new_password: newPassword
    };
    
    const result = await apiCall(`/api/admin/user/${userId}/password`, 'PUT', data);
    if (result) {
        showToast('success', result.message);
        
        // 모달 닫기
        const modal = bootstrap.Modal.getInstance(document.getElementById('resetPasswordModal'));
        modal.hide();
    }
}

// 사용자 삭제
async function deleteUser(userId, username) {
    if (!confirm(`정말로 사용자 '${username}'을(를) 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
        return;
    }
    
    const doubleConfirm = prompt(`확인을 위해 사용자명 '${username}'을 입력하세요:`);
    if (doubleConfirm !== username) {
        showToast('error', '사용자명이 일치하지 않습니다.');
        return;
    }
    
    const result = await apiCall(`/api/admin/user/${userId}`, 'DELETE');
    if (result) {
        showToast('success', result.message);
        setTimeout(() => location.reload(), 1000);
    }
}

// ============================================================================
// 시스템 관리 함수들
// ============================================================================

// 설정 변경 내역 보기
async function viewConfigChange(configId) {
    const result = await apiCall(`/api/admin/config/${configId}`);
    if (result) {
        const data = result.data;
        const details = `
설정 키: ${data.config_key}
사용자: ${data.username} (ID: ${data.user_id})
변경 시간: ${new Date(data.changed_at).toLocaleString('ko-KR')}
IP 주소: ${data.ip_address || 'N/A'}

이전 값:
${data.old_value || '(없음)'}

새 값:
${data.new_value || '(없음)'}
        `;
        alert(details);
    }
}

// 시스템 로그 정리
async function clearLogs() {
    if (!confirm('시스템 로그를 정리하시겠습니까?\n\n30일 이전의 로그가 삭제됩니다.')) {
        return;
    }
    
    const result = await apiCall('/api/admin/logs', 'DELETE');
    if (result) {
        showToast('success', result.message);
        setTimeout(() => location.reload(), 1500);
    }
}

// ============================================================================
// 모달 이벤트 핸들러
// ============================================================================

// 비밀번호 확인 실시간 체크
document.addEventListener('DOMContentLoaded', function() {
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    
    function checkPasswordMatch() {
        if (!newPasswordInput || !confirmPasswordInput) return;
        
        const newPassword = newPasswordInput.value;
        const confirmPassword = confirmPasswordInput.value;
        
        if (confirmPassword && newPassword !== confirmPassword) {
            confirmPasswordInput.classList.add('is-invalid');
        } else {
            confirmPasswordInput.classList.remove('is-invalid');
        }
    }
    
    if (newPasswordInput) newPasswordInput.addEventListener('input', checkPasswordMatch);
    if (confirmPasswordInput) confirmPasswordInput.addEventListener('input', checkPasswordMatch);
});

// Enter 키 이벤트 처리
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        // 비밀번호 리셋 모달에서 Enter
        if (document.getElementById('resetPasswordModal').classList.contains('show')) {
            e.preventDefault();
            savePasswordReset();
        }
        // 사용자 편집 모달에서 Enter
        else if (document.getElementById('editUserModal').classList.contains('show')) {
            e.preventDefault();
            saveUserChanges();
        }
    }
});

// ============================================================================
// 디버그 및 개발자 도구
// ============================================================================

// 콘솔 명령어
window.adminDebug = {
    // 현재 세션 정보
    getSession: () => {
        console.log('현재 세션:', {
            username: '{{ session.get("username") }}',
            user_id: '{{ session.get("user_id") }}',
            is_admin: '{{ session.get("is_admin") }}'
        });
    },
    
    // 통계 정보
    getStats: () => {
        const stats = document.querySelectorAll('.stats-card h3');
        console.log('시스템 통계:', {
            total_users: stats[0]?.textContent,
            active_users: stats[1]?.textContent,
            admin_users: stats[2]?.textContent,
            inactive_users: stats[3]?.textContent
        });
    },
    
    // 테스트 함수들
    testAPI: async () => {
        console.log('API 테스트 실행...');
        const result = await apiCall('/api/status');
        console.log('API 응답:', result);
    }
};

console.log('🛠️ 관리자 페이지 개발자 도구 로드 완료');
console.log('💡 사용 가능한 명령어:');
console.log('   - adminDebug.getSession(): 현재 세션 정보');
console.log('   - adminDebug.getStats(): 시스템 통계');
console.log('   - adminDebug.testAPI(): API 연결 테스트');