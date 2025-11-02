from flask import Blueprint, jsonify, request
from backend.extensions import db
from backend.models import Invoice, Item, MpesaCallback

sales_bp = Blueprint("sales_bp", __name__)

# Allow both GET and OPTIONS to handle CORS preflight
@sales_bp.route("/<int:seller_id>", methods=["GET", "OPTIONS"])
def get_sales(seller_id):
    if request.method == "OPTIONS":
        # Respond to CORS preflight requests
        response = jsonify({"message": "CORS preflight successful"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response, 200

    try:
        # Fetch only invoices that belong to this seller and are marked as "paid"
        paid_invoices = (
            db.session.query(Invoice)
            .filter(Invoice.user_id == seller_id, Invoice.status == "paid")
            .all()
        )

        if not paid_invoices:
            return jsonify([]), 200  # No sales yet

        sales_data = []

        for invoice in paid_invoices:
            for invoice_item in invoice.items:
                item = Item.query.get(invoice_item.item_id)
                if not item:
                    continue

                sale_entry = {
                    "invoice_id": invoice.id,
                    "item_name": item.name,
                    "quantity": invoice_item.quantity,
                    "price": invoice_item.price,
                    "total_price": invoice_item.quantity * invoice_item.price,
                    "date_sold": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "photo_url": f"/static/uploads/{item.photo}" if item.photo else None,
                }

                # Optionally include Mpesa info
                mpesa = MpesaCallback.query.filter_by(invoice_id=invoice.id).first()
                if mpesa:
                    sale_entry["mpesa_receipt_number"] = mpesa.mpesa_receipt_number
                    sale_entry["phone_number"] = mpesa.phone_number

                sales_data.append(sale_entry)

        # Include CORS headers in normal response
        response = jsonify(sales_data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 200

    except Exception as e:
        print(f"❌ Error fetching sales: {e}")
        response = jsonify({"error": "Failed to fetch sales"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500
