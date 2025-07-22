# 파일 경로: api/utils.py
# 코드명: API 공통 유틸리티 함수들

from flask import jsonify, session
from datetime import datetime
from functools import wraps

def api_required(f):
    """API 인증 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return error_response('로그인이 필요합니다.', 'AUTH_REQUIRED', 401)
        return f(*args, **kwargs)
    return decorated_function

def error_response(message, code='ERROR', status_code=400):
    """에러 응답 헬퍼 함수"""
    return jsonify({
        'success': False,
        'error': message,
        'code': code,
        'timestamp': datetime.utcnow().isoformat()
    }), status_code

def success_response(data=None, message='성공'):
    """성공 응답 헬퍼 함수"""
    response = {
        'success': True,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    if data is not None:
        response['data'] = data
    return jsonify(response)

def validate_request_data(request, required_fields):
    """요청 데이터 검증 함수"""
    data = request.get_json()
    if not data:
        return None, error_response('JSON 데이터가 필요합니다.', 'VALIDATION_ERROR')
    
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return None, error_response(f'필수 필드가 누락되었습니다: {", ".join(missing_fields)}', 'VALIDATION_ERROR')
    
    return data, None