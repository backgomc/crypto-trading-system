# 파일 경로: core/ai/predictor.py
# 코드명: AI 모델 추론 클래스 (NAS 전용)

import numpy as np
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from .model_manager import ModelManager

class Predictor:
    """AI 모델 추론 클래스 (NAS에서 실행)"""
    
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.model_manager = ModelManager()
        
        # 모델 관련
        self.current_model = None
        self.scaler = None
        self.model_info = None
        
        # 상태 관리
        self.is_ready = False
        self.last_prediction = None
        self.prediction_history = []
        
        print(f"✅ Predictor 초기화 완료: {symbol}")
        
        # 활성 모델 자동 로드
        self._load_active_model()
    
    def _load_active_model(self) -> bool:
        """활성 모델 로드"""
        try:
            active_model_name = self.model_manager.get_active_model()
            if not active_model_name:
                print("⚠️ 활성 모델이 없습니다. 메인 PC에서 학습을 먼저 수행하세요.")
                return False
            
            return self.load_model(active_model_name)
            
        except Exception as e:
            print(f"❌ 활성 모델 로드 실패: {e}")
            return False
    
    def load_model(self, model_name: str) -> bool:
        """특정 모델 로드"""
        try:
            # 모델 정보 조회
            self.model_info = self.model_manager.get_model_info(model_name)
            if not self.model_info:
                print(f"❌ 모델을 찾을 수 없습니다: {model_name}")
                return False
            
            # 모델 파일 경로
            model_path = Path(self.model_info['model_path'])
            scaler_path = Path(self.model_info['scaler_path'])
            
            # 파일 존재 확인
            if not model_path.exists():
                print(f"❌ 모델 파일이 없습니다: {model_path}")
                return False
            
            if not scaler_path.exists():
                print(f"❌ 스케일러 파일이 없습니다: {scaler_path}")
                return False
            
            # TODO: 메인 PC에서 학습이 완료되면 여기서 실제 모델 로드
            # import tensorflow as tf
            # self.current_model = tf.keras.models.load_model(model_path)
            
            # 스케일러 로드
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            
            self.is_ready = True
            print(f"✅ 모델 로드 완료: {model_name}")
            print(f"   정확도: {self.model_info.get('accuracy', 0):.3f}")
            print(f"   학습일: {self.model_info.get('created_at', 'Unknown')}")
            
            return True
            
        except Exception as e:
            print(f"❌ 모델 로드 실패: {e}")
            self.is_ready = False
            return False
    
    def predict(self, market_data: Dict) -> Dict:
        """시장 데이터를 받아 매매 신호 예측"""
        if not self.is_ready:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': '모델이 로드되지 않았습니다',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # TODO: 실제 모델이 있을 때 예측 수행
            # features = self._prepare_features(market_data)
            # prediction = self.current_model.predict(features)
            
            # 임시: 더미 예측 (메인 PC 학습 완료 전까지)
            prediction_result = {
                'signal': 'HOLD',  # BUY, SELL, HOLD
                'confidence': 0.5,  # 0.0 ~ 1.0
                'reason': '모델 학습 대기 중 (임시 HOLD)',
                'timestamp': datetime.now().isoformat(),
                'model_name': self.model_info['name'] if self.model_info else 'None',
                'model_accuracy': self.model_info.get('accuracy', 0) if self.model_info else 0
            }
            
            # 예측 이력 저장
            self.last_prediction = prediction_result
            self.prediction_history.append(prediction_result)
            
            # 이력이 너무 길면 제한
            if len(self.prediction_history) > 100:
                self.prediction_history = self.prediction_history[-100:]
            
            return prediction_result
            
        except Exception as e:
            print(f"❌ 예측 수행 실패: {e}")
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reason': f'예측 오류: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def _prepare_features(self, market_data: Dict) -> np.ndarray:
        """시장 데이터를 모델 입력 형태로 변환"""
        try:
            # TODO: 실제 특성 준비 로직
            # 현재는 더미 데이터 반환
            
            if not self.model_info:
                return np.array([])
            
            # 모델 학습 시 사용된 특성 컬럼 정보
            feature_columns = self.model_info.get('feature_columns', [])
            data_shape = self.model_info.get('data_shape', (1, 60, 37))
            
            # 임시: 더미 특성 데이터
            dummy_features = np.random.random(data_shape[1:])
            
            return dummy_features.reshape(1, *data_shape[1:])
            
        except Exception as e:
            print(f"❌ 특성 준비 실패: {e}")
            return np.array([])
    
    def get_model_status(self) -> Dict:
        """현재 모델 상태 조회"""
        return {
            'is_ready': self.is_ready,
            'model_info': self.model_info,
            'last_prediction': self.last_prediction,
            'prediction_count': len(self.prediction_history),
            'scaler_loaded': self.scaler is not None,
            'current_model_loaded': self.current_model is not None
        }
    
    def get_prediction_history(self, limit: int = 20) -> List[Dict]:
        """최근 예측 이력 조회"""
        return self.prediction_history[-limit:] if self.prediction_history else []
    
    def refresh_model(self) -> bool:
        """활성 모델 새로고침 (새 모델이 학습되었을 때)"""
        try:
            print("🔄 모델 새로고침 중...")
            return self._load_active_model()
        except Exception as e:
            print(f"❌ 모델 새로고침 실패: {e}")
            return False
    
    def get_signal_summary(self) -> Dict:
        """최근 신호 요약"""
        if not self.prediction_history:
            return {'buy': 0, 'sell': 0, 'hold': 0, 'total': 0}
        
        # 최근 50개 예측 분석
        recent_predictions = self.prediction_history[-50:]
        
        signal_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        for pred in recent_predictions:
            signal = pred.get('signal', 'HOLD')
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        
        total = len(recent_predictions)
        
        return {
            'buy': signal_counts['BUY'],
            'sell': signal_counts['SELL'], 
            'hold': signal_counts['HOLD'],
            'total': total,
            'buy_ratio': signal_counts['BUY'] / total if total > 0 else 0,
            'sell_ratio': signal_counts['SELL'] / total if total > 0 else 0,
            'hold_ratio': signal_counts['HOLD'] / total if total > 0 else 0
        }

# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
    print("🚀 Predictor 테스트 시작")
    
    # 예측기 생성
    predictor = Predictor("BTCUSDT")
    
    # 모델 상태 확인
    status = predictor.get_model_status()
    print(f"📊 모델 상태: {status}")
    
    # 더미 시장 데이터로 예측 테스트
    market_data = {
        'price': 95000,
        'volume': 1000000,
        'rsi': 55,
        'macd': 0.1
    }
    
    prediction = predictor.predict(market_data)
    print(f"🎯 예측 결과: {prediction}")
    
    # 신호 요약
    summary = predictor.get_signal_summary()
    print(f"📈 신호 요약: {summary}")
    
    print("✅ Predictor 테스트 완료")