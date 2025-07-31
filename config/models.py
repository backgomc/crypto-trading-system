# 파일 경로: config/models.py
# 코드명: 데이터베이스 모델 정의 (사용자별 설정 추가)

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json
import pytz

db = SQLAlchemy()

def get_kst_now():
    """한국시간 반환"""
    import pytz
    kst = pytz.timezone('Asia/Seoul')
    return datetime.now(kst).replace(tzinfo=None)

class User(db.Model):
   """사용자 모델"""
   __tablename__ = 'users'
   
   id = db.Column(db.Integer, primary_key=True)
   username = db.Column(db.String(80), unique=True, nullable=False)
   password_hash = db.Column(db.String(120), nullable=False)
   email = db.Column(db.String(120), unique=True, nullable=False)  # 필수 입력으로 변경
   created_at = db.Column(db.DateTime, default=get_kst_now)  # 한국시간으로 변경
   last_login = db.Column(db.DateTime, nullable=True)
   last_active = db.Column(db.DateTime, nullable=True)  # ping 방식용 마지막 활동 시간 추가
   is_active = db.Column(db.Boolean, default=True)
   is_admin = db.Column(db.Boolean, default=False)
   
   def set_password(self, password):
       """비밀번호 해시화"""
       self.password_hash = generate_password_hash(password)
   
   def check_password(self, password):
       """비밀번호 확인"""
       return check_password_hash(self.password_hash, password)
   
   def update_last_login(self):
       """마지막 로그인 시간 업데이트 (한국시간)"""
       self.last_login = get_kst_now()
       db.session.commit()
   
   def update_last_active(self):
       """마지막 활동 시간 업데이트 (ping용, 한국시간)"""
       self.last_active = get_kst_now()
       db.session.commit()
   
   def is_online(self, threshold_minutes=1):
       """접속 상태 확인 (ping 방식 - 1분 임계값)"""
       if not self.last_active:
           return False
       from datetime import timedelta
       threshold = get_kst_now() - timedelta(minutes=threshold_minutes)
       return self.last_active >= threshold
   
   @classmethod
   def get_online_count(cls, threshold_minutes=1):
       """현재 접속자 수 조회 (1분 임계값)"""
       from datetime import timedelta
       threshold = get_kst_now() - timedelta(minutes=threshold_minutes)
       return cls.query.filter(
           cls.is_active == True,
           cls.last_active >= threshold
       ).count()
   
   @classmethod
   def get_online_users(cls, threshold_minutes=1):
       """현재 접속 중인 사용자 목록 (1분 임계값)"""
       from datetime import timedelta
       threshold = get_kst_now() - timedelta(minutes=threshold_minutes)
       return cls.query.filter(
           cls.is_active == True,
           cls.last_active >= threshold
       ).all()
   
   def __repr__(self):
       return f'<User {self.username}>'

class TradingLog(db.Model):
    """매매 기록 모델"""
    __tablename__ = 'trading_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=get_kst_now)
    action = db.Column(db.String(50), nullable=False)  # 'buy', 'sell', 'long', 'short'
    symbol = db.Column(db.String(20), nullable=False, default='BTCUSDT')
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    profit_loss = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), nullable=False, default='completed')  # 'completed', 'failed'
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<TradingLog {self.action} {self.quantity} at {self.price}>'

class SystemLog(db.Model):
    """시스템 로그 모델"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=get_kst_now)
    level = db.Column(db.String(20), nullable=False)  # 'INFO', 'WARNING', 'ERROR'
    category = db.Column(db.String(50), nullable=False)  # 'LOGIN', 'TRADING', 'SYSTEM'
    message = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(200), nullable=True)
    
    def __repr__(self):
        return f'<SystemLog {self.level}: {self.message[:50]}>'

# ============================================================================
# 새로 추가: 사용자별 설정 관리 모델들
# ============================================================================

class UserConfig(db.Model):
    """사용자별 매매 설정 모델"""
    __tablename__ = 'user_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    config_key = db.Column(db.String(100), nullable=False, index=True)
    config_value = db.Column(db.Text, nullable=False)
    config_type = db.Column(db.String(20), default='json', nullable=False)  # json, string, number, boolean
    created_at = db.Column(db.DateTime, default=get_kst_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_kst_now, onupdate=get_kst_now, nullable=False)
    
    # 복합 인덱스: 사용자별 설정 키는 유일
    __table_args__ = (db.UniqueConstraint('user_id', 'config_key', name='uq_user_config'),)
    
    # 관계 설정
    user = db.relationship('User', backref='configs')
    
    def set_value(self, value):
        """값 설정 (타입에 따라 자동 변환)"""
        if isinstance(value, dict) or isinstance(value, list):
            self.config_value = json.dumps(value, ensure_ascii=False)
            self.config_type = 'json'
        elif isinstance(value, bool):
            self.config_value = str(value).lower()
            self.config_type = 'boolean'
        elif isinstance(value, (int, float)):
            self.config_value = str(value)
            self.config_type = 'number'
        else:
            self.config_value = str(value)
            self.config_type = 'string'
    
    def get_value(self):
        """값 반환 (타입에 따라 자동 변환)"""
        if self.config_type == 'json':
            try:
                return json.loads(self.config_value)
            except:
                return {}
        elif self.config_type == 'boolean':
            return self.config_value.lower() == 'true'
        elif self.config_type == 'number':
            try:
                if '.' in self.config_value:
                    return float(self.config_value)
                else:
                    return int(self.config_value)
            except:
                return 0
        else:
            return self.config_value
    
    @classmethod
    def get_user_config(cls, user_id, config_key, default_value=None):
        """사용자 설정 조회"""
        config = cls.query.filter_by(user_id=user_id, config_key=config_key).first()
        if config:
            return config.get_value()
        return default_value
    
    @classmethod
    def set_user_config(cls, user_id, config_key, value):
        """사용자 설정 저장"""
        config = cls.query.filter_by(user_id=user_id, config_key=config_key).first()
        if not config:
            config = cls(user_id=user_id, config_key=config_key)
            db.session.add(config)
        
        config.set_value(value)
        config.updated_at = get_kst_now()
        db.session.commit()
        return config
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'config_key': self.config_key,
            'config_value': self.get_value(),
            'config_type': self.config_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<UserConfig {self.config_key} for user {self.user_id}>'

class TradingState(db.Model):
    """사용자별 매매 상태 모델"""
    __tablename__ = 'trading_states'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    state_key = db.Column(db.String(100), nullable=False, index=True)
    state_value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=get_kst_now, onupdate=get_kst_now, nullable=False)
    
    # 복합 인덱스: 사용자별 상태 키는 유일
    __table_args__ = (db.UniqueConstraint('user_id', 'state_key', name='uq_user_state'),)
    
    # 관계 설정
    user = db.relationship('User', backref='trading_states')
    
    @classmethod
    def get_state(cls, user_id, state_key, default=None):
        """상태 값 조회"""
        state = cls.query.filter_by(user_id=user_id, state_key=state_key).first()
        if state:
            try:
                return json.loads(state.state_value) if state.state_value else default
            except:
                return state.state_value
        return default
    
    @classmethod
    def set_state(cls, user_id, state_key, value):
        """상태 값 설정"""
        state = cls.query.filter_by(user_id=user_id, state_key=state_key).first()
        if not state:
            state = cls(user_id=user_id, state_key=state_key)
            db.session.add(state)
        
        if isinstance(value, (dict, list)):
            state.state_value = json.dumps(value, ensure_ascii=False)
        else:
            state.state_value = str(value) if value is not None else None
        
        state.updated_at = get_kst_now()
        db.session.commit()
        return state
    
    def to_dict(self):
        """딕셔너리로 변환"""
        try:
            value = json.loads(self.state_value) if self.state_value else None
        except:
            value = self.state_value
        
        return {
            'user_id': self.user_id,
            'state_key': self.state_key,
            'state_value': value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<TradingState {self.state_key} for user {self.user_id}>'

class ConfigHistory(db.Model):
    """설정 변경 이력 모델"""
    __tablename__ = 'config_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    config_key = db.Column(db.String(100), nullable=False, index=True)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=get_kst_now, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    
    # 관계 설정
    user = db.relationship('User', backref='config_changes')
    
    @classmethod
    def log_change(cls, user_id, config_key, old_value, new_value, ip_address=None, user_agent=None):
        """설정 변경 로그 생성"""
        history = cls(
            user_id=user_id,
            config_key=config_key,
            old_value=json.dumps(old_value, ensure_ascii=False) if isinstance(old_value, (dict, list)) else str(old_value) if old_value is not None else None,
            new_value=json.dumps(new_value, ensure_ascii=False) if isinstance(new_value, (dict, list)) else str(new_value) if new_value is not None else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(history)
        db.session.commit()
        return history
    
    def to_dict(self):
        """딕셔너리로 변환"""
        try:
            old_val = json.loads(self.old_value) if self.old_value else None
        except:
            old_val = self.old_value
        
        try:
            new_val = json.loads(self.new_value) if self.new_value else None
        except:
            new_val = self.new_value
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'config_key': self.config_key,
            'old_value': old_val,
            'new_value': new_val,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'ip_address': self.ip_address
        }
    
    def __repr__(self):
        return f'<ConfigHistory {self.config_key} changed for user {self.user_id}>'

# ============================================================================
# 헬퍼 함수들
# ============================================================================

def get_default_user_config():
    """기본 사용자 설정 반환"""
    return {
        'trading_settings': {
            'demo_mode': True,
            'virtual_balance': 10000,
            'symbol': 'BTCUSDT',
            'initial_position_size': 0.05,
            'adjustment_size': 0.01,
            'base_threshold': 1000,
            'loop_delay': 60,
            'consecutive_threshold': 4
        },
        'ai_settings': {
            'ai_enabled': True,
            'adaptive_threshold_enabled': True,
            'volatility_window': 20,
            'model_retrain_interval': 86400,
            'main_interval': '15',
            'ai_training_days': 365,
            'timeframes': ['1', '5', '15', '60'],
            'ai_sequence_length': 96
        },
        'macd_settings': {
            'short_window': 90,
            'long_window': 100,
            'signal_window': 9
        },
        'risk_management': {
            'max_position_size': 1.0,
            'stop_loss_percentage': 5.0,
            'take_profit_percentage': 3.0
        },
        'notification_settings': {
            'telegram_enabled': True,
            'telegram_retry_count': 5,
            'telegram_retry_interval': 60
        }
    }

def init_user_config(user_id):
    """사용자 기본 설정 초기화"""
    default_config = get_default_user_config()
    
    for section_key, section_value in default_config.items():
        UserConfig.set_user_config(user_id, section_key, section_value)
    
    print(f"✅ 사용자 {user_id} 기본 설정 초기화 완료")

def get_user_full_config(user_id):
    """사용자 전체 설정 조회"""
    configs = UserConfig.query.filter_by(user_id=user_id).all()
    
    if not configs:
        # 기본 설정으로 초기화
        init_user_config(user_id)
        configs = UserConfig.query.filter_by(user_id=user_id).all()
    
    result = {}
    for config in configs:
        result[config.config_key] = config.get_value()
    
    return result