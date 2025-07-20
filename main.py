import threading
import time
from flask import Flask
from config.settings import SECRET_KEY

def create_app():
    """Flask 앱 생성"""
    import os
    
    # 현재 디렉토리 기준으로 templates 폴더 지정
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    app.config['SECRET_KEY'] = SECRET_KEY
    
    # 웹 페이지 등록
    from web.routes import web_bp
    app.register_blueprint(web_bp)
    
    return app

def main():
    """메인 실행 함수"""
    print("🚀 암호화폐 자동매매 시스템 시작")
    print("⚠️  임시 모드: 웹페이지만 실행")
    
    # Flask 웹서버 시작
    app = create_app()
    
    print("🌐 웹서버 시작: http://localhost:5000")
    app.run(host='0.0.0.0', port=8888, debug=False)

if __name__ == "__main__":
    main()
