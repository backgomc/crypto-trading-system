# 파일 경로: main.py
# 코드명: Flask 메인 애플리케이션 및 로그인 시스템 통합

import threading
import time
import os
from flask import Flask, session
from datetime import timedelta
from config.settings import load_trading_config, SECRET_KEY
from config.models import db, User, SystemLog

def create_app():
    """Flask 앱 생성"""
    # 현재 디렉토리 기준으로 templates 폴더 지정
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    
    # 기본 설정
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
    
    # SQLite 데이터베이스 설정
    basedir = os.path.abspath(os.path.dirname(__file__))
    data_dir = os.path.join(basedir, 'data')
    
    # data 디렉토리가 없으면 생성
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(data_dir, "trading_system.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True
    }
    
    # 데이터베이스 초기화
    db.init_app(app)
    
    # API 블루프린트 등록 (나중에 구현)
    # from api.trading_api import trading_bp
    # from api.control_api import control_bp
    # app.register_blueprint(trading_bp, url_prefix='/api/trading')
    # app.register_blueprint(control_bp, url_prefix='/api/control')
    
    # 웹 페이지 블루프린트 등록
    from web.routes import web_bp
    app.register_blueprint(web_bp)
    
    # 애플리케이션 컨텍스트에서 DB 초기화
    with app.app_context():
        try:
            # 테이블 생성
            db.create_all()
            print("✅ 데이터베이스 테이블 생성 완료")
            
            # 기본 admin 사용자 생성 (없을 경우)
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@localhost',
                    is_admin=True,
                    is_active=True
                )
                admin_user.set_password('admin123')  # 기본 비밀번호
                db.session.add(admin_user)
                
                # 시스템 로그 생성
                system_log = SystemLog(
                    level='INFO',
                    category='SYSTEM',
                    message='기본 admin 계정 생성됨',
                    ip_address='127.0.0.1',
                    user_agent='System'
                )
                db.session.add(system_log)
                
                db.session.commit()
                print("✅ 기본 admin 계정 생성 완료")
                print("📝 로그인 정보: admin / admin123")
            else:
                print("ℹ️ admin 계정이 이미 존재합니다")
                
        except Exception as e:
            print(f"❌ 데이터베이스 초기화 오류: {e}")
            db.session.rollback()
    
    # 세션 설정
    @app.before_request
    def before_request():
        """요청 전 세션 설정"""
        session.permanent = True
    
    # 컨텍스트 프로세서 (템플릿에서 사용할 변수들)
    @app.context_processor
    def inject_template_vars():
        """템플릿에서 사용할 전역 변수 주입"""
        return {
            'app_name': '자동매매 시스템',
            'app_version': 'v2.0',
            'current_user': {
                'username': session.get('username'),
                'is_admin': session.get('is_admin', False),
                'logged_in': session.get('logged_in', False)
            }
        }
    
    return app

def start_trading_system():
    """자동매매 시스템 시작 (나중에 구현)"""
    try:
        # TODO: 나중에 구현
        # from core.trader import AutoTrader
        
        # 설정 로드
        config = load_trading_config()
        if not config:
            print("❌ 설정 파일 로드 실패")
            return
        
        print("⚠️ 자동매매 시스템은 아직 구현되지 않았습니다.")
        print("🔧 현재는 웹 인터페이스만 동작합니다.")
        
        # TODO: 자동매매 인스턴스 생성 및 실행
        # trader = AutoTrader(config)
        # trading_thread = threading.Thread(target=trader.run, daemon=True)
        # trading_thread.start()
        # print("🚀 자동매매 시스템 백그라운드 시작")
        
    except Exception as e:
        print(f"❌ 자동매매 시스템 시작 실패: {e}")

def main():
    """메인 실행 함수"""
    print("="*60)
    print("🚀 암호화폐 자동매매 시스템 시작")
    print("="*60)
    print("📋 현재 모드: 웹 인터페이스 + 로그인 시스템")
    print("🔐 보안: 세션 기반 인증 활성화")
    print("="*60)
    
    # 자동매매 시스템 백그라운드 시작 (나중에 구현)
    start_trading_system()
    
    # Flask 웹서버 시작
    app = create_app()
    
    print("🌐 웹서버 접속 정보:")
    print("   로컬: http://127.0.0.1:8888")
    print("   네트워크: http://14.47.172.143:5000")
    print("📝 기본 로그인:")
    print("   사용자명: admin")
    print("   비밀번호: admin123")
    print("="*60)
    
    app.run(host='0.0.0.0', port=8888, debug=True, threaded=True)

if __name__ == "__main__":
    main()