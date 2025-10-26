from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from backend.extensions import db
from backend.models import User
from datetime import timedelta
from backend.utils.email import send_email
import traceback

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")

VALID_ROLES = ["admin", "seller"]

# =========================
# REGISTER (SIGNUP)
# =========================
@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        print("\n=== RAW REQUEST JSON ===")
        print(data)
        print("========================\n")

        if not data:
            return jsonify({"error": "Missing request data"}), 400

        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        print(f"Received username={username}, email={email}, password={'*' * len(password) if password else None}")

        # Validate inputs
        if not username or not email or not password:
            return jsonify({"error": "Username, email and password are required"}), 400

        # Check for duplicates
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already registered"}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already taken"}), 400

        # Hash password
        password_hash = generate_password_hash(password)

        # First user becomes admin, others are sellers
        first_user = User.query.first()
        role = "admin" if not first_user else "seller"

        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_approved=False
        )
        db.session.add(user)
        db.session.commit()

        # Send confirmation email
        try:
            send_email(
                to=email,
                subject="Account Pending Approval",
                body=f"Hi {username}, your account has been created and is awaiting admin approval. You will be notified once approved."
            )
        except Exception as mail_error:
            current_app.logger.error(f"Email sending failed: {mail_error}")
            return jsonify({
                "message": "User registered successfully, but failed to send email.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role
                },
                "email_error": str(mail_error)
            }), 201

        return jsonify({
            "message": "User registered successfully, awaiting admin approval",
            "email_notice": "A confirmation email has been sent to your inbox. Please check it for approval instructions.",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }), 201

    except Exception as e:
        # Log and return full traceback for clarity
        error_trace = traceback.format_exc()
        current_app.logger.error(f"Registration error: {e}\n{error_trace}")
        print(error_trace)
        return jsonify({
            "error": "Registration failed",
            "details": str(e)
        }), 500

# =========================
# LOGIN
# =========================
@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request data"}), 400

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid email or password"}), 401

        if not user.is_approved:
            return jsonify({"error": "Account not approved yet. Please wait for admin approval."}), 403

        additional_claims = {
            "role": user.role,
            "username": user.username,
            "email": user.email
        }

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims,
            expires_delta=timedelta(minutes=60)
        )

        return jsonify({
            "message": "Login successful",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role
            }
        }), 200

    except Exception as e:
        error_trace = traceback.format_exc()
        current_app.logger.error(f"Login error: {e}\n{error_trace}")
        return jsonify({
            "error": "Login failed",
            "details": str(e)
        }), 500


# =========================
# PROTECTED TEST ROUTE
# =========================
@auth_bp.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    return jsonify({
        "message": f"Hello user with ID {current_user_id}, you have access!",
        "user_id": current_user_id
    }), 200
