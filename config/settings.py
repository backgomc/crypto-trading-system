import os
import json
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ============================================================================
# 보안 설정 (환경변수에서 로드)
# ============================================================================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

# ============================================================================
# 설정 파일 로드 함수
# ============================================================================
def load_trading_config():
    """trading_config.json 파일 로드"""
    try:
        with open('config/trading_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("trading_config.json 파일을 찾을 수 없습니다.")
        return None

def load_runtime_state():
    """runtime_state.json 파일 로드"""
    try:
        with open('data/runtime_state.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("runtime_state.json 파일을 찾을 수 없습니다.")
        return None

def save_runtime_state(state):
    """runtime_state.json 파일 저장"""
    try:
        with open('data/runtime_state.json', 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception as e:
        print(f"상태 저장 실패: {e}")
        return False

# ============================================================================
# 기본 설정값 (trading_config.json 로드 실패 시 사용)
# ============================================================================
DEFAULT_CONFIG = {
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
        "ai_training_days": 365
    }
}
