import sys
import os
from flask import Flask, render_template, request, jsonify, Response

# Add the parent directory to sys.path to allow importing backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.robot_controller import RobotController
from werkzeug.utils import secure_filename

# Ensure upload directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        # Add timestamp to filename to prevent caching/overwriting if desired, 
        # or keep 'photo.jpg' for 'latest'. Let's keep a history.
        import time
        timestamp = int(time.time())
        save_name = f"capture_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, save_name)
        file.save(filepath)
        
        # Also save as 'latest.jpg' for easy access
        latest_path = os.path.join(UPLOAD_FOLDER, "latest.jpg")
        import shutil
        shutil.copy2(filepath, latest_path)
        
        return jsonify({"success": True, "filename": save_name}), 200


def gen_frames():
    while True:
        frame_bytes = robot.get_latest_frame()
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            # Yield empty or placeholder? Just sleep to prevent CPU burn
            import time
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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
