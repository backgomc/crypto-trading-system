# 파일 경로: core/__init__.py
# 코드명: Core 모듈 초기화

"""
NHBot Core 모듈
주요 컴포넌트:
- ai: AI 클라이언트 (통합)
- exchanges: 거래소 연동 (향후 구현)
- trading_engine: 통합 매매 엔진 (향후 구현)
"""

# AI 통합 클라이언트
from .ai import AIClient

__version__ = "2.0.0"
__author__ = "NHBot Team"