# 파일 경로: core/remote_trainer.py
# 코드명: NAS에서 메인 PC Docker 학습 원격 제어

import subprocess
import json
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Callable
from pathlib import Path
from core.ai.model_manager import ModelManager

class RemoteTrainer:
   """원격 학습 제어 클래스 (NAS → 메인 PC)"""
   
   def __init__(self, remote_host: str = None):
       # 원격 연결 정보
       self.remote_host = remote_host or "nah32@192.168.0.27"
       self.container_name = "nhbot-trainer-container"
       self.remote_script = "/app/scripts/train_model.py"
       
       # 모델 관리자
       self.model_manager = ModelManager()
       
       # 학습 상태
       self.is_training = False
       self.monitor_thread = None
       self.status_callback = None
       self.training_status = {
           'status': 'idle',
           'start_time': None,
           'current_epoch': 0,
           'total_epochs': 0,
           'accuracy': 0.0,
           'model_name': None,
           'error': None
       }
       
       print(f"✅ RemoteTrainer 초기화")
       print(f"   원격 호스트: {self.remote_host}")
       print(f"   컨테이너: {self.container_name}")
   
   def check_connection(self) -> bool:
       """원격 서버 연결 확인"""
       try:
           cmd = f'ssh -o ConnectTimeout=5 {self.remote_host} "echo connected"'
           result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
           
           if result.returncode == 0 and "connected" in result.stdout:
               print("✅ 원격 서버 연결 확인됨")
               return True
           else:
               print("❌ 원격 서버 연결 실패")
               return False
               
       except Exception as e:
           print(f"❌ 연결 확인 실패: {e}")
           return False
   
   def check_container_status(self) -> bool:
       """Docker 컨테이너 상태 확인"""
       try:
           cmd = f'ssh {self.remote_host} "docker ps --filter name={self.container_name} --format {{.Status}}"'
           result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
           
           if result.returncode == 0 and "Up" in result.stdout:
               print(f"✅ 컨테이너 실행 중: {self.container_name}")
               return True
           else:
               print(f"⚠️ 컨테이너가 실행 중이 아님: {self.container_name}")
               return False
               
       except Exception as e:
           print(f"❌ 컨테이너 상태 확인 실패: {e}")
           return False
   
   def start_training(self, 
                     selected_indicators: Dict[str, bool],
                     training_params: Dict,
                     progress_callback: Optional[Callable] = None) -> bool:
       """원격 학습 시작"""
       
       if self.is_training:
           print("❌ 이미 학습이 진행 중입니다.")
           return False
       
       try:
           # 연결 확인
           if not self.check_connection():
               raise Exception("원격 서버 연결 실패")
           
           if not self.check_container_status():
               # 컨테이너 시작 시도
               if not self._start_container():
                   raise Exception("Docker 컨테이너 시작 실패")
           
           # 학습 명령 구성
           cmd = self._build_training_command(selected_indicators, training_params)
           
           print("🚀 원격 학습 시작")
           print(f"   명령: {cmd}")
           
           # 백그라운드로 학습 실행
           result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
           
           # 실행 확인 (3초 대기)
           time.sleep(3)
           
           if result.poll() is not None:
               # 프로세스가 즉시 종료됨
               stderr = result.stderr.read().decode('utf-8')
               raise Exception(f"학습 시작 실패: {stderr}")
           
           # 상태 업데이트
           self.is_training = True
           self.training_status = {
               'status': 'running',
               'start_time': datetime.now().isoformat(),
               'current_epoch': 0,
               'total_epochs': training_params.get('epochs', 100),
               'accuracy': 0.0,
               'model_name': None,
               'error': None
           }
           
           # 상태 모니터링 시작
           self.status_callback = progress_callback
           self._start_monitoring()
           
           print("✅ 원격 학습이 시작되었습니다.")
           return True
           
       except Exception as e:
           print(f"❌ 원격 학습 시작 실패: {e}")
           self.is_training = False
           return False
   
   def _build_training_command(self, indicators: Dict, params: Dict) -> str:
       """학습 명령 구성"""
       
       # 지표를 JSON 문자열로 변환
       indicators_json = json.dumps(indicators).replace('"', '\\"')
       
       # Docker exec 명령 구성
       cmd_parts = [
           f'ssh {self.remote_host}',
           f'"docker exec -t {self.container_name}',
           f'python {self.remote_script}',
           f'--symbol {params.get("symbol", "BTCUSDT")}',
           f'--training-days {params.get("training_days", 365)}',
           f'--interval {params.get("interval", "15")}',
           f'--epochs {params.get("epochs", 100)}',
           f'--batch-size {params.get("batch_size", 32)}',
           f'--learning-rate {params.get("learning_rate", 0.001)}',
           f'--sequence-length {params.get("sequence_length", 60)}',
           f'--validation-split {params.get("validation_split", 20)}',
           f"--indicators '{indicators_json}'",
           f'--mode train"'
       ]
       
       return ' '.join(cmd_parts)
   
   def _start_container(self) -> bool:
       """Docker 컨테이너 시작"""
       try:
           print(f"🐳 Docker 컨테이너 시작 중: {self.container_name}")
           
           cmd = f'ssh {self.remote_host} "docker start {self.container_name}"'
           result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
           
           if result.returncode == 0:
               time.sleep(5)  # 컨테이너 시작 대기
               return self.check_container_status()
           else:
               print(f"❌ 컨테이너 시작 실패: {result.stderr}")
               return False
               
       except Exception as e:
           print(f"❌ 컨테이너 시작 오류: {e}")
           return False
   
   def _start_monitoring(self):
       """학습 상태 모니터링 시작"""
       if self.monitor_thread and self.monitor_thread.is_alive():
           return
       
       self.monitor_thread = threading.Thread(target=self._monitor_training, daemon=True)
       self.monitor_thread.start()
   
   def _monitor_training(self):
       """학습 상태 모니터링 (백그라운드 스레드)"""
       
       print("📊 학습 모니터링 시작")
       error_count = 0
       max_errors = 5
       
       while self.is_training:
           try:
               # 원격 상태 파일 읽기
               status = self._get_remote_status()
               
               if status:
                   self.training_status.update(status)
                   
                   # 콜백 호출
                   if self.status_callback:
                       message = f"에폭 {status.get('current_epoch', 0)}/{status.get('total_epochs', 0)}"
                       if status.get('accuracy', 0) > 0:
                           message += f" (정확도: {status['accuracy']:.3f})"
                       self.status_callback(message)
                   
                   # 완료 확인
                   if status.get('status') == 'completed':
                       print(f"✅ 학습 완료: {status.get('model_name')}")
                       self._on_training_completed(status)
                       break
                   
                   elif status.get('status') == 'failed':
                       print(f"❌ 학습 실패: {status.get('error')}")
                       self.is_training = False
                       break
                   
                   error_count = 0  # 성공 시 에러 카운트 리셋
               else:
                   error_count += 1
                   if error_count >= max_errors:
                       print(f"⚠️ 상태 확인 실패 {max_errors}회 초과")
                       break
               
               time.sleep(10)  # 10초마다 확인
               
           except Exception as e:
               print(f"모니터링 오류: {e}")
               error_count += 1
               if error_count >= max_errors:
                   break
               time.sleep(10)
       
       print("📊 학습 모니터링 종료")
       self.is_training = False
   
   def _get_remote_status(self) -> Optional[Dict]:
       """원격 학습 상태 조회"""
       try:
           cmd = f'ssh {self.remote_host} "docker exec {self.container_name} cat /app/training_status.json 2>/dev/null"'
           result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
           
           if result.returncode == 0 and result.stdout:
               return json.loads(result.stdout)
           
           return None
           
       except Exception as e:
           print(f"상태 조회 실패: {e}")
           return None
   
   def _on_training_completed(self, status: Dict):
       """학습 완료 후 처리"""
       try:
           model_name = status.get('model_name')
           if not model_name:
               print("⚠️ 모델명을 찾을 수 없습니다")
               return
           
           print(f"📥 학습된 모델 동기화 중: {model_name}")
           
           # ModelManager를 통해 동기화
           if self.model_manager._sync_model_from_remote(model_name):
               print(f"✅ 모델 동기화 완료: {model_name}")
               
               # 첫 번째 모델이면 자동 활성화
               if not self.model_manager.get_active_model():
                   self.model_manager.set_active_model(model_name)
           else:
               print(f"❌ 모델 동기화 실패: {model_name}")
               
       except Exception as e:
           print(f"학습 완료 처리 실패: {e}")
       
       finally:
           self.is_training = False
   
   def stop_training(self) -> bool:
       """학습 중지"""
       if not self.is_training:
           return False
       
       try:
           print("⏹️ 원격 학습 중지 요청")
           
           # Docker 컨테이너 내 Python 프로세스 종료
           cmd = f'ssh {self.remote_host} "docker exec {self.container_name} pkill -f train_model.py"'
           subprocess.run(cmd, shell=True, capture_output=True)
           
           self.is_training = False
           self.training_status['status'] = 'stopped'
           
           print("✅ 원격 학습이 중지되었습니다.")
           return True
           
       except Exception as e:
           print(f"❌ 학습 중지 실패: {e}")
           return False
   
   def get_training_status(self) -> Dict:
       """현재 학습 상태 반환"""
       if self.is_training:
           # 최신 상태 조회 시도
           remote_status = self._get_remote_status()
           if remote_status:
               self.training_status.update(remote_status)
       
       return self.training_status.copy()
   
   def get_remote_logs(self, lines: int = 50) -> str:
       """원격 학습 로그 조회"""
       try:
           cmd = f'ssh {self.remote_host} "docker exec {self.container_name} tail -n {lines} /app/logs/training.log 2>/dev/null"'
           result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
           
           if result.returncode == 0:
               return result.stdout
           else:
               return "로그를 가져올 수 없습니다."
               
       except Exception as e:
           return f"로그 조회 실패: {e}"
   
   def test_connection(self) -> Dict:
       """연결 테스트"""
       results = {
           'ssh_connection': False,
           'container_running': False,
           'script_exists': False,
           'gpu_available': False
       }
       
       try:
           # SSH 연결 테스트
           results['ssh_connection'] = self.check_connection()
           
           if results['ssh_connection']:
               # 컨테이너 상태
               results['container_running'] = self.check_container_status()
               
               # 스크립트 존재 확인
               cmd = f'ssh {self.remote_host} "docker exec {self.container_name} test -f {self.remote_script} && echo exists"'
               result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
               results['script_exists'] = "exists" in result.stdout
               
               # GPU 확인
               cmd = f'ssh {self.remote_host} "docker exec {self.container_name} python -c \\"import tensorflow as tf; print(len(tf.config.list_physical_devices(\'GPU\')))\\" 2>/dev/null"'
               result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
               try:
                   gpu_count = int(result.stdout.strip())
                   results['gpu_available'] = gpu_count > 0
                   results['gpu_count'] = gpu_count
               except:
                   results['gpu_available'] = False
                   results['gpu_count'] = 0
           
       except Exception as e:
           print(f"테스트 중 오류: {e}")
       
       return results

# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
   print("🚀 RemoteTrainer 테스트 시작")
   
   # 원격 학습기 생성
   trainer = RemoteTrainer()
   
   # 연결 테스트
   print("\n🔌 연결 테스트")
   test_results = trainer.test_connection()
   for key, value in test_results.items():
       status = "✅" if value else "❌"
       print(f"   {status} {key}: {value}")
   
   # 학습 테스트 (실제로 실행하려면 주석 해제)
   """
   print("\n📚 학습 테스트")
   
   selected_indicators = {
       'mfi': True,
       'vwap': True,
       'volatility': True
   }
   
   training_params = {
       'symbol': 'BTCUSDT',
       'training_days': 7,  # 테스트용 7일
       'epochs': 5,  # 테스트용 5 에폭
       'batch_size': 32,
       'learning_rate': 0.001,
       'sequence_length': 60,
       'validation_split': 20,
       'interval': '15'
   }
   
   def progress_callback(message):
       print(f"   📢 {message}")
   
   if trainer.start_training(selected_indicators, training_params, progress_callback):
       print("   ✅ 학습 시작됨")
       
       # 상태 모니터링 (30초)
       for i in range(6):
           time.sleep(5)
           status = trainer.get_training_status()
           print(f"   상태: {status['status']}, 에폭: {status['current_epoch']}/{status['total_epochs']}")
       
       # 학습 중지
       trainer.stop_training()
   """
   
   print("\n✅ RemoteTrainer 테스트 완료")