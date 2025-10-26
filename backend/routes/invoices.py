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

# CREATE invoice with items (total calculated from DB)
@bp.route("/", methods=["POST"])
def create_invoice():
    data = request.get_json()
    items_data = data.get("items", [])

    if not items_data:
        return jsonify({"error": "Invoice must have at least one item"}), 400

    total = 0
    invoice_items = []

    # Prepare InvoiceItems and calculate total
    for item in items_data:
        db_item = Item.query.get(item["item_id"])
        if not db_item:
            return jsonify({"error": f"Item with id {item['item_id']} not found"}), 404

        quantity = item.get("quantity", 1)
        price = db_item.price
        total += price * quantity

        invoice_items.append(
            InvoiceItem(
                item_id=db_item.id,
                quantity=quantity,
                price=price
            )
        )

    if total == 0:
        return jsonify({"error": "Total cannot be zero"}), 400

    # Create Invoice
    invoice = Invoice(
        user_id=data.get("user_id"),
        total=total,  # <- now guaranteed to have a value
        status=data.get("status", "pending")
    )
    db.session.add(invoice)
    db.session.flush()  # get invoice.id

    # Assign invoice_id to invoice items and add
    for inv_item in invoice_items:
        inv_item.invoice_id = invoice.id
        db.session.add(inv_item)

    db.session.commit()
    return jsonify({"message": "Invoice created", "id": invoice.id, "total": total}), 201


# UPDATE invoice (can update items or status)
@bp.route("/<int:invoice_id>", methods=["PUT"])
def update_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    data = request.get_json()

    # Update status if provided
    inv.status = data.get("status", inv.status)

    # Update items if provided
    items_data = data.get("items")
    if items_data:
        # Delete old invoice items
        InvoiceItem.query.filter_by(invoice_id=inv.id).delete()
        total = 0
        new_items = []

        for item in items_data:
            db_item = Item.query.get(item["item_id"])
            if not db_item:
                return jsonify({"error": f"Item with id {item['item_id']} not found"}), 404

            quantity = item.get("quantity", 1)
            price = db_item.price
            total += price * quantity

            new_items.append(
                InvoiceItem(
                    invoice_id=inv.id,
                    item_id=db_item.id,
                    quantity=quantity,
                    price=price
                )
            )

        # Add new items
        for inv_item in new_items:
            db.session.add(inv_item)

        # Update total
        inv.total = total

    # Optional: update checkout_request_id
    if "checkout_request_id" in data:
        inv.checkout_request_id = data["checkout_request_id"]

    db.session.commit()
    return jsonify({"message": "Invoice updated", "total": inv.total})

# DELETE invoice
@bp.route("/<int:invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    # Delete related InvoiceItems first
    InvoiceItem.query.filter_by(invoice_id=inv.id).delete()
    db.session.delete(inv)
    db.session.commit()
    return jsonify({"message": "Invoice deleted"})
