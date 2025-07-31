# 파일 경로: web/routes/pages.py
# 코드명: 페이지 렌더링 라우터 (대시보드, 설정, AI 모델, 관리자)

from flask import Blueprint, render_template, session, redirect, url_for, request
from functools import wraps
from config.models import SystemLog, User, UserConfig, TradingState, ConfigHistory, db

pages_bp = Blueprint('pages', __name__)

def login_required(f):
    """로그인이 필요한 페이지에 사용하는 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('logged_in'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """관리자 권한이 필요한 페이지에 사용하는 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('logged_in'):
            return redirect(url_for('auth.login'))
        if not session.get('is_admin', False):
            log_system_event('WARNING', 'SECURITY', f'관리자 페이지 무권한 접근 시도: {session.get("username")}')
            return redirect(url_for('pages.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_system_event(level, category, message):
    """시스템 이벤트 로깅"""
    try:
        log_entry = SystemLog(
            level=level,
            category=category,
            message=message,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:200]
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"로그 저장 실패: {e}")

@pages_bp.route('/')
@login_required
def dashboard():
    """메인 대시보드 페이지"""
    user_info = {
        'username': session.get('username'),
        'login_time': session.get('login_time'),
        'is_admin': session.get('is_admin', False)
    }
    
    # 대시보드 접속 로그 (선택적)
    log_system_event('INFO', 'PAGE', f'대시보드 접속: {session.get("username")}')
    
    return render_template('dashboard.html', user=user_info)

@pages_bp.route('/settings')
@login_required
def settings():
    """설정 페이지"""
    user_info = {
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    }
    
    # 설정 페이지 접속 로그 (선택적)
    log_system_event('INFO', 'PAGE', f'설정 페이지 접속: {session.get("username")}')
    
    return render_template('settings.html', user=user_info)

@pages_bp.route('/ai-model')
@login_required
def ai_model():
    """AI 모델 관리 페이지"""
    user_info = {
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    }
    
    # AI 모델 페이지 접속 로그
    log_system_event('INFO', 'AI_MODEL', f'AI 모델 관리 페이지 접속: {session.get("username")}')
    
    return render_template('ai_model.html', user=user_info)

# 파일 경로: web/routes/pages.py
# 코드명: 페이지 라우트 (SQLite 호환 수정)

@pages_bp.route('/admin')
@admin_required
def admin():
    """관리자 페이지 (SQLite 호환 수정)"""
    try:
        print("🔍 DEBUG: admin() 함수 시작")
        
        # 시스템 통계 수집
        total_users = User.query.count()
        print(f"🔍 DEBUG: total_users = {total_users}")
        
        active_users = User.query.filter_by(is_active=True).count()
        print(f"🔍 DEBUG: active_users = {active_users}")
        
        admin_users = User.query.filter_by(is_admin=True).count()
        print(f"🔍 DEBUG: admin_users = {admin_users}")
        
        # 최근 사용자 목록 (SQLite 호환)
        # NULLS LAST 대신 CASE WHEN 사용
        recent_users = User.query.order_by(
            db.case(
                (User.last_login.is_(None), 1),
                else_=0
            ),
            User.last_login.desc()
        ).limit(10).all()
        print(f"🔍 DEBUG: recent_users count = {len(recent_users)}")
        
        # 최근 시스템 로그 (최신 20개)
        recent_logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(20).all()
        print(f"🔍 DEBUG: recent_logs count = {len(recent_logs)}")
        
        # 최근 설정 변경 이력 (최신 10개) 
        recent_configs = ConfigHistory.query.order_by(ConfigHistory.changed_at.desc()).limit(10).all()
        print(f"🔍 DEBUG: recent_configs count = {len(recent_configs)}")
        
        # 전체 사용자 목록 (관리용)
        all_users = User.query.order_by(User.created_at.asc()).all()
        print(f"🔍 DEBUG: all_users count = {len(all_users)}")
        
        admin_data = {
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'admin_users': admin_users,
                'inactive_users': total_users - active_users,
                'online_users': User.get_online_count()
            },
            'recent_users': recent_users,
            'recent_logs': recent_logs,
            'recent_configs': recent_configs,
            'all_users': all_users
        }
        
        user_info = {
            'username': session.get('username'),
            'is_admin': session.get('is_admin', False)
        }
        
        # 관리자 페이지 접속 로그
        log_system_event('INFO', 'ADMIN', f'관리자 페이지 접속: {session.get("username")}')
        
        print("🔍 DEBUG: admin_data 준비 완료")
        return render_template('admin.html', user=user_info, admin_data=admin_data)
        
    except Exception as e:
        print(f"❌ DEBUG: admin() 함수 오류: {e}")
        import traceback
        traceback.print_exc()
        
        # 오류 발생 시 빈 데이터로 처리
        admin_data = {
            'stats': {'total_users': 0, 'active_users': 0, 'admin_users': 0, 'inactive_users': 0},
            'recent_users': [], 'recent_logs': [], 'recent_configs': [], 'all_users': []
        }
        user_info = {'username': session.get('username'), 'is_admin': True}
        
        return render_template('admin.html', user=user_info, admin_data=admin_data, error=f'데이터 로드 중 오류: {str(e)}')

# ============================================================================
# 에러 핸들러 (페이지 관련)
# ============================================================================

@pages_bp.errorhandler(404)
def not_found(error):
    """404 에러 처리"""
    if session.get('logged_in'):
        return render_template('dashboard.html', error='페이지를 찾을 수 없습니다.'), 404
    else:
        return redirect(url_for('auth.login'))

@pages_bp.errorhandler(403)
def forbidden(error):
    """403 에러 처리"""
    return redirect(url_for('auth.login'))