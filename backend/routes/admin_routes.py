from backend.routes.auth_middleware import token_required
from flask import Blueprint, jsonify
from backend.extensions import db
from backend.models import User, Invoice

admin_bp = Blueprint("admin_bp", __name__)

@admin_bp.route("/calculate_commission", methods=["GET"])
@token_required()
def calculate_commission():
    """Calculate total sales and 30% commission for each seller"""
    sellers = User.query.filter_by(role="seller").all()
    results = []

    for seller in sellers:
        total_sales = (
            db.session.query(db.func.sum(Invoice.total))
            .filter(Invoice.user_id == seller.id, Invoice.status == "paid")
            .scalar()
            or 0
        )
        commission = round(total_sales * 0.3, 2)
        results.append({
            "seller_id": seller.id,
            "seller_name": seller.username,
            "total_sales": total_sales,
            "commission": commission
        })

    return jsonify(results)
