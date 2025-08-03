# 파일 경로: web/routes/auth.py
# 코드명: 인증 관련 라우터 (로그인/로그아웃) - 세션 관리 추가

from flask import Blueprint, render_template, request, session, redirect, url_for
from datetime import datetime, timedelta
from config.models import User, SystemLog, UserSession, db
import secrets

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
   # 팝업 파라미터 확인
   popup_type = request.args.get('popup')
   show_popup = popup_type in ['session_expired', 'session_invalid']
   
   # 이미 로그인된 경우 처리
   if session.get('logged_in') and not show_popup:
       session_id = session.get('session_id')
       if session_id and UserSession.get_active_session(session_id):  # ✅ 중복 import 제거
           return redirect(url_for('pages.dashboard'))
       # 세션이 무효하면 클리어만 하고 로그인 페이지 표시
       session.clear()
   
   if request.method == 'POST':
       username = request.form.get('username', '').strip()
       password = request.form.get('password', '')
       remember_me = request.form.get('remember_me') == 'on'
       force_login = request.form.get('force_login') == 'true'
       
       # 입력 유효성 검사
       if not username or not password:
           error_msg = '사용자명과 비밀번호를 모두 입력해주세요.'
           log_system_event('WARNING', 'LOGIN', f'로그인 실패: 빈 필드 - {username}')
           return render_template('login.html', error=error_msg, show_popup=show_popup, popup_type=popup_type)
       
       # 사용자 조회
       user = User.query.filter_by(username=username).first()
       
       if user and user.check_password(password) and user.is_active:
           # 기존 세션 무효화
           invalidated_count = UserSession.invalidate_user_sessions(user.id)
           
           if invalidated_count > 0:
               if force_login:
                   log_system_event('INFO', 'LOGIN', f'강제 로그인: {username} - {invalidated_count}개 기존 세션 무효화')
               else:
                   log_system_event('INFO', 'LOGIN', f'중복 로그인 감지: {username} - {invalidated_count}개 기존 세션 무효화')
           
           # 새 세션 생성
           new_session_id = secrets.token_hex(32)
           
           try:
               UserSession.create_session(
                   user_id=user.id,
                   session_id=new_session_id,
                   ip_address=request.remote_addr,
                   user_agent=request.headers.get('User-Agent', '')
               )
           except Exception as e:
               print(f"세션 생성 실패: {e}")
               error_msg = '로그인 처리 중 오류가 발생했습니다.'
               return render_template('login.html', error=error_msg, show_popup=show_popup, popup_type=popup_type)
           
           # 로그인 성공 - 세션 설정
           session.permanent = remember_me
           session['logged_in'] = True
           session['user_id'] = user.id
           session['username'] = user.username
           session['is_admin'] = user.is_admin
           session['session_id'] = new_session_id
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
           
           # 신규 사용자 설정 초기화
           try:
               from config.models import init_user_config, get_user_full_config
               existing_config = get_user_full_config(user.id)
               if not existing_config or len(existing_config) == 0:
                   init_user_config(user.id)
           except Exception as e:
               print(f"사용자 설정 체크 오류: {e}")
           
           # 리다이렉트
           next_page = request.args.get('next')
           if next_page and next_page.startswith('/'):
               return redirect(next_page)
           return redirect(url_for('pages.dashboard'))
       
       else:
           # 로그인 실패
           if user and not user.is_active:
               error_msg = '비활성화된 계정입니다. 관리자에게 문의하세요.'
               log_system_event('WARNING', 'LOGIN', f'로그인 실패: 비활성 계정 - {username}')
           else:
               error_msg = '잘못된 사용자명 또는 비밀번호입니다.'
               log_system_event('WARNING', 'LOGIN', f'로그인 실패: 잘못된 인증 정보 - {username}')
           return render_template('login.html', error=error_msg, show_popup=show_popup, popup_type=popup_type)
   
   return render_template('login.html', show_popup=show_popup, popup_type=popup_type)

@auth_bp.route('/logout')
def logout():
    """로그아웃"""
    username = session.get('username', 'Unknown')
    session_id = session.get('session_id')
    
    # ✅ DB에서 세션 무효화
    if session_id:
        UserSession.invalidate_session(session_id)
    
    # 로그아웃 로그
    log_system_event('INFO', 'LOGIN', f'로그아웃: {username}')
    
    # 세션 클리어
    session.clear()
    
    return redirect(url_for('auth.login'))

# ✅ 세션 유효성 검사 미들웨어 함수
def check_session_validity():
    """세션 유효성 검사"""
    if session.get('logged_in'):
        session_id = session.get('session_id')
        if session_id:
            # DB에서 세션 확인
            db_session = UserSession.get_active_session(session_id)
            if db_session:
                # 세션 활동 시간 업데이트
                UserSession.update_activity(session_id)
                return True
            else:
                # 세션이 무효하면 로그아웃 처리
                session.clear()
                return False
    return False