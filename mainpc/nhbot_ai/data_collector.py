# 파일 경로: mainpc/nhbot_ai/data_collector.py
# 코드명: 메인 PC용 데이터 수집 및 기술적 지표 계산 (GPU 최적화 + 추가 지표)

import os
import numpy as np
import pandas as pd
import cupy as cp
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class DataCollector:
    """메인 PC용 데이터 수집 및 기술적 지표 계산 클래스 (GPU 최적화)"""
    
    def __init__(
        self, 
        symbol: str = "BTCUSDT", 
        config_path: str = None
    ):
        self.symbol = symbol
        self.base_url = "https://api.bybit.com/v5/market/kline"
        
        # 데이터베이스 경로 설정
        self.config_path = config_path or Path(__file__).parent.parent / 'config' / 'data_config.db'
        self.conn = sqlite3.connect(str(self.config_path))
        self._create_tables()
        
        # GPU 지원 여부 확인
        self.gpu_available = self._check_gpu_availability()
        
        # 시간대별 수집 설정
        self.intervals = {
            "1": "1분봉",
            "5": "5분봉", 
            "15": "15분봉",
            "60": "1시간봉"
        }
        
        print(f"✅ DataCollector 초기화: {symbol}")
        print(f"🖥️ GPU 사용 가능: {self.gpu_available}")
    
    def _check_gpu_availability(self):
        """GPU 사용 가능 여부 확인"""
        try:
            cp.cuda.runtime.getDeviceCount()
            return True
        except:
            return False
    
    def _create_tables(self):
        """데이터 수집 설정 테이블 생성"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_collection_config (
                symbol TEXT PRIMARY KEY,
                interval TEXT,
                days INTEGER,
                last_collected DATETIME,
                total_bars INTEGER
            )
        ''')
        self.conn.commit()
    
    def _save_collection_config(self, interval: str, days: int):
        """데이터 수집 설정 저장"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO data_collection_config 
            (symbol, interval, days, last_collected, total_bars) 
            VALUES (?, ?, ?, ?, ?)
        ''', (
            self.symbol, 
            interval, 
            days, 
            datetime.now().isoformat(),
            days * (24 * 60 // int(interval))
        ))
        self.conn.commit()
    
    def collect_historical_data(
        self, 
        interval: str = "15", 
        days: int = 365
    ) -> Optional[pd.DataFrame]:
        """과거 데이터 수집"""
        try:
            # 수집 설정 저장
            self._save_collection_config(interval, days)
            
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
            
            # 기술적 지표 계산
            df = self.calculate_technical_indicators(df)
            
            print(f"📈 데이터 범위: {df.index[0]} ~ {df.index[-1]}")
            print(f"🔧 총 지표: {len(df.columns)}개")
            
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
        
        # ADX (추세 강도)
        df['adx'] = self._calculate_adx(df, period=14)
        df['adx_slope'] = df['adx'].diff(5)  # ADX 기울기
        
        # Aroon (추세 전환 타이밍)
        df['aroon_up'], df['aroon_down'] = self._calculate_aroon(df, period=25)
        df['aroon_oscillator'] = df['aroon_up'] - df['aroon_down']
        
        return df
    
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
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ADX (Average Directional Index) 계산"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def _calculate_aroon(self, df: pd.DataFrame, period: int = 25) -> Tuple[pd.Series, pd.Series]:
        """Aroon Indicator 계산"""
        aroon_up = df['high'].rolling(window=period).apply(
            lambda x: (period - x.argmax()) / period * 100
        )
        aroon_down = df['low'].rolling(window=period).apply(
            lambda x: (period - x.argmin()) / period * 100
        )
        return aroon_up, aroon_down

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
        
        # 🆕 Keltner Channel 추가
        kc_upper, kc_middle, kc_lower = self._calculate_keltner_channel(df)
        df['kc_upper'] = kc_upper
        df['kc_middle'] = kc_middle
        df['kc_lower'] = kc_lower
        df['kc_position'] = (df['close'] - kc_lower) / (kc_upper - kc_lower)
        
        # 🆕 Donchian Channel 추가
        dc_upper, dc_middle, dc_lower = self._calculate_donchian_channel(df)
        df['dc_upper'] = dc_upper
        df['dc_middle'] = dc_middle
        df['dc_lower'] = dc_lower
        df['dc_position'] = (df['close'] - dc_lower) / (dc_upper - dc_lower)
        
        return df

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
    
    def _calculate_keltner_channel(self, df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """🆕 Keltner Channel 계산 (ATR 기반)"""
        middle = df['close'].ewm(span=period).mean()
        atr = self._calculate_atr(df, period)
        upper = middle + (atr * multiplier)
        lower = middle - (atr * multiplier)
        return upper, middle, lower
    
    def _calculate_donchian_channel(self, df: pd.DataFrame, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """🆕 Donchian Channel 계산 (고점/저점 돌파)"""
        upper = df['high'].rolling(window=period).max()
        lower = df['low'].rolling(window=period).min()
        middle = (upper + lower) / 2
        return upper, middle, lower
    
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
        
        # CVD (Cumulative Volume Delta)
        df['cvd'] = self._calculate_cvd(df)
        df['cvd_slope'] = df['cvd'].diff(10)
        
        # MFI (Money Flow Index)
        df['mfi'] = self._calculate_mfi(df, period=14)
        
        # 🆕 VPOC (Volume Point of Control) 추가
        df['vpoc'] = self._calculate_vpoc(df, window=50)
        df['vpoc_distance'] = (df['close'] - df['vpoc']) / df['close'] * 100
        
        # 🆕 Order Flow Imbalance 추가
        df['order_flow_imbalance'] = self._calculate_order_flow_imbalance(df)
        
        return df
    
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
    
    def _calculate_cvd(self, df: pd.DataFrame) -> pd.Series:
        """Cumulative Volume Delta 계산"""
        # 간단한 버전: 가격 상승시 거래량 +, 하락시 -
        delta = np.where(df['close'] > df['close'].shift(1), df['volume'], -df['volume'])
        cvd = pd.Series(delta, index=df.index).cumsum()
        return cvd
    
    def _calculate_mfi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Money Flow Index 계산"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = pd.Series(np.where(typical_price > typical_price.shift(1), money_flow, 0))
        negative_flow = pd.Series(np.where(typical_price < typical_price.shift(1), money_flow, 0))
        
        positive_flow_sum = positive_flow.rolling(window=period).sum()
        negative_flow_sum = negative_flow.rolling(window=period).sum()
        
        mfi = 100 - (100 / (1 + positive_flow_sum / negative_flow_sum))
        return mfi
    
    def _calculate_vpoc(self, df: pd.DataFrame, window: int = 50) -> pd.Series:
        """🆕 VPOC (Volume Point of Control) 계산 - 가격대별 거래량 집중도"""
        vpoc = pd.Series(index=df.index, dtype=float)
        
        for i in range(window, len(df)):
            # 윈도우 내 데이터
            window_data = df.iloc[i-window:i+1]
            
            # 가격 구간을 20개로 나누기
            price_bins = pd.cut(window_data['close'], bins=20)
            
            # 각 가격대별 거래량 합계
            volume_profile = window_data.groupby(price_bins)['volume'].sum()
            
            # 가장 많은 거래량이 발생한 가격대의 중간값
            if len(volume_profile) > 0 and volume_profile.max() > 0:
                max_volume_bin = volume_profile.idxmax()
                vpoc.iloc[i] = max_volume_bin.mid
            else:
                vpoc.iloc[i] = window_data['close'].mean()
        
        # 초기값은 평균으로 채우기
        vpoc.fillna(df['close'].rolling(window).mean(), inplace=True)
        
        return vpoc
    
    def _calculate_order_flow_imbalance(self, df: pd.DataFrame, window: int = 10) -> pd.Series:
        """🆕 Order Flow Imbalance 계산 - 매수/매도 압력 불균형"""
        # 상승 봉의 거래량 vs 하락 봉의 거래량
        buy_volume = pd.Series(
            np.where(df['close'] > df['open'], df['volume'], 0),
            index=df.index
        )
        sell_volume = pd.Series(
            np.where(df['close'] < df['open'], df['volume'], 0),
            index=df.index
        )
        
        # 롤링 윈도우로 불균형 계산
        buy_sum = buy_volume.rolling(window=window).sum()
        sell_sum = sell_volume.rolling(window=window).sum()
        
        # 불균형 비율 (-100 ~ +100)
        total_volume = buy_sum + sell_sum
        imbalance = np.where(
            total_volume > 0,
            (buy_sum - sell_sum) / total_volume * 100,
            0
        )
        
        return pd.Series(imbalance, index=df.index)
    
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
        
        # 다중 시간대 분석 (15분봉 기준)
        df['1h_trend'] = df['close'].rolling(4).mean().diff(4) > 0  # 1시간 추세
        df['4h_trend'] = df['close'].rolling(16).mean().diff(16) > 0  # 4시간 추세
        df['trend_alignment'] = (df['1h_trend'] == df['4h_trend']).astype(int)
        
        # 고점/저점 갱신 카운터
        df['higher_highs'] = self._count_higher_highs(df, window=10)
        df['lower_lows'] = self._count_lower_lows(df, window=10)
        df['trend_strength'] = df['higher_highs'] - df['lower_lows']
        
        # 🆕 Z-score 추가 (평균 회귀)
        df['zscore_20'] = self._calculate_zscore(df['close'], window=20)
        df['zscore_50'] = self._calculate_zscore(df['close'], window=50)
        
        # 🆕 Pivot Points 추가 (지지/저항)
        df['pivot'], df['resistance1'], df['support1'], df['resistance2'], df['support2'] = self._calculate_pivot_points(df)
        df['pivot_position'] = (df['close'] - df['pivot']) / df['close'] * 100
        
        # 🆕 Market Structure Break 추가 (시장 구조 변화)
        df['market_structure_break'] = self._calculate_market_structure_break(df)
        df['ms_break_strength'] = df['market_structure_break'].rolling(10).sum()
        
        return df
    
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
    
    def _count_higher_highs(self, df: pd.DataFrame, window: int = 10) -> pd.Series:
        """연속 고점 갱신 카운터"""
        result = pd.Series(0, index=df.index)
        
        for i in range(window, len(df)):
            count = 0
            for j in range(i-window+1, i+1):
                if j > 0 and df['high'].iloc[j] > df['high'].iloc[j-1]:
                    count += 1
            result.iloc[i] = count
        
        return result
    
    def _count_lower_lows(self, df: pd.DataFrame, window: int = 10) -> pd.Series:
        """연속 저점 갱신 카운터"""
        result = pd.Series(0, index=df.index)
        
        for i in range(window, len(df)):
            count = 0
            for j in range(i-window+1, i+1):
                if j > 0 and df['low'].iloc[j] < df['low'].iloc[j-1]:
                    count += 1
            result.iloc[i] = count
        
        return result
    
    def _calculate_zscore(self, prices: pd.Series, window: int = 20) -> pd.Series:
        """🆕 Z-score 계산 - 평균 회귀 측정"""
        mean = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        zscore = (prices - mean) / std
        return zscore
    
    def _calculate_pivot_points(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        """🆕 Pivot Points 계산 - 지지/저항선"""
        # 전일 고가, 저가, 종가 기준
        pivot = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
        
        # 저항선
        resistance1 = 2 * pivot - df['low'].shift(1)
        resistance2 = pivot + (df['high'].shift(1) - df['low'].shift(1))
        
        # 지지선
        support1 = 2 * pivot - df['high'].shift(1)
        support2 = pivot - (df['high'].shift(1) - df['low'].shift(1))
        
        return pivot, resistance1, support1, resistance2, support2
    
    def _calculate_market_structure_break(self, df: pd.DataFrame, window: int = 20) -> pd.Series:
        """🆕 Market Structure Break 계산 - 시장 구조 변화 감지"""
        result = pd.Series(0, index=df.index)
        
        for i in range(window, len(df)):
            # 이전 고점/저점
            prev_high = df['high'].iloc[i-window:i].max()
            prev_low = df['low'].iloc[i-window:i].min()
            
            # 구조 돌파 체크
            if df['close'].iloc[i] > prev_high:
                result.iloc[i] = 1  # 상승 돌파
            elif df['close'].iloc[i] < prev_low:
                result.iloc[i] = -1  # 하락 돌파
            else:
                result.iloc[i] = 0  # 횡보
        
        return result
    
    def save_data(self, df: pd.DataFrame, filename: str = None) -> bool:
        """데이터 저장"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"market_data_{self.symbol}_{timestamp}.csv"
            
            # data 폴더에 저장
            data_dir = Path(__file__).parent.parent / 'data'
            data_dir.mkdir(exist_ok=True)
            
            filepath = data_dir / filename
            df.to_csv(filepath)
            
            print(f"✅ 데이터 저장 완료: {filepath}")
            print(f"   크기: {len(df)}행 × {len(df.columns)}열")
            
            return True
            
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {e}")
            return False
    
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
                    "macd_signal": latest['macd_signal'],
                    "adx": latest['adx'],
                    "trend_strength": latest['trend_strength']
                },
                "momentum": {
                    "rsi_14": latest['rsi_14'],
                    "stoch_k": latest['stoch_k'],
                    "williams_r": latest['williams_r'],
                    "aroon_oscillator": latest['aroon_oscillator']
                },
                "volatility": {
                    "bb_position": latest['bb_position'],
                    "kc_position": latest['kc_position'],
                    "dc_position": latest['dc_position'],
                    "atr": latest['atr'],
                    "volatility_20": latest['volatility_20']
                },
                "volume": {
                    "volume_ratio": latest['volume_ratio'],
                    "cvd": latest['cvd'],
                    "mfi": latest['mfi'],
                    "vpoc_distance": latest['vpoc_distance'],
                    "order_flow_imbalance": latest['order_flow_imbalance']
                },
                "advanced": {
                    "zscore_20": latest['zscore_20'],
                    "zscore_50": latest['zscore_50'],
                    "pivot_position": latest['pivot_position'],
                    "market_structure_break": latest['market_structure_break'],
                    "ms_break_strength": latest['ms_break_strength']
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
    print("📊 모든 지표 포함 버전")
    
    # 데이터 수집기 생성
    collector = DataCollector("BTCUSDT")
    
    # 과거 7일 15분봉 데이터 수집 테스트
    print("\n📊 과거 데이터 수집 테스트")
    df = collector.collect_historical_data(interval="15", days=7)
    
    if df is not None:
        print(f"✅ 수집 완료: {len(df)}개 데이터")
        print(f"📈 총 컬럼 수: {len(df.columns)}개")
        
        # 새로 추가된 지표 확인
        new_indicators = [
            'kc_upper', 'kc_position',  # Keltner Channel
            'dc_upper', 'dc_position',  # Donchian Channel
            'vpoc', 'vpoc_distance',  # VPOC
            'order_flow_imbalance',  # Order Flow
            'zscore_20', 'zscore_50',  # Z-score
            'pivot', 'resistance1', 'support1',  # Pivot Points
            'market_structure_break', 'ms_break_strength'  # Market Structure
        ]
        
        print("\n🆕 새로 추가된 지표 확인:")
        for indicator in new_indicators:
            if indicator in df.columns:
                print(f"   ✅ {indicator}: {df[indicator].iloc[-1]:.4f}")
            else:
                print(f"   ❌ {indicator}: 없음")
        
        # 요약 정보
        summary = collector.get_indicator_summary(df)
        print(f"\n📋 현재 지표 요약:")
        print(f"   가격: ${summary.get('price', {}).get('close', 0):,.2f}")
        print(f"   RSI: {summary.get('momentum', {}).get('rsi_14', 0):.1f}")
        print(f"   MACD: {summary.get('trend', {}).get('macd', 0):.4f}")
        print(f"   ADX: {summary.get('trend', {}).get('adx', 0):.1f}")
        print(f"   Trend Strength: {summary.get('trend', {}).get('trend_strength', 0):.1f}")
        print(f"   Z-score(20): {summary.get('advanced', {}).get('zscore_20', 0):.2f}")
        print(f"   VPOC Distance: {summary.get('volume', {}).get('vpoc_distance', 0):.2f}%")
        print(f"   Order Flow Imbalance: {summary.get('volume', {}).get('order_flow_imbalance', 0):.1f}")
        print(f"   Market Structure: {summary.get('advanced', {}).get('market_structure_break', 0):.0f}")
        
        # 데이터 저장 테스트
        collector.save_data(df, "test_data_complete.csv")
        
    print("\n✅ DataCollector 테스트 완료 - 모든 지표 추가됨!")