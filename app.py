from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

latest_location = {
    "lat": None,
    "lng": None
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/location")
def location_page():
    return render_template("location.html")

@app.route("/update-location", methods=["POST"])
def update_location():
    data = request.get_json()

    latest_location["lat"] = data.get("lat")
    latest_location["lng"] = data.get("lng")

    return jsonify({"status": "success"})

@app.route("/get-location")
def get_location():
    return jsonify(latest_location)

if __name__ == "__main__":
    app.run(debug=True)
