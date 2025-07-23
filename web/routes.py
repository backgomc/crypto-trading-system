# 파일 경로: web/routes.py
# 코드명: Flask 라우트 및 로그인 시스템 (크롤러 감지 기능 추가)

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from functools import wraps
from datetime import datetime, timedelta
import os
from config.models import User, SystemLog, db

web_bp = Blueprint('web', __name__)

def is_crawler(user_agent):
    """크롤러(소셜미디어 봇) 감지 함수"""
    if not user_agent:
        return False
    
    crawler_list = [
        'facebookexternalhit',  # 페이스북
        'twitterbot',          # 트위터  
        'linkedinbot',         # 링크드인
        'kakao',               # 카카오톡
        'kakaotalk',           # 카카오톡
        'whatsapp',            # 왓츠앱
        'googlebot',           # 구글
        'bingbot',             # 빙
        'slackbot',            # 슬랙
        'telegrambot',         # 텔레그램
        'discordbot',          # 디스코드
        'bot',                 # 일반 봇
        'crawler',             # 크롤러
        'spider'               # 스파이더
    ]
    
    user_agent_lower = user_agent.lower()
    return any(crawler in user_agent_lower for crawler in crawler_list)

# 로그인 필요 데코레이터 (dashboard 제외)
def login_required(f):
    """로그인이 필요한 페이지에 사용하는 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('logged_in'):
            return redirect(url_for('web.login'))
        return f(*args, **kwargs)
    return decorated_function

def log_system_event(level, category, message, ip_address=None, user_agent=None):
    """시스템 이벤트 로깅"""
    try:
        log_entry = SystemLog(
            level=level,
            category=category,
            message=message,
            ip_address=ip_address or request.remote_addr,
            user_agent=user_agent or request.headers.get('User-Agent', '')[:200]
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"로그 저장 실패: {e}")

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    # 이미 로그인된 경우 대시보드로 리다이렉트
    if session.get('logged_in'):
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        # 입력 유효성 검사
        if not username or not password:
            error_msg = '사용자명과 비밀번호를 모두 입력해주세요.'
            log_system_event('WARNING', 'LOGIN', f'로그인 실패: 빈 필드 - {username}')
            return render_template('login.html', error=error_msg)
        
        # 사용자 조회
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            # 로그인 성공
            session.permanent = remember_me
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            session['login_time'] = datetime.utcnow().isoformat()
            
            # 로그인 시간 업데이트
            user.update_last_login()
            
            # 세션 유지 시간 설정
            if remember_me:
                session.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent_session_lifetime = timedelta(hours=8)
            
            # 로그인 성공 로그
            log_system_event('INFO', 'LOGIN', f'로그인 성공: {username}')
            
            # 다음 페이지로 리다이렉트 (원래 가려던 페이지 또는 대시보드)
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('web.dashboard'))
        
        else:
            # 로그인 실패
            error_msg = '잘못된 사용자명 또는 비밀번호입니다.'
            log_system_event('WARNING', 'LOGIN', f'로그인 실패: 잘못된 인증 정보 - {username}')
            return render_template('login.html', error=error_msg)
    
    return render_template('login.html')

@web_bp.route('/logout')
def logout():
    """로그아웃"""
    username = session.get('username', 'Unknown')
    
    # 로그아웃 로그
    log_system_event('INFO', 'LOGIN', f'로그아웃: {username}')
    
    # 세션 클리어
    session.clear()
    
    return redirect(url_for('web.login'))

@web_bp.route('/')
def dashboard():
    """메인 대시보드 (크롤러는 메타태그만, 일반 사용자는 로그인 필요)"""
    user_agent = request.headers.get('User-Agent', '')
    
    # 크롤러인 경우 로그인 체크 없이 기존 base.html의 메타 태그만 제공
    if is_crawler(user_agent):
        log_system_event('INFO', 'CRAWLER', f'크롤러 접근: {user_agent[:100]}')
        # 빈 dashboard.html을 렌더링하되, 메타 태그는 base.html에서 처리
        return render_template('dashboard.html', user={'username': None, 'logged_in': False})
    
    # 일반 사용자는 로그인 체크
    if 'logged_in' not in session or not session.get('logged_in'):
        return redirect(url_for('web.login'))
        
    user_info = {
        'username': session.get('username'),
        'login_time': session.get('login_time'),
        'is_admin': session.get('is_admin', False)
    }
    return render_template('dashboard.html', user=user_info)

@web_bp.route('/ai-model')
@login_required
def ai_model():
    """AI 모델 관리 페이지 (로그인 필요, 크롤러 예외 처리)"""
    user_info = {
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    }
    
    # AI 모델 관리 접속 로그
    log_system_event('INFO', 'AI_MODEL', f'AI 모델 관리 페이지 접속: {session.get("username")}')
    
    return render_template('ai_model.html', user=user_info)

@web_bp.route('/settings')
@login_required
def settings():
    """설정 페이지 (로그인 필요, 크롤러 예외 처리)"""
    user_info = {
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    }
    return render_template('settings.html', user=user_info)

@web_bp.route('/api/status')
@login_required
def api_status():
    """시스템 상태 API"""
    return jsonify({
        'status': 'ok',
        'user': session.get('username'),
        'timestamp': datetime.utcnow().isoformat()
    })

@web_bp.route('/health')
def health_check():
    """헬스 체크 (로그인 불필요)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

# 에러 핸들러
@web_bp.errorhandler(404)
def not_found(error):
    """404 에러 처리"""
    if session.get('logged_in'):
        return render_template('dashboard.html', error='페이지를 찾을 수 없습니다.'), 404
    else:
        return redirect(url_for('web.login'))

@web_bp.errorhandler(403)
def forbidden(error):
    """403 에러 처리"""
    return redirect(url_for('web.login'))

@web_bp.errorhandler(500)
def internal_error(error):
    """500 에러 처리"""
    log_system_event('ERROR', 'SYSTEM', f'Internal server error: {error}')
    db.session.rollback()
    if session.get('logged_in'):
        return render_template('dashboard.html', error='시스템 오류가 발생했습니다.'), 500
    else:
        return redirect(url_for('web.login'))