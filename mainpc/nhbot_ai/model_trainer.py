# 파일 경로: mainpc/nhbot_ai/model_trainer.py
# 코드명: AI 모델 학습 클래스 (3-클래스 분류, MACD 제외 버전)

import tensorflow as tf
import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight
import pickle
import json
from datetime import datetime
from pathlib import Path
import threading
import time
from typing import Dict, List, Optional, Tuple, Callable

class ModelTrainer:
    """AI 모델 학습 클래스 (3-클래스: none/long/short)"""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        
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
        
        # 🆕 MACD 제외한 필수 지표
        self.essential_indicators = {
            # 가격 움직임
            "price": ["close", "price_change", "price_change_abs", "hl_range"],
            
            # 모멘텀 (MACD 완전 제외!)
            "rsi": ["rsi_14", "rsi_30"],
            "stoch": ["stoch_k", "stoch_d"],
            "williams": ["williams_r"],
            
            # 추세 강도
            "adx": ["adx", "adx_slope"],
            "aroon": ["aroon_up", "aroon_down", "aroon_oscillator"],
            
            # 변동성
            "bb": ["bb_position", "bb_width"],
            "atr": ["atr"],
            
            # 거래량
            "volume": ["volume_ratio", "cvd", "cvd_slope", "mfi"],
            
            # 패턴
            "consecutive": ["consecutive_up", "consecutive_down"],
            "trend": ["1h_trend", "4h_trend", "trend_alignment", "trend_strength"]
        }
        
        self.optional_indicators = {
            # 선택적 지표
            "sma": ["sma_20", "close_vs_sma_20", "sma_20_slope"],
            "ema": ["ema_20", "ema_50", "ema_20_slope"],
            "volatility": ["volatility_10", "volatility_20"],
            "vwap": ["vwap"],
            "pivot": ["pivot_position"],
            "zscore": ["zscore_20", "zscore_50"]
        }
        
        # 전체 지표 통합
        self.indicator_mapping = {**self.essential_indicators, **self.optional_indicators}
        
        print(f"✅ ModelTrainer 초기화 완료: {symbol}")
        print(f"   모드: 3-클래스 분류 (none/long/short)")
    
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
            
            # 스레드 내부에서 DataCollector 생성
            from .data_collector import DataCollector
            data_collector = DataCollector(self.symbol)
            
            # 1. 데이터 수집
            training_days = training_params.get("training_days", 365)
            interval = training_params.get("interval", "15")
            
            df = data_collector.collect_historical_data(interval=interval, days=training_days)
            if df is None or len(df) < 1000:
                raise Exception("충분한 학습 데이터를 수집할 수 없습니다.")
            
            # 2. 선택된 지표 추출 (MACD 제외)
            print("📋 선택된 지표 추출 중...")
            self._update_progress_callback("선택된 지표 추출 중...")
            feature_data = self._prepare_features(df, selected_indicators)
            
            # 3. 🆕 3-클래스 라벨링 (추세 전환 방향 구분)
            print("🏷️ 라벨 생성 중 (3-클래스)...")
            labels = self._create_labels_3class(df)
            
            # 4. 학습 데이터 준비
            print("📈 학습 데이터 준비 중...")
            X, y, scaler = self._prepare_training_data(feature_data, labels, training_params)
            
            # 5. 🆕 3-클래스 모델 구성
            print("🧠 모델 구성 중...")
            model = self._build_model_3class(X.shape, training_params)
            
            # 6. 학습 실행
            print("🚀 모델 학습 시작...")
            self._update_progress_callback("모델 학습 중...")
            
            history = self._train_with_progress(model, X, y, training_params)
            
            # 7. 모델 평가
            print("📊 모델 평가 중...")
            accuracy = self._evaluate_model_3class(model, X, y)
            
            # 8. 모델 저장
            print("💾 모델 저장 중...")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_name = f"model_3class_{timestamp}"
            
            model_path = Path("models") / f"{model_name}.h5"
            scaler_path = Path("models") / f"{model_name}_scaler.pkl"
            info_path = Path("models") / f"{model_name}_info.json"
            
            model_path.parent.mkdir(exist_ok=True)
            model.save(str(model_path))
            
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
            
            # 학습 정보 저장
            training_info = {
                "model_name": model_name,
                "model_type": "3-class",  # 모델 타입 명시
                "classes": ["none", "long", "short"],
                "accuracy": float(accuracy),
                "parameters": training_params,
                "indicators": selected_indicators,
                "training_duration": (datetime.now() - self.training_status["start_time"]).total_seconds(),
                "feature_columns": list(feature_data.columns),
                "data_shape": [int(x) for x in X.shape],
                "created_at": datetime.now().isoformat(),
                "symbol": self.symbol
            }
            
            with open(info_path, 'w') as f:
                json.dump(training_info, f, indent=2)
            
            # 학습 완료
            self.training_status["status"] = "completed"
            self.training_status["metrics"]["accuracy"] = accuracy
            
            print(f"✅ 모델 학습 완료! 정확도: {accuracy:.3f}")
            print(f"📁 저장 위치: {model_path}")
            self._update_progress_callback(f"학습 완료! 정확도: {accuracy:.1%}")
            
        except Exception as e:
            print(f"❌ 학습 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            self.training_status["status"] = "failed"
            self._update_progress_callback(f"학습 실패: {str(e)}")
        
        finally:
            self.is_training = False
    
    def _prepare_features(self, df: pd.DataFrame, selected_indicators: Dict[str, bool]) -> pd.DataFrame:
        """선택된 지표만 추출 (MACD 완전 제외)"""
        feature_columns = []
        
        # MACD 관련 컬럼 제외 리스트
        macd_columns = ['macd', 'macd_signal', 'macd_histogram']
        
        print("📋 선택된 지표 (MACD 제외):")
        
        # 필수 지표는 항상 포함
        for indicator, columns in self.essential_indicators.items():
            # MACD 컬럼 제외
            existing_columns = [
                col for col in columns 
                if col in df.columns and col not in macd_columns
            ]
            feature_columns.extend(existing_columns)
            print(f"   ✅ {indicator}: {len(existing_columns)}개 컬럼 (필수)")
        
        # 선택적 지표
        for indicator, selected in selected_indicators.items():
            if selected and indicator in self.optional_indicators:
                columns = self.optional_indicators[indicator]
                existing_columns = [
                    col for col in columns 
                    if col in df.columns and col not in macd_columns
                ]
                feature_columns.extend(existing_columns)
                print(f"   ✅ {indicator}: {len(existing_columns)}개 컬럼 (선택)")
        
        if not feature_columns:
            raise Exception("선택된 지표가 없습니다.")
        
        # 중복 제거
        feature_columns = list(set(feature_columns))
        
        # MACD 컬럼이 실수로 포함되었는지 최종 체크
        feature_columns = [col for col in feature_columns if col not in macd_columns]
        
        print(f"📊 총 특성 개수: {len(feature_columns)}개")
        print(f"   (MACD 관련 지표 제외 확인 완료)")
        
        return df[feature_columns].dropna()
    
    def _create_labels_3class(self, df: pd.DataFrame) -> pd.Series:
        """🆕 3-클래스 라벨링 (0: none, 1: long, 2: short)"""
        
        labels = pd.Series(0, index=df.index)  # 기본값: none
        
        # 가격 기반 추세 전환 감지
        price_change_1h = df['close'].pct_change(periods=4)  # 1시간 변화율 (15분봉 4개)
        price_change_30m = df['close'].pct_change(periods=2)  # 30분 변화율
        
        # RSI 기반 신호
        rsi = df['rsi_14'] if 'rsi_14' in df.columns else pd.Series(50, index=df.index)
        
        # ADX 기반 추세 강도
        adx = df['adx'] if 'adx' in df.columns else pd.Series(25, index=df.index)
        
        # Aroon 기반 추세 전환
        aroon_osc = df['aroon_oscillator'] if 'aroon_oscillator' in df.columns else pd.Series(0, index=df.index)
        
        # 볼린저 밴드 위치
        bb_pos = df['bb_position'] if 'bb_position' in df.columns else pd.Series(0.5, index=df.index)
        
        # 연속 상승/하락
        consec_up = df['consecutive_up'] if 'consecutive_up' in df.columns else pd.Series(0, index=df.index)
        consec_down = df['consecutive_down'] if 'consecutive_down' in df.columns else pd.Series(0, index=df.index)
        
        # 🔴 상승 전환 신호 (하락→상승) - 클래스 1: long
        long_signals = (
            # 조건 1: 가격 반전 (하락 후 상승)
            ((price_change_30m.shift(1) < -0.001) & (price_change_30m > 0.001)) |
            
            # 조건 2: RSI 과매도 탈출
            ((rsi.shift(1) < 35) & (rsi > 35) & (rsi < 50)) |
            
            # 조건 3: 볼린저 밴드 하단 반등
            ((bb_pos.shift(1) < 0.1) & (bb_pos > 0.15)) |
            
            # 조건 4: Aroon 상승 전환
            ((aroon_osc.shift(1) < -30) & (aroon_osc > -10)) |
            
            # 조건 5: 연속 하락 후 반전
            ((consec_down > 5) & (price_change_30m > 0.001))
        )
        
        # 🔵 하락 전환 신호 (상승→하락) - 클래스 2: short
        short_signals = (
            # 조건 1: 가격 반전 (상승 후 하락)
            ((price_change_30m.shift(1) > 0.001) & (price_change_30m < -0.001)) |
            
            # 조건 2: RSI 과매수 탈출
            ((rsi.shift(1) > 65) & (rsi < 65) & (rsi > 50)) |
            
            # 조건 3: 볼린저 밴드 상단 반락
            ((bb_pos.shift(1) > 0.9) & (bb_pos < 0.85)) |
            
            # 조건 4: Aroon 하락 전환
            ((aroon_osc.shift(1) > 30) & (aroon_osc < 10)) |
            
            # 조건 5: 연속 상승 후 반전
            ((consec_up > 5) & (price_change_30m < -0.001))
        )
        
        # 원웨이 장 필터 (너무 강한 추세는 제외)
        extreme_trend = (adx > 50) | (consec_up > 10) | (consec_down > 10)
        
        # 최소 거래량 필터
        if 'volume_ratio' in df.columns:
            sufficient_volume = df['volume_ratio'] > 0.5
        else:
            sufficient_volume = True
        
        # 라벨 할당
        labels[long_signals & ~extreme_trend & sufficient_volume] = 1  # long
        labels[short_signals & ~extreme_trend & sufficient_volume] = 2  # short
        
        # 중복 신호 처리 (동시에 long과 short가 나오면 none으로)
        conflicting = long_signals & short_signals
        labels[conflicting] = 0
        
        # 통계 출력
        none_count = (labels == 0).sum()
        long_count = (labels == 1).sum()
        short_count = (labels == 2).sum()
        total_count = len(labels)
        
        print(f"🏷️ 3-클래스 라벨 분포:")
        print(f"   - None (클래스 0): {none_count:,}개 ({none_count/total_count*100:.1f}%)")
        print(f"   - Long (클래스 1): {long_count:,}개 ({long_count/total_count*100:.1f}%)")
        print(f"   - Short (클래스 2): {short_count:,}개 ({short_count/total_count*100:.1f}%)")
        print(f"   - 총 추세 전환: {long_count + short_count:,}개 ({(long_count + short_count)/total_count*100:.1f}%)")
        
        # 목표: 전체의 3~5% 정도가 추세 전환 신호
        signal_ratio = (long_count + short_count) / total_count
        if signal_ratio < 0.02:
            print("⚠️ 추세 전환 신호가 너무 적습니다 (2% 미만)")
        elif signal_ratio > 0.10:
            print("⚠️ 추세 전환 신호가 너무 많습니다 (10% 초과)")
        else:
            print("✅ 적절한 신호 비율입니다")
        
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
            if not self.is_training:
                break
                
            X.append(scaled_features[i-sequence_length:i])
            y.append(labels.iloc[i])
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"📊 학습 데이터 형태: X={X.shape}, y={y.shape}")
        print(f"   - 시퀀스 길이: {sequence_length}")
        print(f"   - 특성 개수: {X.shape[2] if len(X.shape) > 2 else 0}")
        print(f"   - 샘플 개수: {X.shape[0]}")
        
        return X, y, scaler
    
    def _build_model_3class(self, input_shape: Tuple, training_params: Dict) -> tf.keras.Model:
        """🆕 3-클래스 분류를 위한 LSTM 모델"""
        
        model = Sequential([
            # 첫 번째 LSTM 레이어 (증가)
            LSTM(128, return_sequences=True, input_shape=input_shape[1:]),
            Dropout(0.3),
            BatchNormalization(),
            
            # 두 번째 LSTM 레이어
            LSTM(64, return_sequences=False),
            Dropout(0.3),
            BatchNormalization(),
            
            # Dense 레이어들
            Dense(64, activation='relu'),
            Dropout(0.4),
            Dense(32, activation='relu'),
            Dropout(0.3),
            Dense(16, activation='relu'),
            Dropout(0.2),
            
            # 🆕 출력 레이어 (3-클래스)
            Dense(3, activation='softmax')  # 3개 클래스: none, long, short
        ])
        
        # 컴파일
        learning_rate = training_params.get("learning_rate", 0.001)
        optimizer = Adam(learning_rate=learning_rate)
        
        model.compile(
            optimizer=optimizer,
            loss='sparse_categorical_crossentropy',  # 3-클래스용 loss
            metrics=['accuracy', 
                    tf.keras.metrics.SparseCategoricalAccuracy(name='categorical_accuracy')]
        )
        
        print("🧠 3-클래스 모델 구조:")
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
        
        # 🆕 클래스 가중치 계산 (불균형 해결)
        unique_classes = np.unique(y_train)
        class_weights = compute_class_weight(
            'balanced',
            classes=unique_classes,
            y=y_train
        )
        class_weight_dict = {int(unique_classes[i]): class_weights[i] for i in range(len(unique_classes))}
        
        print(f"⚖️ 클래스 가중치:")
        print(f"   - None (0): {class_weight_dict.get(0, 1.0):.2f}")
        print(f"   - Long (1): {class_weight_dict.get(1, 1.0):.2f}")
        print(f"   - Short (2): {class_weight_dict.get(2, 1.0):.2f}")
        
        # 배치 크기
        batch_size = training_params.get("batch_size", 32)
        epochs = training_params.get("epochs", 100)
        
        # 총 배치 수 계산
        total_batches = len(X_train) // batch_size
        self.training_status["total_batches"] = total_batches
        
        # 콜백 함수들
        callbacks = [
            EarlyStopping(
                patience=20,  # 10 → 20으로 증가
                restore_best_weights=True,
                monitor='val_loss',
                verbose=1
            ),
            ReduceLROnPlateau(
                factor=0.5, 
                patience=10,  # 5 → 10으로 증가
                min_lr=1e-7,
                verbose=1
            ),
            TrainingProgressCallback(self)
        ]
        
        # 학습 실행 (클래스 가중치 적용)
        history = model.fit(
            X_train, y_train,
            batch_size=batch_size,
            epochs=epochs,
            validation_data=(X_val, y_val),
            class_weight=class_weight_dict,  # 클래스 가중치 적용
            callbacks=callbacks,
            verbose=0
        )
        
        return history
    
    def _evaluate_model_3class(self, model: tf.keras.Model, X: np.ndarray, y: np.ndarray) -> float:
        """🆕 3-클래스 모델 평가"""
        
        # 예측 수행
        y_pred_proba = model.predict(X, verbose=0)
        y_pred = np.argmax(y_pred_proba, axis=1)
        
        # 정확도 계산
        accuracy = accuracy_score(y, y_pred)
        
        # 혼동 행렬
        cm = confusion_matrix(y, y_pred)
        
        # 상세 리포트
        print("\n📊 3-클래스 모델 평가 결과:")
        print(f"   전체 정확도: {accuracy:.3f}")
        
        print("\n📈 클래스별 성능:")
        report = classification_report(y, y_pred, 
                                      target_names=['None (0)', 'Long (1)', 'Short (2)'],
                                      output_dict=True)
        
        for class_name in ['None (0)', 'Long (1)', 'Short (2)']:
            if class_name in report:
                metrics = report[class_name]
                print(f"   {class_name}:")
                print(f"      - Precision: {metrics['precision']:.3f}")
                print(f"      - Recall: {metrics['recall']:.3f}")
                print(f"      - F1-Score: {metrics['f1-score']:.3f}")
        
        print("\n🎯 혼동 행렬:")
        print("       예측 →")
        print("실제↓  None  Long  Short")
        labels = ['None', 'Long', 'Short']
        for i, label in enumerate(labels):
            print(f"{label:5} {cm[i][0]:5} {cm[i][1]:5} {cm[i][2]:5}")
        
        # 추세 전환 감지 성능 (Long + Short)
        signal_precision = (report.get('Long (1)', {}).get('precision', 0) + 
                          report.get('Short (2)', {}).get('precision', 0)) / 2
        signal_recall = (report.get('Long (1)', {}).get('recall', 0) + 
                       report.get('Short (2)', {}).get('recall', 0)) / 2
        
        print(f"\n🔍 추세 전환 감지 성능:")
        print(f"   - 평균 Precision: {signal_precision:.3f}")
        print(f"   - 평균 Recall: {signal_recall:.3f}")
        
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
    print("🚀 ModelTrainer 3-클래스 테스트 시작")
    
    # 학습기 생성
    trainer = ModelTrainer("BTCUSDT")
    
    # 선택된 지표 (MACD 제외)
    selected_indicators = {
        "sma": True,
        "ema": True,
        "stoch": True,
        "williams": True,
        "mfi": True,
        "vwap": True,
        "volatility": True,
        "pivot": True,
        "zscore": True
    }
    
    # 학습 파라미터
    training_params = {
        "training_days": 365,  # 1년 데이터
        "epochs": 100,
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
        print("✅ 3-클래스 학습이 시작되었습니다.")
        print("   - 클래스 0: None (추세 전환 아님)")
        print("   - 클래스 1: Long (상승 전환)")
        print("   - 클래스 2: Short (하락 전환)")
        
        # 상태 모니터링 (예시)
        import time
        for _ in range(3):
            time.sleep(5)
            status = trainer.get_training_status()
            if status['status'] == 'running':
                print(f"   진행중: {status['current_epoch']}/{status['total_epochs']} 에폭")
    else:
        print("❌ 학습 시작 실패")
    
    print("\n✅ ModelTrainer 3-클래스 테스트 완료")