# 파일 경로: mainpc/ai_server.py
# 코드명: 메인 PC AI Flask API 서버 (NAS와 통신용)

import os
import sys
import json
import threading
import time
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Optional, Callable

# 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

# AI 모듈 임포트
from nhbot_ai.data_collector import DataCollector
from nhbot_ai.model_trainer import ModelTrainer
from nhbot_ai.predictor import AIPredictor

# Flask 앱 생성
app = Flask(__name__)
CORS(app, origins=['http://192.168.0.*', 'http://localhost:*'])  # NAS에서 접근 허용

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ai_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 전역 인스턴스 관리
# ============================================================================

class AIServerManager:
    """AI 서버 매니저 (싱글톤)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.trainer = None
        self.predictor = None
        self.data_collector = DataCollector("BTCUSDT")
        self.training_thread = None
        self.training_status = {
            'status': 'idle',
            'start_time': None,
            'end_time': None,
            'current_epoch': 0,
            'total_epochs': 0,
            'accuracy': 0.0,
            'model_name': None,
            'error': None,
            'logs': []
        }
        
        # 모델 디렉토리 생성
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)
        
        # 로그 디렉토리 생성
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        self._initialized = True
        logger.info("✅ AI Server Manager 초기화 완료")
    
    def get_trainer(self, symbol: str = "BTCUSDT") -> ModelTrainer:
        """ModelTrainer 인스턴스 반환"""
        if self.trainer is None or self.trainer.symbol != symbol:
            self.trainer = ModelTrainer(symbol)
        return self.trainer
    
    def get_predictor(self, symbol: str = "BTCUSDT") -> AIPredictor:
        """AIPredictor 인스턴스 반환"""
        if self.predictor is None or self.predictor.symbol != symbol:
            self.predictor = AIPredictor(symbol)
        return self.predictor
    
    def update_training_status(self, updates: Dict):
        """학습 상태 업데이트"""
        self.training_status.update(updates)
        
        # 상태 파일 저장 (NAS에서 읽을 수 있도록)
        status_file = Path("training_status.json")
        with open(status_file, 'w') as f:
            json.dump(self.training_status, f, indent=2, default=str)
    
    def add_log(self, message: str, level: str = "INFO"):
        """로그 추가"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        
        self.training_status['logs'].append(log_entry)
        
        # 최대 100개 로그만 유지
        if len(self.training_status['logs']) > 100:
            self.training_status['logs'] = self.training_status['logs'][-100:]

# 싱글톤 인스턴스
ai_manager = AIServerManager()

# ============================================================================
# API 엔드포인트
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Server',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/train', methods=['POST'])
def start_training():
    """AI 모델 학습 시작"""
    try:
        data = request.get_json()
        
        # 이미 학습 중인지 확인
        if ai_manager.training_status['status'] == 'running':
            return jsonify({
                'success': False,
                'error': '이미 학습이 진행 중입니다',
                'status': ai_manager.training_status
            }), 400
        
        # 파라미터 추출
        selected_indicators = data.get('indicators', {})
        training_params = data.get('parameters', {})
        
        # 기본값 설정
        training_params.setdefault('symbol', 'BTCUSDT')
        training_params.setdefault('training_days', 365)
        training_params.setdefault('epochs', 100)
        training_params.setdefault('batch_size', 32)
        training_params.setdefault('learning_rate', 0.001)
        training_params.setdefault('sequence_length', 60)
        training_params.setdefault('validation_split', 20)
        training_params.setdefault('interval', '15')
        
        logger.info(f"🚀 학습 요청 받음: {training_params['epochs']} epochs")
        
        # 학습 스레드 시작
        def run_training():
            try:
                # 상태 초기화
                ai_manager.update_training_status({
                    'status': 'running',
                    'start_time': datetime.now().isoformat(),
                    'end_time': None,
                    'current_epoch': 0,
                    'total_epochs': training_params['epochs'],
                    'accuracy': 0.0,
                    'model_name': None,
                    'error': None,
                    'logs': []
                })
                
                ai_manager.add_log("학습 시작", "INFO")
                
                # ModelTrainer 인스턴스
                trainer = ai_manager.get_trainer(training_params['symbol'])
                
                # 진행률 콜백
                def progress_callback(message):
                    ai_manager.add_log(message, "INFO")
                    
                    # 에폭 정보 추출
                    if "에폭" in message:
                        try:
                            parts = message.split('/')
                            if len(parts) == 2:
                                current = int(parts[0].split()[-1])
                                ai_manager.update_training_status({
                                    'current_epoch': current
                                })
                        except:
                            pass
                
                # 학습 시작
                success = trainer.start_training(
                    selected_indicators,
                    training_params,
                    progress_callback
                )
                
                if not success:
                    raise Exception("학습 시작 실패")
                
                # 학습 완료 대기
                while trainer.is_training:
                    time.sleep(5)
                    
                    # 상태 업데이트
                    status = trainer.get_training_status()
                    ai_manager.update_training_status({
                        'current_epoch': status.get('current_epoch', 0),
                        'accuracy': status['metrics'].get('accuracy', 0) if status.get('metrics') else 0
                    })
                
                # 최종 결과
                final_status = trainer.get_training_status()
                
                if final_status['status'] == 'completed':
                    # 모델명 찾기
                    model_files = list(ai_manager.models_dir.glob("model_*.h5"))
                    if model_files:
                        latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
                        model_name = latest_model.stem
                    else:
                        model_name = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    ai_manager.update_training_status({
                        'status': 'completed',
                        'end_time': datetime.now().isoformat(),
                        'model_name': model_name,
                        'accuracy': final_status['metrics'].get('accuracy', 0)
                    })
                    
                    ai_manager.add_log(f"학습 완료! 정확도: {final_status['metrics'].get('accuracy', 0):.3f}", "SUCCESS")
                    logger.info(f"✅ 학습 완료: {model_name}")
                    
                else:
                    raise Exception(f"학습 실패: {final_status.get('status')}")
                    
            except Exception as e:
                logger.error(f"❌ 학습 중 오류: {e}")
                ai_manager.update_training_status({
                    'status': 'failed',
                    'end_time': datetime.now().isoformat(),
                    'error': str(e)
                })
                ai_manager.add_log(f"학습 실패: {str(e)}", "ERROR")
        
        # 백그라운드 스레드에서 실행
        ai_manager.training_thread = threading.Thread(target=run_training, daemon=True)
        ai_manager.training_thread.start()
        
        return jsonify({
            'success': True,
            'message': '학습이 시작되었습니다',
            'training_id': f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'parameters': training_params
        })
        
    except Exception as e:
        logger.error(f"학습 시작 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/train/stop', methods=['POST'])
def stop_training():
    """학습 중지"""
    try:
        trainer = ai_manager.trainer
        
        if trainer and trainer.is_training:
            success = trainer.stop_training()
            
            if success:
                ai_manager.update_training_status({
                    'status': 'stopped',
                    'end_time': datetime.now().isoformat()
                })
                ai_manager.add_log("학습이 사용자에 의해 중지됨", "WARNING")
                
                return jsonify({
                    'success': True,
                    'message': '학습이 중지되었습니다'
                })
        
        return jsonify({
            'success': False,
            'error': '진행 중인 학습이 없습니다'
        }), 400
        
    except Exception as e:
        logger.error(f"학습 중지 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/status', methods=['GET'])
def get_training_status():
    """학습 상태 조회"""
    try:
        # 진행률 계산
        status = ai_manager.training_status.copy()
        
        if status['total_epochs'] > 0:
            status['progress_percentage'] = (status['current_epoch'] / status['total_epochs']) * 100
        else:
            status['progress_percentage'] = 0
        
        # 경과 시간 계산
        if status['start_time'] and status['status'] == 'running':
            start_time = datetime.fromisoformat(status['start_time'])
            elapsed = datetime.now() - start_time
            status['elapsed_seconds'] = int(elapsed.total_seconds())
            status['elapsed_formatted'] = str(elapsed).split('.')[0]
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"상태 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/predict', methods=['POST'])
def predict():
    """예측 수행"""
    try:
        data = request.get_json()
        
        # 시장 데이터 추출
        market_data = data.get('market_data')
        if not market_data:
            # 최신 데이터 수집
            df = ai_manager.data_collector.get_latest_data(interval="15", limit=100)
            if df is None:
                return jsonify({
                    'success': False,
                    'error': '시장 데이터를 수집할 수 없습니다'
                }), 400
        else:
            # 전달받은 데이터 사용
            import pandas as pd
            df = pd.DataFrame(market_data)
        
        # 예측기 인스턴스
        predictor = ai_manager.get_predictor()
        
        # 예측 수행
        prediction_result = predictor.predict(df)
        
        return jsonify({
            'success': True,
            'prediction': prediction_result
        })
        
    except Exception as e:
        logger.error(f"예측 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/models', methods=['GET'])
def get_models():
    """모델 목록 조회"""
    try:
        model_files = list(ai_manager.models_dir.glob("model_*.h5"))
        models = []
        
        for model_file in model_files:
            model_name = model_file.stem
            info_file = ai_manager.models_dir / f"{model_name}_info.json"
            
            if info_file.exists():
                with open(info_file, 'r') as f:
                    info = json.load(f)
            else:
                info = {}
            
            models.append({
                'name': model_name,
                'created_at': info.get('created_at', model_file.stat().st_mtime),
                'accuracy': info.get('accuracy', 0),
                'size_mb': round(model_file.stat().st_size / 1024 / 1024, 2)
            })
        
        # 최신순 정렬
        models.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'models': models,
            'count': len(models)
        })
        
    except Exception as e:
        logger.error(f"모델 목록 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/models/<model_name>', methods=['GET'])
def get_model_info(model_name):
    """특정 모델 정보 조회"""
    try:
        model_file = ai_manager.models_dir / f"{model_name}.h5"
        
        if not model_file.exists():
            return jsonify({
                'success': False,
                'error': '모델을 찾을 수 없습니다'
            }), 404
        
        info_file = ai_manager.models_dir / f"{model_name}_info.json"
        
        if info_file.exists():
            with open(info_file, 'r') as f:
                info = json.load(f)
        else:
            info = {'name': model_name}
        
        # 파일 크기 추가
        info['size_mb'] = round(model_file.stat().st_size / 1024 / 1024, 2)
        
        # 스케일러 파일 확인
        scaler_file = ai_manager.models_dir / f"{model_name}_scaler.pkl"
        info['has_scaler'] = scaler_file.exists()
        
        return jsonify({
            'success': True,
            'model': info
        })
        
    except Exception as e:
        logger.error(f"모델 정보 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """학습 로그 조회"""
    try:
        # 쿼리 파라미터
        lines = request.args.get('lines', 50, type=int)
        
        # 메모리 로그
        memory_logs = ai_manager.training_status.get('logs', [])
        
        # 파일 로그 (옵션)
        log_file = Path("logs/training.log")
        file_logs = []
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                file_logs = f.readlines()[-lines:]
        
        return jsonify({
            'success': True,
            'memory_logs': memory_logs[-lines:],
            'file_logs': file_logs
        })
        
    except Exception as e:
        logger.error(f"로그 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/system/info', methods=['GET'])
def get_system_info():
    """시스템 정보"""
    try:
        import tensorflow as tf
        
        # GPU 정보
        gpus = tf.config.list_physical_devices('GPU')
        gpu_info = {
            'available': len(gpus) > 0,
            'count': len(gpus),
            'devices': [gpu.name for gpu in gpus]
        }
        
        # 디스크 사용량
        models_size = sum(f.stat().st_size for f in ai_manager.models_dir.glob("*")) if ai_manager.models_dir.exists() else 0
        
        system_info = {
            'gpu': gpu_info,
            'tensorflow_version': tf.__version__,
            'models_directory': str(ai_manager.models_dir),
            'models_count': len(list(ai_manager.models_dir.glob("model_*.h5"))),
            'storage_mb': round(models_size / 1024 / 1024, 2),
            'server_time': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'system': system_info
        })
        
    except Exception as e:
        logger.error(f"시스템 정보 조회 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# 에러 핸들러
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': '엔드포인트를 찾을 수 없습니다'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': '서버 내부 오류가 발생했습니다'
    }), 500

# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == '__main__':
    print("="*60)
    print("🚀 NHBot AI Server 시작")
    print("="*60)
    print(f"📁 모델 디렉토리: {ai_manager.models_dir}")
    print(f"📝 로그 디렉토리: {ai_manager.logs_dir}")
    
    # TensorFlow GPU 확인
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        print(f"🎮 GPU 감지됨: {len(gpus)}개")
        for gpu in gpus:
            print(f"   - {gpu.name}")
    else:
        print("💻 CPU 모드로 실행됩니다")
    
    print("="*60)
    print("📡 API 엔드포인트:")
    print("   POST /train         - 학습 시작")
    print("   POST /train/stop    - 학습 중지")
    print("   GET  /status        - 학습 상태")
    print("   POST /predict       - 예측 수행")
    print("   GET  /models        - 모델 목록")
    print("   GET  /system/info   - 시스템 정보")
    print("="*60)
    
    # Flask 서버 실행
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)