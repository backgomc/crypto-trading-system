// 파일 경로: web/static/js/admin.js
// 코드명: 관리자 페이지 JavaScript 로직 (시스템 로그 문제점 완전 수정)

// 전역 변수
let isLoading = false;
let allUsers = [];
let currentUserId = null;
let currentLogPage = 1;
let logsPerPage = 20;
let hasMoreLogs = false;
let isLoadingLogs = false;

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
    
    // 페이지 로드 애니메이션
    animateCards();
    
    // 비밀번호 실시간 체크 설정
    setupPasswordValidation();
    
    // 10초마다 통계 자동 새로고침 (접속자 수, 사용자 접속 상태 실시간 반영)
    setInterval(loadStats, 10000);
    setInterval(loadUsers, 10000);
    setInterval(() => loadRecentLogs(true, true), 10000);  // isAutoRefresh = true
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

// 현재 사용자 ID 가져오기 (개선된 버전)
async function getCurrentUserId() {
    try {
        const response = await fetch('/api/status');
        const result = await response.json();
        
        if (result && result.user_id) {
            currentUserId = parseInt(result.user_id);
            currentUsername = result.username || null;
        } else {
            currentUserId = null;
            currentUsername = null;
        }
        
        console.log('현재 사용자 정보:', {
            userId: currentUserId,
            username: currentUsername
        });
        
        return currentUserId;
    } catch (error) {
        console.error('현재 사용자 조회 실패:', error);
        currentUserId = null;
        currentUsername = null;
        return null;
    }
}

// 모든 데이터 로드
async function loadAllData() {
    try {
        await loadStats();
        await loadUsers();
        restoreFilterState(); // 먼저 체크박스 상태 복원
        await loadRecentLogs(true, true); // 그 다음 로그 로드
    } catch (error) {
        console.error('데이터 로드 오류:', error);
        showToast('error', '데이터 로드 중 오류가 발생했습니다.');
    }
}

// 통계 데이터 로드
async function loadStats() {
    const result = await apiCallAuto('/api/admin/stats');
    if (result && result.data) {
        displayStats(result.data);
    }
}

// 사용자 목록 로드
async function loadUsers() {
    const result = await apiCallAuto('/api/admin/users');
    if (result && result.data) {
        allUsers = result.data.users || result.data;
        displayUsers(allUsers);
    }
}

// 자동 갱신용 API 호출 함수 (헤더로 구분)
async function apiCallAuto(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-Auto-Refresh': 'true'  // 자동 갱신 표시 헤더
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
        console.error('자동 갱신 API 오류:', error);
        return null;
    }
}

// 최근 로그 로드 (자동 갱신 구분)
async function loadRecentLogs(isFirstLoad = false, isAutoRefresh = false) {
   if (isLoadingLogs && !isAutoRefresh) return;  // 자동 갱신은 로딩 중에도 허용
   
   if (!isAutoRefresh) {
       isLoadingLogs = true;
       updateLoadMoreButton();
   }
   
   try {
       const excludeAdmin = document.getElementById('excludeAdminLogs')?.checked || false;
       const page = isFirstLoad ? 1 : currentLogPage;
       
       const params = new URLSearchParams({
           page: page,
           per_page: logsPerPage,
           exclude_admin: excludeAdmin
       });
       
       // 자동 갱신이면 자동 갱신용 API 사용
       const result = isAutoRefresh 
           ? await apiCallAuto(`/api/admin/logs/recent?${params}`)
           : await apiCall(`/api/admin/logs/recent?${params}`);
       
       if (result && result.data) {
           const logs = result.data.logs || result.data;
           
           if (isFirstLoad || isAutoRefresh) {
               currentLogPage = 1;
               displayRecentLogs(logs, true);
           } else {
               displayRecentLogs(logs, false);
           }
           
           hasMoreLogs = result.meta ? result.meta.has_next : logs.length >= logsPerPage;
           updateLogCount(result.meta ? result.meta.total : logs.length);
       }
   } catch (error) {
       if (!isAutoRefresh) {  // 자동 갱신 에러는 조용히 처리
           console.error('로그 로드 실패:', error);
           showToast('error', '로그 로드에 실패했습니다.');
       }
       hasMoreLogs = false;
   } finally {
       if (!isAutoRefresh) {
           isLoadingLogs = false;
           updateLoadMoreButton();
       }
   }
}

// 통계 표시 (수정: 비활성 사용자로 변경)
function displayStats(stats) {
    const cards = document.querySelectorAll('.stats-card');
    const elements = {
        total: cards[0]?.querySelector('h3'),
        active: cards[1]?.querySelector('h3'),
        inactive: cards[2]?.querySelector('h3'),
        online: cards[3]?.querySelector('h3') // ✅ 이게 진짜 안전하고 정확
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
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">사용자 데이터가 없습니다.</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>
                <strong>${user.username}</strong>
                ${user.id === parseInt(document.body.dataset.currentUserId) ? '<span class="badge bg-info ms-1">나</span>' : ''}
                ${user.email ? `<br><small class="text-muted">${user.email}</small>` : ''}
            </td>
            <td>
                <span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">
                    ${user.is_active ? '활성' : '비활성'}
                </span>
            </td>
            <td>
                <span class="badge ${user.is_admin ? 'bg-warning text-dark' : 'bg-light text-dark'}">
                    ${user.is_admin ? '관리자' : '일반'}
                </span>
            </td>
            <td>
                <span class="badge ${user.is_online ? 'bg-success' : 'bg-secondary'}">
                    <i class="bi bi-circle-fill me-1" style="font-size: 0.6rem;"></i>
                    ${user.is_online ? '접속중' : '오프라인'}
                </span>
            </td>
            <td>
                <small class="text-muted">${user.created_at || '없음'}</small>
            </td>
            <td>
                <small class="text-muted">${user.last_login || '없음'}</small>
            </td>
            <td class="text-center">
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editUser(${user.id})" title="편집">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-warning" onclick="resetPassword(${user.id}, '${user.username}')" title="비밀번호 리셋">
                        <i class="bi bi-key"></i>
                    </button>
                    ${(user.id !== parseInt(document.body.dataset.currentUserId) && !user.is_admin) ? `
                    <button class="btn btn-outline-danger" onclick="deleteUser(${user.id}, '${user.username}')" title="삭제">
                        <i class="bi bi-trash"></i>
                    </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

// 최근 로그 표시 (수정: 더보기 기능 개선)
function displayRecentLogs(logs, isFirstLoad = true) {
    const tbody = document.querySelector('#logsTable tbody');
    if (!tbody) return;
    
    if (logs.length === 0 && isFirstLoad) {
        tbody.innerHTML = '<tr id="emptyLogRow"><td colspan="4" class="text-center text-muted py-3">로그 데이터가 없습니다.</td></tr>';
        return;
    }
    
    // 빈 로그 행 제거
    const emptyRow = document.getElementById('emptyLogRow');
    if (emptyRow) {
        emptyRow.remove();
    }
    
    const newRows = logs.map(log => `
        <tr class="log-item log-${log.level.toLowerCase()}" data-category="${log.category}">
            <td class="text-center" style="width: 80px;">
                <span class="badge ${getBadgeClass(log.level)}">
                    ${log.level}
                </span>
            </td>
            <td class="text-center" style="width: 80px;">
                <small class="text-muted">${log.category}</small>
            </td>
            <td class="log-message">${log.message}</td>
            <td class="text-center" style="width: 90px;">
                <small class="text-muted">
                    ${formatKoreanDateTime(log.timestamp)}
                </small>
            </td>
        </tr>
    `).join('');
    
    if (isFirstLoad) {
        tbody.innerHTML = newRows;
    } else {
        tbody.insertAdjacentHTML('beforeend', newRows);
    }
}

// 더보기 버튼 업데이트
function updateLoadMoreButton() {
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (loadMoreBtn) {
        if (hasMoreLogs && !isLoadingLogs) {
            loadMoreBtn.style.display = 'inline-block';
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = '<i class="bi bi-arrow-down me-1"></i>더보기';
        } else if (isLoadingLogs) {
            loadMoreBtn.style.display = 'inline-block';
            loadMoreBtn.disabled = true;
            loadMoreBtn.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i>로딩...';
        } else {
            loadMoreBtn.style.display = 'none';
        }
    }
}

// 로그 개수 업데이트 (수정: 총 개수 표시)
function updateLogCount(totalCount = null) {
    const logCount = document.getElementById('logCount');
    if (logCount) {
        const visibleRows = document.querySelectorAll('#logsTable tbody tr:not(#emptyLogRow)');
        const displayedCount = visibleRows.length;
        
        if (totalCount !== null) {
            logCount.textContent = `총 ${totalCount}개 로그 (${displayedCount}개 표시)`;
        } else {
            logCount.textContent = `${displayedCount}개 로그 표시`;
        }
    }
}

// 한국시간 포맷 함수 (수정)
function formatKoreanDateTime(dateString) {
    if (!dateString) return '없음';
    
    try {
        const date = new Date(dateString);

        // 대시보드와 동일한 형식으로 표시
        return date.toLocaleString('ko-KR', {
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

// 페이지 로드 시 체크박스 상태 복원 (loadAllData() 함수 끝에 추가)
function restoreFilterState() {
    const savedState = localStorage.getItem('excludeAdminLogs');
    const checkbox = document.getElementById('excludeAdminLogs');
    
    if (savedState !== null && checkbox) {
        checkbox.checked = savedState === 'true';
    } else if (checkbox) {
        // 기본값 설정 (체크됨)
        checkbox.checked = true;
        localStorage.setItem('excludeAdminLogs', 'true');
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

// 확인 모달 표시 (부트스트랩 모달 사용)
function showConfirmModal(title, message) {
    return new Promise((resolve) => {
        // 기존 모달 제거
        const existingModal = document.getElementById('confirmModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 모달 HTML 생성
        const modalHtml = `
            <div class="modal fade" id="confirmModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${message}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>
                            <button type="button" class="btn btn-danger" id="confirmBtn">확인</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        
        // 확인 버튼 클릭
        document.getElementById('confirmBtn').onclick = () => {
            modal.hide();
            resolve(true);
        };
        
        // 모달 숨김 시 false 반환
        document.getElementById('confirmModal').addEventListener('hidden.bs.modal', () => {
            document.getElementById('confirmModal').remove();
            resolve(false);
        });
        
        modal.show();
    });
}

// 카드 애니메이션
function animateCards() {
    let animationExecuted = false;
    if (animationExecuted) return;
    animationExecuted = true;

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
    await updateCurrentUserLoginTime();    
    
    // 수동 새로고침이므로 기존 apiCall 사용 (로그 남김)
    const result = await apiCall('/api/admin/users');
    if (result && result.data) {
        allUsers = result.data.users || result.data;
        displayUsers(allUsers);
    }
    
    // 통계도 함께 새로고침 (수동)
    const statsResult = await apiCall('/api/admin/stats');
    if (statsResult && statsResult.data) {
        displayStats(statsResult.data);
    }
    
    // ✅ 로그 조회는 자동갱신으로 처리 (로그 안 남김)
    restoreFilterState();
    await loadRecentLogs(true, true); // isAutoRefresh = true
}

// 새 사용자 추가 (모달 사용)
async function addUser() {
    // 모달 열기
    const modal = new bootstrap.Modal(document.getElementById('addUserModal'));
    modal.show();
    
    // 폼 초기화
    document.getElementById('addUserForm').reset();
    document.getElementById('usernameCheck').textContent = '';
    document.getElementById('newUsername').classList.remove('is-valid', 'is-invalid');
    document.getElementById('confirmNewPassword').classList.remove('is-invalid');
    
    // 포커스 설정
    setTimeout(() => {
        document.getElementById('newUsername').focus();
    }, 500);
}

// 사용자명 중복체크
async function checkUsername() {
    const username = document.getElementById('newUsername').value.trim();
    const checkDiv = document.getElementById('usernameCheck');
    const usernameInput = document.getElementById('newUsername');
    
    if (!username) {
        checkDiv.textContent = '사용자명을 입력하세요.';
        checkDiv.className = 'form-text text-danger';
        return;
    }
    
    try {
        const result = await apiCall(`/api/admin/check-username/${username}`);
        if (result && result.success) {
            if (result.data.available) {
                checkDiv.textContent = '✅ 사용 가능한 사용자명입니다.';
                checkDiv.className = 'form-text text-success';
                usernameInput.classList.remove('is-invalid');
                usernameInput.classList.add('is-valid');
            } else {
                checkDiv.textContent = '❌ 이미 사용 중인 사용자명입니다.';
                checkDiv.className = 'form-text text-danger';
                usernameInput.classList.remove('is-valid');
                usernameInput.classList.add('is-invalid');
            }
        }
    } catch (error) {
        checkDiv.textContent = '중복체크 중 오류가 발생했습니다.';
        checkDiv.className = 'form-text text-danger';
    }
}

// 사용자 생성 실행
async function createUser() {
    const username = document.getElementById('newUsername').value.trim();
    const password = document.getElementById('addPassword').value;
    const confirmPassword = document.getElementById('addConfirmPassword').value;
    const email = document.getElementById('newEmail').value.trim();
    
    // 유효성 검사
    if (!username) {
        showToast('error', '사용자명을 입력하세요.');
        document.getElementById('newUsername').focus();
        return;
    }
    
    if (!password) {
        showToast('error', '비밀번호를 입력하세요.');
        document.getElementById('newPassword').focus();
        return;
    }
    
    if (password.length < 6) {
        showToast('error', '비밀번호는 최소 6자 이상이어야 합니다.');
        document.getElementById('newPassword').focus();
        return;
    }
    
    if (password !== confirmPassword) {
        showToast('error', '비밀번호가 일치하지 않습니다.');
        document.getElementById('confirmNewPassword').focus();
        return;
    }
    
    if (!email) {
        showToast('error', '이메일을 입력하세요.');
        document.getElementById('newEmail').focus();
        return;
    }
    
    // 이메일 형식 검증
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showToast('error', '올바른 이메일 형식을 입력하세요.');
        document.getElementById('newEmail').focus();
        return;
    }
    
    const data = {
        username: username,
        password: password,
        email: email,
        is_admin: false
    };
    
    const result = await apiCall('/api/admin/users', 'POST', data);
    if (result && result.success) {
        showToast('success', result.message || '사용자가 생성되었습니다.');
        
        // 모달 닫기
        const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
        modal.hide();
        
        await loadAllData();
    }
}

// 관리자 로그 필터링 (수정: 서버에서 필터링)
function filterLogs() {
    const excludeAdmin = document.getElementById('excludeAdminLogs').checked;
    
    // 체크박스 상태 저장
    localStorage.setItem('excludeAdminLogs', excludeAdmin);
    
    // 서버에서 필터링된 로그 다시 로드
    currentLogPage = 1;
    loadRecentLogs(true);
}

// 더 많은 로그 로드 (수정)
async function loadMoreLogs() {
    if (isLoadingLogs || !hasMoreLogs) return;
    
    currentLogPage++;
    await loadRecentLogs(false);
}

// 로그 새로고침 (수정: 확인창 제거)
async function refreshLogs() {
    try {
        currentLogPage = 1;
        await loadRecentLogs(true, false);
        // 확인창 제거 - 조용히 새로고침
    } catch (error) {
        console.error('로그 새로고침 실패:', error);
        showToast('error', '로그 새로고침에 실패했습니다.');
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
    showConfirm('로그 삭제 확인', '정말로 모든 로그를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.', async function(confirmed) {
        if (!confirmed) return;
        
        try {
            showLoading(true);
            const result = await apiCall('/api/admin/logs/cleanup', 'POST');
            
            if (result && result.success) {
                showToast('success', result.message || '모든 로그가 삭제되었습니다.');
                await loadAllData();
            }
        } catch (error) {
            console.error('로그 삭제 실패:', error);
            showToast('error', '로그 삭제에 실패했습니다.');
        } finally {
            showLoading(false);
        }
    });
}

// ============================================================================
// 모달 이벤트 핸들러
// ============================================================================

// 비밀번호 확인 실시간 체크
function setupPasswordValidation() {
    // 기존 코드 (비밀번호 리셋용)
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
    
    // ✅ 여기에 추가: 사용자 추가 모달용
    const addNewPasswordInput = document.getElementById('addPassword');
    const addConfirmPasswordInput = document.getElementById('addConfirmPassword');
    
    function checkAddPasswordMatch() {
        if (!addNewPasswordInput || !addConfirmPasswordInput) return;
        
        const newPassword = addNewPasswordInput.value;
        const confirmPassword = addConfirmPasswordInput.value;
        
        if (confirmPassword && newPassword !== confirmPassword) {
            addConfirmPasswordInput.classList.add('is-invalid');
        } else {
            addConfirmPasswordInput.classList.remove('is-invalid');
        }
    }
    
    if (addNewPasswordInput) addNewPasswordInput.addEventListener('input', checkAddPasswordMatch);
    if (addConfirmPasswordInput) addConfirmPasswordInput.addEventListener('input', checkAddPasswordMatch);
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