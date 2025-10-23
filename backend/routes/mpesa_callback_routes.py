from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.models import Invoice, MpesaCallback
from datetime import datetime

mpesa_callback_bp = Blueprint("mpesa_callback_bp", __name__)

@mpesa_callback_bp.route("/mpesa/callbacks", methods=["POST"])
def mpesa_callbacks():
    """Receive M-Pesa STK Push callback and update invoice accordingly"""
    data = request.get_json()
    print("📩 M-Pesa Callback Received:", data)

    try:
        # Handle both possible Safaricom formats
        stk_callback = (
            data.get("Body", {}).get("stkCallback")
            if "Body" in data
            else data.get("stkCallback", {})
        )

        if not stk_callback:
            print("⚠️ No stkCallback found in payload")
            return jsonify({"error": "Invalid callback structure"}), 400

        checkout_request_id = stk_callback.get("CheckoutRequestID")
        merchant_request_id = stk_callback.get("MerchantRequestID")
        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc")
        callback_metadata = stk_callback.get("CallbackMetadata", {})

        # Extract metadata
        amount = None
        mpesa_receipt = None
        phone_number = None
        transaction_date = None

        for item in callback_metadata.get("Item", []):
            name = item.get("Name")
            value = item.get("Value")
            if name == "Amount":
                amount = value
            elif name == "MpesaReceiptNumber":
                mpesa_receipt = value
            elif name == "PhoneNumber":
                phone_number = str(value)
            elif name == "TransactionDate":
                transaction_date = str(value)

        # Lookup invoice by CheckoutRequestID
        invoice = Invoice.query.filter_by(checkout_request_id=checkout_request_id).first()
        if not invoice:
            print(f"⚠️ Invoice not found for CheckoutRequestID: {checkout_request_id}")
            return jsonify({"error": "Invoice not found"}), 404

        # Check if callback already exists (idempotency)
        existing = MpesaCallback.query.filter_by(
            checkout_request_id=checkout_request_id
        ).first()
        if existing:
            print("ℹ️ Duplicate callback ignored.")
            return jsonify({"status": "duplicate"}), 200

        # Save callback details
        callback = MpesaCallback(
            invoice_id=invoice.id,
            merchant_request_id=merchant_request_id,
            checkout_request_id=checkout_request_id,
            result_code=result_code,
            result_desc=result_desc,
            amount=amount,
            mpesa_receipt_number=mpesa_receipt,
            phone_number=phone_number,
            transaction_date=datetime.strptime(transaction_date, "%Y%m%d%H%M%S")
            if transaction_date
            else None,
        )
        db.session.add(callback)

        # Update invoice status
        if result_code == 0:
            invoice.status = "paid"
            invoice.mpesa_receipt = mpesa_receipt
            invoice.phone_number = phone_number
            invoice.transaction_date = transaction_date
        else:
            invoice.status = "failed"

        db.session.commit()
        print(f"✅ Invoice {invoice.id} updated -> {invoice.status.upper()}")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        db.session.rollback()
        print("❌ Error processing callback:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
