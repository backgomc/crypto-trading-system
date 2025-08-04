# 파일 경로: web/routes/__init__.py  
# 코드명: 라우터 통합 및 Blueprint 등록 (AI API 추가)

from flask import Blueprint
from .auth import auth_bp
from .pages import pages_bp
from .api import api_bp
from .admin_api import admin_api_bp
from .ai_api import ai_api_bp  # 🆕 AI API 추가

# 메인 웹 Blueprint 생성
web_bp = Blueprint('web', __name__)

def register_routes(app):
    """Flask 앱에 모든 라우터 등록"""
    
    # 인증 라우터 등록 (우선순위 높음)
    app.register_blueprint(auth_bp, url_prefix='')
    
    # 페이지 라우터 등록
    app.register_blueprint(pages_bp, url_prefix='')
    
    # API 라우터 등록
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # AI API 라우터 등록 🆕 추가
    app.register_blueprint(ai_api_bp, url_prefix='/api/ai')
    
    # 관리자 API 라우터 등록
    app.register_blueprint(admin_api_bp, url_prefix='')
    
    print("✅ 모든 라우터가 등록되었습니다:")
    print("   🔐 인증 라우터: /login, /logout")
    print("   📄 페이지 라우터: /, /settings, /ai-model, /admin")
    print("   🌐 API 라우터: /api/*")
    print("   🧠 AI API 라우터: /api/ai/*")  # 🆕 추가
    print("   👨‍💼 관리자 API: /api/admin/*")

# 하위 호환성을 위한 기본 export
__all__ = ['web_bp', 'register_routes']