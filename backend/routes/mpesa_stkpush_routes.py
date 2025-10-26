from flask import Blueprint, request, jsonify
import requests
from datetime import datetime
import base64
import os
from backend.models import Invoice
from backend.extensions import db

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
