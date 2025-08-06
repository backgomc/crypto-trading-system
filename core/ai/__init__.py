# 파일 경로: core/ai/__init__.py
# 코드명: AI 모듈 초기화 (NAS용 - 관리 전용)

"""
NHBot AI 모듈 - NAS 버전
주요 기능:
- AI 모델 파일 관리
- 메인 PC 원격 학습 제어
"""

from .model_manager import ModelManager
# from .predictor import Predictor  # 🔴 주석 처리 (TensorFlow 필요해서)

__version__ = "2.0.0"
__all__ = ['ModelManager']  # Predictor 제거

# NAS 역할: 관리만
# 실제 학습 및 추론: 메인 PC에서 수행