# 파일 경로: web/routes/api.py
# 코드명: API 엔드포인트 라우터 (설정, 시스템, AI)

from flask import Blueprint, request, session, jsonify
from functools import wraps
from datetime import datetime
import json, copy
from config.models import User, UserConfig, SystemLog, ConfigHistory, db, get_kst_now

api_bp = Blueprint('api', __name__)

# ============================================================================
# 데코레이터 및 유틸리티 함수들
# ============================================================================

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
# 설정 관리 함수들 (기존 routes.py에서 이동)
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
                default_config = get_default_config()
                config[section] = default_config[section]
        
        return config
        
    except Exception as e:
        print(f"설정 로드 오류: {e}")
        return get_default_config()

def save_user_config(user_id, config_data):
    """사용자 설정 저장"""
    try:
        success_count = 0
        
        for section, data in config_data.items():
            if section not in ['trading', 'ai', 'risk', 'notifications']:
                continue
                
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

# ============================================================================
# 설정 API 엔드포인트들
# ============================================================================

@api_bp.route('/config', methods=['GET'])
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

@api_bp.route('/config', methods=['PUT'])
@api_required
def update_config():
    """설정 업데이트"""
    try:
        user_id = session.get('user_id')
        
        data = request.get_json()
        if not data or 'config' not in data:
            return api_error('config 데이터가 필요합니다', 'INVALID_REQUEST', 400)
        
        new_config = data['config']
        previous_config = load_user_config(user_id)  # ✅ 저장 전 설정값 백업
        current_config = copy.deepcopy(previous_config)  # ✅ 이후 병합용 (깊은 복사 권장)
        
        # 부분 업데이트
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
            
            # ✅ 설정 이력 저장
            ConfigHistory.log_change(
                user_id=user_id,
                config_key='전체 설정',
                old_value=previous_config,
                new_value=current_config,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )

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

@api_bp.route('/config/reset', methods=['POST'])
@api_required
def reset_config():
    """설정 기본값 복원"""
    try:
        user_id = session.get('user_id')
        
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

@api_bp.route('/config/preset/<preset_type>', methods=['POST'])
@api_required
def apply_config_preset(preset_type):
    """프리셋 설정 적용"""
    try:
        user_id = session.get('user_id')
        
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
        
        current_config = load_user_config(user_id)
        preset_config = presets[preset_type]
        
        # 프리셋 설정으로 업데이트 (notifications 설정은 유지)
        for section, section_data in preset_config.items():
            current_config[section].update(section_data)
        
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
# Ping API (접속 상태 관리)
# ============================================================================

@api_bp.route('/ping', methods=['POST'])
@api_required
def user_ping():
    """사용자 ping (30초마다 호출되어 접속 상태 유지)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return api_error('사용자 정보를 찾을 수 없습니다', 'USER_NOT_FOUND', 401)

        user = User.query.get(user_id)
        if not user:
            return api_error('사용자를 찾을 수 없습니다', 'USER_NOT_FOUND', 404)
        
        # 마지막 활동 시간 업데이트 (한국시간)
        user.update_last_active()
        
        return api_success(
            data={
                'user_id': user_id,
                'username': user.username,
                'last_active': user.last_active.isoformat() if user.last_active else None
            },
            message='ping 성공'
        )
        
    except Exception as e:
        print(f"Ping 오류: {e}")
        return api_error('ping 처리 중 오류가 발생했습니다', 'PING_ERROR', 500)
    
@api_bp.route('/check-session', methods=['POST'])
def check_existing_session():
    """로그인 전 기존 세션 확인 (로그인 불필요)"""
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return api_error('사용자명이 필요합니다', 'INVALID_REQUEST', 400)
        
        username = data['username'].strip()
        
        # 사용자 조회
        user = User.query.filter_by(username=username).first()
        if not user:
            return api_success(data={'has_active_session': False})
        
        # 활성 세션 확인
        from config.models import UserSession
        active_sessions = UserSession.query.filter_by(user_id=user.id, is_active=True).count()
        
        return api_success(
            data={
                'has_active_session': active_sessions > 0,
                'active_sessions_count': active_sessions
            }
        )
        
    except Exception as e:
        print(f"세션 체크 오류: {e}")
        return api_error('세션 확인 중 오류가 발생했습니다', 'SESSION_CHECK_ERROR', 500)    
    
# ============================================================================
# 시스템 API 엔드포인트들
# ============================================================================

@api_bp.route('/status')
@api_required
def api_status():
    """시스템 상태 API"""
    return api_success(
        data={
            'user': session.get('username'),
            'user_id': session.get('user_id'),
            'login_time': session.get('login_time'),
            'is_admin': session.get('is_admin', False)
        },
        message='시스템 상태 조회 성공'
    )

@api_bp.route('/health')
def health_check():
    """헬스 체크 (로그인 불필요)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'NHBot Trading System'
    })

# ============================================================================
# AI 관리 API 엔드포인트들 (TODO: 구현 예정)
# ============================================================================

@api_bp.route('/ai/model/current', methods=['GET'])
@api_required
def get_current_ai_model():
    """현재 활성 AI 모델 정보"""
    # TODO: 실제 AI 모델 정보 구현
    mock_data = {
        'name': 'model_20250720_143022',
        'accuracy': 0.853,
        'created_at': '2025-07-20T14:30:22Z',
        'status': 'active',
        'training_epochs': 100,
        'validation_score': 0.847
    }
    
    return api_success(
        data=mock_data,
        message='현재 AI 모델 정보 조회 성공'
    )

@api_bp.route('/ai/model/history', methods=['GET'])
@api_required
def get_ai_model_history():
    """AI 모델 히스토리"""
    # TODO: 실제 모델 히스토리 구현
    mock_data = [
        {'name': 'model_20250720_143022', 'accuracy': 0.853, 'created_at': '2025-07-20T14:30:22Z', 'status': 'active'},
        {'name': 'model_20250720_091544', 'accuracy': 0.827, 'created_at': '2025-07-20T09:15:44Z', 'status': 'inactive'},
        {'name': 'model_20250719_235612', 'accuracy': 0.791, 'created_at': '2025-07-19T23:56:12Z', 'status': 'inactive'}
    ]
    
    return api_success(
        data=mock_data,
        message='AI 모델 히스토리 조회 성공'
    )

@api_bp.route('/ai/training/params', methods=['GET'])
@api_required
def get_training_params():
    """AI 학습 파라미터 조회"""
    # TODO: 실제 학습 파라미터 구현
    mock_data = {
        'training_days': 365,
        'epochs': 100,
        'batch_size': 32,
        'learning_rate': 0.001,
        'sequence_length': 60,
        'validation_split': 20,
        'indicators': {
            'price': True,
            'sma': True,
            'ema': True,
            'bb': True,
            'rsi': True,
            'macd': True,
            'stoch': True,
            'williams': True,
            'volume': True,
            'vwap': True,
            'atr': True,
            'volatility': True
        }
    }
    
    return api_success(
        data=mock_data,
        message='학습 파라미터 조회 성공'
    )

@api_bp.route('/ai/training/start', methods=['POST'])
@api_required
def start_ai_training():
    """AI 모델 학습 시작"""
    # TODO: 실제 학습 시작 로직 구현
    log_system_event('INFO', 'AI', f'AI 학습 시작 요청: 사용자 {session.get("user_id")}')
    
    return api_success(
        data={'training_id': f'train_{datetime.now().strftime("%Y%m%d_%H%M%S")}'},
        message='AI 모델 학습을 시작했습니다'
    )

@api_bp.route('/ai/training/stop', methods=['POST'])
@api_required
def stop_ai_training():
    """AI 모델 학습 중지"""
    # TODO: 실제 학습 중지 로직 구현
    log_system_event('INFO', 'AI', f'AI 학습 중지 요청: 사용자 {session.get("user_id")}')
    
    return api_success(
        message='AI 모델 학습을 중지했습니다'
    )

@api_bp.route('/ai/training/status', methods=['GET'])
@api_required
def get_training_status():
    """AI 모델 학습 상태 조회"""
    # TODO: 실제 학습 상태 구현
    mock_data = {
        'status': 'training',  # 'idle', 'training', 'completed', 'failed'
        'current_epoch': 45,
        'total_epochs': 100,
        'current_batch': 120,
        'total_batches': 500,
        'metrics': {
            'loss': 0.234,
            'accuracy': 0.782,
            'val_loss': 0.256
        },
        'estimated_completion': '2025-07-28T15:30:00Z'
    }
    
    return api_success(
        data=mock_data,
        message='학습 상태 조회 성공'
    )

# ============================================================================
# 에러 핸들러 (API 관련)
# ============================================================================

@api_bp.errorhandler(500)
def internal_api_error(error):
    """API 500 에러 처리"""
    log_system_event('ERROR', 'API', f'Internal API error: {error}')
    db.session.rollback()
    return api_error('서버 내부 오류가 발생했습니다', 'INTERNAL_ERROR', 500)