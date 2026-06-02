from flask import Flask, render_template, request, jsonify, session
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

otps = {}
locations = {}

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
        "type": "text",
        "text": {
            "body": f"Your employee login OTP is {otp}. This OTP is valid for 5 minutes."
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    print(response.status_code)
    print(response.text)

    return response.status_code in [200, 201]

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/employee")
def employee():
    return render_template("employee.html")

@app.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    mobile = data.get("mobile", "").replace("+", "").strip()

    employee = find_employee(mobile)

    if not employee:
        return jsonify({
            "success": False,
            "message": "This mobile number is not registered as employee."
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
            "message": "OTP generated but WhatsApp sending failed. Check Render logs."
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

    session["employee"] = saved["employee"]

    return jsonify({
        "success": True,
        "message": "OTP verified.",
        "employee": saved["employee"]
    })

@app.route("/check-in", methods=["POST"])
def check_in():
    employee = session.get("employee")

    if not employee:
        return jsonify({
            "success": False,
            "message": "Please verify OTP first."
        })

    emp_id = employee["employee_id"]

    locations[emp_id] = {
        "employee_id": emp_id,
        "name": employee["name"],
        "mobile": employee["mobile"],
        "designation": employee.get("designation", ""),
        "lat": None,
        "lng": None,
        "accuracy": None,
        "checked_in": True,
        "checkin_time": time.time(),
        "last_update": None
    }

    return jsonify({
        "success": True,
        "message": "Checked in successfully. Location sharing started."
    })

@app.route("/update-location", methods=["POST"])
def update_location():
    employee = session.get("employee")

    if not employee:
        return jsonify({
            "success": False,
            "message": "Unauthorized"
        })

    emp_id = employee["employee_id"]

    if emp_id not in locations or locations[emp_id]["checked_in"] != True:
        return jsonify({
            "success": False,
            "message": "Please check in first."
        })

    data = request.get_json()

    locations[emp_id]["lat"] = data.get("lat")
    locations[emp_id]["lng"] = data.get("lng")
    locations[emp_id]["accuracy"] = data.get("accuracy")
    locations[emp_id]["last_update"] = time.time()

    return jsonify({
        "success": True,
        "message": "Location updated"
    })

@app.route("/check-out", methods=["POST"])
def check_out():
    employee = session.get("employee")

    if not employee:
        return jsonify({
            "success": False,
            "message": "Employee not logged in"
        })

    emp_id = employee["employee_id"]

    if emp_id in locations:
        locations[emp_id]["checked_in"] = False

    return jsonify({
        "success": True,
        "message": "Checked out successfully. Location sharing stopped."
    })

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/admin/locations")
def admin_locations():
    return jsonify(locations)

if __name__ == "__main__":
    app.run(debug=True)
