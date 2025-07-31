// 파일 경로: web/static/js/admin.js
// 코드명: 관리자 페이지 JavaScript 로직 (모든 문제점 완전 수정)

// 전역 변수
let isLoading = false;
let allUsers = [];
let currentUserId = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 관리자 페이지 로드 완료');
    
    // 현재 사용자 ID 가져오기 (먼저 실행)
    getCurrentUserId().then(() => {
        // 현재 사용자 로그인 시간 즉시 갱신
        updateCurrentUserLoginTime();
        // 실시간 데이터 로드
        loadAllData();
    });
    
    // 실시간 시간 업데이트
    updateTime();
    setInterval(updateTime, 1000);
    
    // 페이지 로드 애니메이션
    animateCards();
    
    // 비밀번호 실시간 체크 설정
    setupPasswordValidation();
    
    // 10초마다 통계 자동 새로고침 (접속자 수 실시간 반영)
    setInterval(loadStats, 10000);
});

// 현재 사용자 로그인 시간 갱신
async function updateCurrentUserLoginTime() {
    try {
        // 현재 사용자의 로그인 시간을 갱신하여 접속중으로 표시
        await fetch('/api/status', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
    } catch (error) {
        console.log('로그인 시간 갱신 실패:', error);
    }
}

// 현재 사용자 ID 가져오기 (수정)
async function getCurrentUserId() {
    try {
        const response = await fetch('/api/status');
        const result = await response.json();
        
        if (result.user_id) {
            currentUserId = parseInt(result.user_id);
        } else {
            // session에서 직접 가져오기 시도
            currentUserId = parseInt(document.body.dataset.userId) || null;
        }
        
        console.log('현재 사용자 ID:', currentUserId);
    } catch (error) {
        console.error('현재 사용자 ID 조회 실패:', error);
    }
}

// 모든 데이터 로드
async function loadAllData() {
    try {
        await loadStats();
        await loadUsers();
        await loadRecentLogs();
    } catch (error) {
        console.error('데이터 로드 오류:', error);
        showToast('error', '데이터 로드 중 오류가 발생했습니다.');
    }
}

// 통계 데이터 로드
async function loadStats() {
    const result = await apiCall('/api/admin/stats');
    if (result && result.data) {
        displayStats(result.data);
    }
}

// 사용자 목록 로드
async function loadUsers() {
    const result = await apiCall('/api/admin/users');
    if (result && result.data) {
        allUsers = result.data.users || result.data;
        displayUsers(allUsers);
    }
}

// 최근 로그 로드
async function loadRecentLogs() {
    const result = await apiCall('/api/admin/logs/recent');
    if (result && result.data) {
        displayRecentLogs(result.data);
    }
}

// 통계 표시 (수정: 비활성 사용자로 변경)
function displayStats(stats) {
    const elements = {
        total: document.querySelector('.stats-card:nth-child(1) h3'),   // 전체 사용자
        active: document.querySelector('.stats-card:nth-child(2) h3'),  // 활성 사용자
        inactive: document.querySelector('.stats-card:nth-child(3) h3'),// 비활성 사용자
        online: document.querySelector('.stats-card:nth-child(4) h3')   // 현재 접속자 수 ✅ 여기가 핵심!
    };

    if (elements.total) elements.total.textContent = stats.users?.total || 0;
    if (elements.active) elements.active.textContent = stats.users?.active || 0;
    if (elements.inactive) elements.inactive.textContent = stats.users?.inactive || 0;
    if (elements.online) elements.online.textContent = stats.users?.online || 0; // ✅ 실시간 반영
}

// 사용자 목록 표시 (수정: 로그인 시간 한국시간 표시, 삭제 버튼 수정)
function displayUsers(users) {
    const tbody = document.querySelector('#usersTable tbody');
    if (!tbody) return;
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">사용자 데이터가 없습니다.</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => {
        const isOnline = user.is_online || false;
        const lastLoginText = user.last_login ? 
            formatKoreanDateTime(user.last_login) : '로그인 기록 없음';
        
        // 정확한 타입 비교
        const isCurrentUser = parseInt(user.id) === parseInt(currentUserId);
        
        return `
        <tr>
            <td>
                <strong>${user.username}</strong>
                ${isCurrentUser ? '<span class="badge bg-info ms-1">나</span>' : ''}
                ${user.email ? `<br><small class="text-muted">${user.email}</small>` : ''}
            </td>
            <td>
                <span class="badge ${user.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${user.is_active ? '활성' : '비활성'}
                </span>
            </td>
            <td>
                <span class="badge ${user.is_admin ? 'bg-warning text-dark' : 'bg-light text-dark'}">
                    ${user.is_admin ? '관리자' : '일반'}
                </span>
            </td>
            <td>
                <span class="badge ${isOnline ? 'bg-success' : 'bg-secondary'}">
                    <i class="bi bi-circle-fill me-1" style="font-size: 0.6rem;"></i>
                    ${isOnline ? '접속중' : '오프라인'}
                </span>
            </td>
            <td>
                <small class="text-muted">${lastLoginText}</small>
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editUser(${user.id})" title="편집">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-warning" onclick="resetPassword(${user.id}, '${user.username}')" title="비밀번호 리셋">
                        <i class="bi bi-key"></i>
                    </button>
                    ${(!isCurrentUser && !user.is_admin) ? `
                    <button class="btn btn-outline-danger" onclick="deleteUser(${user.id}, '${user.username}')" title="삭제">
                        <i class="bi bi-trash"></i>
                    </button>
                    ` : ''}
                </div>
            </td>
        </tr>
        `;
    }).join('');
}

// 최근 로그 표시 (사용자명으로 표시)
function displayRecentLogs(logs) {
    const tbody = document.querySelector('#logsTable tbody');
    if (!tbody) return;
    
    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">로그 데이터가 없습니다.</td></tr>';
        return;
    }
    
    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>
                <span class="badge ${getBadgeClass(log.level)}">
                    ${log.level}
                </span>
            </td>
            <td>
                <small class="text-muted">${log.category}</small>
            </td>
            <td>${log.message}</td>
            <td>
                <small class="text-muted">
                    ${formatKoreanDateTime(log.timestamp)}
                </small>
            </td>
        </tr>
    `).join('');
}

// 한국시간 포맷 함수 (수정)
function formatKoreanDateTime(dateString) {
    if (!dateString) return '없음';
    
    try {
        const date = new Date(dateString);
        
        // UTC 시간을 한국시간(UTC+9)으로 변환
        const koreanDate = new Date(date.getTime() + (9 * 60 * 60 * 1000));
        
        // 대시보드와 동일한 형식으로 표시
        return koreanDate.toLocaleString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (error) {
        return '날짜 오류';
    }
}

// 로그 레벨별 배지 클래스
function getBadgeClass(level) {
    switch (level) {
        case 'ERROR': return 'bg-danger';
        case 'WARNING': return 'bg-warning text-dark';
        case 'INFO': return 'bg-info';
        default: return 'bg-secondary';
    }
}

// API 호출 헬퍼 함수
async function apiCall(url, method = 'GET', data = null) {
    if (isLoading && method !== 'GET') return null;
    
    if (method !== 'GET') {
        isLoading = true;
        showLoading(true);
    }
    
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
        if (method !== 'GET') {
            isLoading = false;
            showLoading(false);
        }
    }
}

// 로딩 상태 표시
function showLoading(show) {
    const buttons = document.querySelectorAll('button:not(.btn-close)');
    buttons.forEach(btn => {
        if (show) {
            btn.disabled = true;
            btn.style.opacity = '0.6';
        } else {
            btn.disabled = false;
            btn.style.opacity = '1';
        }
    });
}

// 토스트 알림 (showConfirm 사용)
function showToast(type, message) {
    if (typeof showConfirm === 'function') {
        const title = type === 'error' ? '오류' : type === 'success' ? '성공' : '알림';
        showConfirm(title, message, function() {});
    } else {
        const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
        alert(`${icon} ${message}`);
    }
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

// 사용자 목록 새로고침 (수정: 확인창 제거)
async function refreshUsers() {
    console.log('사용자 목록 새로고침 실행');
    // 현재 사용자 활동 시간 먼저 갱신
    await updateCurrentUserLoginTime();    
    await loadAllData();
    // 확인창 제거 - 조용히 새로고침
}

// 새 사용자 추가 (수정: 관리자 권한 창 제거, 오류 수정)
async function addUser() {
    const username = prompt('새 사용자명을 입력하세요:');
    if (!username || !username.trim()) return;
    
    const password = prompt('초기 비밀번호를 입력하세요 (최소 6자):');
    if (!password || password.length < 6) {
        showToast('error', '비밀번호는 최소 6자 이상이어야 합니다.');
        return;
    }
    
    const email = prompt('이메일 주소를 입력하세요 (선택사항, 취소 가능):');
    
    // 관리자 권한 창 제거 - 기본값은 일반 사용자
    const data = {
        username: username.trim(),
        password: password,
        email: email?.trim() || null,
        is_admin: false // 기본값: 일반 사용자
    };
    
    console.log('사용자 생성 요청:', data);
    
    const result = await apiCall('/api/admin/users', 'POST', data);
    if (result && result.success) {
        showToast('success', result.message || '사용자가 생성되었습니다.');
        await loadAllData(); // 즉시 새로고침
    }
}

// 사용자 편집
function editUser(userId) {
    const user = allUsers.find(u => parseInt(u.id) === parseInt(userId));
    if (!user) {
        showToast('error', '사용자를 찾을 수 없습니다.');
        return;
    }
    
    // 모달 필드 채우기
    document.getElementById('editUserId').value = user.id;
    document.getElementById('editUsername').value = user.username;
    document.getElementById('editIsActive').checked = user.is_active;
    document.getElementById('editIsAdmin').checked = user.is_admin;
    
    // 모달 열기
    const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
    modal.show();
}

// 사용자 변경사항 저장
async function saveUserChanges() {
    const userId = parseInt(document.getElementById('editUserId').value);
    const isActive = document.getElementById('editIsActive').checked;
    const isAdmin = document.getElementById('editIsAdmin').checked;
    
    // 자기 자신의 관리자 권한 제거 방지
    if (userId === currentUserId && !isAdmin) {
        showToast('error', '자기 자신의 관리자 권한은 제거할 수 없습니다.');
        return;
    }
    
    const data = {
        is_active: isActive,
        is_admin: isAdmin
    };
    
    const result = await apiCall(`/api/admin/users/${userId}`, 'PUT', data);
    if (result && result.success) {
        showToast('success', result.message || '사용자 정보가 수정되었습니다.');
        
        // 모달 닫기
        const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
        modal.hide();
        
        await loadAllData();
    }
}

// 비밀번호 리셋
function resetPassword(userId, username) {
    // 모달 필드 채우기
    document.getElementById('resetUserId').value = userId;
    document.getElementById('resetUsername').value = username;
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
    
    // 유효성 체크 초기화
    document.getElementById('confirmPassword').classList.remove('is-invalid');
    
    // 모달 열기
    const modal = new bootstrap.Modal(document.getElementById('resetPasswordModal'));
    modal.show();
    
    // 포커스 설정
    setTimeout(() => {
        document.getElementById('newPassword').focus();
    }, 500);
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
        document.getElementById('newPassword').focus();
        return;
    }
    
    if (newPassword.length < 6) {
        showToast('error', '비밀번호는 최소 6자 이상이어야 합니다.');
        document.getElementById('newPassword').focus();
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showToast('error', '비밀번호가 일치하지 않습니다.');
        document.getElementById('confirmPassword').focus();
        return;
    }
    
    showConfirm('비밀번호 변경', `사용자 '${username}'의 비밀번호를 변경하시겠습니까?`, async function(confirmed) {
        if (!confirmed) return;
        
        const data = {
            new_password: newPassword
        };
        
        const result = await apiCall(`/api/admin/users/${userId}/reset-password`, 'POST', data);
        if (result && result.success) {
            showToast('success', result.message || '비밀번호가 변경되었습니다.');
            
            // 모달 닫기
            const modal = bootstrap.Modal.getInstance(document.getElementById('resetPasswordModal'));
            modal.hide();
        }
    });
}

// 사용자 삭제
async function deleteUser(userId, username) {
    const userIdNum = parseInt(userId);
    
    // 자기 자신 삭제 방지
    if (userIdNum === currentUserId) {
        showToast('error', '자기 자신은 삭제할 수 없습니다.');
        return;
    }
    
    showConfirm('사용자 삭제', `정말로 사용자 '${username}'을(를) 삭제하시겠습니까?\n\n⚠️ 이 작업은 되돌릴 수 없으며, 해당 사용자의 모든 설정과 데이터가 삭제됩니다.`, function(confirmed) {
        if (!confirmed) return;
        
        // 추가 확인
        const doubleConfirm = prompt(`확인을 위해 사용자명 '${username}'을 정확히 입력하세요:`);
        if (doubleConfirm !== username) {
            showToast('error', '사용자명이 일치하지 않습니다.');
            return;
        }
        
        performDelete();
    });
    
    async function performDelete() {
        const result = await apiCall(`/api/admin/users/${userId}`, 'DELETE');
        if (result && result.success) {
            showToast('success', result.message || '사용자가 삭제되었습니다.');
            await loadAllData();
        }
    }
}

// ============================================================================
// 시스템 관리 함수들
// ============================================================================

// 설정 변경 내역 보기
async function viewConfigChange(configId) {
    const result = await apiCall(`/api/admin/config/${configId}`);
    if (result && result.data) {
        const data = result.data;
        const details = `설정 키: ${data.config_key}
사용자: ${data.username} (ID: ${data.user_id})
변경 시간: ${formatKoreanDateTime(data.changed_at)}
IP 주소: ${data.ip_address || 'N/A'}

이전 값: ${data.old_value || '(없음)'}
새 값: ${data.new_value || '(없음)'}`;
        
        showConfirm('설정 변경 내역', details, function() {});
    }
}

// 시스템 로그 정리 (수정: 모든 로그 삭제)
async function clearLogs() {
    showConfirm('로그 정리', '모든 시스템 로그를 삭제하시겠습니까?\n\n📋 모든 시스템 로그가 삭제됩니다.\n📝 모든 설정 변경 이력도 함께 삭제됩니다.\n\n⚠️ 이 작업은 되돌릴 수 없습니다.', async function(confirmed) {
        if (!confirmed) return;
        
        const result = await apiCall('/api/admin/logs/cleanup', 'POST');
        if (result && result.success) {
            showToast('success', result.message || '모든 로그가 삭제되었습니다.');
            await loadAllData();
        }
    });
}

// ============================================================================
// 모달 이벤트 핸들러
// ============================================================================

// 비밀번호 확인 실시간 체크
function setupPasswordValidation() {
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
}

// Enter 키 이벤트 처리
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        // 비밀번호 리셋 모달에서 Enter
        if (document.getElementById('resetPasswordModal')?.classList.contains('show')) {
            e.preventDefault();
            savePasswordReset();
        }
        // 사용자 편집 모달에서 Enter
        else if (document.getElementById('editUserModal')?.classList.contains('show')) {
            e.preventDefault();
            saveUserChanges();
        }
    }
});

// ============================================================================
// 디버그 및 개발자 도구
// ============================================================================

window.adminDebug = {
    getSession: () => {
        console.log('현재 세션:', {
            currentUserId: currentUserId,
            allUsers: allUsers.length,
            isLoading: isLoading
        });
    },
    
    getStats: () => {
        const stats = document.querySelectorAll('.stats-card h3');
        console.log('시스템 통계:', {
            total_users: stats[0]?.textContent,
            active_users: stats[1]?.textContent,
            admin_users: stats[2]?.textContent,
            inactive_users: stats[3]?.textContent
        });
    },
    
    testAPI: async () => {
        console.log('API 테스트 실행...');
        const result = await apiCall('/api/status');
        console.log('API 응답:', result);
    },
    
    refresh: async () => {
        console.log('데이터 새로고침...');
        await loadAllData();
        console.log('새로고침 완료');
    },
    
    checkCurrentUser: () => {
        console.log('현재 사용자 체크:', {
            currentUserId: currentUserId,
            type: typeof currentUserId,
            users: allUsers.map(u => ({
                id: u.id,
                type: typeof u.id,
                isMatch: parseInt(u.id) === parseInt(currentUserId)
            }))
        });
    }
};

console.log('🛠️ 관리자 페이지 개발자 도구 로드 완료');
console.log('💡 사용 가능한 명령어:');
console.log('   - adminDebug.getSession(): 현재 세션 정보');
console.log('   - adminDebug.getStats(): 시스템 통계');
console.log('   - adminDebug.testAPI(): API 연결 테스트');
console.log('   - adminDebug.refresh(): 데이터 새로고침');
console.log('   - adminDebug.checkCurrentUser(): 현재 사용자 확인');