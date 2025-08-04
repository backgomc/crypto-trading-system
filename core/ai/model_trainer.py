# 파일 경로: core/ai/model_trainer.py
# 코드명: AI 모델 학습 클래스 (사용자 선택 지표 기반)

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pickle
import json
from datetime import datetime
from pathlib import Path
import threading
import time
from typing import Dict, List, Optional, Tuple, Callable

from .data_collector import DataCollector
from .model_manager import ModelManager

class ModelTrainer:
    """AI 모델 학습 클래스 (사용자 커스터마이징 지원)"""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.model_manager = ModelManager()
        self.data_collector = DataCollector(symbol)
        
        # 학습 상태 관리
        self.is_training = False
        self.training_thread = None
        self.training_status = {
            "status": "idle",  # idle, running, completed, failed
            "current_epoch": 0,
            "total_epochs": 0,
            "current_batch": 0,
            "total_batches": 0,
            "metrics": {
                "loss": 0.0,
                "accuracy": 0.0,
                "val_loss": 0.0,
                "val_accuracy": 0.0
            },
            "start_time": None,
            "progress_callback": None
        }
        
        # 지표 매핑 (웹 UI 선택 → 실제 컬럼명)
        self.indicator_mapping = {
            # 가격 지표
            "price": ["open", "high", "low", "close", "volume", "price_change", "hl_range"],
            "sma": ["sma_5", "sma_10", "sma_20", "sma_50", "close_vs_sma_20"],
            "ema": ["ema_5", "ema_10", "ema_20", "ema_50", "close_vs_ema_20"],
            "bb": ["bb_upper", "bb_lower", "bb_position", "bb_width"],
            
            # 모멘텀 지표
            "rsi": ["rsi_14", "rsi_30"],
            "macd": ["macd", "macd_signal", "macd_histogram"],
            "stoch": ["stoch_k", "stoch_d"],
            "williams": ["williams_r"],
            
            # 거래량 지표
            "volume": ["volume_ratio", "volume_sma_10", "volume_sma_20"],
            "vwap": ["vwap"],
            
            # 변동성 지표
            "atr": ["atr"],
            "volatility": ["volatility_10", "volatility_20"]
        }
        
        print(f"✅ ModelTrainer 초기화 완료: {symbol}")
    
    def start_training(self, 
                      selected_indicators: Dict[str, bool],
                      training_params: Dict,
                      progress_callback: Optional[Callable] = None) -> bool:
        """비동기 학습 시작"""
        if self.is_training:
            print("❌ 이미 학습이 진행 중입니다.")
            return False
        
        try:
            # 학습 상태 초기화
            self.training_status = {
                "status": "running",
                "current_epoch": 0,
                "total_epochs": training_params.get("epochs", 100),
                "current_batch": 0,
                "total_batches": 0,
                "metrics": {"loss": 0.0, "accuracy": 0.0, "val_loss": 0.0, "val_accuracy": 0.0},
                "start_time": datetime.now(),
                "progress_callback": progress_callback
            }
            
            # 백그라운드 스레드에서 학습 실행
            self.training_thread = threading.Thread(
                target=self._train_model_async,
                args=(selected_indicators, training_params),
                daemon=True
            )
            
            self.is_training = True
            self.training_thread.start()
            
            print("🚀 AI 모델 학습을 백그라운드에서 시작했습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 학습 시작 실패: {e}")
            self.training_status["status"] = "failed"
            return False
    
    def stop_training(self) -> bool:
        """학습 중지"""
        if not self.is_training:
            return False
        
        try:
            self.is_training = False
            self.training_status["status"] = "stopped"
            
            if self.training_thread and self.training_thread.is_alive():
                # 스레드가 종료될 때까지 잠시 대기
                self.training_thread.join(timeout=5)
            
            print("⏹️ AI 모델 학습이 중지되었습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 학습 중지 실패: {e}")
            return False
    
    def get_training_status(self) -> Dict:
        """현재 학습 상태 조회"""
        return self.training_status.copy()
    
    def _train_model_async(self, selected_indicators: Dict[str, bool], training_params: Dict):
        """비동기 학습 실행 (내부 메서드)"""
        try:
            print("📊 데이터 수집 시작...")
            self._update_progress_callback("데이터 수집 중...")
            
            # 1. 데이터 수집
            training_days = training_params.get("training_days", 365)
            interval = training_params.get("interval", "15")
            
            df = self.data_collector.collect_historical_data(interval=interval, days=training_days)
            if df is None or len(df) < 1000:
                raise Exception("충분한 학습 데이터를 수집할 수 없습니다.")
            
            # 2. 기술적 지표 계산
            print("🔧 기술적 지표 계산 중...")
            self._update_progress_callback("기술적 지표 계산 중...")
            df = self.data_collector.calculate_technical_indicators(df)
            
            # 3. 선택된 지표만 추출
            print("📋 선택된 지표 추출 중...")
            feature_data = self._prepare_features(df, selected_indicators)
            
            # 4. 라벨링 (추세 전환 감지)
            print("🏷️ 라벨 생성 중...")
            labels = self._create_labels(df)
            
            # 5. 학습 데이터 준비
            print("📈 학습 데이터 준비 중...")
            X, y, scaler = self._prepare_training_data(feature_data, labels, training_params)
            
            # 6. 모델 구성
            print("🧠 모델 구성 중...")
            model = self._build_model(X.shape, training_params)
            
            # 7. 학습 실행
            print("🚀 모델 학습 시작...")
            self._update_progress_callback("모델 학습 중...")
            
            history = self._train_with_progress(model, X, y, training_params)
            
            # 8. 모델 평가
            print("📊 모델 평가 중...")
            accuracy = self._evaluate_model(model, X, y)
            
            # 9. 모델 저장
            print("💾 모델 저장 중...")
            model_name = self.model_manager.generate_model_name()
            
            model_data = {
                "parameters": training_params,
                "indicators": selected_indicators,
                "training_duration": (datetime.now() - self.training_status["start_time"]).total_seconds(),
                "feature_columns": list(feature_data.columns),
                "data_shape": X.shape
            }
            
            # 모델 파일 저장
            model_path = Path("models") / f"{model_name}.h5"
            scaler_path = Path("models") / f"{model_name}_scaler.pkl"
            
            model.save(model_path)
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
            
            # 메타데이터 저장
            self.model_manager.save_model(model_name, model_data, accuracy)
            
            # 학습 완료
            self.training_status["status"] = "completed"
            self.training_status["metrics"]["accuracy"] = accuracy
            
            print(f"✅ 모델 학습 완료! 정확도: {accuracy:.3f}")
            self._update_progress_callback(f"학습 완료! 정확도: {accuracy:.1%}")
            
        except Exception as e:
            print(f"❌ 학습 중 오류 발생: {e}")
            self.training_status["status"] = "failed"
            self._update_progress_callback(f"학습 실패: {str(e)}")
        
        finally:
            self.is_training = False
    
    def _prepare_features(self, df: pd.DataFrame, selected_indicators: Dict[str, bool]) -> pd.DataFrame:
        """선택된 지표만 추출하여 특성 데이터 생성"""
        feature_columns = []
        
        print("📋 선택된 지표:")
        for indicator, selected in selected_indicators.items():
            if selected and indicator in self.indicator_mapping:
                columns = self.indicator_mapping[indicator]
                # 실제로 존재하는 컬럼만 추가
                existing_columns = [col for col in columns if col in df.columns]
                feature_columns.extend(existing_columns)
                print(f"   ✅ {indicator}: {len(existing_columns)}개 컬럼")
            elif selected:
                print(f"   ⚠️ {indicator}: 지원하지 않는 지표")
        
        if not feature_columns:
            raise Exception("선택된 지표가 없습니다. 최소 하나 이상의 지표를 선택해주세요.")
        
        print(f"📊 총 특성 개수: {len(feature_columns)}개")
        
        # 중복 제거 후 반환
        feature_columns = list(set(feature_columns))
        return df[feature_columns].dropna()
    
    def _create_labels(self, df: pd.DataFrame, 
                      future_window: int = 4,  # 1시간 후 (15분봉 기준)
                      significant_change: float = 0.005) -> pd.Series:
        """추세 전환 라벨 생성 (NHBot 특화)"""
        
        # 기본 가격 변화 계산
        future_prices = df['close'].shift(-future_window)
        price_change = (future_prices - df['close']) / df['close']
        
        # MACD 기반 추세 전환 감지
        macd_signal = np.where(df['macd'] > df['macd_signal'], 1, -1)
        macd_change = np.diff(macd_signal, prepend=macd_signal[0])
        
        # 의미있는 추세 전환 조건
        # 1. MACD 신호 전환이 있음
        # 2. 가격 변화가 유의미함 (0.5% 이상)
        # 3. RSI가 과매수/과매도 영역에 있지 않음 (30-70 범위)
        
        trend_reversal = (
            (abs(macd_change) > 0) &  # MACD 신호 전환
            (abs(price_change) > significant_change) &  # 유의미한 가격 변화
            (df['rsi_14'] > 30) & (df['rsi_14'] < 70) &  # 중립 영역
            (df['bb_position'] > 0.2) & (df['bb_position'] < 0.8)  # 볼린저밴드 중립
        )
        
        # 라벨 생성: 1(매매 허용), 0(매매 금지)
        labels = trend_reversal.astype(int)
        
        positive_ratio = labels.sum() / len(labels)
        print(f"🏷️ 라벨 분포: 매매 허용 {positive_ratio:.1%}, 매매 금지 {1-positive_ratio:.1%}")
        
        return labels
    
    def _prepare_training_data(self, feature_data: pd.DataFrame, labels: pd.Series, 
                              training_params: Dict) -> Tuple[np.ndarray, np.ndarray, MinMaxScaler]:
        """학습 데이터 준비 (시퀀스 데이터로 변환)"""
        
        sequence_length = training_params.get("sequence_length", 60)
        
        # 데이터 정규화
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(feature_data)
        
        # 시퀀스 데이터 생성
        X, y = [], []
        
        for i in range(sequence_length, len(scaled_features)):
            if not self.is_training:  # 중지 요청 확인
                break
                
            X.append(scaled_features[i-sequence_length:i])
            y.append(labels.iloc[i])
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"📊 학습 데이터 형태: X={X.shape}, y={y.shape}")
        
        return X, y, scaler
    
    def _build_model(self, input_shape: Tuple, training_params: Dict) -> tf.keras.Model:
        """LSTM 모델 구성"""
        
        model = Sequential([
            # 첫 번째 LSTM 레이어
            LSTM(64, return_sequences=True, input_shape=input_shape[1:]),
            Dropout(0.2),
            BatchNormalization(),
            
            # 두 번째 LSTM 레이어  
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            BatchNormalization(),
            
            # Dense 레이어들
            Dense(32, activation='relu'),
            Dropout(0.3),
            Dense(16, activation='relu'),
            Dropout(0.2),
            
            # 출력 레이어 (이진 분류)
            Dense(1, activation='sigmoid')
        ])
        
        # 컴파일
        learning_rate = training_params.get("learning_rate", 0.001)
        optimizer = Adam(learning_rate=learning_rate)
        
        model.compile(
            optimizer=optimizer,
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        print("🧠 모델 구조:")
        model.summary()
        
        return model
    
    def _train_with_progress(self, model: tf.keras.Model, X: np.ndarray, y: np.ndarray, 
                           training_params: Dict) -> tf.keras.callbacks.History:
        """진행률 모니터링과 함께 학습 실행"""
        
        # 학습/검증 데이터 분할
        validation_split = training_params.get("validation_split", 20) / 100
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        # 배치 크기
        batch_size = training_params.get("batch_size", 32)
        epochs = training_params.get("epochs", 100)
        
        # 총 배치 수 계산
        total_batches = len(X_train) // batch_size
        self.training_status["total_batches"] = total_batches
        
        # 콜백 함수들
        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True),
            ReduceLROnPlateau(factor=0.5, patience=5, min_lr=1e-7),
            TrainingProgressCallback(self)  # 커스텀 콜백
        ]
        
        # 학습 실행
        history = model.fit(
            X_train, y_train,
            batch_size=batch_size,
            epochs=epochs,
            validation_data=(X_val, y_val),
            callbacks=callbacks,
            verbose=0  # 진행률은 커스텀 콜백에서 처리
        )
        
        return history
    
    def _evaluate_model(self, model: tf.keras.Model, X: np.ndarray, y: np.ndarray) -> float:
        """모델 평가"""
        
        # 예측 수행
        y_pred_proba = model.predict(X, verbose=0)
        y_pred = (y_pred_proba > 0.5).astype(int).flatten()
        
        # 정확도 계산
        accuracy = accuracy_score(y, y_pred)
        
        # 상세 리포트
        print("\n📊 모델 평가 결과:")
        print(f"   정확도: {accuracy:.3f}")
        print("\n분류 리포트:")
        print(classification_report(y, y_pred, target_names=['매매 금지', '매매 허용']))
        
        return accuracy
    
    def _update_progress_callback(self, message: str):
        """진행률 콜백 업데이트"""
        if self.training_status.get("progress_callback"):
            try:
                self.training_status["progress_callback"](message)
            except:
                pass

class TrainingProgressCallback(tf.keras.callbacks.Callback):
    """학습 진행률 모니터링 콜백"""
    
    def __init__(self, trainer: ModelTrainer):
        super().__init__()
        self.trainer = trainer
    
    def on_epoch_begin(self, epoch, logs=None):
        if not self.trainer.is_training:
            self.model.stop_training = True
            return
            
        self.trainer.training_status["current_epoch"] = epoch + 1
        self.trainer._update_progress_callback(f"에폭 {epoch + 1}/{self.trainer.training_status['total_epochs']}")
    
    def on_batch_end(self, batch, logs=None):
        if not self.trainer.is_training:
            self.model.stop_training = True
            return
            
        self.trainer.training_status["current_batch"] = batch + 1
        
        # 메트릭 업데이트
        if logs:
            metrics = self.trainer.training_status["metrics"]
            metrics["loss"] = logs.get("loss", 0)
            metrics["accuracy"] = logs.get("accuracy", 0)
            metrics["val_loss"] = logs.get("val_loss", 0)
            metrics["val_accuracy"] = logs.get("val_accuracy", 0)
    
    def on_epoch_end(self, epoch, logs=None):
        if logs:
            metrics = self.trainer.training_status["metrics"] 
            metrics["loss"] = logs.get("loss", 0)
            metrics["accuracy"] = logs.get("accuracy", 0)
            metrics["val_loss"] = logs.get("val_loss", 0)
            metrics["val_accuracy"] = logs.get("val_accuracy", 0)
            
            print(f"에폭 {epoch + 1}: 손실={metrics['loss']:.4f}, 정확도={metrics['accuracy']:.3f}")

# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
    print("🚀 ModelTrainer 테스트 시작")
    
    # 학습기 생성
    trainer = ModelTrainer("BTCUSDT")
    
    # 선택된 지표 (웹 UI에서 받을 데이터)
    selected_indicators = {
        "price": True,
        "sma": True,
        "ema": True,
        "rsi": True,
        "macd": True,
        "bb": True,
        "stoch": False,  # 스토캐스틱 사용 안함
        "williams": False,
        "volume": True,
        "atr": True,
        "volatility": True
    }
    
    # 학습 파라미터 (웹 UI에서 받을 데이터)
    training_params = {
        "training_days": 30,  # 테스트용으로 30일만
        "epochs": 10,         # 테스트용으로 10에폭만
        "batch_size": 32,
        "learning_rate": 0.001,
        "sequence_length": 60,
        "validation_split": 20,
        "interval": "15"
    }
    
    # 진행률 콜백 함수
    def progress_callback(message):
        print(f"📢 {message}")
    
    # 학습 시작
    success = trainer.start_training(selected_indicators, training_params, progress_callback)
    
    if success:
        print("✅ 학습이 백그라운드에서 시작되었습니다.")
        
        # 상태 모니터링
        while trainer.is_training:
            status = trainer.get_training_status()
            print(f"진행률: {status['current_epoch']}/{status['total_epochs']} 에폭")
            time.sleep(5)
        
        # 최종 결과
        final_status = trainer.get_training_status()
        print(f"🏁 학습 완료! 상태: {final_status['status']}")
        
    else:
        print("❌ 학습 시작 실패")
    
    print("\n✅ ModelTrainer 테스트 완료")