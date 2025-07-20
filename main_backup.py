import threading
import time
from flask import Flask
from config.settings import load_trading_config, SECRET_KEY

def create_app():
    """Flask 앱 생성"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    
    # API 블루프린트 등록
    from api.trading_api import trading_bp
    from api.control_api import control_bp
    
    # 웹 페이지 블루프린트 등록  
    from web.routes import web_bp
    
    app.register_blueprint(trading_bp, url_prefix='/api/trading')
    app.register_blueprint(control_bp, url_prefix='/api/control')
    app.register_blueprint(web_bp)
    
    return app

def start_trading_system():
    """자동매매 시스템 시작"""
    try:
        from core.trader import AutoTrader
        
        # 설정 로드
        config = load_trading_config()
        if not config:
            print("❌ 설정 파일 로드 실패")
            return
        
        # 자동매매 인스턴스 생성
        trader = AutoTrader(config)
        
        # 백그라운드에서 자동매매 실행
        trading_thread = threading.Thread(target=trader.run, daemon=True)
        trading_thread.start()
        
        print("🚀 자동매매 시스템 백그라운드 시작")
        
    except Exception as e:
        print(f"❌ 자동매매 시스템 시작 실패: {e}")

def main():
    """메인 실행 함수"""
    print("🚀 암호화폐 자동매매 시스템 시작")
    
    # 자동매매 시스템 백그라운드 시작
    start_trading_system()
    
    # Flask 웹서버 시작
    app = create_app()
    
    print("🌐 웹서버 시작: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == "__main__":
    main()
