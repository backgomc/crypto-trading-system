# 파일 경로: core/ai/data_collector.py
# 코드명: 바이비트 데이터 수집 및 기술적 지표 계산

#import pandas as pd
class DummyPandas:
    class DataFrame: pass
pd = DummyPandas()
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
from pathlib import Path

class DataCollector:
    """바이비트 데이터 수집 및 기술적 지표 계산 클래스"""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.base_url = "https://api.bybit.com/v5/market/kline"
        
        # 시간대별 수집 설정
        self.intervals = {
            "1": "1분봉",
            "5": "5분봉", 
            "15": "15분봉",
            "60": "1시간봉"
        }
        
        print(f"✅ DataCollector 초기화 완료: {symbol}")
    
    def collect_historical_data(self, interval: str = "15", days: int = 365) -> Optional[pd.DataFrame]:
        """과거 데이터 수집"""
        try:
            print(f"📊 {self.symbol} {self.intervals.get(interval, interval)} 데이터 수집 시작...")
            print(f"   기간: {days}일 (약 {days * 24 * 60 // int(interval):,}개 봉)")
            
            # 수집할 데이터 개수 계산
            bars_per_day = 24 * 60 // int(interval)
            total_bars = days * bars_per_day
            
            # Bybit API 제한: 한 번에 최대 1000개
            limit = min(1000, total_bars)
            
            all_data = []
            collected_bars = 0
            
            # 현재 시간부터 과거로 거슬러 올라가며 수집
            end_time = int(datetime.now().timestamp() * 1000)
            
            while collected_bars < total_bars:
                remaining = total_bars - collected_bars
                current_limit = min(limit, remaining)
                
                print(f"   진행률: {collected_bars:,}/{total_bars:,} ({collected_bars/total_bars*100:.1f}%)")
                
                # API 호출
                params = {
                    "category": "linear",
                    "symbol": self.symbol,
                    "interval": interval,
                    "limit": str(current_limit),
                    "end": str(end_time)
                }
                
                response = requests.get(self.base_url, params=params, timeout=30)
                
                if response.status_code != 200:
                    print(f"❌ API 호출 실패: {response.status_code}")
                    break
                
                data = response.json()
                
                if data.get("retCode") != 0:
                    print(f"❌ API 오류: {data.get('retMsg', '알 수 없는 오류')}")
                    break
                
                # 데이터 추출
                klines = data.get("result", {}).get("list", [])
                if not klines:
                    print("📝 더 이상 데이터가 없습니다.")
                    break
                
                all_data.extend(klines)
                collected_bars += len(klines)
                
                # 다음 요청을 위한 시간 업데이트 (가장 오래된 데이터의 시간)
                end_time = int(klines[-1][0]) - 1
                
                # API 제한 방지 (초당 10요청)
                time.sleep(0.1)
            
            if not all_data:
                print("❌ 수집된 데이터가 없습니다.")
                return None
            
            print(f"✅ 데이터 수집 완료: {len(all_data):,}개 봉")
            
            # DataFrame 생성
            df = pd.DataFrame(all_data, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])
            
            # 데이터 타입 변환
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms")
            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                df[col] = df[col].astype(float)
            
            # 시간순 정렬 (과거 → 현재)
            df = df.sort_values("timestamp").reset_index(drop=True)
            df.set_index("timestamp", inplace=True)
            
            print(f"📈 데이터 범위: {df.index[0]} ~ {df.index[-1]}")
            
            return df
            
        except Exception as e:
            print(f"❌ 데이터 수집 중 오류: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        try:
            print("🔧 기술적 지표 계산 중...")
            
            # 복사본 생성
            result = df.copy()
            
            # 1. 기본 가격 지표
            result = self._add_price_indicators(result)
            
            # 2. 이동평균
            result = self._add_moving_averages(result)
            
            # 3. 모멘텀 지표
            result = self._add_momentum_indicators(result)
            
            # 4. 변동성 지표
            result = self._add_volatility_indicators(result)
            
            # 5. 거래량 지표
            result = self._add_volume_indicators(result)
            
            # 6. 추가 지표들
            result = self._add_additional_indicators(result)
            
            # NaN 값 처리
            result = result.dropna()
            
            print(f"✅ 기술적 지표 계산 완료: {len(result.columns)}개 컬럼, {len(result)}개 행")
            
            return result
            
        except Exception as e:
            print(f"❌ 기술적 지표 계산 중 오류: {e}")
            return df
    
    def _add_price_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """가격 관련 지표"""
        # 가격 변화율
        df['price_change'] = df['close'].pct_change()
        df['price_change_abs'] = df['price_change'].abs()
        
        # 고가-저가 범위
        df['hl_range'] = (df['high'] - df['low']) / df['close']
        df['oc_range'] = abs(df['open'] - df['close']) / df['close']
        
        # 전일 대비
        df['prev_close'] = df['close'].shift(1)
        df['gap'] = (df['open'] - df['prev_close']) / df['prev_close']
        
        return df
    
    def _add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균 지표"""
        periods = [5, 10, 20, 50, 100, 200]
        
        for period in periods:
            # 단순 이동평균
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            
            # 지수 이동평균
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            
            # 이동평균 대비 위치
            df[f'close_vs_sma_{period}'] = (df['close'] - df[f'sma_{period}']) / df[f'sma_{period}']
            df[f'close_vs_ema_{period}'] = (df['close'] - df[f'ema_{period}']) / df[f'ema_{period}']
        
        # 이동평균 기울기
        df['sma_20_slope'] = df['sma_20'].pct_change(5)
        df['ema_20_slope'] = df['ema_20'].pct_change(5)
        
        return df
    
    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """모멘텀 지표"""
        
        # RSI
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        df['rsi_30'] = self._calculate_rsi(df['close'], 30)
        
        # MACD
        macd, macd_signal, macd_hist = self._calculate_macd(df['close'])
        df['macd'] = macd
        df['macd_signal'] = macd_signal
        df['macd_histogram'] = macd_hist
        
        # 스토캐스틱
        df['stoch_k'], df['stoch_d'] = self._calculate_stochastic(df, 14, 3)
        
        # Williams %R
        df['williams_r'] = self._calculate_williams_r(df, 14)
        
        # ROC (Rate of Change)
        df['roc_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
        df['roc_20'] = ((df['close'] - df['close'].shift(20)) / df['close'].shift(20)) * 100
        
        return df
    
    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """변동성 지표"""
        
        # 볼린저 밴드
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        df['bb_width'] = (bb_upper - bb_lower) / bb_middle
        df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # ATR (Average True Range)
        df['atr'] = self._calculate_atr(df)
        
        # 변동성 (표준편차)
        df['volatility_10'] = df['close'].rolling(window=10).std()
        df['volatility_20'] = df['close'].rolling(window=20).std()
        
        return df
    
    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """거래량 지표"""
        
        # 거래량 이동평균
        df['volume_sma_10'] = df['volume'].rolling(window=10).mean()
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        
        # 상대 거래량
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        # VWAP (Volume Weighted Average Price)
        df['vwap'] = self._calculate_vwap(df)
        
        # OBV (On Balance Volume)
        df['obv'] = self._calculate_obv(df)
        
        return df
    
    def _add_additional_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """추가 지표들"""
        
        # 연속 상승/하락
        df['consecutive_up'] = self._calculate_consecutive(df['close'] > df['close'].shift(1))
        df['consecutive_down'] = self._calculate_consecutive(df['close'] < df['close'].shift(1))
        
        # 최고점/최저점 이후 기간
        df['bars_since_high'] = self._bars_since_extreme(df['high'], 'max')
        df['bars_since_low'] = self._bars_since_extreme(df['low'], 'min')
        
        # 시간 특성 (시간대별 패턴)
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        
        return df
    
    # ============================================================================
    # 지표 계산 헬퍼 함수들
    # ============================================================================
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD 계산"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        return macd, macd_signal, macd_histogram
    
    def _calculate_stochastic(self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """스토캐스틱 계산"""
        lowest_low = df['low'].rolling(window=k_period).min()
        highest_high = df['high'].rolling(window=k_period).max()
        k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent
    
    def _calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Williams %R 계산"""
        highest_high = df['high'].rolling(window=period).max()
        lowest_low = df['low'].rolling(window=period).min()
        return -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """볼린저 밴드 계산"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR 계산"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """VWAP 계산 (당일 기준)"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap
    
    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """OBV 계산"""
        obv = pd.Series(index=df.index, dtype=float)
        obv.iloc[0] = df['volume'].iloc[0]
        
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    
    def _calculate_consecutive(self, condition: pd.Series) -> pd.Series:
        """연속 조건 만족 횟수 계산"""
        consecutive = pd.Series(0, index=condition.index)
        count = 0
        
        for i, val in enumerate(condition):
            if val:
                count += 1
            else:
                count = 0
            consecutive.iloc[i] = count
        
        return consecutive
    
    def _bars_since_extreme(self, series: pd.Series, extreme_type: str, window: int = 50) -> pd.Series:
        """최고점/최저점 이후 경과 기간"""
        result = pd.Series(0, index=series.index)
        
        for i in range(window, len(series)):
            window_data = series.iloc[i-window:i+1]
            if extreme_type == 'max':
                extreme_idx = window_data.idxmax()
            else:
                extreme_idx = window_data.idxmin()
            
            bars_since = i - window_data.index.get_loc(extreme_idx)
            result.iloc[i] = bars_since
        
        return result
    
    def get_latest_data(self, interval: str = "15", limit: int = 100) -> Optional[pd.DataFrame]:
        """최신 데이터 수집 (실시간용)"""
        try:
            params = {
                "category": "linear",
                "symbol": self.symbol,
                "interval": interval,
                "limit": str(limit)
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            if data.get("retCode") != 0:
                return None
            
            klines = data.get("result", {}).get("list", [])
            if not klines:
                return None
            
            df = pd.DataFrame(klines, columns=[
                "timestamp", "open", "high", "low", "close", "volume", "turnover"
            ])
            
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms")
            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                df[col] = df[col].astype(float)
            
            df = df.sort_values("timestamp").reset_index(drop=True)
            df.set_index("timestamp", inplace=True)
            
            # 기술적 지표 계산
            df = self.calculate_technical_indicators(df)
            
            return df
            
        except Exception as e:
            print(f"❌ 최신 데이터 수집 실패: {e}")
            return None
    
    def save_data(self, df: pd.DataFrame, filename: str = None) -> bool:
        """데이터 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"market_data_{self.symbol}_{timestamp}.csv"
            
            # data 폴더에 저장
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            filepath = data_dir / filename
            df.to_csv(filepath)
            
            print(f"✅ 데이터 저장 완료: {filepath}")
            print(f"   크기: {len(df)}행 × {len(df.columns)}열")
            
            return True
            
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {e}")
            return False
    
    def get_indicator_summary(self, df: pd.DataFrame) -> Dict:
        """지표 요약 정보"""
        try:
            latest = df.iloc[-1]
            
            return {
                "timestamp": df.index[-1].isoformat(),
                "price": {
                    "close": latest['close'],
                    "change_24h": latest['price_change'] * 100,
                    "volume": latest['volume']
                },
                "trend": {
                    "sma_20": latest['close_vs_sma_20'] * 100,
                    "ema_20": latest['close_vs_ema_20'] * 100,
                    "macd": latest['macd'],
                    "macd_signal": latest['macd_signal']
                },
                "momentum": {
                    "rsi_14": latest['rsi_14'],
                    "stoch_k": latest['stoch_k'],
                    "williams_r": latest['williams_r']
                },
                "volatility": {
                    "bb_position": latest['bb_position'],
                    "atr": latest['atr'],
                    "volatility_20": latest['volatility_20']
                }
            }
            
        except Exception as e:
            print(f"❌ 지표 요약 생성 실패: {e}")
            return {}

# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
    print("🚀 DataCollector 테스트 시작")
    
    # 데이터 수집기 생성
    collector = DataCollector("BTCUSDT")
    
    # 과거 7일 15분봉 데이터 수집 테스트
    print("\n📊 과거 데이터 수집 테스트")
    df = collector.collect_historical_data(interval="15", days=7)
    
    if df is not None:
        print(f"✅ 수집 완료: {len(df)}개 데이터")
        print(f"📈 컬럼: {list(df.columns)}")
        
        # 기술적 지표 계산
        df_with_indicators = collector.calculate_technical_indicators(df)
        print(f"🔧 지표 추가 후: {len(df_with_indicators.columns)}개 컬럼")
        
        # 요약 정보
        summary = collector.get_indicator_summary(df_with_indicators)
        print(f"📋 현재 지표 요약:")
        print(f"   가격: ${summary.get('price', {}).get('close', 0):,.2f}")
        print(f"   RSI: {summary.get('momentum', {}).get('rsi_14', 0):.1f}")
        print(f"   MACD: {summary.get('trend', {}).get('macd', 0):.4f}")
        
        # 데이터 저장 테스트
        collector.save_data(df_with_indicators, "test_data.csv")
        
    print("\n✅ DataCollector 테스트 완료")