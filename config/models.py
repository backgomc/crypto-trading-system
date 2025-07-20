from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """사용자 모델"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        """비밀번호 해시화"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """비밀번호 확인"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """마지막 로그인 시간 업데이트"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'

class TradingLog(db.Model):
    """매매 기록 모델"""
    __tablename__ = 'trading_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
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
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20), nullable=False)  # 'INFO', 'WARNING', 'ERROR'
    category = db.Column(db.String(50), nullable=False)  # 'LOGIN', 'TRADING', 'SYSTEM'
    message = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(200), nullable=True)
    
    def __repr__(self):
        return f'<SystemLog {self.level}: {self.message[:50]}>'