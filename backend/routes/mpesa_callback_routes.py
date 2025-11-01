from flask import Blueprint, request, jsonify
from backend.extensions import db, socketio
from backend.models import Invoice
from datetime import datetime

mpesa_callback_bp = Blueprint("mpesa_callback_bp", __name__)

@mpesa_callback_bp.route("/mpesa/callbacks", methods=["POST"])
def mpesa_callback():
    data = request.get_json()
    print("📥 M-Pesa Callback received:", data)

    body = data.get("Body", {})
    stk_callback = body.get("stkCallback", {})

    checkout_request_id = stk_callback.get("CheckoutRequestID")
    result_code = stk_callback.get("ResultCode")
    result_desc = stk_callback.get("ResultDesc")

    invoice = Invoice.query.filter_by(checkout_request_id=checkout_request_id).first()

    if not invoice:
        print("⚠️ No matching invoice found for callback.")
        return jsonify({"ResultCode": 0, "ResultDesc": "No matching invoice"}), 200

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

        invoice.status = "paid"
        invoice.mpesa_receipt = mpesa_receipt
        invoice.phone_number = phone_number
        invoice.transaction_date = transaction_date
        db.session.commit()

        socketio.emit("payment_update", {
            "invoice_id": invoice.id,
            "status": "paid",
            "message": f"Invoice {invoice.id} has been paid successfully."
        })

        print(f"✅ Invoice {invoice.id} marked as PAID")

    else:
        if "cancelled" in result_desc.lower():
            invoice.status = "cancelled"
            message = "Client cancelled the payment."
        elif "insufficient" in result_desc.lower():
            invoice.status = "failed_insufficient_funds"
            message = "Client has insufficient funds."
        else:
            invoice.status = "failed"
            message = "Payment failed."

        db.session.commit()
        socketio.emit("payment_update", {
            "invoice_id": invoice.id,
            "status": invoice.status,
            "message": message
        })

        print(f"❌ Payment failed for invoice {invoice.id}: {result_desc}")

    return jsonify({"ResultCode": 0, "ResultDesc": "Callback received successfully"})
