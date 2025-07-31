# 파일 경로: web/routes/admin_api.py
# 코드명: 관리자 전용 API 엔드포인트 (모든 문제점 완전 수정)

from flask import Blueprint, request, session, jsonify
from functools import wraps
from datetime import datetime, timedelta
import pytz, re
from config.models import User, UserConfig, SystemLog, ConfigHistory, TradingState, db, get_kst_now, to_kst_string
from api.utils import (
    error_response, success_response, 
    validate_request_data, handle_api_errors,
    validate_string, validate_boolean
)

admin_api_bp = Blueprint('admin_api', __name__)

# ============================================================================
# 관리자 권한 데코레이터
# ============================================================================

def admin_required(f):
    """관리자 권한 필요 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return error_response('로그인이 필요합니다.', 'AUTH_REQUIRED', 401)
        if not session.get('is_admin', False):
            log_admin_event('WARNING', 'SECURITY', f'관리자 API 무권한 접근: {session.get("username")}')
            return error_response('관리자 권한이 필요합니다.', 'ADMIN_REQUIRED', 403)
        return f(*args, **kwargs)
    return decorated_function

def log_admin_event(level, category, message):
    """관리자 작업 로깅"""
    try:
        log_entry = SystemLog(
            level=level,
            category=category,
            message=message,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:200],
            timestamp=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"관리자 로그 저장 실패: {e}")

def get_online_users():
    try:       
        # 1분 이내 로그인한 사용자를 접속중으로 간주 (더 짧게)
        one_minute_ago = get_kst_now() - timedelta(minutes=1)
        online_count = User.query.filter(
            User.is_active == True,
            User.last_active >= one_minute_ago  # last_active로 변경
        ).count()
        return online_count
    except Exception as e:
        print(f"접속자 수 계산 오류: {e}")
        return 0

def add_user_online_status(users):
    """사용자 목록에 접속 상태 추가 (수정: 현재 사용자 접속 상태 우선 처리)"""
    try:
        # 현재 사용자 ID
        current_user_id = session.get('user_id')
        
        # 1분 이내 로그인한 사용자를 접속중으로 간주
        one_minute_ago = get_kst_now() - timedelta(minutes=1)
        
        for user in users:
            user_id = user.get('id')
            
            # 현재 사용자는 항상 접속중으로 표시
            if user_id == current_user_id:
                user['is_online'] = True
                continue
            
            # 다른 사용자들은 로그인 시간 기준으로 판단
            if user.get('last_active'):
                try:
                    last_active_str = user['last_active']
                    last_active_dt = datetime.fromisoformat(last_active_str.replace('Z', ''))
                    user['is_online'] = last_active_dt >= one_minute_ago
                except Exception as e:
                    print(f"로그인 시간 파싱 오류: {e}")
                    user['is_online'] = False
            else:
                user['is_online'] = False
        
        return users
    except Exception as e:
        print(f"접속 상태 추가 오류: {e}")
        return users

# ============================================================================
# 사용자 관리 API
# ============================================================================

@admin_api_bp.route('/api/admin/users', methods=['GET'])
@admin_required
@handle_api_errors
def get_all_users():
    """모든 사용자 목록 조회 (접속 상태 포함)"""
    try:
        users = User.query.order_by(User.created_at.asc()).all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'is_admin': user.is_admin,
                'created_at': to_kst_string(user.created_at),
                'last_login': to_kst_string(user.last_login),
                'last_active': to_kst_string(user.last_active)
            })
        
        # 접속 상태 추가
        users_data = add_user_online_status(users_data)
        
        log_admin_event('INFO', 'ADMIN', f'사용자 목록 조회: {session.get("username")}')
        
        return success_response(
            data={'users': users_data, 'total': len(users_data)},
            message='사용자 목록 조회 성공'
        )
        
    except Exception as e:
        log_admin_event('ERROR', 'ADMIN', f'사용자 목록 조회 실패: {e}')
        return error_response('사용자 목록 조회 중 오류가 발생했습니다.', 'DATABASE_ERROR', 500)

@admin_api_bp.route('/api/admin/check-username/<username>', methods=['GET'])
@admin_required
@handle_api_errors
def check_username_availability(username):
    """사용자명 중복체크"""
    try:
        # 사용자명 유효성 검사
        if not username or len(username.strip()) < 3:
            return error_response('사용자명은 3자 이상이어야 합니다.', 'VALIDATION_ERROR', 400)
        
        username_clean = username.strip()
        
        # 중복 체크
        existing_user = User.query.filter_by(username=username_clean).first()
        is_available = existing_user is None
        
        log_admin_event('INFO', 'ADMIN', f'사용자명 중복체크: {username_clean} (사용가능: {is_available})')
        
        return success_response(
            data={
                'username': username_clean,
                'available': is_available
            },
            message='사용자명 중복체크 완료'
        )
        
    except Exception as e:
        log_admin_event('ERROR', 'ADMIN', f'사용자명 중복체크 실패: {e}')
        return error_response('중복체크 중 오류가 발생했습니다.', 'CHECK_ERROR', 500)
    
@admin_api_bp.route('/api/admin/users', methods=['POST'])
@admin_required
@handle_api_errors
def create_user():
    """새 사용자 생성"""
    try:
        # 요청 데이터 검증
        data, error = validate_request_data(
            request,
            required_fields=['username', 'password', 'email'],  # 이메일 필수로 변경
            optional_fields=['is_admin']
        )
        if error:
            return error
        
        username = data['username'].strip()
        password = data['password']
        email = data.get('email', '').strip() or None
        is_admin = data.get('is_admin', False)
        
        # 사용자명 중복 체크
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return error_response('이미 존재하는 사용자명입니다.', 'USER_EXISTS', 400)
        
        # 이메일 검증 로직
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return error_response('올바른 이메일 형식이 아닙니다.', 'VALIDATION_ERROR', 400)

        # 이메일 중복 체크
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return error_response('이미 사용 중인 이메일입니다.', 'EMAIL_EXISTS', 400)        
        
        # 사용자명 유효성 검사
        username_clean, error_msg = validate_string(username, min_length=3, max_length=30)
        if error_msg:
            return error_response(f'사용자명 오류: {error_msg}', 'VALIDATION_ERROR', 400)
        
        # 비밀번호 유효성 검사
        if len(password) < 6:
            return error_response('비밀번호는 최소 6자 이상이어야 합니다.', 'VALIDATION_ERROR', 400)
        
        # 새 사용자 생성
        new_user = User(
            username=username_clean,
            email=email,
            is_admin=bool(is_admin),
            is_active=True
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        log_admin_event('INFO', 'ADMIN', f'새 사용자 생성: {username_clean} (관리자: {session.get("username")})')
        
        return success_response(
            data={
                'user_id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'is_admin': new_user.is_admin
            },
            message=f'사용자 "{username_clean}"이 생성되었습니다.'
        )
        
    except Exception as e:
        db.session.rollback()
        log_admin_event('ERROR', 'ADMIN', f'사용자 생성 실패: {e}')
        return error_response('사용자 생성 중 오류가 발생했습니다.', 'DATABASE_ERROR', 500)

@admin_api_bp.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
@handle_api_errors
def update_user(user_id):
    """사용자 정보 수정"""
    try:
        # 대상 사용자 조회
        target_user = User.query.get(user_id)
        if not target_user:
            return error_response('사용자를 찾을 수 없습니다.', 'USER_NOT_FOUND', 404)
        
        # 요청 데이터 검증
        data, error = validate_request_data(
            request,
            optional_fields=['is_active', 'is_admin', 'email']
        )
        if error:
            return error
        
        # 자기 자신의 관리자 권한은 제거할 수 없음
        current_user_id = session.get('user_id')
        if user_id == current_user_id and 'is_admin' in data and not data['is_admin']:
            return error_response('자신의 관리자 권한은 제거할 수 없습니다.', 'SELF_ADMIN_ERROR', 400)
        
        # 변경 내역 추적용
        changes = []
        
        # 활성 상태 변경
        if 'is_active' in data:
            new_active = validate_boolean(data['is_active'])[0]
            if new_active is not None and target_user.is_active != new_active:
                target_user.is_active = new_active
                changes.append(f'활성상태: {new_active}')
        
        # 관리자 권한 변경
        if 'is_admin' in data:
            new_admin = validate_boolean(data['is_admin'])[0]
            if new_admin is not None and target_user.is_admin != new_admin:
                target_user.is_admin = new_admin
                changes.append(f'관리자권한: {new_admin}')
        
        # 이메일 변경
        if 'email' in data:
            new_email = data['email'].strip() or None
            if target_user.email != new_email:
                target_user.email = new_email
                changes.append(f'이메일: {new_email or "제거"}')
        
        if not changes:
            return success_response(message='변경된 사항이 없습니다.')
        
        db.session.commit()
        
        # 로그 기록
        changes_str = ', '.join(changes)
        log_admin_event('INFO', 'ADMIN', f'사용자 수정: {target_user.username} ({changes_str}) - 관리자: {session.get("username")}')
        
        return success_response(
            data={
                'user_id': target_user.id,
                'username': target_user.username,
                'is_active': target_user.is_active,
                'is_admin': target_user.is_admin,
                'email': target_user.email
            },
            message=f'사용자 "{target_user.username}" 정보가 수정되었습니다.'
        )
        
    except Exception as e:
        db.session.rollback()
        log_admin_event('ERROR', 'ADMIN', f'사용자 수정 실패 (ID: {user_id}): {e}')
        return error_response('사용자 정보 수정 중 오류가 발생했습니다.', 'DATABASE_ERROR', 500)

@admin_api_bp.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
@handle_api_errors
def reset_user_password(user_id):
    """사용자 비밀번호 리셋"""
    try:
        # 대상 사용자 조회
        target_user = User.query.get(user_id)
        if not target_user:
            return error_response('사용자를 찾을 수 없습니다.', 'USER_NOT_FOUND', 404)
        
        # 요청 데이터 검증
        data, error = validate_request_data(
            request,
            required_fields=['new_password']
        )
        if error:
            return error
        
        new_password = data['new_password']
        
        # 비밀번호 유효성 검사
        if len(new_password) < 6:
            return error_response('비밀번호는 최소 6자 이상이어야 합니다.', 'VALIDATION_ERROR', 400)
        
        # 비밀번호 변경
        target_user.set_password(new_password)
        db.session.commit()
        
        log_admin_event('INFO', 'ADMIN', f'비밀번호 리셋: {target_user.username} - 관리자: {session.get("username")}')
        
        return success_response(
            message=f'사용자 "{target_user.username}"의 비밀번호가 변경되었습니다.'
        )
        
    except Exception as e:
        db.session.rollback()
        log_admin_event('ERROR', 'ADMIN', f'비밀번호 리셋 실패 (ID: {user_id}): {e}')
        return error_response('비밀번호 변경 중 오류가 발생했습니다.', 'DATABASE_ERROR', 500)

@admin_api_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
@handle_api_errors
def delete_user(user_id):
    """사용자 삭제"""
    try:
        # 대상 사용자 조회
        target_user = User.query.get(user_id)
        if not target_user:
            return error_response('사용자를 찾을 수 없습니다.', 'USER_NOT_FOUND', 404)
        
        # 자기 자신은 삭제할 수 없음
        current_user_id = session.get('user_id')
        if user_id == current_user_id:
            return error_response('자기 자신은 삭제할 수 없습니다.', 'SELF_DELETE_ERROR', 400)
        
        username = target_user.username
        
        # 관련 데이터도 함께 삭제 (CASCADE)
        UserConfig.query.filter_by(user_id=user_id).delete()
        TradingState.query.filter_by(user_id=user_id).delete()
        ConfigHistory.query.filter_by(user_id=user_id).delete()
        
        # 사용자 삭제
        db.session.delete(target_user)
        db.session.commit()
        
        log_admin_event('WARNING', 'ADMIN', f'사용자 삭제: {username} (ID: {user_id}) - 관리자: {session.get("username")}')
        
        return success_response(
            message=f'사용자 "{username}"이 삭제되었습니다.'
        )
        
    except Exception as e:
        db.session.rollback()
        log_admin_event('ERROR', 'ADMIN', f'사용자 삭제 실패 (ID: {user_id}): {e}')
        return error_response('사용자 삭제 중 오류가 발생했습니다.', 'DATABASE_ERROR', 500)

# ============================================================================
# 시스템 관리 API
# ============================================================================

@admin_api_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
@handle_api_errors
def get_system_stats():
    """시스템 통계 조회 (비활성 사용자 통계 추가)"""
    try:
        # 사용자 통계
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        inactive_users = User.query.filter_by(is_active=False).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        online_users = get_online_users()  # 현재 접속자 수
        
        # 최근 로그 통계 (24시간)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_logs = SystemLog.query.filter(SystemLog.timestamp >= yesterday).count()
        error_logs = SystemLog.query.filter(
            SystemLog.timestamp >= yesterday,
            SystemLog.level == 'ERROR'
        ).count()
        
        # 설정 변경 통계 (7일)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_config_changes = ConfigHistory.query.filter(
            ConfigHistory.changed_at >= week_ago
        ).count()
        
        stats = {
            'users': {
                'total': total_users,
                'active': active_users,
                'inactive': inactive_users,  # 비활성 사용자 추가
                'admins': admin_users,
                'online': online_users
            },
            'logs': {
                'recent_24h': recent_logs,
                'errors_24h': error_logs
            },
            'configs': {
                'changes_7d': recent_config_changes
            },
            'system': {
                'database_size': 'N/A',  # TODO: SQLite 파일 크기 조회
                'uptime': 'N/A'  # TODO: 시스템 가동시간 조회
            }
        }
        
        return success_response(
            data=stats,
            message='시스템 통계 조회 성공'
        )
        
    except Exception as e:
        log_admin_event('ERROR', 'ADMIN', f'시스템 통계 조회 실패: {e}')
        return error_response('시스템 통계 조회 중 오류가 발생했습니다.', 'DATABASE_ERROR', 500)

@admin_api_bp.route('/api/admin/logs/recent', methods=['GET'])
@admin_required
@handle_api_errors
def get_recent_logs():
    """최근 로그 조회 (사용자명 표시, 한국시간 적용)"""
    try:
        # 최근 로그와 사용자 정보를 함께 조회
        recent_logs_query = db.session.query(SystemLog, User.username).outerjoin(
            User, SystemLog.message.like(f'%사용자%')
        ).order_by(SystemLog.timestamp.desc()).limit(20)
        
        # 단순하게 최근 로그만 조회하고 메시지에서 사용자명 추출
        recent_logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(20).all()
        
        logs_data = []
        for log in recent_logs:
            # 시간
            timestamp_str = log.timestamp.isoformat() if log.timestamp else None
            
            # 메시지에서 사용자 ID 추출하여 사용자명으로 변경
            message = log.message
            if '사용자 ' in message and message.count('사용자 ') > 0:
                # 메시지에서 "사용자 1", "사용자 2" 등을 실제 사용자명으로 변경
                import re
                user_id_pattern = r'사용자 (\d+)'
                matches = re.findall(user_id_pattern, message)
                for user_id in matches:
                    try:
                        user = User.query.get(int(user_id))
                        if user:
                            message = message.replace(f'사용자 {user_id}', f'{user.username}')
                    except:
                        pass
                
            logs_data.append({
                'id': log.id,
                'timestamp': timestamp_str,
                'level': log.level,
                'category': log.category,
                'message': message,
                'ip_address': log.ip_address
            })
        
        return success_response(data=logs_data, message='최근 로그 조회 성공')
        
    except Exception as e:
        log_admin_event('ERROR', 'ADMIN', f'최근 로그 조회 실패: {e}')
        return error_response('로그 조회 중 오류가 발생했습니다.', 'LOGS_ERROR', 500)

@admin_api_bp.route('/api/admin/logs/cleanup', methods=['POST'])
@admin_required
@handle_api_errors
def cleanup_logs():
    """시스템 로그 정리 (수정: 모든 로그 삭제)"""
    try:
        # 모든 시스템 로그 삭제
        deleted_logs_count = SystemLog.query.delete()
        
        # 모든 설정 변경 이력 삭제
        deleted_configs_count = ConfigHistory.query.delete()
        
        db.session.commit()
        
        log_admin_event('INFO', 'ADMIN', f'모든 로그 정리 완료: 로그 {deleted_logs_count}개, 설정이력 {deleted_configs_count}개 삭제 - 관리자: {session.get("username")}')
        
        return success_response(
            data={
                'deleted_logs': deleted_logs_count,
                'deleted_configs': deleted_configs_count
            },
            message=f'모든 로그 정리 완료: {deleted_logs_count}개 로그, {deleted_configs_count}개 설정 이력 삭제'
        )
        
    except Exception as e:
        db.session.rollback()
        log_admin_event('ERROR', 'ADMIN', f'로그 정리 실패: {e}')
        return error_response('로그 정리 중 오류가 발생했습니다.', 'DATABASE_ERROR', 500)

@admin_api_bp.route('/api/admin/config/<int:config_id>', methods=['GET'])
@admin_required
@handle_api_errors
def get_config_change_detail(config_id):
    """설정 변경 상세 정보 조회 (한국시간 적용, 사용자명 표시)"""
    try:
        config_change = ConfigHistory.query.get(config_id)
        if not config_change:
            return error_response('설정 변경 내역을 찾을 수 없습니다.', 'CONFIG_NOT_FOUND', 404)
        
        # 사용자 정보도 함께 조회
        user = User.query.get(config_change.user_id)
        
        # UTC → 한국시간 변환
        changed_at_str = to_kst_string(config_change.changed_at)
        
        detail = {
            'id': config_change.id,
            'user_id': config_change.user_id,
            'username': user.username if user else 'Unknown',
            'config_key': config_change.config_key,
            'old_value': config_change.old_value,
            'new_value': config_change.new_value,
            'changed_at': changed_at_str,
            'ip_address': config_change.ip_address,
            'user_agent': config_change.user_agent
        }
        
        return success_response(
            data=detail,
            message='설정 변경 상세 정보 조회 성공'
        )
        
    except Exception as e:
        log_admin_event('ERROR', 'ADMIN', f'설정 변경 상세 조회 실패 (ID: {config_id}): {e}')
        return error_response('설정 변경 상세 정보 조회 중 오류가 발생했습니다.', 'DATABASE_ERROR', 500)

# ============================================================================
# 에러 핸들러
# ============================================================================

@admin_api_bp.errorhandler(404)
def admin_api_not_found(error):
    """관리자 API 404 에러"""
    return error_response('요청한 관리자 API를 찾을 수 없습니다.', 'API_NOT_FOUND', 404)

@admin_api_bp.errorhandler(500)
def admin_api_internal_error(error):
    """관리자 API 500 에러"""
    log_admin_event('ERROR', 'ADMIN_API', f'내부 서버 오류: {error}')
    return error_response('관리자 API 내부 오류가 발생했습니다.', 'INTERNAL_ERROR', 500)