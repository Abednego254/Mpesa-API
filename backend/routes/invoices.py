# backend/routes/invoices.py

from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import Invoice, InvoiceItem, Item

bp = Blueprint("invoices", __name__)

# GET all invoices
@bp.route("/", methods=["GET"])
def get_invoices():
    invoices = Invoice.query.all()
    return jsonify([{
        "id": inv.id,
        "user_id": inv.user_id,
        "total": inv.total,
        "status": inv.status,
        "created_at": inv.created_at,
        "items": [
            {"item_id": ii.item_id, "quantity": ii.quantity, "price": ii.price} 
            for ii in inv.items
        ]
    } for inv in invoices])

# GET single invoice
@bp.route("/<int:invoice_id>", methods=["GET"])
def get_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    return jsonify({
        "id": inv.id,
        "user_id": inv.user_id,
        "total": inv.total,
        "status": inv.status,
        "created_at": inv.created_at,
        "items": [
            {"item_id": ii.item_id, "quantity": ii.quantity, "price": ii.price} 
            for ii in inv.items
        ]
    })

# CREATE invoice with items
@bp.route("/", methods=["POST"])
def create_invoice():
    data = request.get_json()
    invoice = Invoice(
        user_id=data.get("user_id"),
        total=data.get("total"),
        status=data.get("status", "pending")
    )
    db.session.add(invoice)
    db.session.flush()  # get invoice.id before commit

    items_data = data.get("items", [])
    for item in items_data:
        inv_item = InvoiceItem(
            invoice_id=invoice.id,
            item_id=item["item_id"],
            quantity=item.get("quantity", 1),
            price=item["price"]
        )
        db.session.add(inv_item)

    db.session.commit()
    return jsonify({"message": "Invoice created", "id": invoice.id}), 201

# UPDATE invoice
@bp.route("/<int:invoice_id>", methods=["PUT"])
def update_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    data = request.get_json()

    inv.status = data.get("status", inv.status)
    inv.total = data.get("total", inv.total)
    if "checkout_request_id" in data:
        inv.checkout_request_id = data["checkout_request_id"]

    db.session.commit()
    return jsonify({"message": "Invoice updated"})

# DELETE invoice
@bp.route("/<int:invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    # Delete related InvoiceItems first
    InvoiceItem.query.filter_by(invoice_id=inv.id).delete()
    db.session.delete(inv)
    db.session.commit()
    return jsonify({"message": "Invoice deleted"})
