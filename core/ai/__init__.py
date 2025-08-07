# 파일 경로: core/ai/__init__.py
# 코드명: AI 모듈 초기화 (통합 클라이언트 사용)

"""
NHBot AI 모듈 - NAS 버전
주요 기능:
- 메인 PC와 API 통신
- 학습 제어, 예측, 모델 관리 통합
"""

from .ai_client import AIClient

__version__ = "3.0.0"  # 통합 버전
__all__ = ['AIClient']

# 이전 모듈들은 AIClient로 통합됨:
# - RemoteTrainer → AIClient.start_training()
# - PredictorClient → AIClient.predict()  
# - ModelManager → AIClient.get_model_list()