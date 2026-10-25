import os
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

# Set a strong secret token for incoming request authorization
API_TOKEN = "your-secret-token-here"

@app.route('/exec', methods=['POST'])
def execute_command():
    token = request.headers.get('X-API-Token')
    if token != API_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({'error': 'No command provided'}), 400

    cmd = data['command']
    
    try:
        # Execute command safely in Termux environment
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Command timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Binds to 0.0.0.0 (all network interfaces) on port 8080
    app.run(host='0.0.0.0', port=8080)

# ==============================================================================
# IN-MEMORY TELEMETRY BUFFER & HUD DISPATCH
# ==============================================================================
telemetry_data = {
    "engine_rpm": 0.0,
    "vehicle_speed_kmh": 0,
    "battery_voltage": "0.0V",
    "status": "DISCONNECTED",
    "stamp": "R2_LINUM"
}

@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    return jsonify(telemetry_data), 200

@app.route('/telemetry', methods=['POST'])
def update_telemetry():
    global telemetry_data
    payload = request.get_json(silent=True)
    if payload:
        telemetry_data.update(payload)
        return jsonify({"status": "updated"}), 200
    return jsonify({"error": "invalid payload"}), 400

# Suppress standard HTTP request logging on terminal
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def dashboard_ui():
    with open('/data/data/com.termux/files/home/linum/templates_index.html', 'r') as f:
        return f.read()
