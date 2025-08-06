# 파일 경로: core/ai/predictor.py
# 코드명: AI 예측기 클래스 (ModelManager 연동 버전)

import numpy as np
import pandas as pd
import tensorflow as tf
import pickle
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from core.ai.model_manager import ModelManager

class AIPredictor:
   """AI 기반 매매 신호 예측 클래스"""
   
   def __init__(self, symbol: str = "BTCUSDT"):
       self.symbol = symbol
       self.model = None
       self.scaler = None
       self.model_manager = ModelManager()
       self.model_name = None
       self.model_accuracy = 0.0
       self.feature_columns = []
       self.sequence_length = 60
       
       # 예측 임계값 (신뢰도)
       self.prediction_threshold = 0.6  # 60% 이상 확신도일 때만 신호
       
       # 모델 로드
       self.load_model()
       
       print(f"✅ AIPredictor 초기화: {symbol}")
   
   def load_model(self) -> bool:
       """AI 모델 로드 (ModelManager 사용)"""
       try:
           # ModelManager에서 활성 모델 가져오기
           active_model = self.model_manager.get_active_model()
           if not active_model:
               print("⚠️ 활성 모델이 없습니다. AI 예측 비활성화.")
               return False
           
           model_info = self.model_manager.get_model_info(active_model)
           if not model_info:
               print(f"⚠️ 모델 정보를 찾을 수 없습니다: {active_model}")
               return False
           
           # 모델 파일 경로
           model_path = model_info.get('model_path')
           scaler_path = model_info.get('scaler_path')
           info_path = model_info.get('info_path')
           
           if not Path(model_path).exists():
               print(f"⚠️ 모델 파일이 없습니다: {model_path}")
               # 원격에서 동기화 시도
               if not self.model_manager._sync_model_from_remote(active_model):
                   return False
           
           # 모델 로드
           self.model = tf.keras.models.load_model(model_path)
           self.model_name = active_model
           self.model_accuracy = model_info.get('accuracy', 0)
           
           # 스케일러 로드
           if scaler_path and Path(scaler_path).exists():
               with open(scaler_path, 'rb') as f:
                   self.scaler = pickle.load(f)
           else:
               print("⚠️ 스케일러 파일이 없습니다. 정규화 없이 예측합니다.")
           
           # 모델 정보 로드 (feature columns, sequence_length 등)
           if info_path and Path(info_path).exists():
               import json
               with open(info_path, 'r') as f:
                   info = json.load(f)
                   self.feature_columns = info.get('feature_columns', [])
                   params = info.get('parameters', {})
                   self.sequence_length = params.get('sequence_length', 60)
           
           print(f"✅ 모델 로드 완료: {active_model}")
           print(f"   정확도: {self.model_accuracy:.1%}")
           print(f"   특성 개수: {len(self.feature_columns)}")
           print(f"   시퀀스 길이: {self.sequence_length}")
           
           return True
           
       except Exception as e:
           print(f"❌ 모델 로드 실패: {e}")
           self.model = None
           self.scaler = None
           return False
   
   def reload_model(self) -> bool:
       """모델 재로드 (새 모델 활성화 시)"""
       print("🔄 AI 모델 재로드 중...")
       return self.load_model()
   
   def predict(self, market_data: pd.DataFrame) -> Dict:
       """매매 신호 예측"""
       try:
           # 모델이 없으면 중립 반환
           if self.model is None:
               return self._get_neutral_prediction()
           
           # 데이터 검증
           if market_data is None or len(market_data) < self.sequence_length:
               print(f"⚠️ 데이터 부족: {len(market_data) if market_data is not None else 0}개 (최소 {self.sequence_length}개 필요)")
               return self._get_neutral_prediction()
           
           # 특성 추출 및 전처리
           features = self._prepare_features(market_data)
           if features is None:
               return self._get_neutral_prediction()
           
           # 예측 수행
           with tf.device('/CPU:0'):  # CPU 사용 (NAS 환경)
               prediction = self.model.predict(features, verbose=0)
           
           # 예측 결과 해석
           prediction_value = float(prediction[0][0])
           
           # 신호 결정 (임계값 기반)
           if prediction_value > self.prediction_threshold:
               signal = "ALLOW"  # 매매 허용
               confidence = prediction_value
           elif prediction_value < (1 - self.prediction_threshold):
               signal = "BLOCK"  # 매매 차단
               confidence = 1 - prediction_value
           else:
               signal = "NEUTRAL"  # 중립
               confidence = 0.5
           
           # 결과 구성
           result = {
               "signal": signal,
               "confidence": confidence,
               "raw_prediction": prediction_value,
               "model_name": self.model_name,
               "model_accuracy": self.model_accuracy,
               "timestamp": datetime.now().isoformat(),
               "features_used": len(self.feature_columns),
               "threshold": self.prediction_threshold
           }
           
           # 예측 이유 추가 (디버깅용)
           result["reason"] = self._get_prediction_reason(market_data, prediction_value)
           
           return result
           
       except Exception as e:
           print(f"❌ 예측 중 오류: {e}")
           return self._get_neutral_prediction()
   
   def _prepare_features(self, market_data: pd.DataFrame) -> Optional[np.ndarray]:
       """예측을 위한 특성 준비"""
       try:
           # 필요한 컬럼만 선택
           if self.feature_columns:
               # 모델 학습 시 사용한 컬럼만 선택
               missing_columns = set(self.feature_columns) - set(market_data.columns)
               if missing_columns:
                   print(f"⚠️ 누락된 컬럼: {missing_columns}")
                   # 누락된 컬럼은 0으로 채움
                   for col in missing_columns:
                       market_data[col] = 0
               
               feature_data = market_data[self.feature_columns].copy()
           else:
               # feature_columns 정보가 없으면 모든 숫자 컬럼 사용
               numeric_columns = market_data.select_dtypes(include=[np.number]).columns
               feature_data = market_data[numeric_columns].copy()
           
           # NaN 값 처리
           feature_data = feature_data.fillna(0)
           
           # 최신 sequence_length 개 데이터만 사용
           if len(feature_data) > self.sequence_length:
               feature_data = feature_data.iloc[-self.sequence_length:]
           
           # 정규화
           if self.scaler:
               feature_array = self.scaler.transform(feature_data)
           else:
               # 스케일러가 없으면 간단한 정규화
               feature_array = feature_data.values
               # 0으로 나누기 방지
               with np.errstate(divide='ignore', invalid='ignore'):
                   feature_array = (feature_array - np.mean(feature_array, axis=0)) / (np.std(feature_array, axis=0) + 1e-8)
                   feature_array = np.nan_to_num(feature_array, 0)
           
           # 3D 형태로 변환 (samples, timesteps, features)
           features = np.expand_dims(feature_array, axis=0)
           
           return features
           
       except Exception as e:
           print(f"❌ 특성 준비 실패: {e}")
           return None
   
   def _get_prediction_reason(self, market_data: pd.DataFrame, prediction: float) -> str:
       """예측 이유 생성 (디버깅 및 로깅용)"""
       try:
           latest = market_data.iloc[-1]
           reasons = []
           
           # 주요 지표 확인
           if 'rsi_14' in latest:
               rsi = latest['rsi_14']
               if rsi > 70:
                   reasons.append(f"RSI 과매수 ({rsi:.1f})")
               elif rsi < 30:
                   reasons.append(f"RSI 과매도 ({rsi:.1f})")
           
           if 'macd' in latest and 'macd_signal' in latest:
               macd_diff = latest['macd'] - latest['macd_signal']
               if abs(macd_diff) > 0.001:
                   reasons.append(f"MACD {'상승' if macd_diff > 0 else '하락'} 신호")
           
           if 'adx' in latest:
               adx = latest['adx']
               if adx > 40:
                   reasons.append(f"강한 추세 (ADX: {adx:.1f})")
               elif adx < 20:
                   reasons.append(f"약한 추세 (ADX: {adx:.1f})")
           
           if 'consecutive_up' in latest:
               consec_up = latest['consecutive_up']
               if consec_up > 5:
                   reasons.append(f"연속 {int(consec_up)}개 상승")
           
           if 'consecutive_down' in latest:
               consec_down = latest['consecutive_down']
               if consec_down > 5:
                   reasons.append(f"연속 {int(consec_down)}개 하락")
           
           # 예측 신뢰도 추가
           if prediction > 0.8:
               reasons.append(f"높은 확신도 ({prediction:.1%})")
           elif prediction < 0.2:
               reasons.append(f"낮은 허용 확률 ({prediction:.1%})")
           
           return " | ".join(reasons) if reasons else "일반적 시장 상황"
           
       except Exception as e:
           return f"이유 생성 실패: {e}"
   
   def _get_neutral_prediction(self) -> Dict:
       """중립 예측 반환 (모델이 없거나 오류 시)"""
       return {
           "signal": "NEUTRAL",
           "confidence": 0.5,
           "raw_prediction": 0.5,
           "model_name": self.model_name or "NO_MODEL",
           "model_accuracy": self.model_accuracy,
           "timestamp": datetime.now().isoformat(),
           "features_used": 0,
           "threshold": self.prediction_threshold,
           "reason": "AI 모델 비활성 또는 데이터 부족"
       }
   
   def update_threshold(self, new_threshold: float) -> bool:
       """예측 임계값 업데이트"""
       if 0.5 <= new_threshold <= 0.9:
           self.prediction_threshold = new_threshold
           print(f"✅ 예측 임계값 업데이트: {new_threshold:.1%}")
           return True
       else:
           print(f"❌ 잘못된 임계값: {new_threshold} (0.5~0.9 사이여야 함)")
           return False
   
   def get_model_info(self) -> Dict:
       """현재 모델 정보 반환"""
       return {
           "model_loaded": self.model is not None,
           "model_name": self.model_name,
           "model_accuracy": self.model_accuracy,
           "feature_count": len(self.feature_columns),
           "sequence_length": self.sequence_length,
           "prediction_threshold": self.prediction_threshold,
           "symbol": self.symbol
       }
   
   def validate_features(self, market_data: pd.DataFrame) -> Dict:
       """특성 검증 (디버깅용)"""
       result = {
           "total_columns": len(market_data.columns),
           "required_columns": len(self.feature_columns),
           "missing_columns": [],
           "data_rows": len(market_data),
           "required_rows": self.sequence_length,
           "has_nan": market_data.isnull().any().any(),
           "is_valid": False
       }
       
       if self.feature_columns:
           missing = set(self.feature_columns) - set(market_data.columns)
           result["missing_columns"] = list(missing)
       
       result["is_valid"] = (
           len(result["missing_columns"]) == 0 and
           result["data_rows"] >= result["required_rows"] and
           not result["has_nan"]
       )
       
       return result

# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
   print("🚀 AIPredictor 테스트 시작")
   
   # 예측기 생성
   predictor = AIPredictor("BTCUSDT")
   
   # 모델 정보 확인
   print("\n📋 모델 정보:")
   info = predictor.get_model_info()
   for key, value in info.items():
       print(f"   {key}: {value}")
   
   # 테스트용 더미 데이터 생성
   print("\n🧪 예측 테스트")
   
   # 실제로는 market_data를 받아와야 함
   import numpy as np
   
   # 더미 데이터 생성 (실제로는 DataCollector에서 받아옴)
   dummy_data = pd.DataFrame({
       'close': np.random.randn(100) * 1000 + 95000,
       'volume': np.random.randn(100) * 100 + 1000,
       'rsi_14': np.random.randn(100) * 20 + 50,
       'macd': np.random.randn(100) * 0.01,
       'macd_signal': np.random.randn(100) * 0.01,
       'adx': np.random.randn(100) * 10 + 25,
       'consecutive_up': np.random.randint(0, 10, 100),
       'consecutive_down': np.random.randint(0, 10, 100)
   })
   
   # 특성 검증
   validation = predictor.validate_features(dummy_data)
   print(f"   데이터 검증: {'✅ 유효' if validation['is_valid'] else '❌ 무효'}")
   
   # 예측 수행
   prediction = predictor.predict(dummy_data)
   print(f"\n📊 예측 결과:")
   print(f"   신호: {prediction['signal']}")
   print(f"   확신도: {prediction['confidence']:.1%}")
   print(f"   이유: {prediction['reason']}")
   
   print("\n✅ AIPredictor 테스트 완료")