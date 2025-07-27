# 파일 경로: web/routes/pages.py
# 코드명: 페이지 렌더링 라우터 (대시보드, 설정, AI 모델)

from flask import Blueprint, render_template, session, redirect, url_for, request
from functools import wraps
from config.models import SystemLog, db

pages_bp = Blueprint('pages', __name__)

def login_required(f):
    """로그인이 필요한 페이지에 사용하는 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('logged_in'):
            return redirect(url_for('auth.login'))
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