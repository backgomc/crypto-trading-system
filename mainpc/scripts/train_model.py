# 파일 경로: mainpc/scripts/train_model.py
# 코드명: 메인 PC Docker 컨테이너용 학습 실행 스크립트

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 상위 디렉토리 모듈 import 가능하도록 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from nhbot_ai.data_collector import DataCollector
from nhbot_ai.model_trainer import ModelTrainer

# 로깅 설정
logging.basicConfig(
   level=logging.INFO,
   format='%(asctime)s - %(levelname)s - %(message)s',
   handlers=[
       logging.FileHandler('/app/logs/training.log'),
       logging.StreamHandler()
   ]
)
logger = logging.getLogger(__name__)

class TrainingExecutor:
   """Docker 컨테이너에서 실행될 학습 실행기"""
   
   def __init__(self):
       self.status_file = Path('/app/training_status.json')
       self.models_dir = Path('/app/models')
       self.models_dir.mkdir(exist_ok=True)
       
       # 학습 상태
       self.training_status = {
           'status': 'idle',
           'start_time': None,
           'end_time': None,
           'current_epoch': 0,
           'total_epochs': 0,
           'accuracy': 0.0,
           'model_name': None,
           'error': None
       }
       
       self._update_status()
   
   def _update_status(self):
       """상태 파일 업데이트"""
       try:
           with open(self.status_file, 'w') as f:
               json.dump(self.training_status, f, indent=2)
       except Exception as e:
           logger.error(f"상태 파일 업데이트 실패: {e}")
   
   def parse_arguments(self):
       """커맨드라인 인자 파싱"""
       parser = argparse.ArgumentParser(description='NHBot AI 모델 학습')
       
       # 기본 파라미터
       parser.add_argument('--symbol', type=str, default='BTCUSDT',
                         help='거래 심볼 (기본: BTCUSDT)')
       parser.add_argument('--training-days', type=int, default=365,
                         help='학습 데이터 기간 (일)')
       parser.add_argument('--interval', type=str, default='15',
                         help='캔들 간격 (1, 5, 15, 60)')
       
       # 학습 파라미터
       parser.add_argument('--epochs', type=int, default=100,
                         help='학습 에폭 수')
       parser.add_argument('--batch-size', type=int, default=32,
                         help='배치 크기')
       parser.add_argument('--learning-rate', type=float, default=0.001,
                         help='학습률')
       parser.add_argument('--sequence-length', type=int, default=60,
                         help='시퀀스 길이')
       parser.add_argument('--validation-split', type=int, default=20,
                         help='검증 데이터 비율 (%)')
       
       # 지표 선택 (JSON 문자열로 받기)
       parser.add_argument('--indicators', type=str, default='{}',
                         help='선택된 지표 (JSON 형식)')
       
       # 실행 모드
       parser.add_argument('--mode', type=str, default='train',
                         choices=['train', 'test', 'info'],
                         help='실행 모드')
       
       return parser.parse_args()
   
   def train(self, args):
       """학습 실행"""
       try:
           logger.info("="*60)
           logger.info("🚀 NHBot AI 모델 학습 시작")
           logger.info("="*60)
           
           # 상태 업데이트
           self.training_status = {
               'status': 'running',
               'start_time': datetime.now().isoformat(),
               'end_time': None,
               'current_epoch': 0,
               'total_epochs': args.epochs,
               'accuracy': 0.0,
               'model_name': None,
               'error': None,
               'parameters': {
                   'symbol': args.symbol,
                   'training_days': args.training_days,
                   'interval': args.interval,
                   'epochs': args.epochs,
                   'batch_size': args.batch_size,
                   'learning_rate': args.learning_rate,
                   'sequence_length': args.sequence_length,
                   'validation_split': args.validation_split
               }
           }
           self._update_status()
           
           # 지표 파싱
           try:
               selected_indicators = json.loads(args.indicators) if args.indicators else {}
           except:
               selected_indicators = {}
           
           logger.info(f"📊 설정:")
           logger.info(f"   심볼: {args.symbol}")
           logger.info(f"   학습 기간: {args.training_days}일")
           logger.info(f"   에폭: {args.epochs}")
           logger.info(f"   배치 크기: {args.batch_size}")
           logger.info(f"   학습률: {args.learning_rate}")
           logger.info(f"   선택된 지표: {len(selected_indicators)}개")
           
           # ModelTrainer 인스턴스 생성
           trainer = ModelTrainer(args.symbol)
           
           # 학습 파라미터 준비
           training_params = {
               'training_days': args.training_days,
               'interval': args.interval,
               'epochs': args.epochs,
               'batch_size': args.batch_size,
               'learning_rate': args.learning_rate,
               'sequence_length': args.sequence_length,
               'validation_split': args.validation_split
           }
           
           # 진행률 콜백
           def progress_callback(message):
               logger.info(f"📢 {message}")
               # 에폭 정보 추출 시도
               if "에폭" in message:
                   try:
                       parts = message.split('/')
                       if len(parts) == 2:
                           current = int(parts[0].split()[-1])
                           self.training_status['current_epoch'] = current
                           self._update_status()
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
           logger.info("⏳ 학습 진행 중...")
           while trainer.is_training:
               import time
               time.sleep(5)
               
               # 상태 업데이트
               status = trainer.get_training_status()
               self.training_status['current_epoch'] = status.get('current_epoch', 0)
               
               if status.get('metrics'):
                   self.training_status['accuracy'] = status['metrics'].get('accuracy', 0)
               
               self._update_status()
           
           # 최종 결과
           final_status = trainer.get_training_status()
           
           if final_status['status'] == 'completed':
               # 모델명 찾기 (가장 최근 생성된 모델)
               model_files = list(self.models_dir.glob("model_*.h5"))
               if model_files:
                   latest_model = max(model_files, key=lambda x: x.stat().st_mtime)
                   model_name = latest_model.stem
               else:
                   model_name = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
               
               self.training_status = {
                   'status': 'completed',
                   'start_time': self.training_status['start_time'],
                   'end_time': datetime.now().isoformat(),
                   'current_epoch': final_status.get('current_epoch', args.epochs),
                   'total_epochs': args.epochs,
                   'accuracy': final_status['metrics'].get('accuracy', 0),
                   'model_name': model_name,
                   'error': None,
                   'parameters': self.training_status['parameters']
               }
               
               logger.info("="*60)
               logger.info(f"✅ 학습 완료!")
               logger.info(f"   모델명: {model_name}")
               logger.info(f"   정확도: {self.training_status['accuracy']:.3f}")
               logger.info("="*60)
               
           else:
               raise Exception(f"학습 실패: {final_status.get('status')}")
           
       except Exception as e:
           logger.error(f"❌ 학습 중 오류 발생: {e}")
           self.training_status['status'] = 'failed'
           self.training_status['error'] = str(e)
           self.training_status['end_time'] = datetime.now().isoformat()
           raise
       
       finally:
           self._update_status()
   
   def test(self, args):
       """테스트 모드 - 데이터 수집만 테스트"""
       try:
           logger.info("🧪 데이터 수집 테스트 모드")
           
           collector = DataCollector(args.symbol)
           
           # 최신 100개 데이터만 수집
           df = collector.get_latest_data(interval=args.interval, limit=100)
           
           if df is not None:
               logger.info(f"✅ 데이터 수집 성공")
               logger.info(f"   데이터 크기: {df.shape}")
               logger.info(f"   컬럼 수: {len(df.columns)}")
               logger.info(f"   시작: {df.index[0]}")
               logger.info(f"   종료: {df.index[-1]}")
               
               # 지표 요약
               summary = collector.get_indicator_summary(df)
               logger.info(f"📊 현재 지표:")
               logger.info(f"   가격: ${summary['price']['close']:,.2f}")
               logger.info(f"   RSI: {summary['momentum']['rsi_14']:.1f}")
               logger.info(f"   ADX: {summary['trend']['adx']:.1f}")
           else:
               logger.error("데이터 수집 실패")
               
       except Exception as e:
           logger.error(f"테스트 실패: {e}")
           raise
   
   def info(self, args):
       """정보 모드 - 시스템 정보 출력"""
       try:
           logger.info("ℹ️ 시스템 정보")
           logger.info(f"   Python: {sys.version}")
           logger.info(f"   작업 디렉토리: {os.getcwd()}")
           logger.info(f"   모델 디렉토리: {self.models_dir}")
           
           # 기존 모델 확인
           model_files = list(self.models_dir.glob("*.h5"))
           logger.info(f"   저장된 모델: {len(model_files)}개")
           
           for model_file in model_files[:5]:  # 최근 5개만
               logger.info(f"      - {model_file.name}")
           
           # GPU 정보
           try:
               import tensorflow as tf
               gpus = tf.config.list_physical_devices('GPU')
               if gpus:
                   logger.info(f"   GPU: {len(gpus)}개 감지됨")
                   for gpu in gpus:
                       logger.info(f"      - {gpu.name}")
               else:
                   logger.info("   GPU: 사용 불가 (CPU 모드)")
           except:
               logger.info("   GPU: 확인 불가")
               
       except Exception as e:
           logger.error(f"정보 조회 실패: {e}")
           raise
   
   def run(self):
       """메인 실행"""
       args = self.parse_arguments()
       
       try:
           if args.mode == 'train':
               self.train(args)
           elif args.mode == 'test':
               self.test(args)
           elif args.mode == 'info':
               self.info(args)
           else:
               logger.error(f"알 수 없는 모드: {args.mode}")
               sys.exit(1)
               
       except Exception as e:
           logger.error(f"실행 실패: {e}")
           sys.exit(1)

def main():
   """메인 함수"""
   executor = TrainingExecutor()
   executor.run()

if __name__ == "__main__":
   main()