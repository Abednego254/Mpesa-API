from flask import Blueprint, request, jsonify
import requests
from datetime import datetime
import base64
import os
from backend.models import Invoice
from backend.extensions import db
from backend.extensions import db, socketio

mpesa_stk_bp = Blueprint("mpesa_stk_bp", __name__)

# M-Pesa sandbox credentials
BUSINESS_SHORTCODE = os.getenv("MPESA_SHORTCODE")
PASSKEY = os.getenv("MPESA_PASSKEY")
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")


def get_access_token():
    """Get OAuth access token from Safaricom"""
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    response.raise_for_status()
    return response.json().get("access_token")


@mpesa_stk_bp.route("/stkpush", methods=["POST"])
def stk_push():
    """Initiate STK Push"""
    data = request.get_json()
    invoice_id = data.get("invoice_id")
    phone = str(data.get("phone_number")).replace("+", "").replace(" ", "")

    if not invoice_id or not phone:
        return jsonify({"error": "Invoice ID and phone number are required"}), 400

    # Fetch invoice from DB
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    # Use invoice total as amount
    amount = int(invoice.total)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode((BUSINESS_SHORTCODE + PASSKEY + timestamp).encode()).decode()

    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": BUSINESS_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": f"INV{invoice_id}",
        "TransactionDesc": "Payment for invoice"
    }

    # Debug print to verify payload
    print("📤 STK Push Payload:", payload)

    try:
        res = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=10
        )
        res.raise_for_status()
        response_data = res.json()

        # Save CheckoutRequestID to invoice for callback tracking
        invoice.checkout_request_id = response_data.get("CheckoutRequestID")
        db.session.commit()

        print("✅ STK Push sent, invoice updated with CheckoutRequestID")
        return jsonify(response_data), res.status_code

    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

# @mpesa_stk_bp.route("/callbacks", methods=["POST"])
# def mpesa_callback():
#     """Handle M-Pesa STK Push callback"""
#     data = request.get_json()
#     print("📥 M-Pesa Callback received:", data)
#
#     body = data.get("Body", {})
#     stk_callback = body.get("stkCallback", {})
#
#     # Check if callback contains metadata (successful payment)
#     if stk_callback.get("ResultCode") == 0:
#         metadata = stk_callback.get("CallbackMetadata", {}).get("Item", [])
#         checkout_request_id = stk_callback.get("CheckoutRequestID")
#
#         # Extract values
#         mpesa_receipt = None
#         phone_number = None
#         amount = None
#         transaction_date = None
#
#         for item in metadata:
#             name = item.get("Name")
#             if name == "MpesaReceiptNumber":
#                 mpesa_receipt = item.get("Value")
#             elif name == "PhoneNumber":
#                 phone_number = str(item.get("Value"))
#             elif name == "Amount":
#                 amount = item.get("Value")
#             elif name == "TransactionDate":
#                 raw_date = str(item.get("Value"))
#                 # Convert to MySQL-compatible format
#                 transaction_date = datetime.strptime(raw_date, "%Y%m%d%H%M%S")
#
#         # Find the invoice
#         invoice = Invoice.query.filter_by(checkout_request_id=checkout_request_id).first()
#
#         if invoice:
#             invoice.status = "paid"
#             invoice.mpesa_receipt = mpesa_receipt
#             invoice.phone_number = phone_number
#             invoice.transaction_date = transaction_date
#             db.session.commit()
#             print(f"✅ Invoice {invoice.id} updated as paid.")
#         else:
#             print("⚠️ No matching invoice found for callback.")
#
#     else:
#         # Payment failed or cancelled
#         print("❌ STK Push failed or was cancelled:", stk_callback.get("ResultDesc"))
#
#     return jsonify({"ResultCode": 0, "ResultDesc": "Callback received successfully"})
#
from backend.extensions import db, socketio

@mpesa_stk_bp.route("/callbacks", methods=["POST"])
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

    # ✅ Successful payment
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

        print(f"✅ Invoice {invoice.id} marked as PAID")

        # 🔥 Emit real-time update to frontend
        socketio.emit("payment_update", {
            "invoice_id": invoice.id,
            "status": "paid",
            "message": f"Invoice {invoice.id} has been paid successfully."
        })

    # ❌ Failed / Cancelled / Insufficient funds
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
        print(f"❌ Payment failed for invoice {invoice.id}: {result_desc}")

        # 🔥 Emit to frontend
        socketio.emit("payment_update", {
            "invoice_id": invoice.id,
            "status": invoice.status,
            "message": message
        })

    return jsonify({"ResultCode": 0, "ResultDesc": "Callback received successfully"})
