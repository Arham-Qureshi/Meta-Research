import re
from functools import wraps
from flask import request
from errors import ValidationError

def require_json(*required_fields):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            data = request.get_json(silent=True)
            if not data:
                raise ValidationError('JSON body is required.')

            missing = [f for f in required_fields if not data.get(f)]
            if missing:
                raise ValidationError(
                    f'Missing required fields: {", ".join(missing)}',
                    details={'missing_fields': missing},
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

def validate_email(email: str) -> str:
    email = (email or '').strip()
    if not email or not _EMAIL_RE.match(email):
        raise ValidationError('A valid email address is required.')
    return email

def validate_password(password: str, min_len: int = 8) -> str:
    if not password or len(password) < min_len:
        raise ValidationError(
            f'Password must be at least {min_len} characters.'
        )
    return password

def validate_string(value: str, field_name: str,
                    min_len: int = 1, max_len: int = 512) -> str:
    value = (value or '').strip()
    if len(value) < min_len:
        raise ValidationError(
            f'{field_name} must be at least {min_len} character(s).'
        )
    if len(value) > max_len:
        raise ValidationError(
            f'{field_name} must be at most {max_len} characters.'
        )
    return value

def validate_int(value, field_name: str,
                 min_val: int = None, max_val: int = None,
                 default: int = None) -> int:
    if value is None or value == '':
        if default is not None:
            return default
        raise ValidationError(f'{field_name} is required.')
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f'{field_name} must be an integer.')
    if min_val is not None and value < min_val:
        raise ValidationError(f'{field_name} must be at least {min_val}.')
    if max_val is not None and value > max_val:
        raise ValidationError(f'{field_name} must be at most {max_val}.')
    return value
