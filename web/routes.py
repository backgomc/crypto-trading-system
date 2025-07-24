# 파일 경로: web/routes.py
# 코드명: Flask 라우트 및 로그인 시스템 + 설정 API 추가

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from functools import wraps
from datetime import datetime, timedelta
import os
from config.models import User, SystemLog, db
from api.utils import (
    api_required, error_response, success_response, 
    validate_request_data, handle_api_errors,
    validate_trading_config, log_config_change
)

web_bp = Blueprint('web', __name__)

# 로그인 필요 데코레이터
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

# ============================================================================
# 웹 페이지 라우트
# ============================================================================

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
            
            # 신규 사용자 설정 초기화
            from config.settings import init_new_user, load_user_config
            try:
                # 기존 설정이 있는지 확인
                existing_config = load_user_config(user.id)
                if not existing_config or len(existing_config) == 0:
                    init_new_user(user.id)
            except Exception as e:
                print(f"사용자 설정 초기화 오류: {e}")
            
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
@login_required
def dashboard():
    """메인 대시보드 (로그인 필요)"""
    user_info = {
        'username': session.get('username'),
        'login_time': session.get('login_time'),
        'is_admin': session.get('is_admin', False)
    }
    return render_template('dashboard.html', user=user_info)

@web_bp.route('/ai-model')
@login_required
def ai_model():
    """AI 모델 관리 페이지 (로그인 필요)"""
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
    """설정 페이지 (로그인 필요)"""
    user_info = {
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    }
    return render_template('settings.html', user=user_info)

# ============================================================================
# 설정 관련 API
# ============================================================================

@web_bp.route('/api/settings', methods=['GET'])
@api_required
@handle_api_errors
def get_settings():
    """현재 사용자 설정 조회"""
    try:
        from config.settings import load_user_config
        
        user_id = session.get('user_id')
        config = load_user_config(user_id)
        
        log_system_event('INFO', 'API', f'설정 조회: 사용자 {user_id}')
        
        return success_response(
            data=config,
            message='설정 조회 성공'
        )
        
    except Exception as e:
        log_system_event('ERROR', 'API', f'설정 조회 실패: {e}')
        return error_response('설정 조회 중 오류가 발생했습니다', 'SETTINGS_ERROR', 500)

@web_bp.route('/api/settings', methods=['POST'])
@api_required
@handle_api_errors  
def save_settings():
    """사용자 설정 저장"""
    try:
        from config.settings import save_user_config, get_user_config_value
        
        # 요청 데이터 검증
        data, error = validate_request_data(
            request,
            required_fields=['config_key', 'config_value']
        )
        if error:
            return error
        
        user_id = session.get('user_id')
        config_key = data['config_key']
        config_value = data['config_value']
        
        # 매매 설정인 경우 추가 검증
        if config_key in ['trading_settings', 'ai_settings', 'risk_management']:
            valid, errors = validate_trading_config({config_key: config_value})
            if not valid:
                return error_response(
                    '설정 검증 실패', 
                    'VALIDATION_ERROR', 
                    400, 
                    {'errors': errors}
                )
        
        # 기존 값 조회 (로깅용)
        old_value = get_user_config_value(user_id, config_key)
        
        # 설정 저장
        success = save_user_config(
            user_id=user_id,
            config_key=config_key,
            config_value=config_value,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        if success:
            log_system_event('INFO', 'SETTINGS', f'설정 저장 성공: {config_key}')
            log_config_change(config_key, old_value, config_value)
            
            return success_response(
                message=f'{config_key} 설정이 저장되었습니다'
            )
        else:
            return error_response('설정 저장에 실패했습니다', 'SAVE_ERROR', 500)
            
    except Exception as e:
        log_system_event('ERROR', 'API', f'설정 저장 실패: {e}')
        return error_response('설정 저장 중 오류가 발생했습니다', 'SETTINGS_ERROR', 500)

@web_bp.route('/api/settings/bulk', methods=['POST'])
@api_required
@handle_api_errors
def save_settings_bulk():
    """사용자 설정 일괄 저장"""
    try:
        from config.settings import update_user_config
        
        # 요청 데이터 검증
        data, error = validate_request_data(
            request,
            required_fields=['settings']
        )
        if error:
            return error
        
        user_id = session.get('user_id')
        settings = data['settings']
        
        # 전체 설정 검증
        valid, errors = validate_trading_config(settings)
        if not valid:
            return error_response(
                '설정 검증 실패',
                'VALIDATION_ERROR',
                400,
                {'errors': errors}
            )
        
        # 일괄 저장
        success = update_user_config(
            user_id=user_id,
            config_updates=settings,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        if success:
            log_system_event('INFO', 'SETTINGS', f'설정 일괄 저장 성공: {len(settings)}개 항목')
            
            return success_response(
                message=f'{len(settings)}개 설정이 저장되었습니다'
            )
        else:
            return error_response('설정 일괄 저장에 실패했습니다', 'BULK_SAVE_ERROR', 500)
            
    except Exception as e:
        log_system_event('ERROR', 'API', f'설정 일괄 저장 실패: {e}')
        return error_response('설정 저장 중 오류가 발생했습니다', 'SETTINGS_ERROR', 500)

@web_bp.route('/api/settings/reset', methods=['POST'])
@api_required
@handle_api_errors
def reset_settings():
    """설정 기본값 복원"""
    try:
        from config.settings import init_new_user, load_user_config
        
        user_id = session.get('user_id')
        
        # 기존 설정 백업용 조회
        old_config = load_user_config(user_id)
        
        # 기본 설정으로 초기화
        success = init_new_user(user_id)
        
        if success:
            log_system_event('INFO', 'SETTINGS', f'설정 초기화 성공: 사용자 {user_id}')
            
            # 변경 이력 로깅
            log_config_change('ALL_SETTINGS', old_config, 'RESET_TO_DEFAULT')
            
            return success_response(
                message='모든 설정이 기본값으로 복원되었습니다'
            )
        else:
            return error_response('설정 초기화에 실패했습니다', 'RESET_ERROR', 500)
            
    except Exception as e:
        log_system_event('ERROR', 'API', f'설정 초기화 실패: {e}')
        return error_response('설정 초기화 중 오류가 발생했습니다', 'SETTINGS_ERROR', 500)

@web_bp.route('/api/settings/preset/<preset_type>', methods=['POST'])
@api_required
@handle_api_errors
def apply_preset_settings(preset_type):
    """빠른 설정 적용 (보수적/균형/공격적)"""
    try:
        from config.settings import update_user_config
        
        user_id = session.get('user_id')
        
        # 프리셋 설정 정의
        presets = {
            'conservative': {
                'trading_settings': {
                    'initial_position_size': 0.03,
                    'adjustment_size': 0.005,
                    'base_threshold': 1500,
                    'consecutive_threshold': 3
                },
                'risk_management': {
                    'max_position_size': 0.3,
                    'stop_loss_percentage': 3.0,
                    'take_profit_percentage': 2.0
                }
            },
            'balanced': {
                'trading_settings': {
                    'initial_position_size': 0.05,
                    'adjustment_size': 0.01,
                    'base_threshold': 1000,
                    'consecutive_threshold': 4
                },
                'risk_management': {
                    'max_position_size': 0.5,
                    'stop_loss_percentage': 5.0,
                    'take_profit_percentage': 3.0
                }
            },
            'aggressive': {
                'trading_settings': {
                    'initial_position_size': 0.08,
                    'adjustment_size': 0.02,
                    'base_threshold': 500,
                    'consecutive_threshold': 5
                },
                'risk_management': {
                    'max_position_size': 1.0,
                    'stop_loss_percentage': 8.0,
                    'take_profit_percentage': 5.0
                }
            }
        }
        
        if preset_type not in presets:
            return error_response(
                f'지원하지 않는 프리셋: {preset_type}',
                'INVALID_PRESET',
                400
            )
        
        preset_config = presets[preset_type]
        
        # 프리셋 적용
        success = update_user_config(
            user_id=user_id,
            config_updates=preset_config,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        if success:
            log_system_event('INFO', 'SETTINGS', f'{preset_type} 프리셋 적용 성공: 사용자 {user_id}')
            
            preset_names = {
                'conservative': '보수적',
                'balanced': '균형',
                'aggressive': '공격적'
            }
            
            return success_response(
                message=f'{preset_names[preset_type]} 설정이 적용되었습니다'
            )
        else:
            return error_response('프리셋 적용에 실패했습니다', 'PRESET_ERROR', 500)
            
    except Exception as e:
        log_system_event('ERROR', 'API', f'프리셋 적용 실패: {e}')
        return error_response('프리셋 적용 중 오류가 발생했습니다', 'SETTINGS_ERROR', 500)

# ============================================================================
# 기타 API
# ============================================================================

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

# ============================================================================
# 에러 핸들러
# ============================================================================

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