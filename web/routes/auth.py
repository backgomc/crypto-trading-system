# 파일 경로: web/routes/auth.py
# 코드명: 인증 관련 라우터 (로그인/로그아웃)

from flask import Blueprint, render_template, request, session, redirect, url_for
from datetime import datetime, timedelta
from config.models import User, SystemLog, db

auth_bp = Blueprint('auth', __name__)

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

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    # 이미 로그인된 경우 대시보드로 리다이렉트
    if session.get('logged_in'):
        return redirect(url_for('pages.dashboard'))
    
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
            
            # 신규 사용자 설정 초기화 체크
            try:
                from api.utils import init_user_config_if_needed
                init_user_config_if_needed(user.id)
            except Exception as e:
                print(f"사용자 설정 체크 오류: {e}")
            
            # 다음 페이지로 리다이렉트
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('pages.dashboard'))
        
        else:
            # 로그인 실패
            error_msg = '잘못된 사용자명 또는 비밀번호입니다.'
            log_system_event('WARNING', 'LOGIN', f'로그인 실패: 잘못된 인증 정보 - {username}')
            return render_template('login.html', error=error_msg)
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """로그아웃"""
    username = session.get('username', 'Unknown')
    
    # 로그아웃 로그
    log_system_event('INFO', 'LOGIN', f'로그아웃: {username}')
    
    # 세션 클리어
    session.clear()
    
    return redirect(url_for('auth.login'))