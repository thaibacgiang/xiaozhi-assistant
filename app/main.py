#!/usr/bin/env python3
"""
XiaoZhi Assistant - Trợ lý AI điều khiển 2 chiều
Giao tiếp real-time với Home Assistant
"""

import os
import json
import requests
import logging
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
import eventlet
eventlet.monkey_patch()  # ← QUAN TRỌNG: Fix lỗi async

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'xiaozhi_secret_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Biến toàn cục lưu câu trả lời gần nhất
last_reply = {"reply": "Xin chào, tôi là XiaoZhi Assistant!"}

# ----------------------------------------
# LỚP ASSISTANT (giữ nguyên như code bạn đã gửi)
# ----------------------------------------
class XiaoZhiAssistant:
    def __init__(self):
        self.ha_url = "http://supervisor/core/api"
        self.ha_token = os.getenv('SUPERVISOR_TOKEN', '')
        self.language = "vi"
        self.devices = {}
        logger.info(f"🔗 Home Assistant URL: {self.ha_url}")
        logger.info(f"🔑 Token available: {bool(self.ha_token)}")
    # ... (các hàm khác giữ nguyên)
    # process_command, handle_turn_on, handle_turn_off, handle_status_check, handle_list_devices, handle_unknown_command
    # ----------------------------------------

assistant = XiaoZhiAssistant()

# ----------------------------------------
# ROUTES API
# ----------------------------------------

@app.route('/')
def index():
    """Trang chủ"""
    return jsonify({
        "name": "XiaoZhi Assistant",
        "version": "2.0.0", 
        "status": "running",
        "description": "AI Assistant điều khiển 2 chiều cho Home Assistant",
        "features": [
            "Điều khiển thiết bị bằng giọng nói",
            "Phản hồi real-time", 
            "WebSocket support",
            "Tích hợp trực tiếp với HA"
        ],
        "endpoints": {
            "GET /": "Thông tin service",
            "POST /api/command": "Gửi lệnh điều khiển",
            "GET /api/devices": "Danh sách thiết bị", 
            "GET /api/health": "Health check",
            "POST /chat": "Nhận tin nhắn từ Telegram",
            "GET /reply": "Trả câu trả lời cuối cùng"
        }
    })

@app.route('/api/command', methods=['POST'])
def api_command():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "❌ Thiếu dữ liệu JSON"}), 400
        command = data.get('command', '').strip()
        if not command:
            return jsonify({"success": False, "message": "❌ Thiếu lệnh"}), 400
        result = assistant.process_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Lỗi API command: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/devices')
def api_devices():
    try:
        devices = assistant.get_entities()
        return jsonify({"success": True, "devices": devices, "count": len(devices)})
    except Exception as e:
        logger.error(f"❌ Lỗi API devices: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/health')
def api_health():
    try:
        devices = assistant.get_entities()
        return jsonify({
            "status": "healthy",
            "ha_connected": len(devices) > 0,
            "devices_count": len(devices),
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e), "timestamp": time.time()}), 500

# ----------------------------------------
# ENDPOINT Telegram 2 chiều
# ----------------------------------------

@app.route('/chat', methods=['POST'])
def chat():
    """Nhận tin nhắn từ Telegram và xử lý"""
    global last_reply
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        if not user_msg:
            return jsonify({"reply": "❌ Tin nhắn rỗng"}), 400

        result = assistant.process_command(user_msg)
        reply = result.get("message", "🤖 Tôi không hiểu bạn nói gì")
        last_reply["reply"] = reply
        return jsonify({"reply": reply})
    except Exception as e:
        logger.error(f"❌ Lỗi /chat: {e}")
        return jsonify({"reply": f"❌ Lỗi server: {str(e)}"}), 500

@app.route('/reply', methods=['GET'])
def reply():
    """Trả về câu trả lời gần nhất để HA gửi lại Telegram"""
    global last_reply
    return jsonify(last_reply)

# ----------------------------------------
# SOCKET.IO EVENTS (giữ nguyên)
# ----------------------------------------

# ... (connect, disconnect, ping, send_command giữ nguyên)

# ----------------------------------------
# BACKGROUND TASKS (giữ nguyên)
# ----------------------------------------

# ... start_background_tasks() giữ nguyên

if __name__ == '__main__':
    logger.info("🚀 Khởi động XiaoZhi Assistant...")
    logger.info("🔧 Phiên bản: 2.0.0")
    logger.info("🌐 Port: 5050")
    logger.info("📡 WebSocket: Enabled")
    start_background_tasks()
    try:
        socketio.run(app, host='0.0.0.0', port=5050, debug=False, use_reloader=False, log_output=True)
    except Exception as e:
        logger.error(f"❌ Lỗi khởi động server: {e}")
        exit(1)
