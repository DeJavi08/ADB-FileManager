#!/usr/bin/env python3
"""
Android Backup Professional - Windows Native
FULL VERSION - Dengan semua fitur: file manager, browse output, progress real-time
"""

import subprocess
import os
import sys
import time
import json
import hashlib
import threading
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any
from collections import deque

# Flask
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# ============================================================================
# UTILITY
# ============================================================================

def format_bytes(size: int) -> str:
    if size <= 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    size = float(size)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

def format_time(seconds: float) -> str:
    if seconds <= 0:
        return "0s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

# ============================================================================
# ADB HANDLER
# ============================================================================

class ADBHandler:
    def __init__(self):
        self.device_serial = None
    
    def check_adb(self) -> bool:
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True, timeout=5, shell=True)
            return result.returncode == 0
        except:
            return False
    
    def get_devices(self) -> List[Dict]:
        devices = []
        try:
            result = subprocess.run(['adb', 'devices', '-l'], capture_output=True, text=True, timeout=5, shell=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    for line in lines[1:]:
                        if line.strip() and 'device' in line and 'offline' not in line:
                            parts = line.split()
                            devices.append({'serial': parts[0], 'state': parts[1]})
        except:
            pass
        return devices
    
    def get_device_info(self) -> Dict:
        info = {}
        try:
            cmd = ['adb']
            if self.device_serial:
                cmd.extend(['-s', self.device_serial])
            
            m_cmd = cmd + ['shell', 'getprop ro.product.model']
            result = subprocess.run(m_cmd, capture_output=True, text=True, timeout=5, shell=True)
            info['model'] = result.stdout.strip()
            
            v_cmd = cmd + ['shell', 'getprop ro.build.version.release']
            result = subprocess.run(v_cmd, capture_output=True, text=True, timeout=5, shell=True)
            info['android_version'] = result.stdout.strip()
            
            s_cmd = cmd + ['shell', 'df -h /sdcard/']
            result = subprocess.run(s_cmd, capture_output=True, text=True, timeout=5, shell=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[-1].split()
                if len(parts) >= 2:
                    info['storage_total'] = parts[1]
        except:
            pass
        return info
    
    def list_folder(self, path: str = "/sdcard/") -> Dict:
        try:
            escaped_path = path.replace("'", "'\\''")
            cmd = ['adb']
            if self.device_serial:
                cmd.extend(['-s', self.device_serial])
            cmd.extend(['shell', f'ls -la "{escaped_path}" 2>/dev/null || echo "ERROR"'])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, shell=True)
            
            if 'ERROR' in result.stdout or not result.stdout.strip():
                return {'error': f'Folder not found: {path}', 'items': []}
            
            items = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip().replace('\r', '')
                if not line or line.startswith('total'):
                    continue
                parts = line.split()
                if len(parts) < 8:
                    continue
                
                is_dir = parts[0].startswith('d') or parts[0].startswith('l')
                name = ' '.join(parts[7:]) if len(parts) > 7 else parts[-1]
                if name in ['.', '..'] or ' -> ' in name:
                    continue
                
                try:
                    size_bytes = int(parts[4])
                except:
                    size_bytes = 0
                    
                clean_path = path.rstrip('/') + '/' + name if path != '/' else '/' + name
                items.append({
                    'name': name,
                    'path': clean_path,
                    'is_dir': is_dir,
                    'size': size_bytes,
                    'size_formatted': format_bytes(size_bytes) if size_bytes > 0 else '0 B'
                })
            
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            parent = str(Path(path).parent).replace('\\', '/') if path != '/' else None
            if parent == '' or parent == '.':
                parent = '/'
            
            return {
                'current_path': path.rstrip('/') + '/',
                'parent': parent,
                'items': items,
                'item_count': len(items)
            }
        except Exception as e:
            return {'error': str(e), 'items': []}
    
    def get_folder_size(self, folder: str) -> int:
        try:
            escaped_folder = folder.replace("'", "'\\''")
            cmd = ['adb']
            if self.device_serial:
                cmd.extend(['-s', self.device_serial])
            
            m1_cmd = cmd + ['shell', f'du -s "{escaped_folder}" 2>/dev/null']
            result = subprocess.run(m1_cmd, capture_output=True, text=True, timeout=30, shell=True)
            stdout = result.stdout.strip().replace('\r', '')
            if stdout and not stdout.startswith('0'):
                size_kb = int(stdout.split()[0])
                return size_kb * 1024
            
            m2_cmd = cmd + ['shell', f'find "{escaped_folder}" -type f 2>/dev/null | wc -l']
            result = subprocess.run(m2_cmd, capture_output=True, text=True, timeout=30, shell=True)
            stdout = result.stdout.strip().replace('\r', '')
            if stdout:
                file_count = int(re.sub(r'\D', '', stdout) or '0')
                if file_count > 0:
                    return file_count * 2 * 1024 * 1024
            
            return 100 * 1024 * 1024
            
        except Exception as e:
            print(f"Error getting folder size: {e}")
            return 100 * 1024 * 1024
    
    def check_folder(self, folder: str) -> bool:
        try:
            escaped_folder = folder.replace("'", "'\\''")
            cmd = ['adb']
            if self.device_serial:
                cmd.extend(['-s', self.device_serial])
            cmd.extend(['shell', f'ls -d "{escaped_folder}" && echo "exists"'])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, shell=True)
            return 'exists' in result.stdout
        except:
            return False

    def stream_tar(self, folder: str) -> subprocess.Popen:
        escaped_folder = folder.replace("'", "'\\''")
        cmd = ['adb']
        if self.device_serial:
            cmd.extend(['-s', self.device_serial])
        cmd.extend([
            'exec-out',
            'tar',
            '-c',
            '-f', '-',
            '-C', escaped_folder,
            '.'
        ])
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=16*1024*1024, shell=True)

# ============================================================================
# BACKUP ENGINE
# ============================================================================

class BackupEngine:
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.adb = ADBHandler()
        self.is_running = False
        self.process = None
        self.extract_process = None
        self.progress = {
            'total_bytes': 0,
            'processed_bytes': 0,
            'percentage': 0,
            'status': 'idle',
            'message': '',
            'current_speed_display': '0 B/s',
            'elapsed': '0s',
            'eta': '-'
        }
        self.start_time = None
        self.speed_history = deque(maxlen=50)
    
    def start_backup(self, source: str, destination: str) -> Dict:
        if self.is_running:
            return {"error": "Backup already running"}
        
        source = source.strip()
        if not source.startswith('/'):
            source = '/' + source
        
        if not self.adb.check_adb():
            return {"error": "ADB not available. Is it installed and in PATH?"}
        
        devices = self.adb.get_devices()
        if not devices:
            return {"error": "No Android device connected"}
        
        self.adb.device_serial = devices[0]['serial']
        
        if not self.adb.check_folder(source):
            return {"error": f"Folder not found: {source}"}
        
        total_size = self.adb.get_folder_size(source)
        
        self.progress['total_bytes'] = total_size
        self.progress['processed_bytes'] = 0
        self.progress['percentage'] = 0
        self.progress['status'] = 'starting'
        
        threading.Thread(target=self._run_backup, args=(source, destination), daemon=True).start()
        
        return {"status": "started", "total_bytes": total_size}
    
    def _run_backup(self, source: str, destination: str):
        self.is_running = True
        self.start_time = time.time()
        self.progress['status'] = 'running'
        self.progress['message'] = f'Backing up {source}...'
        
        try:
            dest_path = Path(destination).resolve()
            dest_path.mkdir(parents=True, exist_ok=True)
            
            tar_path = shutil.which('tar') or "C:\\Windows\\System32\\tar.exe"
            if not os.path.exists(tar_path) and not shutil.which('tar'):
                raise RuntimeError("Native Windows tar.exe not found.")
            
            self.process = self.adb.stream_tar(source)
            
            extract_cmd = [tar_path, '-xf', '-', '-C', str(dest_path)]
            self.extract_process = subprocess.Popen(
                extract_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                bufsize=16 * 1024 * 1024,
                shell=True
            )
            
            chunk_size = 1024 * 1024
            bytes_processed = 0
            last_update = time.time()
            
            while self.is_running:
                chunk = self.process.stdout.read(chunk_size)
                if not chunk:
                    break
                
                try:
                    self.extract_process.stdin.write(chunk)
                    self.extract_process.stdin.flush()
                except (IOError, ValueError):
                    break
                    
                bytes_processed += len(chunk)
                
                now = time.time()
                if now - last_update > 0.4:
                    self.progress['processed_bytes'] = bytes_processed
                    elapsed = now - self.start_time
                    if elapsed > 0 and self.progress['total_bytes'] > 0:
                        speed = bytes_processed / elapsed
                        self.progress['current_speed_display'] = f"{format_bytes(speed)}/s"
                        self.progress['percentage'] = min(99.9, (bytes_processed / self.progress['total_bytes'] * 100))
                        self.progress['elapsed'] = format_time(elapsed)
                        if speed > 0 and self.progress['total_bytes'] > bytes_processed:
                            eta = (self.progress['total_bytes'] - bytes_processed) / speed
                            self.progress['eta'] = format_time(eta)
                    
                    if self.progress_callback:
                        self.progress_callback(self.progress.copy())
                    last_update = now
            
            try:
                self.extract_process.stdin.close()
            except:
                pass
                
            self.process.wait(timeout=5)
            self.extract_process.wait(timeout=5)
            
            if self.is_running:
                self.progress['status'] = 'completed'
                self.progress['percentage'] = 100
                self.progress['message'] = f'Backup completed! Saved to: {dest_path}'
            
        except Exception as e:
            self.progress['status'] = 'failed'
            self.progress['message'] = f'Error: {str(e)}'
        finally:
            self.is_running = False
            if self.progress_callback:
                self.progress_callback(self.progress.copy())
    
    def stop_backup(self):
        self.is_running = False
        try:
            if self.process:
                self.process.terminate()
            if self.extract_process:
                self.extract_process.terminate()
        except:
            pass
        self.progress['status'] = 'stopped'
        self.progress['message'] = 'Stopped by user'
    
    def get_status(self) -> Dict:
        status = self.progress.copy()
        status['is_running'] = self.is_running
        status['processed_bytes_formatted'] = format_bytes(self.progress.get('processed_bytes', 0))
        status['total_bytes_formatted'] = format_bytes(self.progress.get('total_bytes', 0))
        return status

# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'backup-secret'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

backup_engine = BackupEngine(progress_callback=lambda data: socketio.emit('progress_update', data))

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error loading template: {e}"

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/status')
def get_status():
    return jsonify(backup_engine.get_status())

@app.route('/api/devices')
def get_devices():
    devices = backup_engine.adb.get_devices()
    info = {}
    if devices:
        backup_engine.adb.device_serial = devices[0]['serial']
        info = backup_engine.adb.get_device_info()
    return jsonify({'devices': devices, 'info': info})

@app.route('/api/folder')
def get_folder():
    path = request.args.get('path', '/sdcard/')
    if not path.startswith('/'):
        path = '/' + path
    
    devices = backup_engine.adb.get_devices()
    if not devices:
        return jsonify({'error': 'No device connected', 'items': []})
    
    backup_engine.adb.device_serial = devices[0]['serial']
    return jsonify(backup_engine.adb.list_folder(path))

@app.route('/api/start', methods=['POST'])
def start_backup():
    data = request.json or {}
    source = data.get('source', '/sdcard/DCIM/')
    destination = data.get('destination', 'backup')
    result = backup_engine.start_backup(source, destination)
    return jsonify(result)

@app.route('/api/stop', methods=['POST'])
def stop_backup():
    backup_engine.stop_backup()
    return jsonify({'status': 'stopped'})

# ============================================================================
# OUTPUT FOLDER BROWSER (Tanpa tkinter - pakai fallback)
# ============================================================================

@app.route('/api/browse_folder', methods=['POST'])
def browse_folder():
    """Browse folder - fallback tanpa tkinter"""
    try:
        # Gunakan dialog folder sederhana via input
        # Karena tkinter sering bermasalah, kita return error dengan instruksi manual
        return jsonify({'error': 'Please type the folder path manually, or use "Open" button to create folder'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/open_folder', methods=['POST'])
def open_folder():
    """Open folder in Windows Explorer"""
    try:
        data = request.json
        path = data.get('path', '')
        
        if not path:
            return jsonify({'error': 'No path provided'})
        
        path = os.path.normpath(path)
        os.makedirs(path, exist_ok=True)
        subprocess.Popen(['explorer', path], shell=True)
        
        return jsonify({'status': 'opened', 'path': path})
        
    except Exception as e:
        return jsonify({'error': str(e)})

# ============================================================================
# SOCKET.IO
# ============================================================================

@socketio.on('connect')
def handle_connect():
    emit('progress_update', backup_engine.get_status())

@socketio.on('disconnect')
def handle_disconnect():
    pass

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Android Backup Professional - Windows Native")
    print("=" * 60)
    print("Web: http://localhost:5000")
    print("=" * 60)
    print("FITUR:")
    print("  - File manager dengan show/hide files")
    print("  - Browse output folder (manual input)")
    print("  - Buka folder output dengan tombol Open")
    print("  - Real-time progress monitoring")
    print("=" * 60)
    print()
    print("📁 Pastikan struktur folder:")
    print("   - templates/index.html")
    print("   - static/css/style.css")
    print("   - static/js/app.js")
    print()
    print("=" * 60)
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"Error starting server: {e}")
        input("Press Enter to exit...")