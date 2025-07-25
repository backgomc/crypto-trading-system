# 파일 경로: web/routes.py
# 코드명: Flask 라우트 및 API First 설정 관리

from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from functools import wraps
from datetime import datetime, timedelta
import json
from config.models import User, SystemLog, db

web_bp = Blueprint('web', __name__)

# ============================================================================
# 유틸리티 함수들
# ============================================================================

def login_required(f):
    """로그인이 필요한 페이지에 사용하는 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('logged_in'):
            return redirect(url_for('web.login'))
        return f(*args, **kwargs)
    return decorated_function

def api_required(f):
    """API 인증 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return api_error('로그인이 필요합니다', 'AUTH_REQUIRED', 401)
        return f(*args, **kwargs)
    return decorated_function

def api_success(data=None, message='성공'):
    """API 성공 응답"""
    response = {
        'success': True,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'meta': {
            'user_id': session.get('user_id'),
            'request_id': f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    }
    if data is not None:
        response['data'] = data
    return jsonify(response)

def api_error(message, code='ERROR', status_code=400, details=None):
    """API 오류 응답"""
    response = {
        'success': False,
        'error': message,
        'code': code,
        'timestamp': datetime.utcnow().isoformat(),
        'meta': {
            'user_id': session.get('user_id'),
            'request_id': f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    }
    if details:
        response['details'] = details
    return jsonify(response), status_code

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

# ============================================================================
# 설정 관리 함수들
# ============================================================================

def get_default_config():
    """기본 설정 반환"""
    return {
        "trading": {
            "demo_mode": True,
            "virtual_balance": 10000,
            "symbol": "BTCUSDT",
            "initial_position_size": 0.05,
            "adjustment_size": 0.01,
            "base_threshold": 1000,
            "consecutive_threshold": 4,
            "adaptive_threshold_enabled": True,
            "volatility_window": 20,
            "loop_delay": 60
        },
        "ai": {
            "enabled": True,
            "main_interval": "15",
            "training_days": 365,
            "retrain_interval_days": 14,
            "timeframes": ["1", "5", "15", "60"]
        },
        "risk": {
            "max_loss_percent": 5.0,
            "daily_trade_limit": 10,
            "max_position_size": 0.5,
            "emergency_stop_enabled": True,
            "consecutive_loss_limit": 3,
            "cooldown_minutes": 30
        },
        "notifications": {
            "telegram_enabled": True,
            "email_enabled": False,
            "frequency": "all",
            "profit_threshold_krw": 1000
        }
    }

def load_user_config(user_id):
    """사용자 설정 로드"""
    try:
        from config.models import UserConfig
        
        # 각 섹션별로 설정 조회
        sections = ['trading', 'ai', 'risk', 'notifications']
        config = {}
        
        for section in sections:
            user_config = UserConfig.query.filter_by(
                user_id=user_id, 
                config_key=section
            ).first()
            
            if user_config and user_config.config_value:
                if isinstance(user_config.config_value, str):
                    config[section] = json.loads(user_config.config_value)
                else:
                    config[section] = user_config.config_value
            else:
                # 기본값 사용
                default_config = get_default_config()
                config[section] = default_config[section]
        
        return config
        
    except Exception as e:
        print(f"설정 로드 오류: {e}")
        return get_default_config()

def save_user_config(user_id, config_data):
    """사용자 설정 저장"""
    try:
        from config.models import UserConfig
        
        success_count = 0
        
        for section, data in config_data.items():
            if section not in ['trading', 'ai', 'risk', 'notifications']:
                continue
                
            # 기존 설정 조회 또는 생성
            user_config = UserConfig.query.filter_by(
                user_id=user_id, 
                config_key=section
            ).first()
            
            if not user_config:
                user_config = UserConfig(
                    user_id=user_id,
                    config_key=section
                )
                db.session.add(user_config)
            
            # JSON 직렬화하여 저장
            user_config.config_value = json.dumps(data) if isinstance(data, dict) else data
            user_config.updated_at = datetime.utcnow()
            
            success_count += 1
        
        db.session.commit()
        return success_count > 0
        
    except Exception as e:
        print(f"설정 저장 오류: {e}")
        db.session.rollback()
        return False

def validate_config(config_data):
    """설정 유효성 검사"""
    errors = []
    
    # 검증 규칙
    validation_rules = {
        'trading': {
            'initial_position_size': {'min': 0.001, 'max': 1.0, 'type': float},
            'adjustment_size': {'min': 0.001, 'max': 0.1, 'type': float},
            'base_threshold': {'min': 100, 'max': 10000, 'type': int},
            'consecutive_threshold': {'min': 2, 'max': 10, 'type': int},
            'volatility_window': {'min': 5, 'max': 100, 'type': int},
            'loop_delay': {'min': 10, 'max': 300, 'type': int},
            'virtual_balance': {'min': 1000, 'max': 1000000, 'type': float}
        },
        'ai': {
            'training_days': {'min': 30, 'max': 1095, 'type': int},
            'retrain_interval_days': {'min': 1, 'max': 30, 'type': int}
        },
        'risk': {
            'max_loss_percent': {'min': 1.0, 'max': 20.0, 'type': float},
            'daily_trade_limit': {'min': 1, 'max': 100, 'type': int},
            'max_position_size': {'min': 0.01, 'max': 2.0, 'type': float},
            'consecutive_loss_limit': {'min': 2, 'max': 10, 'type': int},
            'cooldown_minutes': {'min': 5, 'max': 120, 'type': int}
        },
        'notifications': {
            'profit_threshold_krw': {'min': 100, 'max': 100000, 'type': int}
        }
    }
    
    for section, data in config_data.items():
        if section not in validation_rules:
            continue
            
        section_rules = validation_rules[section]
        
        for field, value in data.items():
            if field not in section_rules:
                continue
                
            rule = section_rules[field]
            
            # 타입 검사
            if rule['type'] == int:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    errors.append(f"{section}.{field}: 정수 값이어야 합니다")
                    continue
            elif rule['type'] == float:
                try:
                    value = float(value)
                except (ValueError, TypeError):
                    errors.append(f"{section}.{field}: 숫자 값이어야 합니다")
                    continue
            
            # 범위 검사
            if 'min' in rule and value < rule['min']:
                errors.append(f"{section}.{field}: {rule['min']} 이상이어야 합니다")
            if 'max' in rule and value > rule['max']:
                errors.append(f"{section}.{field}: {rule['max']} 이하여야 합니다")
    
    return len(errors) == 0, errors

def init_user_config(user_id):
    """신규 사용자 기본 설정 초기화"""
    try:
        default_config = get_default_config()
        return save_user_config(user_id, default_config)
    except Exception as e:
        print(f"사용자 설정 초기화 오류: {e}")
        return False

# ============================================================================
# 웹 페이지 라우트
# ============================================================================

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    if session.get('logged_in'):
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        if not username or not password:
            error_msg = '사용자명과 비밀번호를 모두 입력해주세요.'
            log_system_event('WARNING', 'LOGIN', f'로그인 실패: 빈 필드 - {username}')
            return render_template('login.html', error=error_msg)
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            # 로그인 성공
            session.permanent = remember_me
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            session['login_time'] = datetime.utcnow().isoformat()
            
            user.update_last_login()
            
            if remember_me:
                session.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent_session_lifetime = timedelta(hours=8)
            
            log_system_event('INFO', 'LOGIN', f'로그인 성공: {username}')
            
            # 신규 사용자 설정 초기화 체크
            try:
                config = load_user_config(user.id)
                if not config or len(config) == 0:
                    init_user_config(user.id)
            except Exception as e:
                print(f"사용자 설정 체크 오류: {e}")
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('web.dashboard'))
        
        else:
            error_msg = '잘못된 사용자명 또는 비밀번호입니다.'
            log_system_event('WARNING', 'LOGIN', f'로그인 실패: 잘못된 인증 정보 - {username}')
            return render_template('login.html', error=error_msg)
    
    return render_template('login.html')

@web_bp.route('/logout')
def logout():
    """로그아웃"""
    username = session.get('username', 'Unknown')
    log_system_event('INFO', 'LOGIN', f'로그아웃: {username}')
    session.clear()
    return redirect(url_for('web.login'))

@web_bp.route('/')
@login_required
def dashboard():
    """메인 대시보드"""
    user_info = {
        'username': session.get('username'),
        'login_time': session.get('login_time'),
        'is_admin': session.get('is_admin', False)
    }
    return render_template('dashboard.html', user=user_info)

@web_bp.route('/ai-model')
@login_required
def ai_model():
    """AI 모델 관리 페이지"""
    user_info = {
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    }
    log_system_event('INFO', 'AI_MODEL', f'AI 모델 관리 페이지 접속: {session.get("username")}')
    return render_template('ai_model.html', user=user_info)

@web_bp.route('/settings')
@login_required
def settings():
    """설정 페이지"""
    user_info = {
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False)
    }
    return render_template('settings.html', user=user_info)

# ============================================================================
# 설정 API (API First 설계)
# ============================================================================

@web_bp.route('/api/config', methods=['GET'])
@api_required
def get_config():
    """사용자 설정 조회"""
    try:
        user_id = session.get('user_id')
        config = load_user_config(user_id)
        
        log_system_event('INFO', 'API', f'설정 조회: 사용자 {user_id}')
        
        return api_success(
            data={'config': config},
            message='설정 조회 성공'
        )
        
    except Exception as e:
        print(f"설정 조회 예외: {e}")
        log_system_event('ERROR', 'API', f'설정 조회 실패: {e}')
        return api_error('설정 조회 중 오류가 발생했습니다', 'CONFIG_ERROR', 500)

@web_bp.route('/api/config', methods=['PUT'])
@api_required
def update_config():
    """설정 업데이트 (부분 업데이트 지원)"""
    try:
        user_id = session.get('user_id')
        
        # 요청 데이터 검증
        data = request.get_json()
        if not data or 'config' not in data:
            return api_error('config 데이터가 필요합니다', 'INVALID_REQUEST', 400)
        
        new_config = data['config']
        
        # 기존 설정 로드
        current_config = load_user_config(user_id)
        
        # 부분 업데이트: 새로운 값으로 기존 설정 업데이트
        for section, section_data in new_config.items():
            if section in current_config:
                current_config[section].update(section_data)
            else:
                current_config[section] = section_data
        
        # 유효성 검사
        is_valid, errors = validate_config(current_config)
        if not is_valid:
            return api_error(
                '설정 검증 실패',
                'VALIDATION_ERROR',
                400,
                {'validation_errors': errors}
            )
        
        # 설정 저장
        success = save_user_config(user_id, current_config)
        
        if success:
            log_system_event('INFO', 'API', f'설정 업데이트: 사용자 {user_id}')
            
            return api_success(
                data={'config': current_config},
                message='설정이 성공적으로 업데이트되었습니다'
            )
        else:
            return api_error('설정 저장에 실패했습니다', 'SAVE_ERROR', 500)
            
    except Exception as e:
        print(f"설정 업데이트 예외: {e}")
        log_system_event('ERROR', 'API', f'설정 업데이트 실패: {e}')
        return api_error('설정 업데이트 중 오류가 발생했습니다', 'CONFIG_ERROR', 500)

@web_bp.route('/api/config/reset', methods=['POST'])
@api_required
def reset_config():
    """설정 기본값 복원"""
    try:
        user_id = session.get('user_id')
        
        # 기본 설정으로 초기화
        default_config = get_default_config()
        success = save_user_config(user_id, default_config)
        
        if success:
            log_system_event('INFO', 'API', f'설정 초기화: 사용자 {user_id}')
            
            return api_success(
                data={'config': default_config},
                message='모든 설정이 기본값으로 복원되었습니다'
            )
        else:
            return api_error('설정 초기화에 실패했습니다', 'RESET_ERROR', 500)
            
    except Exception as e:
        print(f"설정 초기화 예외: {e}")
        log_system_event('ERROR', 'API', f'설정 초기화 실패: {e}')
        return api_error('설정 초기화 중 오류가 발생했습니다', 'CONFIG_ERROR', 500)

@web_bp.route('/api/config/preset/<preset_type>', methods=['POST'])
@api_required
def apply_config_preset(preset_type):
    """프리셋 설정 적용"""
    try:
        user_id = session.get('user_id')
        
        # 프리셋 정의
        presets = {
            'conservative': {
                'trading': {
                    'demo_mode': True,
                    'virtual_balance': 10000,
                    'initial_position_size': 0.03,
                    'adjustment_size': 0.005,
                    'base_threshold': 1500,
                    'consecutive_threshold': 3,
                    'adaptive_threshold_enabled': True,
                    'volatility_window': 25,
                    'loop_delay': 90
                },
                'risk': {
                    'max_loss_percent': 3.0,
                    'daily_trade_limit': 5,
                    'max_position_size': 0.3,
                    'emergency_stop_enabled': True,
                    'consecutive_loss_limit': 2,
                    'cooldown_minutes': 60
                },
                'ai': {
                    'enabled': True,
                    'main_interval': '15',
                    'training_days': 180,
                    'retrain_interval_days': 7
                }
            },
            'balanced': {
                'trading': {
                    'demo_mode': True,
                    'virtual_balance': 10000,
                    'initial_position_size': 0.05,
                    'adjustment_size': 0.01,
                    'base_threshold': 1000,
                    'consecutive_threshold': 4,
                    'adaptive_threshold_enabled': True,
                    'volatility_window': 20,
                    'loop_delay': 60
                },
                'risk': {
                    'max_loss_percent': 5.0,
                    'daily_trade_limit': 10,
                    'max_position_size': 0.5,
                    'emergency_stop_enabled': True,
                    'consecutive_loss_limit': 3,
                    'cooldown_minutes': 30
                },
                'ai': {
                    'enabled': True,
                    'main_interval': '15',
                    'training_days': 365,
                    'retrain_interval_days': 14
                }
            },
            'aggressive': {
                'trading': {
                    'demo_mode': True,
                    'virtual_balance': 20000,
                    'initial_position_size': 0.08,
                    'adjustment_size': 0.02,
                    'base_threshold': 500,
                    'consecutive_threshold': 5,
                    'adaptive_threshold_enabled': True,
                    'volatility_window': 15,
                    'loop_delay': 30
                },
                'risk': {
                    'max_loss_percent': 8.0,
                    'daily_trade_limit': 20,
                    'max_position_size': 1.0,
                    'emergency_stop_enabled': True,
                    'consecutive_loss_limit': 5,
                    'cooldown_minutes': 15
                },
                'ai': {
                    'enabled': True,
                    'main_interval': '5',
                    'training_days': 730,
                    'retrain_interval_days': 7
                }
            }
        }
        
        if preset_type not in presets:
            return api_error(
                f'지원하지 않는 프리셋: {preset_type}',
                'INVALID_PRESET',
                400
            )
        
        # 기존 설정 로드 후 프리셋 적용
        current_config = load_user_config(user_id)
        preset_config = presets[preset_type]
        
        # 프리셋 설정으로 업데이트 (기존 notifications 설정은 유지)
        for section, section_data in preset_config.items():
            current_config[section].update(section_data)
        
        # 설정 저장
        success = save_user_config(user_id, current_config)
        
        if success:
            preset_names = {
                'conservative': '보수적',
                'balanced': '균형',
                'aggressive': '공격적'
            }
            
            log_system_event('INFO', 'API', f'{preset_type} 프리셋 적용: 사용자 {user_id}')
            
            return api_success(
                data={'config': current_config},
                message=f'{preset_names[preset_type]} 설정이 적용되었습니다'
            )
        else:
            return api_error('프리셋 적용에 실패했습니다', 'PRESET_ERROR', 500)
            
    except Exception as e:
        print(f"프리셋 적용 예외: {e}")
        log_system_event('ERROR', 'API', f'프리셋 적용 실패: {e}')
        return api_error('프리셋 적용 중 오류가 발생했습니다', 'CONFIG_ERROR', 500)

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
    """헬스 체크"""
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