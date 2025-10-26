from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import User
from werkzeug.security import generate_password_hash, check_password_hash

from backend.routes.auth_middleware import token_required
from backend.utils.email import send_email

user_bp = Blueprint("user_bp", __name__, url_prefix="/users")

VALID_ROLES = ["admin", "seller"]

# Get all users
@user_bp.route("", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "role": u.role
    } for u in users]), 200

# Get single user
@user_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }), 200

# Create user
@user_bp.route("", methods=["POST"])
def create_user():
    data = request.get_json()
    if not data.get("username") or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Username, email and password required"}), 400

    password_hash = generate_password_hash(data["password"])

    # Check if there are any users in DB
    first_user = User.query.first()
    if not first_user:
        # No users exist yet → make this user admin automatically
        role = "admin"
    else:
        # Default role is seller unless provided
        role = data.get("role", "seller")
        if role not in VALID_ROLES:
            return jsonify({"error": f"Invalid role. Must be one of {VALID_ROLES}"}), 400

    user = User(
        username=data["username"],
        email=data["email"],
        role=role,
        password_hash=password_hash
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": f"User created as {role}", "id": user.id}), 201

# Update user
@user_bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    username = data.get("username", user.username)
    email = data.get("email", user.email)
    role = data.get("role", user.role)

    if role not in VALID_ROLES:
        return jsonify({"error": f"Invalid role. Must be one of {VALID_ROLES}"}), 400

    # Safeguard: prevent downgrading the only admin
    if user.role == "admin" and role != "admin":
        admin_count = User.query.filter_by(role="admin").count()
        if admin_count <= 1:
            return jsonify({"error": "Cannot downgrade the only admin"}), 400

    user.username = username
    user.email = email
    user.role = role

    # Update password if provided
    if data.get("password"):
        user.password_hash = generate_password_hash(data["password"])

    db.session.commit()
    return jsonify({"message": "User updated"}), 200

# Delete user
@user_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Safeguard: prevent deleting the only admin
    if user.role == "admin":
        admin_count = User.query.filter_by(role="admin").count()
        if admin_count <= 1:
            return jsonify({"error": "Cannot delete the only admin"}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"}), 200

@user_bp.route("/<int:user_id>/approve", methods=["PUT"])
@token_required(roles=["admin"])
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_approved:
        return jsonify({"message": "User already approved"}), 400

    user.is_approved = True
    db.session.commit()

    # Send email notifying user of approval
    send_email(
        to=user.email,
        subject="Account Approved",
        body=f"Hi {user.username}, your account has been approved! You can now log in."
    )

    return jsonify({"message": f"User {user.username} has been approved"}), 200

