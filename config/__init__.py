# 파일 경로: config/__init__.py
# 코드명: Config 모듈 초기화

"""
NHBot Config 모듈

주요 구성:
- models: 데이터베이스 모델 및 헬퍼 함수
- settings: 환경설정 및 사용자별 설정 관리
"""

# ============================================================================
# 데이터베이스 관련 (models.py)
# ============================================================================

# 핵심 데이터베이스 객체
from .models import db

# 주요 모델 클래스들
from .models import (
    User, 
    UserConfig, 
    TradingState, 
    SystemLog, 
    TradingLog,
    ConfigHistory,
    UserSession
)

# 시간 관련 유틸리티
from .models import get_kst_now, format_kst_string, to_kst_string

# 설정 관련 헬퍼 함수들
from .models import (
    get_default_user_config,
    init_user_config,
    get_user_full_config
)

# ============================================================================
# 환경설정 관련 (settings.py)
# ============================================================================

# 환경변수들
from .settings import (
    BYBIT_API_KEY,
    BYBIT_API_SECRET, 
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    SECRET_KEY,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    FLASK_HOST,
    FLASK_PORT,
    DATABASE_URL
)

# 디렉토리 경로들
from .settings import DATA_DIR, LOGS_DIR, MODELS_DIR

# 핵심 설정 함수들
from .settings import (
    load_user_config,
    save_user_config,
    get_user_config_value,
    update_user_config,
    load_user_state,
    save_user_state,
    init_new_user,
    get_default_config,
    validate_config,
    get_system_info
)

# 하위 호환성 함수들
from .settings import (
    load_trading_config,
    load_runtime_state,
    save_runtime_state
)

# ============================================================================
# 공개 API 정의
# ============================================================================

__all__ = [
    # 데이터베이스
    'db',
    
    # 모델 클래스
    'User', 'UserConfig', 'TradingState', 'SystemLog', 
    'TradingLog', 'ConfigHistory', 'UserSession',
    
    # 시간 유틸리티
    'get_kst_now', 'format_kst_string', 'to_kst_string',
    
    # 설정 헬퍼 (models.py)
    'get_default_user_config', 'init_user_config', 'get_user_full_config',
    
    # 환경변수 (자주 사용되는 것들만)
    'BYBIT_API_KEY', 'BYBIT_API_SECRET', 'DATABASE_URL',
    'TELEGRAM_BOT_TOKEN', 'SECRET_KEY',
    
    # 디렉토리
    'DATA_DIR', 'LOGS_DIR', 'MODELS_DIR',
    
    # 핵심 설정 함수들
    'load_user_config', 'save_user_config', 'get_user_config_value',
    'update_user_config', 'validate_config', 'get_system_info',
    
    # 하위 호환성
    'load_trading_config', 'get_default_config'
]

__version__ = "2.0.0"