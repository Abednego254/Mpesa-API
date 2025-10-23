from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from backend.extensions import db
from backend.models import User
from datetime import timedelta

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")

VALID_ROLES = ["admin", "seller"]

# =========================
# REGISTER (SIGNUP)
# =========================
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing request data"}), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Username, email and password are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 400

    password_hash = generate_password_hash(password)

    # Assign role automatically — first user becomes admin
    first_user = User.query.first()
    role = "admin" if not first_user else "seller"

    user = User(username=username, email=email, password_hash=password_hash, role=role)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": f"User registered successfully as {role}",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 201

# =========================
# LOGIN
# =========================
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Missing request data"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Look up the user
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    # ✅ Include both identity (string) and role in claims
    additional_claims = {
        "role": user.role,
        "username": user.username,
        "email": user.email
    }

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims,
        expires_delta=timedelta(minutes=60)  # Optional: increase validity
    )

    # ✅ Optional: include refresh token if you’ll use token refreshing later
    # refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        # "refresh_token": refresh_token,  # uncomment if needed
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 200

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
