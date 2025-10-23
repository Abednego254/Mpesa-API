from flask import Blueprint, request, jsonify
import requests
from datetime import datetime
import base64
import os

mpesa_stk_bp = Blueprint("mpesa_stk_bp", __name__)

# M-Pesa credentials from environment variables
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
    phone = data.get("phone_number")
    amount = data.get("amount")
    invoice_id = data.get("invoice_id")

    if not phone or not amount:
        return jsonify({"error": "Phone number and amount are required"}), 400

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode((BUSINESS_SHORTCODE + PASSKEY + timestamp).encode()).decode()

    try:
        access_token = get_access_token()
        print("ACCESS TOKEN:", access_token)
    except Exception as e:
        return jsonify({"error": f"Failed to get access token: {str(e)}"}), 500

    headers = {
        "Authorization": f"Bearer {access_token}",
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
        "AccountReference": f"INV{invoice_id or 0}",
        "TransactionDesc": "Payment for invoice"
    }

    try:
        res = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=10
        )
        res.raise_for_status()
        return jsonify(res.json()), res.status_code
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500
