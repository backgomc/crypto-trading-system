# 파일 경로: core/ai/ai_client.py
# 코드명: NAS에서 메인 PC AI 서버와 통신하는 통합 클라이언트

import requests
import json
import time
import threading
import logging
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

class AIClient:
    """메인 PC AI 서버와 통신하는 통합 클라이언트 (학습/예측/모델관리 통합)"""
    
    def __init__(self, host: str = "192.168.0.27", port: int = 5000):
        """
        AI 클라이언트 초기화
        
        Args:
            host: 메인 PC IP 주소
            port: Flask API 서버 포트
        """
        # API 연결 정보
        self.base_url = f"http://{host}:{port}"
        self.api_endpoints = {
            # 기본 엔드포인트
            'health': f"{self.base_url}/health",
            'status': f"{self.base_url}/status",
            'system_info': f"{self.base_url}/system/info",
            
            # 학습 관련
            'train': f"{self.base_url}/train",
            'train_stop': f"{self.base_url}/train/stop",
            'logs': f"{self.base_url}/logs",
            
            # 예측 관련
            'predict': f"{self.base_url}/predict",
            
            # 모델 관리
            'models': f"{self.base_url}/models",
            'model_info': f"{self.base_url}/models/{{model_name}}",
            'model_activate': f"{self.base_url}/models/{{model_name}}/activate",
            'model_delete': f"{self.base_url}/models/{{model_name}}/delete",
            'model_download': f"{self.base_url}/models/{{model_name}}/download"
        }
        
        # 세션 설정 (연결 재사용)
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'NHBot-AIClient/2.0'
        })
        
        # 학습 상태 관리
        self.is_training = False
        self.monitor_thread = None
        self.status_callback = None
        self.training_status = {
            'status': 'idle',
            'start_time': None,
            'current_epoch': 0,
            'total_epochs': 0,
            'accuracy': 0.0,
            'loss': 0.0,
            'val_accuracy': 0.0,
            'val_loss': 0.0,
            'model_name': None,
            'error': None,
            'training_id': None,
            'progress_percentage': 0
        }
        
        # 예측 캐시 설정
        self.cache_enabled = True
        self.cache_ttl = 60  # 60초 캐시
        self.prediction_cache = {}
        self.last_cache_time = None
        
        # 모델 관리 (로컬 메타데이터)
        self.models_dir = Path("models")
        self.models_dir.mkdir(exist_ok=True)
        self.metadata_file = self.models_dir / "models_metadata.json"
        self.active_model_file = self.models_dir / "active_model.txt"
        self._init_metadata()
        
        # 연결 상태
        self.is_connected = False
        self._check_connection()
        
        print(f"✅ AIClient 초기화 완료")
        print(f"   API 서버: {self.base_url}")
        print(f"   연결 상태: {'연결됨' if self.is_connected else '연결 안됨'}")
    
    # ============================================================================
    # 공통 기능
    # ============================================================================
    
    def _check_connection(self) -> bool:
        """API 서버 연결 확인"""
        try:
            response = self.session.get(self.api_endpoints['health'], timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    self.is_connected = True
                    print(f"✅ API 서버 연결 확인: {data.get('service', 'AI Server')}")
                    return True
            
            print(f"❌ API 서버 응답 오류: {response.status_code}")
            self.is_connected = False
            return False
            
        except requests.exceptions.ConnectTimeout:
            print(f"❌ API 서버 연결 시간 초과")
            self.is_connected = False
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ API 서버에 연결할 수 없습니다: {self.base_url}")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"❌ 연결 확인 실패: {e}")
            self.is_connected = False
            return False
    
    def check_connection(self) -> bool:
        """외부에서 호출 가능한 연결 확인"""
        return self._check_connection()
    
    def get_system_info(self) -> Dict:
        """시스템 정보 조회"""
        try:
            response = self.session.get(self.api_endpoints['system_info'], timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result.get('system', {})
            
            return {}
        except Exception as e:
            print(f"시스템 정보 조회 실패: {e}")
            return {}
    
    def test_connection(self) -> Dict:
        """연결 테스트 및 종합 정보"""
        results = {
            'api_connection': False,
            'server_healthy': False,
            'gpu_available': False,
            'gpu_count': 0,
            'models_count': 0,
            'tensorflow_version': 'unknown',
            'response_time_ms': None
        }
        
        try:
            # 응답 시간 측정
            start_time = time.time()
            
            # API 연결 테스트
            results['api_connection'] = self._check_connection()
            
            if results['api_connection']:
                # 시스템 정보 조회
                system_info = self.get_system_info()
                
                results['server_healthy'] = True
                results['gpu_available'] = system_info.get('gpu', {}).get('available', False)
                results['gpu_count'] = system_info.get('gpu', {}).get('count', 0)
                results['models_count'] = system_info.get('models_count', 0)
                results['tensorflow_version'] = system_info.get('tensorflow_version', 'unknown')
            
            # 응답 시간 계산
            elapsed = (time.time() - start_time) * 1000
            results['response_time_ms'] = round(elapsed, 2)
            
        except Exception as e:
            print(f"테스트 중 오류: {e}")
            results['error'] = str(e)
        
        return results
    
    # ============================================================================
    # 학습 관련 기능 (RemoteTrainer에서 가져옴)
    # ============================================================================
    
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
            if not self._check_connection():
                raise Exception("API 서버 연결 실패")
            
            # API 요청 데이터 구성
            request_data = {
                'indicators': selected_indicators,
                'parameters': training_params
            }
            
            print("🚀 원격 학습 시작 (API)")
            print(f"   선택된 지표: {sum(1 for v in selected_indicators.values() if v)}개")
            print(f"   에폭: {training_params.get('epochs', 100)}")
            
            # API 호출
            response = self.session.post(
                self.api_endpoints['train'],
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    # 상태 업데이트
                    self.is_training = True
                    self.training_status = {
                        'status': 'running',
                        'start_time': datetime.now().isoformat(),
                        'current_epoch': 0,
                        'total_epochs': training_params.get('epochs', 100),
                        'accuracy': 0.0,
                        'loss': 0.0,
                        'val_accuracy': 0.0,
                        'val_loss': 0.0,
                        'model_name': None,
                        'error': None,
                        'training_id': result.get('training_id'),
                        'progress_percentage': 0
                    }
                    
                    # 상태 모니터링 시작
                    self.status_callback = progress_callback
                    self._start_monitoring()
                    
                    print(f"✅ 원격 학습이 시작되었습니다: {result.get('training_id')}")
                    return True
                else:
                    error_msg = result.get('error', '알 수 없는 오류')
                    print(f"❌ 학습 시작 실패: {error_msg}")
                    return False
            else:
                print(f"❌ API 응답 오류: {response.status_code}")
                if response.text:
                    try:
                        error_data = response.json()
                        print(f"   오류 메시지: {error_data.get('error', response.text)}")
                    except:
                        print(f"   응답: {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"❌ 학습 시작 요청 시간 초과")
            return False
        except Exception as e:
            print(f"❌ 원격 학습 시작 실패: {e}")
            self.is_training = False
            return False
    
    def _start_monitoring(self):
        """학습 상태 모니터링 시작"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        
        self.monitor_thread = threading.Thread(target=self._monitor_training, daemon=True)
        self.monitor_thread.start()
    
    def _monitor_training(self):
        """학습 상태 모니터링 (백그라운드 스레드)"""
        
        print("📊 학습 모니터링 시작 (API)")
        error_count = 0
        max_errors = 5
        check_interval = 5  # 5초마다 상태 확인
        
        while self.is_training:
            try:
                # API로 상태 조회
                response = self.session.get(self.api_endpoints['status'], timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success'):
                        status = result.get('status', {})
                        
                        # 상태 업데이트
                        self.training_status.update({
                            'status': status.get('status', 'unknown'),
                            'current_epoch': status.get('current_epoch', 0),
                            'total_epochs': status.get('total_epochs', 0),
                            'accuracy': status.get('accuracy', 0.0),
                            'loss': status.get('loss', 0.0),
                            'val_accuracy': status.get('val_accuracy', 0.0),
                            'val_loss': status.get('val_loss', 0.0),
                            'model_name': status.get('model_name'),
                            'error': status.get('error'),
                            'progress_percentage': status.get('progress_percentage', 0)
                        })
                        
                        # 콜백 호출
                        if self.status_callback:
                            message = f"에폭 {status.get('current_epoch', 0)}/{status.get('total_epochs', 0)}"
                            if status.get('accuracy', 0) > 0:
                                message += f" (정확도: {status['accuracy']:.3f})"
                            if status.get('val_accuracy', 0) > 0:
                                message += f" (검증: {status['val_accuracy']:.3f})"
                            if status.get('progress_percentage', 0) > 0:
                                message += f" [{status['progress_percentage']:.1f}%]"
                            self.status_callback(message)
                        
                        # 완료/실패 확인
                        if status.get('status') == 'completed':
                            print(f"✅ 학습 완료: {status.get('model_name')}")
                            self._on_training_completed(status)
                            break
                        
                        elif status.get('status') == 'failed':
                            print(f"❌ 학습 실패: {status.get('error')}")
                            if self.status_callback:
                                self.status_callback(f"학습 실패: {status.get('error')}")
                            self.is_training = False
                            break
                        
                        elif status.get('status') == 'stopped':
                            print(f"⏹️ 학습 중지됨")
                            if self.status_callback:
                                self.status_callback("학습이 중지되었습니다")
                            self.is_training = False
                            break
                        
                        error_count = 0  # 성공 시 에러 카운트 리셋
                    else:
                        print(f"⚠️ 상태 조회 실패: {result.get('error')}")
                        error_count += 1
                else:
                    print(f"⚠️ 상태 조회 응답 오류: {response.status_code}")
                    error_count += 1
                
                if error_count >= max_errors:
                    print(f"❌ 상태 확인 실패 {max_errors}회 초과")
                    self.is_training = False
                    break
                
                time.sleep(check_interval)
                
            except requests.exceptions.Timeout:
                print("⚠️ 상태 조회 시간 초과")
                error_count += 1
            except Exception as e:
                print(f"⚠️ 모니터링 오류: {e}")
                error_count += 1
                
            if error_count >= max_errors:
                self.is_training = False
                break
                
            time.sleep(check_interval)
        
        print("📊 학습 모니터링 종료")
        self.is_training = False
    
    def _on_training_completed(self, status: Dict):
        """학습 완료 후 처리"""
        try:
            model_name = status.get('model_name')
            if not model_name:
                print("⚠️ 모델명을 찾을 수 없습니다")
                return
            
            print(f"📥 학습된 모델 정보 저장 중: {model_name}")
            
            # API로 모델 정보 조회
            response = self.session.get(
                self.api_endpoints['model_info'].format(model_name=model_name),
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    model_info = result.get('model', {})
                    
                    # 로컬 메타데이터에 저장
                    self._save_model_metadata(
                        model_name=model_name,
                        model_info=model_info
                    )
                    
                    print(f"✅ 모델 정보 저장 완료: {model_name}")
                    
                    # 첫 번째 모델이면 자동 활성화
                    if not self.get_active_model():
                        self.set_active_model(model_name)
                        print(f"✅ 모델 자동 활성화: {model_name}")
                else:
                    print(f"❌ 모델 정보 조회 실패: {result.get('error')}")
            else:
                print(f"❌ 모델 정보 API 응답 오류: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 학습 완료 처리 실패: {e}")
        
        finally:
            self.is_training = False
    
    def stop_training(self) -> bool:
        """학습 중지"""
        if not self.is_training:
            return False
        
        try:
            print("⏹️ 원격 학습 중지 요청")
            
            # API 호출
            response = self.session.post(self.api_endpoints['train_stop'], timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    self.is_training = False
                    self.training_status['status'] = 'stopped'
                    print("✅ 원격 학습이 중지되었습니다.")
                    return True
                else:
                    print(f"❌ 학습 중지 실패: {result.get('error')}")
                    return False
            else:
                print(f"❌ 학습 중지 API 응답 오류: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 학습 중지 실패: {e}")
            return False
    
    def get_training_status(self) -> Dict:
        """현재 학습 상태 반환"""
        if self.is_training:
            # 최신 상태 조회 시도
            try:
                response = self.session.get(self.api_endpoints['status'], timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        status = result.get('status', {})
                        self.training_status.update(status)
            except:
                pass
        
        return self.training_status.copy()
    
    def get_remote_logs(self, lines: int = 50) -> str:
        """원격 학습 로그 조회"""
        try:
            response = self.session.get(
                self.api_endpoints['logs'],
                params={'lines': lines},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    memory_logs = result.get('memory_logs', [])
                    
                    # 로그 포맷팅
                    formatted_logs = []
                    for log in memory_logs:
                        timestamp = log.get('timestamp', '')
                        level = log.get('level', 'INFO')
                        message = log.get('message', '')
                        formatted_logs.append(f"[{timestamp}] [{level}] {message}")
                    
                    return "\n".join(formatted_logs)
                else:
                    return f"로그 조회 실패: {result.get('error')}"
            else:
                return f"로그 API 응답 오류: {response.status_code}"
                
        except Exception as e:
            return f"로그 조회 실패: {e}"
    
    # ============================================================================
    # 예측 관련 기능 (PredictorClient에서 가져옴)
    # ============================================================================
    
    def predict(self, market_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        AI 예측 수행
        
        Args:
            market_data: 시장 데이터 DataFrame (None이면 메인 PC에서 최신 데이터 수집)
            
        Returns:
            예측 결과 딕셔너리
        """
        try:
            # 연결 확인
            if not self.is_connected:
                if not self._check_connection():
                    return self._get_fallback_prediction("API 서버 연결 실패")
            
            # 캐시 확인
            if self.cache_enabled and self._is_cache_valid():
                print("📦 캐시된 예측 결과 사용")
                return self.prediction_cache['result']
            
            # 요청 데이터 준비
            request_data = {}
            
            if market_data is not None:
                # DataFrame을 JSON으로 변환
                if isinstance(market_data, pd.DataFrame):
                    # 인덱스가 datetime인 경우 문자열로 변환
                    if isinstance(market_data.index, pd.DatetimeIndex):
                        market_data_dict = market_data.reset_index().to_dict('records')
                        for record in market_data_dict:
                            if 'index' in record and hasattr(record['index'], 'isoformat'):
                                record['timestamp'] = record['index'].isoformat()
                                del record['index']
                    else:
                        market_data_dict = market_data.to_dict('records')
                    
                    request_data['market_data'] = market_data_dict
                else:
                    request_data['market_data'] = market_data
            
            # API 호출
            print("🔮 예측 API 호출 중...")
            response = self.session.post(
                self.api_endpoints['predict'],
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    prediction = result.get('prediction', {})
                    
                    # 캐시 업데이트
                    if self.cache_enabled:
                        self.prediction_cache = {
                            'result': prediction,
                            'time': datetime.now()
                        }
                        self.last_cache_time = datetime.now()
                    
                    # 결과 로깅
                    self._log_prediction(prediction)
                    
                    return prediction
                else:
                    error_msg = result.get('error', '알 수 없는 오류')
                    print(f"❌ 예측 실패: {error_msg}")
                    return self._get_fallback_prediction(f"API 오류: {error_msg}")
            else:
                print(f"❌ API 응답 오류: {response.status_code}")
                return self._get_fallback_prediction(f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⏱️ 예측 요청 시간 초과")
            return self._get_fallback_prediction("요청 시간 초과")
            
        except requests.exceptions.ConnectionError:
            print("🔌 API 서버 연결 실패")
            self.is_connected = False
            return self._get_fallback_prediction("연결 실패")
            
        except Exception as e:
            print(f"❌ 예측 중 오류: {e}")
            return self._get_fallback_prediction(str(e))
    
    def predict_batch(self, market_data_list: List[pd.DataFrame]) -> List[Dict]:
        """배치 예측 수행"""
        predictions = []
        
        for market_data in market_data_list:
            prediction = self.predict(market_data)
            predictions.append(prediction)
            
            # API 서버 부하 방지를 위한 딜레이
            time.sleep(0.1)
        
        return predictions
    
    def get_prediction_with_confidence(self, 
                                      market_data: Optional[pd.DataFrame] = None,
                                      min_confidence: float = 0.6) -> Dict:
        """최소 확신도 이상일 때만 예측 반환"""
        prediction = self.predict(market_data)
        
        # 확신도가 낮으면 중립 반환
        if prediction.get('confidence', 0) < min_confidence:
            prediction['signal'] = 'NEUTRAL'
            prediction['reason'] = f"확신도 부족 ({prediction.get('confidence', 0):.1%} < {min_confidence:.1%})"
        
        return prediction
    
    def validate_prediction(self, prediction: Dict) -> bool:
        """예측 결과 유효성 검증"""
        required_fields = ['signal', 'confidence', 'timestamp']
        
        for field in required_fields:
            if field not in prediction:
                return False
        
        # 신호 유효성
        if prediction['signal'] not in ['ALLOW', 'BLOCK', 'NEUTRAL']:
            return False
        
        # 확신도 범위
        if not (0.0 <= prediction['confidence'] <= 1.0):
            return False
        
        return True
    
    def _is_cache_valid(self) -> bool:
        """캐시 유효성 확인"""
        if not self.prediction_cache or not self.last_cache_time:
            return False
        
        elapsed = (datetime.now() - self.last_cache_time).total_seconds()
        return elapsed < self.cache_ttl
    
    def _get_fallback_prediction(self, reason: str) -> Dict:
        """폴백 예측 (API 실패 시)"""
        return {
            'signal': 'NEUTRAL',
            'confidence': 0.5,
            'raw_prediction': 0.5,
            'model_name': 'FALLBACK',
            'model_accuracy': 0.0,
            'timestamp': datetime.now().isoformat(),
            'reason': f"API 사용 불가: {reason}",
            'features_used': 0,
            'threshold': 0.5
        }
    
    def _log_prediction(self, prediction: Dict):
        """예측 결과 로깅"""
        signal = prediction.get('signal', 'UNKNOWN')
        confidence = prediction.get('confidence', 0)
        model = prediction.get('model_name', 'UNKNOWN')
        
        emoji = {
            'ALLOW': '✅',
            'BLOCK': '🚫',
            'NEUTRAL': '⚪'
        }.get(signal, '❓')
        
        print(f"{emoji} 예측: {signal} (확신도: {confidence:.1%}, 모델: {model})")
        
        if prediction.get('reason'):
            print(f"   이유: {prediction['reason']}")
    
    def clear_cache(self):
        """예측 캐시 클리어"""
        self.prediction_cache = {}
        self.last_cache_time = None
        print("🗑️ 예측 캐시 클리어됨")
    
    def set_cache_ttl(self, seconds: int):
        """캐시 TTL 설정"""
        self.cache_ttl = max(0, seconds)
        print(f"⏱️ 캐시 TTL 설정: {self.cache_ttl}초")
    
    def enable_cache(self, enabled: bool = True):
        """캐시 활성화/비활성화"""
        self.cache_enabled = enabled
        if not enabled:
            self.clear_cache()
        print(f"💾 캐시 {'활성화' if enabled else '비활성화'}")
    
    # ============================================================================
    # 모델 관리 기능 (ModelManager를 API 방식으로 전환)
    # ============================================================================
    
    def _init_metadata(self):
        """메타데이터 파일 초기화"""
        if not self.metadata_file.exists():
            self._save_metadata({})
    
    def _load_metadata(self) -> Dict:
        """메타데이터 로드"""
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_metadata(self, metadata: Dict):
        """메타데이터 저장"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _save_model_metadata(self, model_name: str, model_info: Dict):
        """모델 메타데이터 저장 (로컬)"""
        metadata = self._load_metadata()
        metadata[model_name] = {
            "name": model_name,
            "created_at": model_info.get("created_at", datetime.now().isoformat()),
            "accuracy": model_info.get("accuracy", 0),
            "val_accuracy": model_info.get("val_accuracy", 0),
            "loss": model_info.get("loss", 0),
            "val_loss": model_info.get("val_loss", 0),
            "status": "remote",  # 메인 PC에 있음
            "parameters": model_info.get("parameters", {}),
            "indicators": model_info.get("indicators", {}),
            "training_duration": model_info.get("training_duration", 0),
            "epochs_trained": model_info.get("epochs_trained", 0),
            "synced_at": datetime.now().isoformat(),
            "source": "mainpc"
        }
        self._save_metadata(metadata)
    
    def sync_models(self) -> int:
        """메인 PC와 모델 목록 동기화 (API 방식)"""
        try:
            print("🔄 메인 PC와 모델 동기화 시작...")
            
            # API로 모델 목록 조회
            response = self.session.get(self.api_endpoints['models'], timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    remote_models = result.get('models', [])
                    local_metadata = self._load_metadata()
                    
                    synced_count = 0
                    
                    for model in remote_models:
                        model_name = model.get('name')
                        
                        if model_name and model_name not in local_metadata:
                            # 새 모델 발견 - 메타데이터 저장
                            print(f"   🆕 새 모델 발견: {model_name}")
                            self._save_model_metadata(model_name, model)
                            synced_count += 1
                        elif model_name:
                            # 기존 모델 업데이트
                            existing = local_metadata.get(model_name, {})
                            if existing.get('accuracy', 0) != model.get('accuracy', 0):
                                print(f"   🔄 모델 업데이트: {model_name}")
                                self._save_model_metadata(model_name, model)
                                synced_count += 1
                    
                    print(f"✅ 동기화 완료: {synced_count}개 모델")
                    return synced_count
                else:
                    print(f"❌ 모델 목록 조회 실패: {result.get('error')}")
                    return 0
            else:
                print(f"❌ API 응답 오류: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"❌ 동기화 실패: {e}")
            return 0
    
    def get_available_models(self) -> List[Dict]:
        """사용 가능한 모델 목록 조회"""
        try:
            # API로 최신 목록 조회
            response = self.session.get(self.api_endpoints['models'], timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    models = result.get('models', [])
                    
                    # 로컬 메타데이터 업데이트
                    for model in models:
                        model_name = model.get('name')
                        if model_name:
                            self._save_model_metadata(model_name, model)
                    
                    return models
            
            # API 실패 시 로컬 메타데이터 반환
            metadata = self._load_metadata()
            return list(metadata.values())
            
        except Exception as e:
            print(f"모델 목록 조회 실패: {e}")
            # 로컬 메타데이터 반환
            metadata = self._load_metadata()
            return list(metadata.values())
    
    def get_model_list(self) -> List[Dict]:
        """모델 목록 조회 (최신순 정렬)"""
        models = self.get_available_models()
        
        # 생성일 기준 내림차순 정렬
        models.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return models
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """특정 모델 정보 조회"""
        try:
            # API로 상세 정보 조회
            response = self.session.get(
                self.api_endpoints['model_info'].format(model_name=model_name),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    model_info = result.get('model', {})
                    # 로컬 메타데이터 업데이트
                    self._save_model_metadata(model_name, model_info)
                    return model_info
            
            # API 실패 시 로컬 메타데이터에서 조회
            metadata = self._load_metadata()
            return metadata.get(model_name)
            
        except Exception as e:
            print(f"모델 정보 조회 실패: {e}")
            # 로컬 메타데이터에서 조회
            metadata = self._load_metadata()
            return metadata.get(model_name)
    
    def get_active_model(self) -> Optional[str]:
        """현재 활성 모델명 조회"""
        try:
            if self.active_model_file.exists():
                with open(self.active_model_file, 'r') as f:
                    return f.read().strip()
        except:
            pass
        return None
    
    def set_active_model(self, model_name: str) -> bool:
        """활성 모델 설정"""
        try:
            # 모델 존재 확인
            model_info = self.get_model_info(model_name)
            if not model_info:
                print(f"모델을 찾을 수 없습니다: {model_name}")
                return False
            
            # API로 활성화 요청
            response = self.session.post(
                self.api_endpoints['model_activate'].format(model_name=model_name),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    # 로컬 파일에 저장
                    with open(self.active_model_file, 'w') as f:
                        f.write(model_name)
                    
                    print(f"✅ 활성 모델 변경: {model_name}")
                    return True
                else:
                    print(f"❌ 모델 활성화 실패: {result.get('error')}")
                    return False
            else:
                print(f"❌ API 응답 오류: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"활성 모델 설정 실패: {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """모델 삭제"""
        try:
            # 활성 모델인지 확인
            if self.get_active_model() == model_name:
                print("활성 모델은 삭제할 수 없습니다.")
                return False
            
            # API로 삭제 요청
            response = self.session.delete(
                self.api_endpoints['model_delete'].format(model_name=model_name),
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    # 로컬 메타데이터에서도 제거
                    metadata = self._load_metadata()
                    if model_name in metadata:
                        del metadata[model_name]
                        self._save_metadata(metadata)
                    
                    print(f"✅ 모델 삭제 완료: {model_name}")
                    return True
                else:
                    print(f"❌ 모델 삭제 실패: {result.get('error')}")
                    return False
            else:
                print(f"❌ API 응답 오류: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"모델 삭제 실패: {e}")
            return False
    
    def cleanup_old_models(self, keep_count: int = 5) -> int:
        """오래된 모델 정리"""
        try:
            models = self.get_model_list()
            active_model = self.get_active_model()
            
            # 활성 모델은 보호
            models_to_delete = []
            kept_count = 0
            
            for model in models:
                model_name = model["name"]
                
                if model_name == active_model:
                    continue
                elif kept_count < keep_count:
                    kept_count += 1
                    continue
                else:
                    models_to_delete.append(model_name)
            
            # 삭제 실행
            deleted_count = 0
            for model_name in models_to_delete:
                if self.delete_model(model_name):
                    deleted_count += 1
            
            print(f"✅ 모델 정리 완료: {deleted_count}개 삭제")
            return deleted_count
            
        except Exception as e:
            print(f"모델 정리 실패: {e}")
            return 0
    
    def get_storage_info(self) -> Dict:
        """모델 저장소 정보"""
        try:
            models = self.get_model_list()
            
            return {
                "total_models": len(models),
                "active_model": self.get_active_model(),
                "models_directory": str(self.models_dir),
                "metadata_file": str(self.metadata_file)
            }
            
        except Exception as e:
            print(f"저장소 정보 조회 실패: {e}")
            return {}
    
    def generate_model_name(self) -> str:
        """새 모델명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"model_{timestamp}"
    
    # ============================================================================
    # 추가 유틸리티 메서드
    # ============================================================================
    
    def get_api_status(self) -> Dict:
        """API 서버 상태 조회"""
        try:
            response = self.session.get(self.api_endpoints['status'], timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result.get('status', {})
            
            return {'status': 'error', 'message': 'API 응답 오류'}
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def download_model(self, model_name: str, save_path: Optional[Path] = None) -> bool:
        """모델 파일 다운로드 (필요시)"""
        try:
            if save_path is None:
                save_path = self.models_dir / f"{model_name}.h5"
            
            response = self.session.get(
                self.api_endpoints['model_download'].format(model_name=model_name),
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"✅ 모델 다운로드 완료: {save_path}")
                return True
            else:
                print(f"❌ 모델 다운로드 실패: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 모델 다운로드 오류: {e}")
            return False

# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
    print("🚀 AIClient 통합 테스트 시작")
    print("="*60)
    
    # AI 클라이언트 생성
    client = AIClient(host="192.168.0.27", port=5000)
    
    # 1. 연결 테스트
    print("\n📡 연결 테스트")
    test_results = client.test_connection()
    for key, value in test_results.items():
        status = "✅" if value else "❌"
        print(f"   {status} {key}: {value}")
    
    # 2. 모델 목록 조회
    print("\n📋 모델 목록")
    models = client.get_model_list()
    for i, model in enumerate(models[:5], 1):
        print(f"   {i}. {model.get('name')}: 정확도 {model.get('accuracy', 0):.3f}")
    
    # 3. 현재 활성 모델
    print("\n🎯 활성 모델")
    active = client.get_active_model()
    print(f"   현재 활성: {active if active else '없음'}")
    
    # 4. 학습 상태 확인
    print("\n📊 학습 상태")
    status = client.get_training_status()
    print(f"   상태: {status['status']}")
    if status['status'] == 'running':
        print(f"   진행: {status['current_epoch']}/{status['total_epochs']} 에폭")
        print(f"   정확도: {status['accuracy']:.3f}")
    
    # 5. 예측 테스트 (더미 데이터)
    print("\n🔮 예측 테스트")
    dummy_data = pd.DataFrame({
        'close': np.random.randn(100) * 1000 + 95000,
        'volume': np.random.randn(100) * 100 + 1000,
        'rsi_14': np.random.randn(100) * 20 + 50
    })
    
    prediction = client.predict(dummy_data)
    print(f"   신호: {prediction['signal']}")
    print(f"   확신도: {prediction['confidence']:.1%}")
    print(f"   모델: {prediction.get('model_name', 'N/A')}")
    
    # 6. 저장소 정보
    print("\n💾 저장소 정보")
    info = client.get_storage_info()
    print(f"   총 모델: {info['total_models']}개")
    print(f"   활성 모델: {info['active_model']}")
    
    print("\n" + "="*60)
    print("✅ AIClient 통합 테스트 완료")