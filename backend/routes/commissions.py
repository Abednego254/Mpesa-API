# backend/routes/commissions.py
from backend.routes.auth_middleware import token_required
from flask import Blueprint, jsonify
from backend.extensions import db
from backend.models import User, Invoice, Commission

commission_bp = Blueprint("commission_bp", __name__)

@commission_bp.route("/calculate", methods=["GET"])
@token_required(role="admin")
def calculate_commissions():
    """
    Calculate total sales and 30% commissions for all users with role 'seller' or 'admin'.
    For each paid invoice, create a Commission record if one does not already exist.
    Returns a JSON summary of sellers with their total sales and commission totals.
    """
    sellers = User.query.filter(User.role.in_(["seller", "admin"])).all()
    response_list = []

    for seller in sellers:
        # Get all paid invoices for this seller
        paid_invoices = Invoice.query.filter_by(user_id=seller.id, status="paid").all()

        total_sales = 0.0
        new_commissions_total = 0.0

        for invoice in paid_invoices:
            total_sales += float(invoice.total or 0.0)

            # Check if a commission for this invoice already exists
            existing = Commission.query.filter_by(invoice_id=invoice.id).first()
            if existing:
                continue

            # Calculate commission (30%)
            commission_rate = 0.30
            commission_amount = round((float(invoice.total or 0.0) * commission_rate), 2)

            # Create and add commission record
            commission_record = Commission(
                seller_id=seller.id,
                invoice_id=invoice.id,
                amount=float(invoice.total or 0.0),
                rate=commission_rate,
                commission_amount=commission_amount,
            )
            db.session.add(commission_record)
            new_commissions_total += commission_amount

        # Commit new commission records for this seller (if any)
        try:
            if db.session.new:
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": f"Failed to save commissions for seller {seller.id}: {str(e)}"
            }), 500

        response_list.append({
            "seller_id": seller.id,
            "seller_username": seller.username,
            "role": seller.role,
            "total_sales": round(total_sales, 2),
            "commission_total_calculated": round(total_sales * 0.30, 2),
            "new_commissions_created": round(new_commissions_total, 2)
        })

    return jsonify({
        "status": "success",
        "message": "Commissions calculated (and new ones saved).",
        "sellers": response_list
    }), 200
