from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def token_required(roles=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # ✅ Allow CORS preflight requests to pass through
            if request.method == "OPTIONS":
                return jsonify({"message": "CORS preflight OK"}), 200

            try:
                # ✅ Verify token normally for other requests
                verify_jwt_in_request()
                claims = get_jwt()

                # ✅ Role-based access control
                if roles and claims.get("role") not in roles:
                    return jsonify({"error": "Unauthorized access"}), 403

            except Exception:
                return jsonify({"error": "Invalid or missing token"}), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator
