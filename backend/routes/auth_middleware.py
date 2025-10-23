# auth_middleware.py
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def token_required(role=None):
    """
    Protects routes using JWT tokens. 
    Optionally checks for a required role ('admin' or 'seller').
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()

                # Role check (if required)
                if role and claims.get("role") != role:
                    return jsonify({"error": "Unauthorized access"}), 403

            except Exception as e:
                return jsonify({"error": "Invalid or missing token"}), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator
