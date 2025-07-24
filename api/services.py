# 파일 경로: api/services.py
# 코드명: API 비즈니스 로직 서비스 (환경변수 중복 제거)

import requests
import time
import pandas as pd
from datetime import datetime
from pybit.unified_trading import HTTP
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 환경변수는 settings에서 가져옴
from config.settings import (
    BYBIT_API_KEY, 
    BYBIT_API_SECRET, 
    TELEGRAM_BOT_TOKEN, 
    TELEGRAM_CHAT_ID
)

# Bybit API 세션 초기화
_bybit_session = None

def get_bybit_session():
    """Bybit API 세션 싱글톤"""
    global _bybit_session
    if _bybit_session is None and BYBIT_API_KEY and BYBIT_API_SECRET:
        _bybit_session = HTTP(
            testnet=False,
            api_key=BYBIT_API_KEY,
            api_secret=BYBIT_API_SECRET
        )
    return _bybit_session

# ============================================================================
# 환율 서비스
# ============================================================================

def get_exchange_rate(base_currency="USD", target_currency="KRW", max_retries=3, retry_delay=5):
    """
    외부 API를 통해 환율 정보를 가져오는 함수
    """
    session_req = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=retry_delay,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session_req.mount("http://", adapter)
    session_req.mount("https://", adapter)

    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = session_req.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        rate = data.get("rates", {}).get(target_currency)
        
        if rate is not None:
            return float(rate)
        
        print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : {target_currency} 환율 정보를 찾을 수 없습니다.")
        return None
        
    except Exception as e:
        print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 환율 조회 오류: {e}")
        return None
    finally:
        session_req.close()

# ============================================================================
# 텔레그램 서비스
# ============================================================================

def send_telegram_message(message, max_retries=5, retry_interval=60):
    """
    텔레그램 메시지 전송 함수 (원본 코드 파라미터 그대로 유지)
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("텔레그램 설정이 완료되지 않았습니다.")
        return False
        
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    
    attempt = 0
    while attempt < max_retries:
        try:
            # 메시지 전송 전 5초 대기 (원본 코드 유지)
            time.sleep(5)
            res = requests.post(TELEGRAM_API_URL, json=data, timeout=10)
            if res.status_code == 200:
                return True
            else:
                print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 텔레그램 메시지 전송 실패, 상태 코드: {res.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 텔레그램 메시지 전송 중 오류 발생: {e}")
        
        attempt += 1
        print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 전송 실패. {attempt}/{max_retries}번 시도. {retry_interval}초 후 재시도합니다.")
        time.sleep(retry_interval)
    
    print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 최대 재시도 횟수에 도달했습니다. 메시지 전송 실패.")
    return False

def is_telegram_configured():
    """텔레그램 설정 확인"""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# ============================================================================
# Bybit 거래소 서비스
# ============================================================================

def get_account_balance():
    """
    계좌 잔고 조회 함수
    """
    try:
        session = get_bybit_session()
        if not session:
            print("Bybit API 세션이 초기화되지 않았습니다.")
            return 0.0
            
        response = session.get_wallet_balance(coin="USDT", accountType="unified")
        if response.get("retCode") == 0:
            account_info = response.get("result", {}).get("list", [])[0]
            if account_info:
                return float(account_info.get("totalWalletBalance", 0))
        else:
            print(f"계좌 잔고 가져오기 실패: {response['retMsg']}")
            return 0.0
    except Exception as e:
        print(f"계좌 잔고 조회 중 예외 발생: {e}")
        return 0.0

def get_current_price(symbol="BTCUSDT"):
    """
    현재 가격 조회 함수
    """
    try:
        session = get_bybit_session()
        if not session:
            print("Bybit API 세션이 초기화되지 않았습니다.")
            return None
            
        response = session.get_tickers(category="linear", symbol=symbol)
        
        if response["retCode"] == 0:
            current_price = float(response["result"]["list"][0]["lastPrice"])
            return current_price
        else:
            print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 현재 가격을 가져오는 중 오류 발생: {response['retMsg']}")
            return None
            
    except Exception as e:
        print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 현재 가격을 가져오는 중 예외 발생: {e}")
        return None

def get_position_info(symbol="BTCUSDT"):
    """
    포지션 정보 조회 함수
    """
    try:
        session = get_bybit_session()
        if not session:
            print("Bybit API 세션이 초기화되지 않았습니다.")
            return 0, None, None, 0, None, None
            
        response = session.get_positions(category="linear", symbol=symbol)
        
        if response["retCode"] == 0:
            positions = response["result"]["list"]
            long_size, long_avg_price, long_unrealised_pnl = 0, None, None
            short_size, short_avg_price, short_unrealised_pnl = 0, None, None

            # 포지션 정보 추출
            for position in positions:
                if position['side'] == 'Buy':  # 롱 포지션
                    long_size = float(position['size'])
                    long_avg_price = float(position['avgPrice'])
                    long_unrealised_pnl = float(position['unrealisedPnl']) if 'unrealisedPnl' in position else None
                elif position['side'] == 'Sell':  # 숏 포지션
                    short_size = float(position['size'])
                    short_avg_price = float(position['avgPrice'])
                    short_unrealised_pnl = float(position['unrealisedPnl']) if 'unrealisedPnl' in position else None
            
            return long_size, long_avg_price, long_unrealised_pnl, short_size, short_avg_price, short_unrealised_pnl
        else:
            print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 포지션 정보를 가져오는 중 오류 발생: {response['retMsg']}")
            return 0, None, None, 0, None, None
            
    except Exception as e:
        print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 포지션 정보를 가져오는 중 예외 발생: {e}")
        return 0, None, None, 0, None, None

def place_order(side, qty, positionIdx, symbol="BTCUSDT"):
    """
    주문 생성 함수 (원본 코드에서 추가)
    """
    try:
        session = get_bybit_session()
        if not session:
            print("Bybit API 세션이 초기화되지 않았습니다.")
            return None
            
        response = session.place_order(
            category='linear',
            symbol=symbol,
            side=side,
            orderType='Market',
            qty=qty,
            timeInForce='GoodTillCancel',
            positionIdx=positionIdx
        )
        if response['retCode'] == 0:
            return response
        else:
            print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 주문 생성 중 오류 발생: {response['retMsg']}")
            return None
    except Exception as e:
        print(f"{datetime.now().strftime('%Y/%m/%d %H:%M:%S')} : 주문 생성 중 예외 발생: {e}")
        return None

def get_market_data(symbol="BTCUSDT", interval="1", limit=100):
    """
    시장 데이터 조회 함수 (원본 코드와 동일)
    """
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {"category": "linear", "symbol": symbol, "interval": interval, "limit": str(limit)}
        response = requests.get(url, params=params)
        data = response.json()
        
        if data["retCode"] != 0:
            raise Exception(f"Error: {data['retMsg']}")
        
        df = pd.DataFrame(data["result"]["list"])
        df.columns = ["start", "open", "high", "low", "close", "volume", "turnover"]
        df["timestamp"] = pd.to_datetime(df["start"].astype(float), unit="ms")
        df["timestamp"] = df["timestamp"].dt.tz_localize('UTC').dt.tz_convert('Asia/Seoul')
        df.set_index("timestamp", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        df = df[::-1]  # 최신 데이터가 아래로 가도록 역순 정렬
        df = df.iloc[:-1]  # 가장 최근 데이터 제외
        return df
        
    except Exception as e:
        print(f"시장 데이터 조회 예외: {e}")
        return None

def is_bybit_configured():
    """Bybit API 설정 확인"""
    return bool(BYBIT_API_KEY and BYBIT_API_SECRET)

# ============================================================================
# 종합 정보 서비스
# ============================================================================

def get_trading_summary():
    """거래 요약 정보 조회"""
    try:
        # 계좌 잔고
        balance_usd = get_account_balance()
        
        # 현재 BTC 가격
        btc_price = get_current_price("BTCUSDT")
        
        # 환율 정보
        usd_to_krw = get_exchange_rate("USD", "KRW")
        
        # 포지션 정보
        position_info = get_position_info("BTCUSDT")
        
        summary = {
            'balance_usd': balance_usd,
            'balance_krw': balance_usd * usd_to_krw if balance_usd and usd_to_krw else None,
            'btc_price': btc_price,
            'exchange_rate': usd_to_krw,
            'position_info': position_info,
            'last_updated': datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        }
        
        return summary
        
    except Exception as e:
        print(f"거래 요약 정보 조회 예외: {e}")
        return None

def get_system_status():
    """시스템 상태 확인"""
    return {
        'bybit_configured': is_bybit_configured(),
        'bybit_connected': get_bybit_session() is not None,
        'telegram_configured': is_telegram_configured(),
        'server_time': datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    }

# ============================================================================
# 원본 코드 호환성 함수들 (별칭)
# ============================================================================

# 원본 코드에서 사용하던 함수명으로 호출 가능하도록 별칭 제공
send_telegram = send_telegram_message  # 원본: send_telegram()