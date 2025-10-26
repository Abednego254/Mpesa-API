# auth_middleware.py
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def token_required(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                if roles and claims.get("role") not in roles:
                    return jsonify({"error": "Unauthorized access"}), 403
            except Exception as e:
                return jsonify({"error": "Invalid or missing token"}), 401
            return fn(*args, **kwargs)
        return wrapper
    return decorator
