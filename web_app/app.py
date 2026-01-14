import sys
import os
from flask import Flask, render_template, request, jsonify

# Add the parent directory to sys.path to allow importing backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Add unitree_sdk2_python to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../unitree_sdk2_python')))

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
    
@app.route('/api/photo_mode', methods=['POST'])
def photo_mode():
    data = request.json
    active = data.get('active', False)
    robot.set_photo_mode(active)
    return jsonify({"success": True, "active": active})

@app.route('/api/photo_settings', methods=['GET', 'POST'])
def photo_settings():
    if request.method == 'POST':
        data = request.json
        interval = data.get('interval', 60)
        url = data.get('url', "")
        robot.update_photo_settings(interval, url)
        return jsonify({"success": True})
    else:
        return jsonify({
            "interval": robot.photo_interval,
            "url": robot.photo_url
        })

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
    # Read from hardware
    batt_status = robot.get_battery_status()
    # If invalid, maybe keep old behavior or show 0? 
    # Let's pass the whole dict or just percentage.
    # Frontend expects "battery": int
    return jsonify({
        "connection": "ok",
        "battery": batt_status.get('soc', 0), 
        "battery_detail": batt_status,
        "chat_active": robot.chat_active,
        "photo_active": robot.photo_active
    })

if __name__ == '__main__':
    # Run heavily accessible
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
