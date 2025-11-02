from flask import Blueprint, request, jsonify
from backend.extensions import db, socketio
from backend.models import Invoice, InvoiceItem, Item
from datetime import datetime

# ----------------------------
# Define Blueprint
# ----------------------------
mpesa_callback_bp = Blueprint("mpesa_callback_bp", __name__)

# ----------------------------
# M-Pesa callback route
# ----------------------------
@mpesa_callback_bp.route("/mpesa/callbacks", methods=["POST"])
def mpesa_callback():
    """Handles M-Pesa STK Push payment callback"""
    data = request.get_json()
    print("📥 M-Pesa Callback received:", data)

    body = data.get("Body", {})
    stk_callback = body.get("stkCallback", {})

    checkout_request_id = stk_callback.get("CheckoutRequestID")
    result_code = stk_callback.get("ResultCode")
    result_desc = stk_callback.get("ResultDesc", "").lower().strip()

    # Find invoice by CheckoutRequestID
    invoice = Invoice.query.filter_by(checkout_request_id=checkout_request_id).first()

    if not invoice:
        print("⚠️ No matching invoice found for callback.")
        return jsonify({
            "ResultCode": 0,
            "ResultDesc": "No matching invoice found"
        }), 200

    # Prevent double-deduction
    if invoice.status == "paid":
        print(f"ℹ️ Invoice #{invoice.id} already marked as PAID. Skipping stock deduction.")
        return jsonify({
            "ResultCode": 0,
            "ResultDesc": "Invoice already processed"
        }), 200

    # ----------------------------
    # SUCCESSFUL PAYMENT
    # ----------------------------
    if result_code == 0:
        metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        mpesa_receipt = None
        phone_number = None
        transaction_date = None

        for item in metadata:
            name = item.get("Name")
            if name == "MpesaReceiptNumber":
                mpesa_receipt = item.get("Value")
            elif name == "PhoneNumber":
                phone_number = str(item.get("Value"))
            elif name == "TransactionDate":
                raw_date = str(item.get("Value"))
                transaction_date = datetime.strptime(raw_date, "%Y%m%d%H%M%S")

        try:
            # Mark invoice as paid
            invoice.status = "paid"
            invoice.mpesa_receipt = mpesa_receipt
            invoice.phone_number = phone_number
            invoice.transaction_date = transaction_date
            db.session.add(invoice)
            print(f"✅ Invoice #{invoice.id} marked as PAID")

            # Deduct stock
            invoice_items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
            print(f"🔹 Deducting stock for {len(invoice_items)} item(s) in Invoice #{invoice.id}")

            for inv_item in invoice_items:
                item = Item.query.get(inv_item.item_id)
                if item:
                    print(f"Before: {item.name} stock = {item.stock}")
                    item.stock = max(0, item.stock - inv_item.quantity)
                    print(f"After: {item.name} stock = {item.stock}")
                    db.session.add(item)
                else:
                    print(f"⚠️ Item ID {inv_item.item_id} not found in database.")

            db.session.commit()
            print(f"💰 Stock updated successfully for Invoice #{invoice.id}")

            # Emit update to frontend
            socketio.emit("payment_update", {
                "invoice_id": invoice.id,
                "status": "paid",
                "message": f"✅ Payment received. Stock updated for Invoice #{invoice.id}",
                "mpesa_receipt": mpesa_receipt
            })

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error processing invoice #{invoice.id}: {str(e)}")
            socketio.emit("payment_update", {
                "invoice_id": invoice.id,
                "status": "error",
                "message": f"⚠️ Payment received but processing failed: {str(e)}"
            })
            return jsonify({
                "ResultCode": 1,
                "ResultDesc": "Stock update error"
            }), 500

    # ----------------------------
    # FAILED OR CANCELLED PAYMENT
    # ----------------------------
    else:
        if "cancelled" in result_desc:
            invoice.status = "cancelled"
            message = "🚫 Client cancelled the payment."
        elif "insufficient" in result_desc or result_code == 1:
            invoice.status = "failed_insufficient_funds"
            message = "⚠️ Client has insufficient funds."
        else:
            invoice.status = "failed"
            message = f"❌ Payment failed. Reason: {result_desc or 'Unknown error'}"

        db.session.add(invoice)
        db.session.commit()

        print(f"❌ Payment failed for Invoice #{invoice.id}: {message}")

        socketio.emit("payment_update", {
            "invoice_id": invoice.id,
            "status": invoice.status,
            "message": message
        })

    return jsonify({
        "ResultCode": 0,
        "ResultDesc": "Callback processed successfully"
    })
