# 파일 경로: web/routes/__init__.py
# 코드명: 라우터 통합 및 Blueprint 등록

from flask import Blueprint

# 메인 웹 Blueprint 생성
web_bp = Blueprint('web', __name__)

def register_routes(app):
    """Flask 앱에 모든 라우터 등록"""

    # 필요한 시점에만 임포트해서 순환참조 방지
    from .auth import auth_bp
    from .pages import pages_bp
    from .api import api_bp    
    
    # 인증 라우터 등록 (우선순위 높음)
    app.register_blueprint(auth_bp, url_prefix='')
    
    # 페이지 라우터 등록
    app.register_blueprint(pages_bp, url_prefix='')
    
    # API 라우터 등록
    app.register_blueprint(api_bp, url_prefix='/api')
    
    print("✅ 모든 라우터가 등록되었습니다:")
    print("   🔐 인증 라우터: /login, /logout")
    print("   📄 페이지 라우터: /, /settings, /ai-model")
    print("   🌐 API 라우터: /api/*")

# 하위 호환성을 위한 기본 export
__all__ = ['web_bp', 'register_routes']