# 파일 경로: core/ai/model_manager.py
# 코드명: AI 모델 버전 관리 및 파일 시스템 (메인 PC 동기화 기능 추가)

import os
import json
import glob
import subprocess
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

class ModelManager:
    """AI 모델 버전 관리 클래스 (NAS용)"""
    
    def __init__(self, models_dir: str = "models", remote_host: str = None):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.metadata_file = self.models_dir / "models_metadata.json"
        self.active_model_file = self.models_dir / "active_model.txt"
        
        # 메인 PC 연결 정보
        self.remote_host = remote_host or "nah32@192.168.0.27"
        self.remote_models_dir = "/home/nah32/nhbot_ai/models"
        self.remote_container = "nhbot-trainer-container"
        
        # 메타데이터 파일 초기화
        self._init_metadata()
        
        print(f"✅ ModelManager 초기화")
        print(f"   로컬 디렉토리: {self.models_dir}")
        print(f"   원격 호스트: {self.remote_host}")
    
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
    
    def sync_with_remote(self) -> int:
        """메인 PC와 모델 동기화"""
        try:
            print("🔄 메인 PC와 모델 동기화 시작...")
            
            # 1. 원격에서 모델 목록 가져오기
            remote_models = self._get_remote_models()
            local_metadata = self._load_metadata()
            
            synced_count = 0
            
            for model_name in remote_models:
                if model_name not in local_metadata:
                    # 새 모델 발견 - 동기화 필요
                    print(f"   🆕 새 모델 발견: {model_name}")
                    
                    if self._sync_model_from_remote(model_name):
                        synced_count += 1
                        print(f"   ✅ {model_name} 동기화 완료")
                    else:
                        print(f"   ❌ {model_name} 동기화 실패")
            
            print(f"✅ 동기화 완료: {synced_count}개 모델")
            return synced_count
            
        except Exception as e:
            print(f"❌ 동기화 실패: {e}")
            return 0
    
    def _get_remote_models(self) -> List[str]:
        """원격 서버의 모델 목록 조회"""
        try:
            # SSH로 원격 모델 디렉토리 목록 조회
            cmd = f'ssh {self.remote_host} "ls {self.remote_models_dir}/*.h5 2>/dev/null"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return []
            
            # 파일명만 추출
            models = []
            for path in result.stdout.strip().split('\n'):
                if path:
                    filename = Path(path).stem  # model_XXXXXX 형태
                    if filename.startswith('model_'):
                        models.append(filename)
            
            return models
            
        except Exception as e:
            print(f"원격 모델 목록 조회 실패: {e}")
            return []
    
    def _sync_model_from_remote(self, model_name: str) -> bool:
        """특정 모델을 원격에서 로컬로 동기화"""
        try:
            # 1. 모델 정보 파일 복사
            info_file = f"{model_name}_info.json"
            remote_info_path = f"{self.remote_models_dir}/{info_file}"
            local_info_path = self.models_dir / info_file
            
            scp_cmd = f'scp {self.remote_host}:{remote_info_path} {local_info_path}'
            result = subprocess.run(scp_cmd, shell=True, capture_output=True)
            
            if result.returncode != 0:
                print(f"   정보 파일 복사 실패: {model_name}")
                return False
            
            # 2. 정보 파일 읽기
            with open(local_info_path, 'r') as f:
                model_info = json.load(f)
            
            # 3. 모델 파일 복사 (.h5)
            model_file = f"{model_name}.h5"
            remote_model_path = f"{self.remote_models_dir}/{model_file}"
            local_model_path = self.models_dir / model_file
            
            scp_cmd = f'scp {self.remote_host}:{remote_model_path} {local_model_path}'
            result = subprocess.run(scp_cmd, shell=True, capture_output=True)
            
            if result.returncode != 0:
                print(f"   모델 파일 복사 실패: {model_name}")
                return False
            
            # 4. 스케일러 파일 복사 (.pkl)
            scaler_file = f"{model_name}_scaler.pkl"
            remote_scaler_path = f"{self.remote_models_dir}/{scaler_file}"
            local_scaler_path = self.models_dir / scaler_file
            
            scp_cmd = f'scp {self.remote_host}:{remote_scaler_path} {local_scaler_path}'
            result = subprocess.run(scp_cmd, shell=True, capture_output=True)
            
            if result.returncode != 0:
                print(f"   스케일러 파일 복사 실패: {model_name}")
                # 스케일러는 선택적이므로 실패해도 계속 진행
            
            # 5. 메타데이터 업데이트
            metadata = self._load_metadata()
            metadata[model_name] = {
                "name": model_name,
                "created_at": model_info.get("created_at", datetime.now().isoformat()),
                "accuracy": model_info.get("accuracy", 0),
                "model_path": str(local_model_path),
                "scaler_path": str(local_scaler_path),
                "info_path": str(local_info_path),
                "status": "synced",
                "parameters": model_info.get("parameters", {}),
                "indicators": model_info.get("indicators", {}),
                "training_duration": model_info.get("training_duration", 0),
                "synced_at": datetime.now().isoformat(),
                "source": "mainpc"
            }
            
            self._save_metadata(metadata)
            
            return True
            
        except Exception as e:
            print(f"   모델 동기화 오류 ({model_name}): {e}")
            return False
    
    def check_remote_training_status(self) -> Dict:
        """원격 학습 상태 확인"""
        try:
            # Docker 컨테이너에서 학습 상태 파일 확인
            cmd = f'ssh {self.remote_host} "docker exec {self.remote_container} cat /app/training_status.json 2>/dev/null"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
            
            return {"status": "idle"}
            
        except Exception as e:
            print(f"원격 학습 상태 확인 실패: {e}")
            return {"status": "error", "message": str(e)}
    
    def generate_model_name(self) -> str:
        """새 모델명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"model_{timestamp}"
    
    def save_model(self, model_name: str, model_data: Dict, accuracy: float) -> bool:
        """모델 저장 (로컬 학습용)"""
        try:
            # 모델 파일 경로
            model_path = self.models_dir / f"{model_name}.h5"
            scaler_path = self.models_dir / f"{model_name}_scaler.pkl"
            
            # 메타데이터 업데이트
            metadata = self._load_metadata()
            metadata[model_name] = {
                "name": model_name,
                "created_at": datetime.now().isoformat(),
                "accuracy": accuracy,
                "model_path": str(model_path),
                "scaler_path": str(scaler_path),
                "status": "trained",
                "parameters": model_data.get("parameters", {}),
                "indicators": model_data.get("indicators", {}),
                "training_duration": model_data.get("training_duration", 0),
                "source": "local"
            }
            
            self._save_metadata(metadata)
            
            # 첫 번째 모델이면 자동으로 활성화
            if not self.get_active_model():
                self.set_active_model(model_name)
            
            return True
        except Exception as e:
            print(f"모델 저장 실패: {e}")
            return False
    
    def get_model_list(self) -> List[Dict]:
        """모델 목록 조회 (최신순)"""
        # 동기화 실행
        self.sync_with_remote()
        
        metadata = self._load_metadata()
        models = list(metadata.values())
        
        # 생성일 기준 내림차순 정렬
        models.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return models
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """특정 모델 정보 조회"""
        metadata = self._load_metadata()
        model_info = metadata.get(model_name)
        
        if not model_info:
            # 원격에서 찾아보기
            if self._sync_model_from_remote(model_name):
                metadata = self._load_metadata()
                model_info = metadata.get(model_name)
        
        return model_info
    
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
            
            # 모델 파일 존재 확인
            model_path = Path(model_info['model_path'])
            if not model_path.exists():
                print(f"모델 파일이 없습니다. 원격에서 동기화 중...")
                if not self._sync_model_from_remote(model_name):
                    return False
            
            with open(self.active_model_file, 'w') as f:
                f.write(model_name)
            
            print(f"✅ 활성 모델 변경: {model_name}")
            return True
            
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
            
            # 메타데이터에서 제거
            metadata = self._load_metadata()
            if model_name in metadata:
                model_info = metadata[model_name]
                
                # 파일 삭제
                for path_key in ['model_path', 'scaler_path', 'info_path']:
                    if path_key in model_info:
                        file_path = Path(model_info[path_key])
                        if file_path.exists():
                            file_path.unlink()
                
                del metadata[model_name]
                self._save_metadata(metadata)
                
                print(f"✅ 모델 삭제 완료: {model_name}")
                return True
            
            return False
        except Exception as e:
            print(f"모델 삭제 실패: {e}")
            return False
    
    def cleanup_old_models(self, keep_count: int = 5) -> int:
        """오래된 모델 정리 (최신 N개만 보관)"""
        try:
            models = self.get_model_list()
            active_model = self.get_active_model()
            
            # 활성 모델은 보호
            models_to_delete = []
            kept_count = 0
            
            for model in models:
                model_name = model["name"]
                
                if model_name == active_model:
                    # 활성 모델은 항상 보관
                    continue
                elif kept_count < keep_count:
                    # 보관 개수 내에서는 유지
                    kept_count += 1
                    continue
                else:
                    # 삭제 대상
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
            total_size = 0
            local_count = 0
            remote_count = 0
            
            # 모델 파일 크기 계산
            for model_file in self.models_dir.glob("*.h5"):
                total_size += model_file.stat().st_size
            
            for scaler_file in self.models_dir.glob("*_scaler.pkl"):
                total_size += scaler_file.stat().st_size
            
            # 소스별 카운트
            for model in models:
                if model.get('source') == 'local':
                    local_count += 1
                else:
                    remote_count += 1
            
            return {
                "total_models": len(models),
                "local_models": local_count,
                "remote_models": remote_count,
                "active_model": self.get_active_model(),
                "storage_size_mb": round(total_size / 1024 / 1024, 2),
                "models_directory": str(self.models_dir)
            }
            
        except Exception as e:
            print(f"저장소 정보 조회 실패: {e}")
            return {}

# ============================================================================
# 사용 예시 및 테스트
# ============================================================================

if __name__ == "__main__":
    print("🚀 ModelManager 테스트 시작")
    
    # 모델 관리자 생성
    manager = ModelManager()
    
    # 원격 동기화 테스트
    print("\n📡 원격 모델 동기화")
    synced = manager.sync_with_remote()
    print(f"   동기화된 모델: {synced}개")
    
    # 모델 목록 조회
    print("\n📋 모델 목록")
    models = manager.get_model_list()
    for model in models[:5]:  # 상위 5개만
        print(f"   - {model['name']}: 정확도 {model.get('accuracy', 0):.3f}")
    
    # 저장소 정보
    print("\n💾 저장소 정보")
    info = manager.get_storage_info()
    print(f"   총 모델: {info['total_models']}개")
    print(f"   로컬: {info['local_models']}개, 원격: {info['remote_models']}개")
    print(f"   용량: {info['storage_size_mb']} MB")
    
    print("\n✅ ModelManager 테스트 완료")