# 파일 경로: web/routes/ai_api.py
# 코드명: AI 관련 API 엔드포인트 (완전 분리)

from flask import Blueprint, request, session, jsonify
from functools import wraps
from datetime import datetime
import json
import os
from pathlib import Path

# AI 모듈 임포트
from core.ai import ModelManager
from config.models import SystemLog, db

ai_api_bp = Blueprint('ai_api', __name__)

# ============================================================================
# 전역 AI 인스턴스 (싱글톤 패턴)
# ============================================================================

_model_manager = None
_data_collector = None
_model_trainer = None

def get_model_manager():
    """ModelManager 싱글톤"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager

# ============================================================================
# 유틸리티 함수들
# ============================================================================

def ai_api_required(f):
    """AI API 인증 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return ai_api_error('로그인이 필요합니다', 'AUTH_REQUIRED', 401)
        return f(*args, **kwargs)
    return decorated_function

def ai_api_success(data=None, message='성공'):
    """AI API 성공 응답"""
    response = {
        'success': True,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'meta': {
            'service': 'AI',
            'user_id': session.get('user_id'),
            'request_id': f"ai_req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    }
    if data is not None:
        response['data'] = data
    return jsonify(response)

def ai_api_error(message, code='AI_ERROR', status_code=400, details=None):
    """AI API 오류 응답"""
    response = {
        'success': False,
        'error': message,
        'code': code,
        'timestamp': datetime.utcnow().isoformat(),
        'meta': {
            'service': 'AI',
            'user_id': session.get('user_id'),
            'request_id': f"ai_req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    }
    if details:
        response['details'] = details
    return jsonify(response), status_code

def log_ai_event(level, message, details=None):
    """AI 이벤트 로깅"""
    try:
        full_message = f"AI: {message}"
        if details:
            full_message += f" - {details}"
            
        log_entry = SystemLog(
            level=level,
            category='AI',
            message=full_message,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:200]
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"AI 로그 저장 실패: {e}")

# ============================================================================
# 모델 관리 API
# ============================================================================

@ai_api_bp.route('/models', methods=['GET'])
@ai_api_required
def get_models():
    """AI 모델 목록 조회"""
    try:
        manager = get_model_manager()
        models = manager.get_model_list()
        active_model = manager.get_active_model()
        storage_info = manager.get_storage_info()
        
        log_ai_event('INFO', '모델 목록 조회')
        
        return ai_api_success(
            data={
                'models': models,
                'active_model': active_model,
                'storage_info': storage_info
            },
            message='모델 목록 조회 성공'
        )
        
    except Exception as e:
        log_ai_event('ERROR', '모델 목록 조회 실패', str(e))
        return ai_api_error('모델 목록 조회 중 오류가 발생했습니다', 'MODEL_LIST_ERROR', 500)

@ai_api_bp.route('/models/<model_name>', methods=['GET'])
@ai_api_required
def get_model_info(model_name):
    """특정 모델 정보 조회"""
    try:
        manager = get_model_manager()
        model_info = manager.get_model_info(model_name)
        
        if not model_info:
            return ai_api_error('모델을 찾을 수 없습니다', 'MODEL_NOT_FOUND', 404)
        
        log_ai_event('INFO', f'모델 정보 조회: {model_name}')
        
        return ai_api_success(
            data={'model': model_info},
            message='모델 정보 조회 성공'
        )
        
    except Exception as e:
        log_ai_event('ERROR', f'모델 정보 조회 실패: {model_name}', str(e))
        return ai_api_error('모델 정보 조회 중 오류가 발생했습니다', 'MODEL_INFO_ERROR', 500)

@ai_api_bp.route('/models/activate', methods=['POST'])
@ai_api_required
def activate_model():
    """모델 활성화"""
    try:
        data = request.get_json()
        if not data or 'model_name' not in data:
            return ai_api_error('model_name이 필요합니다', 'INVALID_REQUEST', 400)
        
        model_name = data['model_name']
        manager = get_model_manager()
        
        success = manager.set_active_model(model_name)
        
        if success:
            log_ai_event('INFO', f'모델 활성화: {model_name}')
            return ai_api_success(
                data={'active_model': model_name},
                message=f'{model_name} 모델이 활성화되었습니다'
            )
        else:
            return ai_api_error('모델 활성화에 실패했습니다', 'ACTIVATION_ERROR', 500)
            
    except Exception as e:
        log_ai_event('ERROR', '모델 활성화 실패', str(e))
        return ai_api_error('모델 활성화 중 오류가 발생했습니다', 'ACTIVATION_ERROR', 500)

@ai_api_bp.route('/models/<model_name>', methods=['DELETE'])
@ai_api_required
def delete_model(model_name):
    """모델 삭제"""
    try:
        manager = get_model_manager()
        
        # 활성 모델인지 확인
        if manager.get_active_model() == model_name:
            return ai_api_error('활성 모델은 삭제할 수 없습니다', 'ACTIVE_MODEL_DELETE', 400)
        
        success = manager.delete_model(model_name)
        
        if success:
            log_ai_event('INFO', f'모델 삭제: {model_name}')
            return ai_api_success(message=f'{model_name} 모델이 삭제되었습니다')
        else:
            return ai_api_error('모델 삭제에 실패했습니다', 'DELETE_ERROR', 500)
            
    except Exception as e:
        log_ai_event('ERROR', f'모델 삭제 실패: {model_name}', str(e))
        return ai_api_error('모델 삭제 중 오류가 발생했습니다', 'DELETE_ERROR', 500)

@ai_api_bp.route('/models/cleanup', methods=['POST'])
@ai_api_required
def cleanup_models():
    """오래된 모델 정리"""
    try:
        data = request.get_json() or {}
        keep_count = data.get('keep_count', 5)
        
        manager = get_model_manager()
        deleted_count = manager.cleanup_old_models(keep_count)
        
        log_ai_event('INFO', f'모델 정리 완료: {deleted_count}개 삭제')
        
        return ai_api_success(
            data={'deleted_count': deleted_count},
            message=f'{deleted_count}개 모델이 정리되었습니다'
        )
        
    except Exception as e:
        log_ai_event('ERROR', '모델 정리 실패', str(e))
        return ai_api_error('모델 정리 중 오류가 발생했습니다', 'CLEANUP_ERROR', 500)

# ============================================================================
# 학습 관리 API
# ============================================================================

@ai_api_bp.route('/training/start', methods=['POST'])
@ai_api_required
def start_training():
    """AI 모델 학습 시작"""
    try:
        data = request.get_json()
        if not data:
            return ai_api_error('학습 설정이 필요합니다', 'INVALID_REQUEST', 400)
        
        # 선택된 지표 추출
        selected_indicators = data.get('indicators', {})
        if not any(selected_indicators.values()):
            return ai_api_error('최소 하나 이상의 지표를 선택해주세요', 'NO_INDICATORS', 400)
        
        # 학습 파라미터 추출
        training_params = {
            'training_days': data.get('training_days', 365),
            'epochs': data.get('epochs', 100),
            'batch_size': data.get('batch_size', 32),
            'learning_rate': data.get('learning_rate', 0.001),
            'sequence_length': data.get('sequence_length', 60),
            'validation_split': data.get('validation_split', 20),
            'interval': data.get('interval', '15')
        }
        
        # 파라미터 유효성 검사
        validation_errors = []
        
        if not (30 <= training_params['training_days'] <= 1095):
            validation_errors.append('학습 기간은 30~1095일 사이여야 합니다')
        
        if not (10 <= training_params['epochs'] <= 1000):
            validation_errors.append('에폭은 10~1000 사이여야 합니다')
        
        if not (8 <= training_params['batch_size'] <= 128):
            validation_errors.append('배치 크기는 8~128 사이여야 합니다')
        
        if not (0.0001 <= training_params['learning_rate'] <= 0.1):
            validation_errors.append('학습률은 0.0001~0.1 사이여야 합니다')
        
        if validation_errors:
            return ai_api_error(
                '파라미터 검증 실패', 
                'VALIDATION_ERROR', 
                400, 
                {'errors': validation_errors}
            )
        
        # 학습 시작
        trainer = get_model_trainer()
        
        if trainer.is_training:
            return ai_api_error('이미 학습이 진행 중입니다', 'TRAINING_IN_PROGRESS', 400)
        
        success = trainer.start_training(selected_indicators, training_params)
        
        if success:
            log_ai_event('INFO', '모델 학습 시작', f"지표: {sum(selected_indicators.values())}개, 에폭: {training_params['epochs']}")
            
            return ai_api_success(
                data={
                    'training_id': f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'selected_indicators': selected_indicators,
                    'training_params': training_params
                },
                message='AI 모델 학습을 시작했습니다'
            )
        else:
            return ai_api_error('학습 시작에 실패했습니다', 'TRAINING_START_ERROR', 500)
            
    except Exception as e:
        log_ai_event('ERROR', '학습 시작 실패', str(e))
        return ai_api_error('학습 시작 중 오류가 발생했습니다', 'TRAINING_ERROR', 500)

@ai_api_bp.route('/training/stop', methods=['POST'])
@ai_api_required
def stop_training():
    """AI 모델 학습 중지"""
    try:
        trainer = get_model_trainer()
        
        if not trainer.is_training:
            return ai_api_error('진행 중인 학습이 없습니다', 'NO_TRAINING', 400)
        
        success = trainer.stop_training()
        
        if success:
            log_ai_event('INFO', '모델 학습 중지')
            return ai_api_success(message='AI 모델 학습을 중지했습니다')
        else:
            return ai_api_error('학습 중지에 실패했습니다', 'TRAINING_STOP_ERROR', 500)
            
    except Exception as e:
        log_ai_event('ERROR', '학습 중지 실패', str(e))
        return ai_api_error('학습 중지 중 오류가 발생했습니다', 'TRAINING_ERROR', 500)

@ai_api_bp.route('/training/status', methods=['GET'])
@ai_api_required
def get_training_status():
    """AI 모델 학습 상태 조회"""
    try:
        trainer = get_model_trainer()
        status = trainer.get_training_status()
        
        # 상태 정보 보강
        enhanced_status = {
            **status,
            'is_training': trainer.is_training,
            'progress_percentage': 0
        }
        
        # 진행률 계산
        if status['total_epochs'] > 0:
            enhanced_status['progress_percentage'] = (
                status['current_epoch'] / status['total_epochs'] * 100
            )
        
        # 경과 시간 계산
        if status.get('start_time'):
            elapsed = datetime.now() - status['start_time']
            enhanced_status['elapsed_seconds'] = int(elapsed.total_seconds())
            enhanced_status['elapsed_formatted'] = str(elapsed).split('.')[0]  # 초 단위 제거
        
        return ai_api_success(
            data=enhanced_status,
            message='학습 상태 조회 성공'
        )
        
    except Exception as e:
        log_ai_event('ERROR', '학습 상태 조회 실패', str(e))
        return ai_api_error('학습 상태 조회 중 오류가 발생했습니다', 'STATUS_ERROR', 500)

@ai_api_bp.route('/training/parameters', methods=['GET'])
@ai_api_required
def get_training_parameters():
    """학습 파라미터 기본값 조회"""
    try:
        default_params = {
            'training_days': 365,
            'epochs': 100,
            'batch_size': 32,
            'learning_rate': 0.001,
            'sequence_length': 60,
            'validation_split': 20,
            'interval': '15'
        }
        
        default_indicators = {
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
        
        return ai_api_success(
            data={
                'parameters': default_params,
                'indicators': default_indicators
            },
            message='학습 파라미터 조회 성공'
        )
        
    except Exception as e:
        log_ai_event('ERROR', '학습 파라미터 조회 실패', str(e))
        return ai_api_error('학습 파라미터 조회 중 오류가 발생했습니다', 'PARAMS_ERROR', 500)

# ============================================================================
# 데이터 수집 API
# ============================================================================

@ai_api_bp.route('/data/indicators', methods=['GET'])
@ai_api_required
def get_available_indicators():
    """사용 가능한 기술적 지표 목록"""
    try:
        trainer = get_model_trainer()
        indicators = trainer.indicator_mapping
        
        # 지표 설명 추가
        indicator_descriptions = {
            'price': {'name': '가격 데이터', 'description': 'OHLCV 기본 가격 정보'},
            'sma': {'name': '단순이동평균', 'description': '가격의 단순 평균선'},
            'ema': {'name': '지수이동평균', 'description': '최근 가격에 가중치를 둔 평균선'},
            'bb': {'name': '볼린저 밴드', 'description': '가격 변동성 기반 지지/저항선'},
            'rsi': {'name': 'RSI', 'description': '과매수/과매도 모멘텀 지표'},
            'macd': {'name': 'MACD', 'description': '이동평균 수렴확산 지표'},
            'stoch': {'name': '스토캐스틱', 'description': '고저점 대비 현재가 위치'},
            'williams': {'name': 'Williams %R', 'description': '스토캐스틱과 유사한 모멘텀 지표'},
            'volume': {'name': '거래량', 'description': '거래량 관련 지표들'},
            'vwap': {'name': 'VWAP', 'description': '거래량 가중 평균 가격'},
            'atr': {'name': 'ATR', 'description': '평균 실제 범위(변동성)'},
            'volatility': {'name': '변동성', 'description': '가격 변동성 지표'}
        }
        
        # 지표별 컬럼 수 계산
        result = {}
        for indicator, columns in indicators.items():
            result[indicator] = {
                **indicator_descriptions.get(indicator, {'name': indicator, 'description': ''}),
                'columns': columns,
                'column_count': len(columns)
            }
        
        return ai_api_success(
            data={'indicators': result},
            message='지표 목록 조회 성공'
        )
        
    except Exception as e:
        log_ai_event('ERROR', '지표 목록 조회 실패', str(e))
        return ai_api_error('지표 목록 조회 중 오류가 발생했습니다', 'INDICATORS_ERROR', 500)

@ai_api_bp.route('/data/summary', methods=['GET'])
@ai_api_required
def get_market_data_summary():
    """시장 데이터 요약 정보"""
    try:
        collector = get_data_collector()
        
        # 최신 데이터 수집 (100개 봉)
        df = collector.get_latest_data(interval="15", limit=100)
        
        if df is None or len(df) == 0:
            return ai_api_error('시장 데이터를 가져올 수 없습니다', 'DATA_ERROR', 500)
        
        # 요약 정보 생성
        summary = collector.get_indicator_summary(df)
        
        return ai_api_success(
            data={
                'summary': summary,
                'data_count': len(df),
                'last_updated': df.index[-1].isoformat() if len(df) > 0 else None
            },
            message='시장 데이터 요약 조회 성공'
        )
        
    except Exception as e:
        log_ai_event('ERROR', '시장 데이터 요약 실패', str(e))
        return ai_api_error('시장 데이터 요약 중 오류가 발생했습니다', 'DATA_SUMMARY_ERROR', 500)

# ============================================================================
# 시스템 정보 API
# ============================================================================

@ai_api_bp.route('/system/info', methods=['GET'])
@ai_api_required
def get_ai_system_info():
    """AI 시스템 정보"""
    try:
        # 모델 저장소 정보
        manager = get_model_manager()
        storage_info = manager.get_storage_info()
        
        # TensorFlow 정보
        import tensorflow as tf
        tf_info = {
            'version': tf.__version__,
            'gpu_available': len(tf.config.list_physical_devices('GPU')) > 0,
            'cpu_count': os.cpu_count()
        }
        
        # 데이터 폴더 정보
        data_dir = Path("data")
        models_dir = Path("models")
        
        data_size = sum(f.stat().st_size for f in data_dir.glob("**/*") if f.is_file()) if data_dir.exists() else 0
        models_size = sum(f.stat().st_size for f in models_dir.glob("**/*") if f.is_file()) if models_dir.exists() else 0
        
        system_info = {
            'tensorflow': tf_info,
            'storage': storage_info,
            'disk_usage': {
                'data_size_mb': round(data_size / 1024 / 1024, 2),
                'models_size_mb': round(models_size / 1024 / 1024, 2),
                'total_size_mb': round((data_size + models_size) / 1024 / 1024, 2)
            },
            'directories': {
                'data_exists': data_dir.exists(),
                'models_exists': models_dir.exists()
            }
        }
        
        return ai_api_success(
            data=system_info,
            message='AI 시스템 정보 조회 성공'
        )
        
    except Exception as e:
        log_ai_event('ERROR', 'AI 시스템 정보 조회 실패', str(e))
        return ai_api_error('AI 시스템 정보 조회 중 오류가 발생했습니다', 'SYSTEM_INFO_ERROR', 500)

# ============================================================================
# 자동 학습 스케줄러 API
# ============================================================================

@ai_api_bp.route('/schedule', methods=['GET'])
@ai_api_required
def get_schedule_settings():
    """자동 학습 스케줄 설정 조회"""
    try:
        from config.models import UserConfig
        user_id = session.get('user_id')
        
        # 스케줄 설정 조회
        schedule_config = UserConfig.query.filter_by(
            user_id=user_id, 
            config_key='ai_schedule'
        ).first()
        
        if schedule_config and schedule_config.config_value:
            if isinstance(schedule_config.config_value, str):
                import json
                settings = json.loads(schedule_config.config_value)
            else:
                settings = schedule_config.config_value
        else:
            # 기본값
            settings = {
                'enabled': True,
                'interval': 86400,  # 24시간 (초 단위)
                'last_training': None
            }
        
        # 다음 학습 시간 계산
        if settings.get('enabled') and settings.get('last_training'):
            from datetime import datetime, timedelta
            last_training = datetime.fromisoformat(settings['last_training'])
            next_training = last_training + timedelta(seconds=settings['interval'])
        else:
            from datetime import datetime, timedelta
            next_training = datetime.now() + timedelta(seconds=settings.get('interval', 86400))
        
        result_data = {
            **settings,
            'next_training': next_training.isoformat()
        }
        
        log_ai_event('INFO', '스케줄 설정 조회')
        
        return ai_api_success(
            data=result_data,
            message='스케줄 설정 조회 성공'
        )
        
    except Exception as e:
        log_ai_event('ERROR', '스케줄 설정 조회 실패', str(e))
        return ai_api_error('스케줄 설정 조회 중 오류가 발생했습니다', 'SCHEDULE_GET_ERROR', 500)

@ai_api_bp.route('/schedule', methods=['PUT'])
@ai_api_required
def update_schedule_settings():
    """자동 학습 스케줄 설정 업데이트"""
    try:
        data = request.get_json()
        if not data:
            return ai_api_error('스케줄 설정 데이터가 필요합니다', 'INVALID_REQUEST', 400)
        
        # 파라미터 검증
        enabled = data.get('enabled', True)
        interval = data.get('interval', 86400)
        
        if not isinstance(enabled, bool):
            return ai_api_error('enabled는 boolean 값이어야 합니다', 'VALIDATION_ERROR', 400)
        
        if not isinstance(interval, int) or interval < 3600:  # 최소 1시간
            return ai_api_error('interval은 3600초(1시간) 이상이어야 합니다', 'VALIDATION_ERROR', 400)
        
        if interval > 2592000:  # 최대 30일
            return ai_api_error('interval은 2592000초(30일) 이하여야 합니다', 'VALIDATION_ERROR', 400)
        
        from config.models import UserConfig
        user_id = session.get('user_id')
        
        # 기존 설정 조회
        schedule_config = UserConfig.query.filter_by(
            user_id=user_id, 
            config_key='ai_schedule'
        ).first()
        
        if not schedule_config:
            schedule_config = UserConfig(
                user_id=user_id,
                config_key='ai_schedule'
            )
            db.session.add(schedule_config)
        
        # 새 설정 저장
        new_settings = {
            'enabled': enabled,
            'interval': interval,
            'last_training': data.get('last_training'),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        import json
        schedule_config.config_value = json.dumps(new_settings)
        schedule_config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # 다음 학습 시간 계산
        if enabled:
            from datetime import timedelta
            if new_settings.get('last_training'):
                last_training = datetime.fromisoformat(new_settings['last_training'])
                next_training = last_training + timedelta(seconds=interval)
            else:
                next_training = datetime.now() + timedelta(seconds=interval)
        else:
            next_training = None
        
        result_data = {
            **new_settings,
            'next_training': next_training.isoformat() if next_training else None
        }
        
        # 스케줄 상태에 따른 로그
        status = '활성화' if enabled else '비활성화'
        interval_hours = interval // 3600
        log_ai_event('INFO', f'스케줄 설정 업데이트: {status}, {interval_hours}시간 간격')
        
        return ai_api_success(
            data=result_data,
            message=f'자동 학습 스케줄이 {status}되었습니다'
        )
        
    except Exception as e:
        log_ai_event('ERROR', '스케줄 설정 업데이트 실패', str(e))
        db.session.rollback()
        return ai_api_error('스케줄 설정 업데이트 중 오류가 발생했습니다', 'SCHEDULE_UPDATE_ERROR', 500)

# ============================================================================
# 에러 핸들러
# ============================================================================

@ai_api_bp.errorhandler(500)
def ai_internal_error(error):
    """AI API 500 에러 처리"""
    log_ai_event('ERROR', f'Internal AI API error: {error}')
    db.session.rollback()
    return ai_api_error('AI 서비스 내부 오류가 발생했습니다', 'AI_INTERNAL_ERROR', 500)

@ai_api_bp.errorhandler(404)
def ai_not_found(error):
    """AI API 404 에러 처리"""
    return ai_api_error('요청한 AI API 엔드포인트를 찾을 수 없습니다', 'AI_ENDPOINT_NOT_FOUND', 404)