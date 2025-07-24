# 파일 경로: api/utils.py
# 코드명: API 공통 유틸리티 함수들 (개선됨)

from flask import jsonify, session, request
from datetime import datetime, timezone
from functools import wraps
import traceback
import re

# ============================================================================
# 인증 및 권한 데코레이터
# ============================================================================

def api_required(f):
    """API 인증 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return error_response('로그인이 필요합니다.', 'AUTH_REQUIRED', 401)
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """관리자 권한 필요 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return error_response('로그인이 필요합니다.', 'AUTH_REQUIRED', 401)
        if not session.get('is_admin', False):
            return error_response('관리자 권한이 필요합니다.', 'ADMIN_REQUIRED', 403)
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """현재 로그인한 사용자 ID 반환"""
    return session.get('user_id')

def get_current_username():
    """현재 로그인한 사용자명 반환"""
    return session.get('username')

# ============================================================================
# API 응답 헬퍼 함수들
# ============================================================================

def error_response(message, code='ERROR', status_code=400, details=None):
    """에러 응답 헬퍼 함수 (개선됨)"""
    response = {
        'success': False,
        'error': message,
        'code': code,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    if details:
        response['details'] = details
    
    # 개발 환경에서만 traceback 포함
    if status_code >= 500:
        try:
            from config.settings import FLASK_DEBUG
            if FLASK_DEBUG:
                response['traceback'] = traceback.format_exc()
        except:
            pass
    
    return jsonify(response), status_code

def success_response(data=None, message='성공', meta=None):
    """성공 응답 헬퍼 함수 (개선됨)"""
    response = {
        'success': True,
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if meta:
        response['meta'] = meta
    
    return jsonify(response)

def paginated_response(data, page, per_page, total, message='조회 성공'):
    """페이지네이션 응답 헬퍼 함수"""
    total_pages = (total + per_page - 1) // per_page
    
    meta = {
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }
    
    return success_response(data=data, message=message, meta=meta)

# ============================================================================
# 요청 데이터 검증 함수들
# ============================================================================

def validate_request_data(request_obj, required_fields=None, optional_fields=None):
    """요청 데이터 검증 함수 (개선됨)"""
    data = request_obj.get_json()
    if not data:
        return None, error_response('JSON 데이터가 필요합니다.', 'VALIDATION_ERROR', 400)
    
    # 필수 필드 검증
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            return None, error_response(
                f'필수 필드가 누락되었습니다: {", ".join(missing_fields)}', 
                'VALIDATION_ERROR', 
                400
            )
    
    # 허용된 필드만 추출 (보안)
    allowed_fields = set()
    if required_fields:
        allowed_fields.update(required_fields)
    if optional_fields:
        allowed_fields.update(optional_fields)
    
    if allowed_fields:
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
        return filtered_data, None
    
    return data, None

def validate_pagination_params():
    """페이지네이션 파라미터 검증"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:  # 최대 100개 제한
            per_page = 20
            
        return page, per_page
    except ValueError:
        return 1, 20

def validate_sort_params(allowed_fields=None):
    """정렬 파라미터 검증"""
    sort_by = request.args.get('sort_by', 'id')
    sort_order = request.args.get('sort_order', 'desc').lower()
    
    # 허용된 필드 체크
    if allowed_fields and sort_by not in allowed_fields:
        sort_by = allowed_fields[0] if allowed_fields else 'id'
    
    # 정렬 순서 체크
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    
    return sort_by, sort_order

# ============================================================================
# 데이터 타입 검증 함수들
# ============================================================================

def validate_number(value, min_val=None, max_val=None, allow_float=True):
    """숫자 검증"""
    try:
        if allow_float:
            num = float(value)
        else:
            num = int(value)
        
        if min_val is not None and num < min_val:
            return None, f"값은 {min_val} 이상이어야 합니다"
        
        if max_val is not None and num > max_val:
            return None, f"값은 {max_val} 이하여야 합니다"
        
        return num, None
    except (ValueError, TypeError):
        return None, "올바른 숫자 형식이 아닙니다"

def validate_string(value, min_length=None, max_length=None, pattern=None):
    """문자열 검증"""
    if not isinstance(value, str):
        return None, "문자열이 아닙니다"
    
    if min_length is not None and len(value) < min_length:
        return None, f"최소 {min_length}자 이상이어야 합니다"
    
    if max_length is not None and len(value) > max_length:
        return None, f"최대 {max_length}자 이하여야 합니다"
    
    if pattern and not re.match(pattern, value):
        return None, "올바른 형식이 아닙니다"
    
    return value.strip(), None

def validate_boolean(value):
    """불린 검증"""
    if isinstance(value, bool):
        return value, None
    
    if isinstance(value, str):
        if value.lower() in ['true', '1', 'yes', 'on']:
            return True, None
        elif value.lower() in ['false', '0', 'no', 'off']:
            return False, None
    
    return None, "올바른 불린 값이 아닙니다"

def validate_email(email):
    """이메일 검증"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return email.lower(), None
    return None, "올바른 이메일 형식이 아닙니다"

# ============================================================================
# 로깅 및 감사 함수들
# ============================================================================

def log_api_call(endpoint, method, user_id=None, ip_address=None, user_agent=None):
    """API 호출 로깅"""
    try:
        from config.models import SystemLog
        
        user_id = user_id or get_current_user_id()
        ip_address = ip_address or request.remote_addr
        user_agent = user_agent or request.headers.get('User-Agent', '')[:200]
        
        message = f"API 호출: {method} {endpoint}"
        if user_id:
            message += f" (사용자: {user_id})"
        
        SystemLog.log('INFO', 'API', message, {
            'endpoint': endpoint,
            'method': method,
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent
        })
        
    except Exception as e:
        print(f"API 호출 로깅 실패: {e}")

def log_config_change(config_key, old_value, new_value):
    """설정 변경 로깅"""
    try:
        from config.models import ConfigHistory
        
        user_id = get_current_user_id()
        if user_id:
            ConfigHistory.log_change(
                user_id=user_id,
                config_key=config_key,
                old_value=old_value,
                new_value=new_value,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:200]
            )
    except Exception as e:
        print(f"설정 변경 로깅 실패: {e}")

# ============================================================================
# 예외 처리 데코레이터
# ============================================================================

def handle_api_errors(f):
    """API 예외 처리 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return error_response(str(e), 'VALIDATION_ERROR', 400)
        except PermissionError as e:
            return error_response(str(e), 'PERMISSION_ERROR', 403)
        except FileNotFoundError as e:
            return error_response('리소스를 찾을 수 없습니다', 'NOT_FOUND', 404)
        except Exception as e:
            print(f"API 오류: {e}")
            return error_response('서버 내부 오류가 발생했습니다', 'INTERNAL_ERROR', 500)
    return decorated_function

# ============================================================================
# 매매 관련 검증 함수들
# ============================================================================

def validate_trading_config(config_data):
    """매매 설정 검증"""
    errors = []
    
    # trading_settings 검증
    if 'trading_settings' in config_data:
        ts = config_data['trading_settings']
        
        # 포지션 크기 검증
        if 'initial_position_size' in ts:
            size, error = validate_number(ts['initial_position_size'], min_val=0.001, max_val=10)
            if error:
                errors.append(f"초기 포지션 크기: {error}")
        
        # 임계값 검증
        if 'base_threshold' in ts:
            threshold, error = validate_number(ts['base_threshold'], min_val=100, max_val=50000, allow_float=False)
            if error:
                errors.append(f"기본 임계값: {error}")
    
    # ai_settings 검증
    if 'ai_settings' in config_data:
        ai = config_data['ai_settings']
        
        # 학습 기간 검증
        if 'ai_training_days' in ai:
            days, error = validate_number(ai['ai_training_days'], min_val=30, max_val=1095, allow_float=False)
            if error:
                errors.append(f"AI 학습 기간: {error}")
    
    if errors:
        return False, errors
    
    return True, []

# ============================================================================
# 유틸리티 함수들
# ============================================================================

def format_currency(amount, currency='KRW'):
    """통화 포맷팅"""
    if amount is None:
        return "N/A"
    
    if currency == 'KRW':
        return f"{amount:,.0f}원"
    elif currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'BTC':
        return f"{amount:.6f} BTC"
    else:
        return f"{amount:,.2f} {currency}"

def safe_float(value, default=0.0):
    """안전한 float 변환"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """안전한 int 변환"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def truncate_string(text, max_length=100, suffix="..."):
    """문자열 자르기"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix