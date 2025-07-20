from flask import Blueprint, render_template

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def dashboard():
    """메인 대시보드"""
    return render_template('dashboard.html')

@web_bp.route('/settings')
def settings():
    """설정 페이지"""
    return render_template('settings.html')
