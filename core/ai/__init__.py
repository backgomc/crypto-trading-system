# 파일 경로: core/ai/__init__.py
# 코드명: AI 모듈 초기화

"""
NHBot AI 모델 관리 모듈

주요 기능:
- 시장 데이터 수집 및 전처리
- AI 모델 학습 및 관리
- 실시간 예측 및 신호 생성
"""

from .model_manager import ModelManager
from .data_collector import DataCollector
from .model_trainer import ModelTrainer
from .predictor import Predictor

__version__ = "1.0.0"
__all__ = ['ModelManager', 'DataCollector', 'ModelTrainer', 'Predictor']