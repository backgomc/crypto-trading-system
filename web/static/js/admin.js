// 파일 경로: web/static/js/admin.js
// 코드명: 관리자 페이지 JavaScript 로직 (개선된 기능 + 모달 적용)

// 전역 변수
let isLoading = false;
let allUsers = [];
let currentUserId = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
   console.log('🔧 관리자 페이지 로드 완료');
   
   // 현재 사용자 ID 가져오기
   getCurrentUserId();
   
   // 실시간 시간 업데이트
   updateTime();
   setInterval(updateTime, 1000);
   
   // 페이지 로드 애니메이션
   animateCards();
   
   // 모든 데이터 로드
   loadAllData();
   
   // 비밀번호 실시간 체크 이벤트 추가
   setupPasswordValidation();
});

// 현재 사용자 ID 가져오기
async function getCurrentUserId() {
   try {
       const result = await apiCall('/api/status');
       if (result && result.user_id) {
           currentUserId = parseInt(result.user_id);
       }
   } catch (error) {
       console.error('현재 사용자 ID 조회 실패:', error);
   }
}

// 모든 데이터 로드 (실시간 갱신)
async function loadAllData() {
   try {
       // 통계 데이터 로드
       await loadStats();
       
       // 사용자 목록 로드
       await loadUsers();
       
       // 최근 로그 로드
       await loadRecentLogs();
       
   } catch (error) {
       console.error('데이터 로드 오류:', error);
       showAlert('error', '데이터 로드 중 오류가 발생했습니다.');
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
       allUsers = result.data;
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

// 통계 표시
function displayStats(stats) {
   const elements = {
       total: document.querySelector('.stats-card:nth-child(1) h3'),
       active: document.querySelector('.stats-card:nth-child(2) h3'),
       admin: document.querySelector('.stats-card:nth-child(3) h3'),
       inactive: document.querySelector('.stats-card:nth-child(4) h3')
   };
   
   if (elements.total) elements.total.textContent = stats.total_users || 0;
   if (elements.active) elements.active.textContent = stats.active_users || 0;
   if (elements.admin) elements.admin.textContent = stats.admin_users || 0;
   if (elements.inactive) elements.inactive.textContent = stats.inactive_users || 0;
}

// 사용자 목록 표시 (동적 렌더링)
function displayUsers(users) {
   const tbody = document.querySelector('#usersTable tbody');
   if (!tbody) return;
   
   if (users.length === 0) {
       tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">사용자 데이터가 없습니다.</td></tr>';
       return;
   }
   
   tbody.innerHTML = users.map(user => `
       <tr>
           <td>${user.id}</td>
           <td>
               <strong>${user.username}</strong>
               ${user.email ? `<br><small class="text-muted">${user.email}</small>` : ''}
           </td>
           <td>
               <span class="badge ${user.is_active ? 'bg-success' : 'bg-secondary'}">
                   ${user.is_active ? '활성' : '비활성'}
               </span>
           </td>
           <td>
               <span class="badge ${user.is_admin ? 'bg-primary' : 'bg-secondary'}">
                   ${user.is_admin ? '관리자' : '일반'}
               </span>
           </td>
           <td>
               <small class="text-muted">
                   ${user.last_login ? new Date(user.last_login).toLocaleString('ko-KR') : '로그인 기록 없음'}
               </small>
           </td>
           <td>
               <div class="btn-group btn-group-sm">
                   <button class="btn btn-outline-primary" onclick="editUser(${user.id})" title="편집">
                       <i class="bi bi-pencil"></i>
                   </button>
                   <button class="btn btn-outline-warning" onclick="resetPassword(${user.id}, '${user.username}')" title="비밀번호 리셋">
                       <i class="bi bi-key"></i>
                   </button>
                   <button class="btn btn-outline-danger" onclick="deleteUser(${user.id}, '${user.username}')" title="삭제">
                       <i class="bi bi-trash"></i>
                   </button>
               </div>
           </td>
       </tr>
   `).join('');
}

// 최근 로그 표시
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
                   ${new Date(log.timestamp).toLocaleString('ko-KR')}
               </small>
           </td>
       </tr>
   `).join('');
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
   const buttons = document.querySelectorAll('button');
   buttons.forEach(btn => {
       btn.disabled = show;
   });
}

// 토스트 알림 (기존 방식 유지)
function showToast(type, message) {
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

// 사용자 목록 새로고침 (개선: 페이지 새로고침 없이)
async function refreshUsers() {
   showToast('info', '사용자 목록을 새로고침합니다...');
   await loadAllData();
}

// 새 사용자 추가 (기존 prompt 방식에서 모달로 개선)
async function addUser() {
   const username = prompt('새 사용자명을 입력하세요:');
   if (!username) return;
   
   const password = prompt('초기 비밀번호를 입력하세요:');
   if (!password) return;
   
   const email = prompt('이메일 주소를 입력하세요 (선택):');
   
   // ✅ showConfirm 사용
   showConfirm('관리자 권한', '관리자 권한을 부여하시겠습니까?', async function(isAdmin) {
       const data = {
           username: username.trim(),
           password: password,
           email: email?.trim() || '',
           is_admin: isAdmin
       };
       
       const result = await apiCall('/api/admin/users', 'POST', data);
       if (result) {
           showToast('success', result.message);
           await loadAllData(); // 실시간 갱신
       }
   });
}

// 사용자 편집 (기존 방식 유지)
function editUser(userId, username, isActive, isAdmin) {
   const user = allUsers.find(u => u.id === userId);
   if (!user) return;
   
   // 모달 필드 채우기
   document.getElementById('editUserId').value = user.id;
   document.getElementById('editUsername').value = user.username;
   document.getElementById('editIsActive').checked = user.is_active;
   document.getElementById('editIsAdmin').checked = user.is_admin;
   
   // 모달 열기
   const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
   modal.show();
}

// 사용자 변경사항 저장 (자기 자신 보호 기능 추가)
async function saveUserChanges() {
   const userId = parseInt(document.getElementById('editUserId').value);
   const isActive = document.getElementById('editIsActive').checked;
   const isAdmin = document.getElementById('editIsAdmin').checked;
   
   // ✅ 자기 자신의 관리자 권한 제거 방지
   if (userId === currentUserId && !isAdmin) {
       showToast('error', '자기 자신의 관리자 권한은 제거할 수 없습니다.');
       return;
   }
   
   const data = {
       is_active: isActive,
       is_admin: isAdmin
   };
   
   const result = await apiCall(`/api/admin/users/${userId}`, 'PUT', data);
   if (result) {
       showToast('success', result.message);
       
       // 모달 닫기
       const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
       modal.hide();
       
       await loadAllData(); // 실시간 갱신
   }
}

// 비밀번호 리셋 (기존 모달 방식 유지)
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

// 비밀번호 리셋 저장 (✅ showConfirm 적용)
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
   
   // ✅ showConfirm 사용
   showConfirm('비밀번호 변경', `사용자 '${username}'의 비밀번호를 변경하시겠습니까?`, async function(confirmed) {
       if (!confirmed) return;
       
       const data = {
           new_password: newPassword
       };
       
       const result = await apiCall(`/api/admin/users/${userId}/password`, 'PUT', data);
       if (result) {
           showToast('success', result.message);
           
           // 모달 닫기
           const modal = bootstrap.Modal.getInstance(document.getElementById('resetPasswordModal'));
           modal.hide();
       }
   });
}

// 사용자 삭제 (✅ showConfirm 적용 + 자기 자신 보호)
async function deleteUser(userId, username) {
   const userIdNum = parseInt(userId);
   
   // ✅ 자기 자신 삭제 방지
   if (userIdNum === currentUserId) {
       showToast('error', '자기 자신은 삭제할 수 없습니다.');
       return;
   }
   
   // ✅ showConfirm 사용
   showConfirm('사용자 삭제', `정말로 사용자 '${username}'을(를) 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`, function(confirmed) {
       if (!confirmed) return;
       
       // 추가 확인 (사용자명 입력)
       const doubleConfirm = prompt(`확인을 위해 사용자명 '${username}'을 입력하세요:`);
       if (doubleConfirm !== username) {
           showToast('error', '사용자명이 일치하지 않습니다.');
           return;
       }
       
       // 실제 삭제 실행
       performDelete();
   });
   
   async function performDelete() {
       const result = await apiCall(`/api/admin/users/${userId}`, 'DELETE');
       if (result) {
           showToast('success', result.message);
           await loadAllData(); // 실시간 갱신
       }
   }
}

// ============================================================================
// 시스템 관리 함수들
// ============================================================================

// 설정 변경 내역 보기 (기존 유지)
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

// 시스템 로그 정리 (✅ showConfirm 적용)
async function clearLogs() {
   showConfirm('로그 정리', '시스템 로그를 정리하시겠습니까?\n\n30일 이전의 로그가 삭제됩니다.', async function(confirmed) {
       if (!confirmed) return;
       
       const result = await apiCall('/api/admin/logs', 'DELETE');
       if (result) {
           showToast('success', result.message);
           await loadAllData(); // 실시간 갱신
       }
   });
}

// ============================================================================
// 모달 이벤트 핸들러 (비밀번호 실시간 체크 복원)
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
// 디버그 및 개발자 도구 (개선)
// ============================================================================

// 콘솔 명령어
window.adminDebug = {
   // 현재 세션 정보
   getSession: () => {
       console.log('현재 세션:', {
           currentUserId: currentUserId,
           allUsers: allUsers.length,
           isLoading: isLoading
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
   },
   
   // 데이터 새로고침
   refresh: async () => {
       console.log('데이터 새로고침...');
       await loadAllData();
       console.log('새로고침 완료');
   }
};

console.log('🛠️ 관리자 페이지 개발자 도구 로드 완료');
console.log('💡 사용 가능한 명령어:');
console.log('   - adminDebug.getSession(): 현재 세션 정보');
console.log('   - adminDebug.getStats(): 시스템 통계');
console.log('   - adminDebug.testAPI(): API 연결 테스트');
console.log('   - adminDebug.refresh(): 데이터 새로고침');