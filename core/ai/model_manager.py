# 파일 경로: core/ai/model_manager.py
# 코드명: AI 모델 버전 관리 및 파일 시스템

import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

class ModelManager:
    """AI 모델 버전 관리 클래스"""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.metadata_file = self.models_dir / "models_metadata.json"
        self.active_model_file = self.models_dir / "active_model.txt"
        
        # 메타데이터 파일 초기화
        self._init_metadata()
    
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
    
    def generate_model_name(self) -> str:
        """새 모델명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"model_{timestamp}"
    
    def save_model(self, model_name: str, model_data: Dict, accuracy: float) -> bool:
        """모델 저장"""
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
                "training_duration": model_data.get("training_duration", 0)
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
        metadata = self._load_metadata()
        models = list(metadata.values())
        
        # 생성일 기준 내림차순 정렬
        models.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return models
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """특정 모델 정보 조회"""
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
            if not self.get_model_info(model_name):
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
                for path_key in ['model_path', 'scaler_path']:
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
            
            # 모델 파일 크기 계산
            for model_file in self.models_dir.glob("*.h5"):
                total_size += model_file.stat().st_size
            
            for scaler_file in self.models_dir.glob("*_scaler.pkl"):
                total_size += scaler_file.stat().st_size
            
            return {
                "total_models": len(models),
                "active_model": self.get_active_model(),
                "storage_size_mb": round(total_size / 1024 / 1024, 2),
                "models_directory": str(self.models_dir)
            }
            
        except Exception as e:
            print(f"저장소 정보 조회 실패: {e}")
            return {}