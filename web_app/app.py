import sys
import os
from flask import Flask, render_template, request, jsonify

# Add the parent directory to sys.path to allow importing backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.robot_controller import RobotController

app = Flask(__name__)

# Initialize the Robot Controller logic
robot = RobotController()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/toggle_chat', methods=['POST'])
def toggle_chat():
    data = request.json
    active = data.get('active', False)
    robot.set_chat_mode(active)
    return jsonify({"success": True, "active": active})

@app.route('/api/trigger_action', methods=['POST'])
def trigger_action():
    data = request.json
    btn_id = data.get('button_id')
    
    if btn_id:
        robot.trigger_action(btn_id)
        return jsonify({"success": True, "message": f"Triggered {btn_id}"})
    else:
        return jsonify({"success": False, "error": "No button ID provided"}), 400

@app.route('/api/status', methods=['GET'])
def status():
    # Mock battery for now. In real implementation, read from hardware.
    return jsonify({
        "connection": "ok",
        "battery": 87, 
        "chat_active": robot.chat_active
    })

if __name__ == '__main__':
    # Run heavily accessible
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
