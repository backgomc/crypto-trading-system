# 파일 경로: config/settings.py
# 코드명: 환경설정 및 데이터베이스 기반 매매 설정 관리

import os
from dotenv import load_dotenv
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

# .env 파일 로드
env_path = PROJECT_ROOT / '.env'
load_dotenv(env_path)

# ============================================================================
# 보안 설정 (환경변수에서 로드)
# ============================================================================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

# 관리자 계정 설정 (main.py에서 사용)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123!')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@localhost')

# Flask 설정
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.getenv('FLASK_PORT', '8888'))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# ============================================================================
# 디렉토리 설정
# ============================================================================
DATA_DIR = PROJECT_ROOT / 'data'
LOGS_DIR = PROJECT_ROOT / 'logs'
MODELS_DIR = PROJECT_ROOT / 'models'
CONFIG_DIR = PROJECT_ROOT / 'config'

# 디렉토리 생성
for directory in [DATA_DIR, LOGS_DIR, MODELS_DIR]:
    directory.mkdir(exist_ok=True)

# ============================================================================
# 데이터베이스 설정
# ============================================================================
DATABASE_URL = f'sqlite:///{DATA_DIR}/trading_system.db'

# ============================================================================
# 설정 검증 함수
# ============================================================================
def validate_config():
    """필수 환경변수 검증"""
    required_vars = [
        ('BYBIT_API_KEY', BYBIT_API_KEY),
        ('BYBIT_API_SECRET', BYBIT_API_SECRET),
        ('TELEGRAM_BOT_TOKEN', TELEGRAM_BOT_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID),
        ('SECRET_KEY', SECRET_KEY),
    ]
    
    missing_vars = []
    for var_name, var_value in required_vars:
        if not var_value:
            missing_vars.append(var_name)
    
    if missing_vars:
        raise ValueError(f"필수 환경변수가 누락되었습니다: {', '.join(missing_vars)}")
    
    return True

def get_config_summary():
    """환경 설정 요약 정보 반환"""
    return {
        'flask_host': FLASK_HOST,
        'flask_port': FLASK_PORT,
        'flask_debug': FLASK_DEBUG,
        'admin_username': ADMIN_USERNAME,
        'data_dir': str(DATA_DIR),
        'logs_dir': str(LOGS_DIR),
        'models_dir': str(MODELS_DIR)
    }

# ============================================================================
# 데이터베이스 기반 설정 관리 함수들
# ============================================================================

def load_user_config(user_id):
    """사용자 설정 로드 (데이터베이스에서)"""
    try:
        from config.models import get_user_full_config
        config = get_user_full_config(user_id)
        print(f"✅ 사용자 {user_id} 설정 로드 완료")
        return config
    except Exception as e:
        print(f"❌ 사용자 {user_id} 설정 로드 실패: {e}")
        return get_default_config()

def save_user_config(user_id, config_key, config_value, ip_address=None, user_agent=None):
    """사용자 설정 저장 (데이터베이스에)"""
    try:
        from config.models import UserConfig, ConfigHistory
        
        # 기존 값 조회 (이력 저장용)
        old_value = UserConfig.get_user_config(user_id, config_key)
        
        # 새 값 저장
        UserConfig.set_user_config(user_id, config_key, config_value)
        
        # 변경 이력 저장
        ConfigHistory.log_change(
            user_id=user_id,
            config_key=config_key,
            old_value=old_value,
            new_value=config_value,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        print(f"✅ 사용자 {user_id} 설정 저장 완료: {config_key}")
        return True
        
    except Exception as e:
        print(f"❌ 사용자 {user_id} 설정 저장 실패: {e}")
        return False

def get_user_config_value(user_id, config_key, default_value=None):
    """사용자 특정 설정 값 조회"""
    try:
        from config.models import UserConfig
        return UserConfig.get_user_config(user_id, config_key, default_value)
    except Exception as e:
        print(f"❌ 사용자 {user_id} 설정 조회 실패 ({config_key}): {e}")
        return default_value

def update_user_config(user_id, config_updates, ip_address=None, user_agent=None):
    """사용자 설정 일괄 업데이트"""
    try:
        success_count = 0
        for config_key, config_value in config_updates.items():
            if save_user_config(user_id, config_key, config_value, ip_address, user_agent):
                success_count += 1
        
        print(f"✅ 사용자 {user_id} 설정 {success_count}/{len(config_updates)}개 업데이트 완료")
        return success_count == len(config_updates)
        
    except Exception as e:
        print(f"❌ 사용자 {user_id} 설정 일괄 업데이트 실패: {e}")
        return False

def load_user_state(user_id):
    """사용자 매매 상태 로드"""
    try:
        from config.models import TradingState
        
        # 주요 상태 키들
        state_keys = [
            'last_rebalance_price',
            'consecutive_up_count', 
            'consecutive_down_count',
            'last_macd_direction',
            'initial_balance_usd',
            'is_trading_active',
            'start_time'
        ]
        
        state = {}
        for key in state_keys:
            state[key] = TradingState.get_state(user_id, key, 0 if 'count' in key or 'price' in key or 'balance' in key else None)
        
        return state
        
    except Exception as e:
        print(f"❌ 사용자 {user_id} 상태 로드 실패: {e}")
        return get_default_runtime_state()

def save_user_state(user_id, state_key, state_value):
    """사용자 매매 상태 저장"""
    try:
        from config.models import TradingState
        TradingState.set_state(user_id, state_key, state_value)
        return True
    except Exception as e:
        print(f"❌ 사용자 {user_id} 상태 저장 실패 ({state_key}): {e}")
        return False

def init_new_user(user_id):
    """신규 사용자 초기 설정"""
    try:
        from config.models import init_user_config
        init_user_config(user_id)
        
        # 기본 상태 초기화
        default_state = get_default_runtime_state()
        for key, value in default_state.items():
            save_user_state(user_id, key, value)
        
        print(f"✅ 신규 사용자 {user_id} 초기화 완료")
        return True
        
    except Exception as e:
        print(f"❌ 신규 사용자 {user_id} 초기화 실패: {e}")
        return False

# ============================================================================
# 기본 설정값 (하위 호환성을 위해 유지)
# ============================================================================
def get_default_config():
    """기본 매매 설정 반환"""
    return {
        "trading_settings": {
            "demo_mode": True,
            "virtual_balance": 10000,
            "symbol": "BTCUSDT",
            "initial_position_size": 0.05,
            "adjustment_size": 0.01,
            "base_threshold": 1000,
            "loop_delay": 60,
            "consecutive_threshold": 4
        },
        "ai_settings": {
            "ai_enabled": True,
            "adaptive_threshold_enabled": True,
            "volatility_window": 20,
            "model_retrain_interval": 86400,
            "main_interval": "15",
            "ai_training_days": 365,
            "timeframes": ["1", "5", "15", "60"],
            "ai_sequence_length": 96
        },
        "macd_settings": {
            "short_window": 90,
            "long_window": 100,
            "signal_window": 9
        },
        "risk_management": {
            "max_position_size": 1.0,
            "stop_loss_percentage": 5.0,
            "take_profit_percentage": 3.0
        },
        "notification_settings": {
            "telegram_enabled": True,
            "telegram_retry_count": 5,
            "telegram_retry_interval": 60
        }
    }

def get_default_runtime_state():
    """기본 런타임 상태 반환"""
    return {
        # trading_state
        "last_rebalance_price": 0,
        "consecutive_up_count": 0,
        "consecutive_down_count": 0,
        "last_macd_direction": None,
        "is_trading_active": False,
        
        # balance_info
        "initial_balance_usd": 0.0,
        "current_balance_usd": 0.0,
        "profit_in_usd": 0.0,
        "profit_in_krw": 0.0,
        
        # system_info
        "start_time": 0,
        "last_trade_time": 0,
        "total_trades": 0,
        "program_status": "stopped",
        
        # ai_info
        "last_training_time": 0,
        "model_accuracy": 0.0,
        "last_prediction": None
    }

# ============================================================================
# 하위 호환성 함수들 (기존 코드와의 호환성 유지)
# ============================================================================
def load_trading_config(user_id=1):
    """매매 설정 로드 (하위 호환성)"""
    return load_user_config(user_id)

def load_runtime_state(user_id=1):
    """런타임 상태 로드 (하위 호환성)"""
    return load_user_state(user_id)

def save_runtime_state(state, user_id=1):
    """런타임 상태 저장 (하위 호환성)"""
    try:
        for key, value in state.items():
            save_user_state(user_id, key, value)
        return True
    except Exception as e:
        print(f"❌ 런타임 상태 저장 실패: {e}")
        return False

# ============================================================================
# 시스템 정보 함수들
# ============================================================================
def get_system_info():
    """시스템 정보 반환"""
    return {
        'environment': {
            'bybit_configured': bool(BYBIT_API_KEY and BYBIT_API_SECRET),
            'telegram_configured': bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
            'database_url': DATABASE_URL,
            'flask_debug': FLASK_DEBUG
        },
        'directories': {
            'data': str(DATA_DIR),
            'logs': str(LOGS_DIR),
            'models': str(MODELS_DIR),
            'config': str(CONFIG_DIR)
        },
        'admin': {
            'username': ADMIN_USERNAME,
            'email': ADMIN_EMAIL
        }
    }

if __name__ == "__main__":
    # 설정 검증 테스트
    print("🧪 설정 시스템 테스트 시작")
    
    try:
        validate_config()
        print("✅ 모든 필수 환경변수가 설정되었습니다.")
        
        system_info = get_system_info()
        print("📋 시스템 정보:")
        print(f"  - Bybit API 설정: {system_info['environment']['bybit_configured']}")
        print(f"  - 텔레그램 설정: {system_info['environment']['telegram_configured']}")
        print(f"  - Flask 포트: {FLASK_PORT}")
        print(f"  - 관리자: {ADMIN_USERNAME}")
        print(f"  - 데이터베이스: {DATABASE_URL}")
        
        # 테스트용 사용자 설정 (실제 DB 연결이 필요)
        print("\n📝 참고: 사용자별 설정은 Flask 앱 실행 후 DB 연결 시 사용 가능")
        
        print("✅ 설정 시스템 테스트 완료")
        
    except ValueError as e:
        print(f"❌ 설정 오류: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")