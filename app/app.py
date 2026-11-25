"""
Loan EMI Calculator - DS-584 Cloud Computing, Assignment 4
Flask + MongoDB. All configuration comes from environment variables.
"""
import math
import os
import socket
from datetime import datetime, timezone

import pymongo
from flask import Flask, jsonify, render_template, request
from pymongo import DESCENDING, MongoClient, ReadPreference
from pymongo.errors import PyMongoError

# ---------------------------------------------------------------- configuration
MONGO_URL = os.environ["MONGO_URL"]                 # connection string, set from the ConfigMap
APP_VERSION = os.environ.get("APP_VERSION", "1.0")
POD_NAME = os.environ.get("HOSTNAME", socket.gethostname())


def get_pod_ip():
    ip = os.environ.get("POD_IP")
    if ip:
        return ip
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "unknown"


POD_IP = get_pod_ip()

app = Flask(__name__)

# One client per gunicorn worker. The driver finds the PRIMARY of the replica
# set by itself and retries a write once if the PRIMARY changes.
client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=15000, connectTimeoutMS=3000)
db = client.get_default_database()
calculations = db["calculations"]
index_ready = False


def ensure_index():
    """Index on createdAt so that the history query stays fast."""
    global index_ready
    if not index_ready:
        calculations.create_index([("createdAt", DESCENDING)])
        index_ready = True


# ---------------------------------------------------------------- helpers
def calculate_emi(principal, annual_rate, months):
    r = annual_rate / 12 / 100
    factor = (1 + r) ** months
    emi = principal * r * factor / (factor - 1)
    total = emi * months
    return round(emi, 2), round(total, 2), round(total - principal, 2)


def read_inputs():
    """Read P, rate and n from a JSON body or from form fields and validate them."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = request.form
    raw_p = data.get("principal", data.get("P"))
    raw_rate = data.get("rate")
    raw_n = data.get("months", data.get("n"))

    errors = {}
    values = {}
    for name, raw in (("principal", raw_p), ("rate", raw_rate), ("months", raw_n)):
        try:
            if isinstance(raw, bool):
                raise ValueError
            value = float(raw)
        except (TypeError, ValueError):
            errors[name] = "must be a number"
            continue
        if not math.isfinite(value) or value <= 0:
            errors[name] = "must be a positive number"
        else:
            values[name] = value
    if "months" in values:
        if values["months"] != int(values["months"]):
            errors["months"] = "must be a whole number of months"
        else:
            values["months"] = int(values["months"])
    return values, errors


# ---------------------------------------------------------------- routes
@app.route("/")
def index():
    return render_template("index.html", version=APP_VERSION)


@app.route("/api/emi", methods=["POST"])
def api_emi():
    values, errors = read_inputs()
    if errors:
        return jsonify({"error": "invalid input", "details": errors}), 400

    try:
        emi, total_payment, total_interest = calculate_emi(
            values["principal"], values["rate"], values["months"])
        if not math.isfinite(emi):
            raise OverflowError
    except (OverflowError, ZeroDivisionError):
        return jsonify({"error": "invalid input", "details": {"months": "values are out of range"}}), 400
    doc = {
        "principal": values["principal"],
        "rate": values["rate"],
        "months": values["months"],
        "emi": emi,
        "servedBy": POD_NAME,
        "createdAt": datetime.now(timezone.utc),
    }
    try:
        calculations.insert_one(doc)
    except PyMongoError as exc:
        app.logger.error("insert failed: %s", exc)
        return jsonify({"error": "database not available"}), 503

    return jsonify({
        "principal": values["principal"],
        "rate": values["rate"],
        "months": values["months"],
        "emi": emi,
        "totalPayment": total_payment,
        "totalInterest": total_interest,
        "servedBy": POD_NAME,
        "podIP": POD_IP,
        "version": APP_VERSION,
    })


@app.route("/api/history")
def api_history():
    try:
        ensure_index()
        rows = list(calculations.find({}, {"_id": 0}).sort("createdAt", DESCENDING).limit(10))
    except PyMongoError as exc:
        app.logger.error("history failed: %s", exc)
        return jsonify({"error": "database not available"}), 503
    for row in rows:
        row["createdAt"] = row["createdAt"].replace(tzinfo=timezone.utc).isoformat()
    return jsonify(rows)


@app.route("/health")
def health():
    """200 only if a member of the MongoDB replica set answers a ping within 2 s."""
    try:
        with pymongo.timeout(2):
            client.admin.command("ping", read_preference=ReadPreference.PRIMARY_PREFERRED)
    except PyMongoError:
        return jsonify({"status": "unhealthy", "mongo": "unreachable", "pod": POD_NAME}), 503
    return jsonify({"status": "ok", "mongo": "reachable", "pod": POD_NAME, "version": APP_VERSION})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
