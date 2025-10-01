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

class XiaoZhiAssistant:
    def __init__(self):
        # Sử dụng URL và token chuẩn của Home Assistant Supervisor
        self.ha_url = "http://supervisor/core/api"
        self.ha_token = os.getenv('SUPERVISOR_TOKEN', '')
        self.language = "vi"
        self.devices = {}
        logger.info(f"🔗 Home Assistant URL: {self.ha_url}")
        logger.info(f"🔑 Token available: {bool(self.ha_token)}")
        
    def get_ha_headers(self):
        """Tạo headers cho API calls"""
        return {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json"
        }
    
    def call_ha_service(self, domain, service, entity_id=None, data=None):
        """Gọi service Home Assistant"""
        try:
            url = f"{self.ha_url}/services/{domain}/{service}"
            payload = data or {}
            if entity_id:
                payload["entity_id"] = entity_id
                
            logger.info(f"📞 Gọi service: {domain}.{service} trên {entity_id}")
            response = requests.post(
                url, 
                headers=self.get_ha_headers(), 
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Thành công: {domain}.{service}")
                return {"success": True, "data": response.json()}
            else:
                logger.error(f"❌ Lỗi {response.status_code}: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.exceptions.Timeout:
            logger.error("⏰ Timeout khi gọi HA service")
            return {"success": False, "error": "Timeout"}
        except requests.exceptions.ConnectionError:
            logger.error("🔌 Lỗi kết nối đến Home Assistant")
            return {"success": False, "error": "Không thể kết nối đến Home Assistant"}
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định: {e}")
            return {"success": False, "error": str(e)}
    
    def get_entities(self):
        """Lấy danh sách entities từ HA"""
        try:
            url = f"{self.ha_url}/states"
            logger.info("📋 Đang lấy danh sách entities...")
            response = requests.get(
                url, 
                headers=self.get_ha_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                entities = response.json()
                # Lọc các entity có thể điều khiển
                controllable = [
                    e for e in entities 
                    if e['entity_id'].split('.')[0] in 
                    ['light', 'switch', 'cover', 'fan', 'climate', 'media_player']
                ]
                logger.info(f"📊 Tìm thấy {len(controllable)} thiết bị điều khiển được")
                return controllable
            else:
                logger.error(f"❌ Lỗi lấy entities: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Lỗi kết nối lấy entities: {e}")
            return []
    
    def find_device_by_name(self, command, device_type):
        """Tìm device dựa trên tên trong câu lệnh"""
        entities = self.get_entities()
        
        for entity in entities:
            friendly_name = entity['attributes'].get('friendly_name', '').lower()
            entity_id = entity['entity_id']
            
            # Kiểm tra type và tên thiết bị
            if device_type in entity_id and friendly_name:
                # Tìm tên thiết bị trong câu lệnh
                for word in friendly_name.split():
                    if word in command and len(word) > 2:  # Tránh từ ngắn
                        return entity
        
        # Nếu không tìm thấy theo tên, trả về device đầu tiên
        for entity in entities:
            if device_type in entity['entity_id']:
                return entity
                
        return None
    
    def process_command(self, command_text):
        """Xử lý câu lệnh và trả kết quả 2 chiều"""
        command = command_text.lower().strip()
        logger.info(f"🎯 Xử lý lệnh: '{command}'")
        
        try:
            # Phân tích lệnh
            if any(word in command for word in ['bật', 'mở', 'turn on', 'on']):
                return self.handle_turn_on(command)
            elif any(word in command for word in ['tắt', 'đóng', 'turn off', 'off']):
                return self.handle_turn_off(command)
            elif any(word in command for word in ['trạng thái', 'kiểm tra', 'status', 'state']):
                return self.handle_status_check(command)
            elif any(word in command for word in ['danh sách', 'list', 'thiết bị', 'devices']):
                return self.handle_list_devices()
            elif any(word in command for word in ['chào', 'hello', 'xin chào', 'hi']):
                return {
                    "type": "greeting",
                    "success": True,
                    "message": "👋 Xin chào! Tôi là XiaoZhi - trợ lý AI của bạn. Tôi có thể giúp gì?",
                    "action": "greeting"
                }
            else:
                return self.handle_unknown_command(command)
                
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý command: {e}")
            return {
                "type": "error",
                "success": False,
                "message": f"❌ Lỗi hệ thống: {str(e)}"
            }
    
    def handle_turn_on(self, command):
        """Xử lý lệnh bật/mở"""
        # Tìm device phù hợp
        device = None
        if any(device_word in command for device_word in ['đèn', 'light', 'đèn điện']):
            device = self.find_device_by_name(command, 'light')
            domain = 'light'
            action_name = 'bật'
        elif any(device_word in command for device_word in ['quạt', 'fan']):
            device = self.find_device_by_name(command, 'fan') 
            domain = 'fan'
            action_name = 'bật'
        elif any(device_word in command for device_word in ['cửa', 'cover', 'rèm']):
            device = self.find_device_by_name(command, 'cover')
            domain = 'cover'
            action_name = 'mở'
        else:
            # Mặc định tìm light
            device = self.find_device_by_name(command, 'light')
            domain = 'light'
            action_name = 'bật'
        
        if device:
            friendly_name = device['attributes'].get('friendly_name', device['entity_id'])
            result = self.call_ha_service(domain, 'turn_on', device['entity_id'])
            
            return {
                "type": "control",
                "success": result["success"],
                "message": f"✅ Đã {action_name} {friendly_name}" if result["success"] else f"❌ Lỗi khi {action_name} {friendly_name}",
                "entity_id": device['entity_id'],
                "action": "turn_on",
                "device_name": friendly_name
            }
        
        return {
            "type": "error",
            "success": False,
            "message": "❌ Không tìm thấy thiết bị phù hợp để bật"
        }
    
    def handle_turn_off(self, command):
        """Xử lý lệnh tắt/đóng"""
        # Tìm device phù hợp
        device = None
        if any(device_word in command for device_word in ['đèn', 'light', 'đèn điện']):
            device = self.find_device_by_name(command, 'light')
            domain = 'light'
            action_name = 'tắt'
        elif any(device_word in command for device_word in ['quạt', 'fan']):
            device = self.find_device_by_name(command, 'fan')
            domain = 'fan' 
            action_name = 'tắt'
        elif any(device_word in command for device_word in ['cửa', 'cover', 'rèm']):
            device = self.find_device_by_name(command, 'cover')
            domain = 'cover'
            action_name = 'đóng'
        else:
            # Mặc định tìm light
            device = self.find_device_by_name(command, 'light')
            domain = 'light'
            action_name = 'tắt'
        
        if device:
            friendly_name = device['attributes'].get('friendly_name', device['entity_id'])
            result = self.call_ha_service(domain, 'turn_off', device['entity_id'])
            
            return {
                "type": "control",
                "success": result["success"],
                "message": f"✅ Đã {action_name} {friendly_name}" if result["success"] else f"❌ Lỗi khi {action_name} {friendly_name}",
                "entity_id": device['entity_id'],
                "action": "turn_off",
                "device_name": friendly_name
            }
        
        return {
            "type": "error", 
            "success": False,
            "message": "❌ Không tìm thấy thiết bị phù hợp để tắt"
        }
    
    def handle_status_check(self, command):
        """Kiểm tra trạng thái thiết bị"""
        entities = self.get_entities()
        
        if not entities:
            return {
                "type": "error",
                "success": False,
                "message": "❌ Không thể kết nối đến Home Assistant"
            }
        
        status_messages = []
        online_devices = 0
        
        for entity in entities[:8]:  # Giới hạn 8 thiết bị
            friendly_name = entity['attributes'].get('friendly_name', entity['entity_id'])
            state = entity['state']
            
            # Biểu tượng trạng thái
            icon = "🟢" if state not in ['off', 'unavailable', 'unknown'] else "🔴"
            
            status_messages.append(f"{icon} {friendly_name}: {state}")
            if state not in ['off', 'unavailable', 'unknown']:
                online_devices += 1
        
        return {
            "type": "status",
            "success": True,
            "message": f"📊 Trạng thái hệ thống ({online_devices}/{len(entities)} thiết bị online):\n" + "\n".join(status_messages),
            "devices": entities[:8],
            "online_count": online_devices,
            "total_count": len(entities)
        }
    
    def handle_list_devices(self):
        """Liệt kê thiết bị"""
        entities = self.get_entities()
        
        if not entities:
            return {
                "type": "error",
                "success": False, 
                "message": "❌ Không thể lấy danh sách thiết bị"
            }
        
        device_list = []
        for entity in entities[:10]:  # Giới hạn 10 thiết bị
            entity_type = entity['entity_id'].split('.')[0]
            friendly_name = entity['attributes'].get('friendly_name', entity['entity_id'])
            
            # Icon theo loại device
            icons = {
                'light': '💡', 'switch': '🔌', 'fan': '🌀', 
                'cover': '🪟', 'climate': '❄️', 'media_player': '📻'
            }
            icon = icons.get(entity_type, '⚙️')
            
            device_list.append(f"{icon} {friendly_name} ({entity_type})")
        
        return {
            "type": "list",
            "success": True,
            "message": f"📋 Danh sách thiết bị ({len(entities)} total):\n" + "\n".join(device_list),
            "count": len(entities)
        }
    
    def handle_unknown_command(self, command):
        """Xử lý lệnh không xác định"""
        return {
            "type": "unknown",
            "success": False,
            "message": f"🤖 Tôi không hiểu lệnh '{command}'. Thử:\n• 'bật đèn' - Bật thiết bị\n• 'tắt quạt' - Tắt thiết bị\n• 'trạng thái' - Kiểm tra hệ thống\n• 'danh sách' - Xem thiết bị"
        }

# Khởi tạo assistant
assistant = XiaoZhiAssistant()

# Routes API
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
            "WS /socket.io": "WebSocket real-time"
        }
    })

@app.route('/api/command', methods=['POST'])
def api_command():
    """API nhận lệnh điều khiển"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "type": "error",
                "success": False, 
                "message": "❌ Thiếu dữ liệu JSON"
            }), 400
            
        command = data.get('command', '').strip()
        if not command:
            return jsonify({
                "type": "error", 
                "success": False,
                "message": "❌ Thiếu lệnh (command)"
            }), 400
        
        # Xử lý lệnh
        result = assistant.process_command(command)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Lỗi API command: {e}")
        return jsonify({
            "type": "error",
            "success": False,
            "message": f"❌ Lỗi server: {str(e)}"
        }), 500

@app.route('/api/devices')
def api_devices():
    """API lấy danh sách thiết bị"""
    try:
        devices = assistant.get_entities()
        return jsonify({
            "success": True,
            "devices": devices,
            "count": len(devices)
        })
    except Exception as e:
        logger.error(f"❌ Lỗi API devices: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health')
def api_health():
    """Health check endpoint"""
    try:
        # Test kết nối HA
        devices = assistant.get_entities()
        return jsonify({
            "status": "healthy",
            "service": "XiaoZhi Assistant",
            "ha_connected": len(devices) > 0,
            "devices_count": len(devices),
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "service": "XiaoZhi Assistant",
            "error": str(e),
            "timestamp": time.time()
        }), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Khi client kết nối WebSocket"""
    client_id = request.sid
    logger.info(f"🔌 WebSocket client connected: {client_id}")
    emit('connected', {
        'message': 'Kết nối thành công với XiaoZhi Assistant!',
        'client_id': client_id,
        'timestamp': time.time()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Khi client ngắt kết nối WebSocket"""
    client_id = request.sid
    logger.info(f"🔌 WebSocket client disconnected: {client_id}")

@socketio.on('ping')
def handle_ping():
    """Ping để kiểm tra kết nối"""
    emit('pong', {'timestamp': time.time()})

@socketio.on('send_command')
def handle_command(data):
    """Nhận lệnh qua WebSocket"""
    try:
        command = data.get('command', '').strip()
        client_id = request.sid
        
        if not command:
            emit('command_result', {
                "type": "error",
                "success": False, 
                "message": "❌ Lệnh không được để trống"
            })
            return
            
        logger.info(f"🎯 WebSocket command từ {client_id}: '{command}'")
        
        # Xử lý lệnh
        result = assistant.process_command(command)
        
        # Gửi kết quả ngược lại
        emit('command_result', result)
        
        # Gửi update devices nếu là lệnh điều khiển
        if result.get('type') in ['control', 'status']:
            devices = assistant.get_entities()[:6]
            emit('devices_update', {
                'devices': devices,
                'timestamp': time.time()
            })
            
    except Exception as e:
        logger.error(f"❌ Lỗi WebSocket command: {e}")
        emit('command_result', {
            "type": "error",
            "success": False,
            "message": f"❌ Lỗi xử lý: {str(e)}"
        })

def start_background_tasks():
    """Chạy tasks nền để update trạng thái"""
    def devices_monitor():
        """Monitor và gửi update devices định kỳ"""
        logger.info("🔄 Bắt đầu devices monitor...")
        while True:
            try:
                devices = assistant.get_entities()[:6]  # 6 devices mới nhất
                socketio.emit('devices_update', {
                    'devices': devices,
                    'timestamp': time.time(),
                    'type': 'periodic_update'
                })
                time.sleep(15)  # Update mỗi 15 giây
            except Exception as e:
                logger.error(f"❌ Lỗi devices monitor: {e}")
                time.sleep(30)  # Đợi lâu hơn nếu có lỗi
    
    # Start background thread
    monitor_thread = threading.Thread(target=devices_monitor, daemon=True)
    monitor_thread.start()
    logger.info("✅ Background tasks started")

if __name__ == '__main__':
    logger.info("🚀 Khởi động XiaoZhi Assistant...")
    logger.info("🔧 Phiên bản: 2.0.0")
    logger.info("🌐 Port: 5050")
    logger.info("📡 WebSocket: Enabled")
    
    # Start background tasks
    start_background_tasks()
    
    # Start Flask-SocketIO server
    try:
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=5050, 
            debug=False,
            use_reloader=False,
            log_output=True
        )
    except Exception as e:
        logger.error(f"❌ Lỗi khởi động server: {e}")
        exit(1)