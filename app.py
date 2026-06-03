from flask import Flask, render_template, request, jsonify, session, redirect
import json
import random
import time
import requests
import os

app = Flask(__name__)
app.secret_key = "change_this_secret_key"

EMPLOYEE_FILE = "static/json/employees.json"

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

OTP_TEMPLATE_NAME = "login_otp"
OTP_TEMPLATE_LANGUAGE = "en"

otps = {}
verified_locations = {}

def load_employees():
    with open(EMPLOYEE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def find_employee(mobile):
    mobile = mobile.replace("+", "").strip()
    employees = load_employees()

    for emp in employees:
        if emp["mobile"] == mobile and emp.get("active") == True:
            return emp

    return None

def send_whatsapp_otp(mobile, otp):
    print(f"OTP for {mobile}: {otp}")

    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("WhatsApp token or phone number id missing")
        return False

    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": mobile,
        "type": "template",
        "template": {
            "name": OTP_TEMPLATE_NAME,
            "language": {
                "code": OTP_TEMPLATE_LANGUAGE
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": otp
                        }
                    ]
                },
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {
                            "type": "text",
                            "text": otp
                        }
                    ]
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    print(response.status_code)
    print(response.text)

    return response.status_code in [200, 201]

@app.route("/")
def home():
    if session.get("verified_employee") and session.get("location_allowed"):
        return render_template("index.html")

    return render_template("verify.html")

@app.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    mobile = data.get("mobile", "").replace("+", "").strip()

    employee = find_employee(mobile)

    if not employee:
        return jsonify({
            "success": False,
            "message": "Mobile number not found in employee list."
        })

    otp = str(random.randint(100000, 999999))

    otps[mobile] = {
        "otp": otp,
        "time": time.time(),
        "employee": employee
    }

    sent = send_whatsapp_otp(mobile, otp)

    if not sent:
        return jsonify({
            "success": False,
            "message": "OTP sending failed. Check Render logs."
        })

    return jsonify({
        "success": True,
        "message": "OTP sent successfully."
    })

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    mobile = data.get("mobile", "").replace("+", "").strip()
    otp = data.get("otp", "").strip()

    saved = otps.get(mobile)

    if not saved:
        return jsonify({
            "success": False,
            "message": "OTP not found. Send OTP again."
        })

    if time.time() - saved["time"] > 300:
        return jsonify({
            "success": False,
            "message": "OTP expired."
        })

    if saved["otp"] != otp:
        return jsonify({
            "success": False,
            "message": "Invalid OTP."
        })

    session["verified_employee"] = True
    session["employee"] = saved["employee"]

    return jsonify({
        "success": True,
        "message": "OTP verified successfully.",
        "employee": saved["employee"]
    })

@app.route("/save-location-permission", methods=["POST"])
def save_location_permission():
    if not session.get("verified_employee"):
        return jsonify({
            "success": False,
            "message": "Employee not verified."
        })

    employee = session.get("employee")
    data = request.get_json()

    emp_id = employee["employee_id"]

    session["location_allowed"] = True

    verified_locations[emp_id] = {
        "employee_id": emp_id,
        "name": employee["name"],
        "mobile": employee["mobile"],
        "designation": employee.get("designation", ""),
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "accuracy": data.get("accuracy"),
        "last_update": time.time()
    }

    return jsonify({
        "success": True,
        "message": "Location permission saved."
    })

@app.route("/live-location-update", methods=["POST"])
def live_location_update():
    if not session.get("verified_employee") or not session.get("location_allowed"):
        return jsonify({
            "success": False,
            "message": "Not verified or location not allowed."
        })

    employee = session.get("employee")
    data = request.get_json()

    emp_id = employee["employee_id"]

    verified_locations[emp_id] = {
        "employee_id": emp_id,
        "name": employee["name"],
        "mobile": employee["mobile"],
        "designation": employee.get("designation", ""),
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "accuracy": data.get("accuracy"),
        "last_update": time.time()
    }

    return jsonify({
        "success": True,
        "message": "Live location updated."
    })

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/admin/verified")
def admin_verified():
    return jsonify(verified_locations)

@app.route("/admin/locations")
def admin_locations():
    return jsonify(verified_locations)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
