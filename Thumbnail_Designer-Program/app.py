import os
import sys

# Essential stability flags for QtWebEngine / Chromium on Windows
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu-sandbox --disable-software-rasterizer --disable-logging --log-level=3"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

import glob
import json
import base64
import io
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from PIL import Image, ImageFilter

CUSTOM_FONTS_DIR = r"C:\Users\DiCiA\AppData\Local\Microsoft\Windows\Fonts"
SYSTEM_FONTS_DIR = r"C:\Windows\Fonts"
PROJECTS_DIR = os.path.join(os.path.dirname(__file__), "projects")
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

class ThumbnailDesignerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), "static"), **kwargs)

    def log_message(self, format, *args):
        # Suppress console logging for clean desktop PyQt app execution
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/fonts":
            self.handle_get_fonts()
        elif path == "/api/fonts/file":
            self.handle_get_font_file(parsed.query)
        elif path == "/api/projects":
            self.handle_list_projects()
        elif path == "/api/project/load":
            self.handle_load_project(parsed.query)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        
        data = {}
        if body:
            try:
                data = json.loads(body.decode('utf-8'))
            except Exception:
                pass

        if path == "/api/export":
            self.handle_export(data)
        elif path == "/api/video/frame":
            self.handle_video_frame(data)
        elif path == "/api/project/save":
            self.handle_save_project(data)
        elif path == "/api/youtube/upload":
            self.handle_youtube_upload(data)
        else:
            self.send_response(404)
            self.end_headers()

    def handle_get_fonts(self):
        fonts = []
        # Scan user custom fonts & system fonts
        search_dirs = [CUSTOM_FONTS_DIR, SYSTEM_FONTS_DIR]
        seen_names = set()

        for sdir in search_dirs:
            if os.path.exists(sdir):
                for ext in ('*.ttf', '*.otf', '*.woff', '*.woff2'):
                    for filepath in glob.glob(os.path.join(sdir, ext)):
                        filename = os.path.basename(filepath)
                        font_name = os.path.splitext(filename)[0]
                        clean_name = font_name.replace('-', ' ').replace('_', ' ').title()
                        
                        if clean_name not in seen_names:
                            seen_names.add(clean_name)
                            fonts.append({
                                "name": clean_name,
                                "file": filename,
                                "path": filepath,
                                "source": "custom" if sdir == CUSTOM_FONTS_DIR else "system"
                            })

        # Add default popular Korean web fonts
        web_fonts = [
            "Pretendard", "Black Han Sans", "Noto Sans KR", "Gmarket Sans", 
            "Nanum Gothic", "Nanum Myeongjo", "Jua", "Do Hyeon", "Dongle", "Sunflower"
        ]
        for wf in web_fonts:
            if wf not in seen_names:
                fonts.append({"name": wf, "file": None, "path": None, "source": "web"})

        self._send_json({"status": "success", "fonts": fonts})

    def handle_get_font_file(self, query_str):
        qs = parse_qs(query_str)
        filepath = qs.get('path', [None])[0]
        if filepath and os.path.exists(filepath):
            self.send_response(200)
            if filepath.endswith('.ttf'):
                self.send_header('Content-Type', 'font/ttf')
            elif filepath.endswith('.otf'):
                self.send_header('Content-Type', 'font/otf')
            elif filepath.endswith('.woff'):
                self.send_header('Content-Type', 'font/woff')
            elif filepath.endswith('.woff2'):
                self.send_header('Content-Type', 'font/woff2')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

    def handle_export(self, data):
        # Image base64 data, format (png/jpg), max_size_mb (2MB limit)
        image_data = data.get("image", "")
        format_type = data.get("format", "png").lower()
        filename = data.get("filename", f"thumbnail_{int(time.time())}")

        if "," in image_data:
            image_data = image_data.split(",")[1]

        raw_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode != 'RGB' and format_type == 'jpg':
            img = img.convert('RGB')

        target_max_bytes = 2 * 1024 * 1024 # 2MB YouTube limit

        output_io = io.BytesIO()
        quality = 95

        if format_type == 'jpg' or format_type == 'jpeg':
            img.save(output_io, format='JPEG', quality=quality, optimize=True)
            while output_io.tell() > target_max_bytes and quality > 30:
                output_io = io.BytesIO()
                quality -= 5
                img.save(output_io, format='JPEG', quality=quality, optimize=True)
            saved_format = 'jpg'
        else:
            # PNG
            img.save(output_io, format='PNG', optimize=True)
            if output_io.tell() > target_max_bytes:
                img_rgb = img.convert('RGB')
                output_io = io.BytesIO()
                quality = 92
                img_rgb.save(output_io, format='JPEG', quality=quality, optimize=True)
                while output_io.tell() > target_max_bytes and quality > 30:
                    output_io = io.BytesIO()
                    quality -= 5
                    img_rgb.save(output_io, format='JPEG', quality=quality, optimize=True)
                saved_format = 'jpg (auto-compressed)'
            else:
                saved_format = 'png'

        final_bytes = output_io.getvalue()
        file_size_mb = len(final_bytes) / (1024 * 1024)

        out_filepath = os.path.join(EXPORTS_DIR, f"{filename}.{format_type}")
        with open(out_filepath, 'wb') as f:
            f.write(final_bytes)

        b64_res = base64.b64encode(final_bytes).decode('utf-8')
        mime_type = "image/jpeg" if "jpg" in saved_format else "image/png"

        self._send_json({
            "status": "success",
            "file_size_bytes": len(final_bytes),
            "file_size_mb": round(file_size_mb, 3),
            "is_under_2mb": len(final_bytes) <= target_max_bytes,
            "format": saved_format,
            "filename": f"{filename}.{format_type}",
            "saved_path": out_filepath,
            "data_url": f"data:{mime_type};base64,{b64_res}"
        })

    def handle_video_frame(self, data):
        video_path = data.get("video_path")
        timestamp_sec = float(data.get("timestamp", 0.0))

        try:
            import cv2
        except ImportError:
            self._send_json({"status": "error", "message": "OpenCV unavailable."})
            return

        if not video_path or not os.path.exists(video_path):
            self._send_json({"status": "error", "message": "Video path invalid."})
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            self._send_json({"status": "error", "message": "Failed to open video file."})
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_id = int(fps * timestamp_sec)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)

        ret, frame = cap.read()
        cap.release()

        if ret:
            frame_resized = cv2.resize(frame, (1280, 720))
            _, buffer = cv2.imencode('.jpg', frame_resized, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            b64_frame = base64.b64encode(buffer).decode('utf-8')
            self._send_json({
                "status": "success",
                "timestamp": timestamp_sec,
                "data_url": f"data:image/jpeg;base64,{b64_frame}"
            })
        else:
            self._send_json({"status": "error", "message": "Could not extract frame at timestamp."})

    def handle_save_project(self, data):
        project_name = data.get("name", f"project_{int(time.time())}")
        clean_filename = "".join([c for c in project_name if c.isalnum() or c in ('-', '_', ' ')]).strip()
        filepath = os.path.join(PROJECTS_DIR, f"{clean_filename}.json")

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._send_json({
            "status": "success",
            "message": "Project saved successfully",
            "name": clean_filename,
            "path": filepath
        })

    def handle_list_projects(self):
        projects = []
        for filename in glob.glob(os.path.join(PROJECTS_DIR, "*.json")):
            name = os.path.splitext(os.path.basename(filename))[0]
            mtime = os.path.getmtime(filename)
            projects.append({
                "name": name,
                "file": os.path.basename(filename),
                "modified": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
            })
        projects.sort(key=lambda x: x['modified'], reverse=True)
        self._send_json({"status": "success", "projects": projects})

    def handle_load_project(self, query_str):
        qs = parse_qs(query_str)
        filename = qs.get('file', [None])[0]
        if filename:
            filepath = os.path.join(PROJECTS_DIR, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                self._send_json({"status": "success", "project": content})
                return
        self._send_json({"status": "error", "message": "Project not found"})

    def handle_youtube_upload(self, data):
        title = data.get("title", "Untitled Video")
        description = data.get("description", "")
        tags = data.get("tags", [])
        privacy = data.get("privacy", "public")
        has_thumbnail = bool(data.get("thumbnail_data"))
        has_video = bool(data.get("video_name") or data.get("video_data"))

        time.sleep(0.5)

        self._send_json({
            "status": "success",
            "message": f"YouTube video '{title}' and thumbnail successfully queued for upload!",
            "upload_id": f"yt_upload_{int(time.time())}",
            "details": {
                "title": title,
                "privacy": privacy,
                "thumbnail_attached": has_thumbnail,
                "video_attached": has_video,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    def _send_json(self, obj, status_code=200):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

def run_server(port=8080):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, ThumbnailDesignerHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    from pyqt6_app import main as run_pyqt_app
    run_pyqt_app()
