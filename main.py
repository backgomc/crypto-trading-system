# 파일 경로: main.py
# 코드명: Flask 메인 애플리케이션 (분리된 라우터 구조 적용)

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

    # HTTPS 리버스 프록시 환경에서 HTTPS 인식 강제
    from flask import request
    @app.before_request
    def fix_https_proxy():
        if request.headers.get('X-Forwarded-Proto', 'http') == 'https':
            request.environ['wsgi.url_scheme'] = 'https'

    # HTTPS URL 스킴 고정 (리디렉션 시 http로 안 가도록)
    app.config['PREFERRED_URL_SCHEME'] = 'https'    
    
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
    
    # 🆕 분리된 라우터 등록
    from web.routes import register_routes
    register_routes(app)

    # ✅ 세션 유효성 검사 미들웨어 수정
    @app.before_request
    def check_session_validity():
        """모든 요청 전에 세션 유효성 검사"""
        from flask import request, session, redirect, url_for
        from config.models import UserSession
        
        # 제외할 경로들 (✅ /api/ 경로 추가)
        excluded_paths = ['/login', '/logout', '/static/', '/health', '/api/check-session']
        excluded_endpoints = ['auth.login', 'auth.logout', 'static', 'health_check', 'api.check_existing_session']
        
        # 제외 경로 체크
        if (request.endpoint in excluded_endpoints or 
            any(request.path.startswith(path) for path in excluded_paths)):
            return
        
        # 로그인된 사용자만 검사
        if session.get('logged_in'):
            session_id = session.get('session_id')

            # ✅ 관리자는 세션 검증 완화
            if session.get('is_admin'):
                # 관리자는 DB 세션이 없어도 허용 (단, 활동 시간은 업데이트)
                if session_id:
                    UserSession.update_activity(session_id)
                return
            
            # 추가: 사용자의 계정 활성화 상태 확인
            user = User.query.get(session.get('user_id'))
            if user and not user.is_active:
                # 계정이 비활성화된 경우
                session.clear()
                
                # AJAX 요청인지 확인
                if request.headers.get('Content-Type') == 'application/json':
                    # JSON 응답으로 401 에러 반환
                    from flask import jsonify
                    return jsonify({
                        'success': False,
                        'error': '계정이 비활성화되었습니다',
                        'code': 'ACCOUNT_DISABLED'
                    }), 401
                else:
                    # 일반 요청은 로그인 페이지로 리다이렉트
                    return redirect(url_for('auth.login', popup='account_disabled'))
                        
            if session_id:
                # DB에서 세션 확인
                db_session = UserSession.get_active_session(session_id)
                if not db_session:
                    # ✅ 세션이 무효하면 클리어하고 리다이렉트
                    session.clear()
                    
                    # AJAX 요청인지 확인
                    if request.headers.get('Content-Type') == 'application/json':
                        # JSON 응답으로 401 에러 반환
                        from flask import jsonify
                        return jsonify({
                            'success': False,
                            'error': '세션이 만료되었습니다',
                            'code': 'SESSION_EXPIRED'
                        }), 401
                    else:
                        # 일반 요청은 로그인 페이지로 리다이렉트
                        return redirect(url_for('auth.login', popup='session_expired'))
                else:
                    # 세션 활동 시간 업데이트
                    UserSession.update_activity(session_id)
            else:
                # session_id가 없으면 로그아웃
                session.clear()
                return redirect(url_for('auth.login', popup='session_invalid'))
    
    # 애플리케이션 컨텍스트에서 DB 초기화
    with app.app_context():
        try:
            # 테이블 생성
            db.create_all()
            print("✅ 데이터베이스 테이블 생성 완료")

            # ✅ 여기에 추가: last_active 컬럼 추가
            try:
                db.engine.execute("ALTER TABLE users ADD COLUMN last_active DATETIME")
                print("✅ last_active 컬럼 추가 완료")
            except Exception as alter_error:
                # 이미 컬럼이 존재하는 경우 무시
                if "duplicate column name" not in str(alter_error).lower():
                    print(f"⚠️ 컬럼 추가 실패 (무시 가능): {alter_error}")            
            
            # 환경변수에서 관리자 계정 정보 가져오기
            admin_username = os.getenv('ADMIN_USERNAME', 'admin')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123!')
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@localhost')
            
            # 기본 admin 사용자 생성 (없을 경우)
            admin_user = User.query.filter_by(username=admin_username).first()
            if not admin_user:
                admin_user = User(
                    username=admin_username,
                    email=admin_email,
                    is_admin=True,
                    is_active=True
                )
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                
                # 시스템 로그 생성
                system_log = SystemLog(
                    level='INFO',
                    category='SYSTEM',
                    message=f'관리자 계정 생성됨: {admin_username}',
                    ip_address='127.0.0.1',
                    user_agent='System'
                )
                db.session.add(system_log)
                
                db.session.commit()
                print("✅ 관리자 계정 생성 완료")
                print("📝 .env 파일에서 ADMIN_USERNAME, ADMIN_PASSWORD 설정 가능")
            else:
                print("ℹ️ 관리자 계정이 이미 존재합니다")
                
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
        # print("🚀 자동매매 시스템 백그라운드 시작!")
        
    except Exception as e:
        print(f"❌ 자동매매 시스템 시작 실패: {e}")

def main():
    """메인 실행 함수"""
    print("="*60)
    print("🚀 암호화폐 자동매매 시스템 시작")
    print("="*60)
    print("📋 현재 모드: 웹 인터페이스 + 로그인 시스템")
    print("🔐 보안: 세션 기반 인증 활성화")
    print("🔧 라우터: 기능별 분리 구조")
    print("="*60)
    
    # 자동매매 시스템 백그라운드 시작 (나중에 구현)
    start_trading_system()
    
    # Flask 웹서버 시작
    app = create_app()
    
    print("🌐 웹서버 접속 정보:")
    print("   로컬: http://127.0.0.1:8888")
    print("   네트워크: http://14.47.172.143:5000")
    print("📝 로그인 계정: .env 파일에서 설정 가능")
    print("="*60)
    
    app.run(host='0.0.0.0', port=8888, debug=True, threaded=True)

if __name__ == "__main__":
    main()