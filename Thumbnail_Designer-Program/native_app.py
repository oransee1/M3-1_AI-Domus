"""
유튜브 썸네일 디자이너 Pro v2.0 - Pure PyQt6 Desktop Edition
- 100% Native PyQt6 GUI (Zero WebEngine, Zero Chromium, Zero 0xC0000409 crashes)
- 1280x720 16:9 Standard YouTube Canvas Engine with 2X 4K Exporter
- Vector Shapes (Donut/Ring, Polygon, Star, Arrow, Badge, Rounded Rect)
- Linear & Radial Gradient Engine, Outer Stroke & Drop Shadow
- High-Performance Text Rendering with System Font Scanner (360+ Fonts)
- Video Frame Extractor & YouTube Metadata Manager
- Multi-Tab Project Manager with Native JSON Save & Load (Crash-Proof)
"""

import sys
import os

if getattr(sys, 'frozen', False):
    RESOURCE_DIR = sys._MEIPASS
    BASE_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = RESOURCE_DIR

import shutil
import glob
import json
import base64
import time
import math
import io
from PIL import Image

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    pass

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QSpinBox,
    QDoubleSpinBox, QSlider, QComboBox, QCheckBox, QTabWidget, QTabBar,
    QScrollArea, QFrame, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QColorDialog, QFontDialog, QDialog, QProgressBar,
    QStatusBar, QGroupBox, QSplitter
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QTimer, pyqtSignal, QByteArray, QBuffer, QIODevice, QUrl, QEvent, QObject
)

class KeepComboOpenFilter(QObject):
    def __init__(self, combo):
        super().__init__(combo)
        self.combo = combo
        
    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Type.MouseButtonRelease:
                view = self.combo.view()
                if view:
                    idx = view.indexAt(event.pos())
                    if idx.isValid():
                        self.combo.setCurrentIndex(idx.row())
                        return True
            elif event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                    current_row = self.combo.currentIndex()
                    if event.key() == Qt.Key.Key_Up:
                        new_row = max(0, current_row - 1)
                    else:
                        new_row = min(self.combo.count() - 1, current_row + 1)
                    self.combo.setCurrentIndex(new_row)
                    if self.combo.view() and self.combo.model():
                        self.combo.view().setCurrentIndex(self.combo.model().index(new_row, 0))
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QFontMetricsF, QFontDatabase, QImage, QPixmap,
    QPainterPath, QLinearGradient, QRadialGradient, QTransform,
    QKeySequence, QShortcut, QDesktopServices, QIcon
)
try:
    from PyQt6.QtTextToSpeech import QTextToSpeech
except ImportError:
    QTextToSpeech = None

PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
CUSTOM_FONTS_DIR = r"C:\Users\DiCiA\AppData\Local\Microsoft\Windows\Fonts"
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "client_secret.json")
if not os.path.exists(CLIENT_SECRETS_FILE):
    CLIENT_SECRETS_FILE = os.path.join(RESOURCE_DIR, "client_secret.json")
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]

os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #121218;
    color: #e4e4e7;
    font-family: 'Pretendard', 'Segoe UI', sans-serif;
}
QWidget {
    background-color: transparent;
    color: #e4e4e7;
    font-size: 12px;
}
QFrame.panel {
    background-color: #18181f;
    border: 1px solid #272732;
    border-radius: 10px;
}
QFrame.subpanel {
    background-color: #1f1f2a;
    border: 1px solid #2e2e3e;
    border-radius: 8px;
    padding: 8px;
}
QGroupBox {
    background-color: #1f1f2a;
    border: 1px solid #2e2e3e;
    border-radius: 8px;
    padding-top: 24px;
    margin-top: 10px;
    font-weight: bold;
    color: #a1a1aa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    left: 10px;
}
QPushButton {
    background-color: #272736;
    color: #f4f4f5;
    border: 1px solid #3f3f50;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #343448;
    border-color: #52526b;
}
QPushButton:pressed {
    background-color: #1a1a24;
}
QPushButton.primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0055, stop:1 #ff5500);
    color: #ffffff;
    border: none;
}
QPushButton.primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff1a6b, stop:1 #ff6b1a);
}
QPushButton.accent {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d99ff, stop:1 #00e5ff);
    color: #ffffff;
    border: none;
}
QPushButton.accent:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #26a5ff, stop:1 #1ae8ff);
}
QPushButton.tool-btn {
    background-color: #20202c;
    border: 1px solid #2e2e3e;
    border-radius: 6px;
    padding: 6px;
    min-width: 32px;
    min-height: 32px;
}
QPushButton.tool-btn:hover {
    background-color: #2e2e42;
    border-color: #0d99ff;
}
QPushButton.tool-btn:checked {
    background-color: #0d99ff;
    color: white;
    border-color: #0d99ff;
}
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #4e4e60;
    color: #ffffff;
    border: 1px solid #606075;
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: #0d99ff;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #0d99ff;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #4e4e60;
    color: #ffffff;
    border: 1px solid #606075;
    selection-background-color: #0d99ff;
}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: transparent;
    width: 16px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #272736;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d99ff, stop:1 #00e5ff);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #0d99ff;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}
QListWidget {
    background-color: #14141c;
    border: 1px solid #272732;
    border-radius: 8px;
}
QListWidget::item {
    background-color: #1c1c27;
    border: 1px solid #282837;
    border-radius: 6px;
    margin: 3px 4px;
    padding: 6px;
}
QListWidget::item:selected {
    background-color: #242b45;
    border: 1px solid #0d99ff;
}
QTabWidget::pane {
    border: 1px solid #272732;
    background: #18181f;
    border-radius: 8px;
}
QTabBar::tab {
    background: #14141c;
    color: #a1a1aa;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #18181f;
    color: #ffffff;
    font-weight: bold;
    border-bottom: 2px solid #0d99ff;
}
QScrollBar:vertical {
    border: none;
    background: #14141c;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #333346;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #4f4f69;
}
"""

import uuid

class Layer:
    def __init__(self, layer_type="shape", name="새 레이어"):
        self.id = f"layer_{uuid.uuid4().hex[:12]}"
        self.name = name
        self.type = layer_type
        self.x = 100.0
        self.y = 100.0
        self.w = 300.0
        self.h = 100.0
        self.rotation = 0.0
        self.opacity = 100
        self.blur = 0
        self.whiteness = 0
        self.locked = False
        self.visible = True
        self.flip_h = False
        self.flip_v = False

        # Shape attributes
        self.shape_type = "rect"  # rect, rounded_rect, circle, ring, polygon, star, arrow, badge
        self.corner_radius = 16
        self.inner_radius_ratio = 0.6
        self.sides = 6
        self.fill_type = "solid"  # solid, linear_gradient, radial_gradient
        self.fill_color = "#0d99ff"
        self.fill_transparent = False
        self.gradient_color1 = "#ff0055"
        self.gradient_color2 = "#00e5ff"
        self.gradient_angle = 45
        self.stroke_color = "#ffffff"
        self.stroke_width = 0
        self.shadow_color = "#000000"
        self.shadow_x = 4
        self.shadow_y = 4
        self.shadow_blur = 10
        self.shadow_enabled = False

        # Text attributes
        self.text = "유튜브 썸네일 타이틀"
        self.font_family = "Pretendard"
        self.font_size = 64
        self.font_weight = 700
        self.text_align = "left"

        # Image attributes
        self.image_path = ""
        self.pixmap = None
        self.image_base64 = ""

    def copy(self):
        new_l = Layer(self.type, self.name + " (복사본)")
        d = self.to_dict()
        new_l.from_dict(d)
        new_l.id = f"layer_{int(time.time() * 1000)}"
        new_l.x += 20
        new_l.y += 20
        return new_l

    def to_dict(self):
        if self.type == "image" and self.pixmap and not self.image_base64:
            try:
                buf = QByteArray()
                qbuf = QBuffer(buf)
                qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
                self.pixmap.save(qbuf, "PNG")
                self.image_base64 = "data:image/png;base64," + base64.b64encode(buf.data()).decode("utf-8")
            except Exception:
                pass
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "rotation": self.rotation,
            "opacity": self.opacity,
            "blur": self.blur,
            "whiteness": self.whiteness,
            "locked": self.locked,
            "visible": self.visible,
            "flip_h": self.flip_h,
            "flip_v": self.flip_v,
            "shape_type": self.shape_type,
            "corner_radius": self.corner_radius,
            "inner_radius_ratio": self.inner_radius_ratio,
            "sides": self.sides,
            "fill_type": self.fill_type,
            "fill_color": self.fill_color,
            "fill_transparent": self.fill_transparent,
            "gradient_color1": self.gradient_color1,
            "gradient_color2": self.gradient_color2,
            "gradient_angle": self.gradient_angle,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "shadow_color": self.shadow_color,
            "shadow_x": self.shadow_x,
            "shadow_y": self.shadow_y,
            "shadow_blur": self.shadow_blur,
            "shadow_enabled": self.shadow_enabled,
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "text_align": self.text_align,
            "image_path": self.image_path,
            "image_base64": self.image_base64
        }

    def from_dict(self, d):
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)
        if self.image_base64 and not self.pixmap:
            try:
                raw = base64.b64decode(self.image_base64.split(",")[-1])
                qimg = QImage()
                qimg.loadFromData(raw)
                self.pixmap = QPixmap.fromImage(qimg)
            except Exception:
                pass


class LayerListWidget(QListWidget):
    order_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QAbstractItemView
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
    def dropEvent(self, event):
        self.blockSignals(True)
        super().dropEvent(event)
        self.blockSignals(False)
        self.order_changed.emit()


class ThumbnailCanvasWidget(QWidget):
    layer_selected = pyqtSignal(object)
    history_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Standard 16:9 Canvas
        self.canvas_width = 1280
        self.canvas_height = 720
        self.zoom = 0.65

        # Layers and active state
        self.layers = []
        self.selected_layer = None
        self.active_tab_name = "프로젝트 1"

        # Overlays
        self.show_safe_zone = True
        self.show_grid = False

        # Transform & Interaction state
        self.is_dragging = False
        self.is_resizing = False
        self.is_rotating = False
        self.active_handle = None
        self.drag_start_pos = QPointF()
        self.initial_layer_rect = QRectF()
        self.initial_layer_rot = 0.0

        # Undo / Redo History Stack
        self.history = []
        self.history_index = -1
        self.clipboard = None

        self.setup_initial_layers()
        self.push_state()

    def setup_initial_layers(self):
        # 1. Background
        bg = Layer("shape", "배경 (Background)")
        bg.x, bg.y, bg.w, bg.h = 0, 0, 1280, 720
        bg.fill_type = "linear_gradient"
        bg.gradient_color1 = "#0f172a"
        bg.gradient_color2 = "#1e1b4b"
        bg.gradient_angle = 45
        bg.locked = True

        # 2. Point Ring/Donut
        ring = Layer("shape", "포인트 링 (Ring)")
        ring.shape_type = "ring"
        ring.x, ring.y, ring.w, ring.h = 820, 100, 360, 360
        ring.fill_type = "linear_gradient"
        ring.gradient_color1 = "#ff0055"
        ring.gradient_color2 = "#3b82f6"
        ring.stroke_color = "#ffffff"
        ring.stroke_width = 4
        ring.opacity = 90

        # 3. Main Title Text
        t1 = Layer("text", "메인 타이틀")
        t1.text = "유튜브 썸네일 디자이너"
        t1.font_family = "Black Han Sans"
        t1.font_size = 80
        t1.x, t1.y, t1.w, t1.h = 80, 180, 800, 120
        t1.fill_color = "#facc15"
        t1.stroke_color = "#000000"
        t1.stroke_width = 8
        t1.shadow_enabled = True
        t1.shadow_x, t1.shadow_y, t1.shadow_blur = 6, 6, 12

        # 4. Subtitle Text
        t2 = Layer("text", "서브 타이틀")
        t2.text = "고클릭률 썸네일 원클릭 템플릿 & 4K 지원"
        t2.font_family = "Pretendard"
        t2.font_size = 40
        t2.font_weight = 700
        t2.x, t2.y, t2.w, t2.h = 80, 320, 750, 70
        t2.fill_color = "#ffffff"
        t2.stroke_color = "#000000"
        t2.stroke_width = 4

        self.layers = [bg, ring, t1, t2]
        self.selected_layer = t1
        self.multi_selected_layers = [t1]
        self.multi_initial_rects = {}
        self.clipboard_layers = []

    def push_state(self):
        state = [l.to_dict() for l in self.layers]
        self.history = self.history[:self.history_index + 1]
        self.history.append(state)
        self.history_index = len(self.history) - 1
        self.history_changed.emit()

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_state(self.history[self.history_index])

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_state(self.history[self.history_index])

    def restore_state(self, state):
        new_layers = []
        for d in state:
            l = Layer(d.get("type", "shape"))
            l.from_dict(d)
            new_layers.append(l)
        self.layers = new_layers
        if self.selected_layer:
            matching = [l for l in self.layers if l.id == self.selected_layer.id]
            self.selected_layer = matching[0] if matching else (self.layers[-1] if self.layers else None)
        self.layer_selected.emit(self.selected_layer)
        self.update()

    def add_layer(self, layer):
        self.layers.append(layer)
        self.selected_layer = layer
        self.push_state()
        self.layer_selected.emit(self.selected_layer)
        self.update()

    def delete_selected_layer(self):
        if self.selected_layer and not self.selected_layer.locked:
            self.layers = [l for l in self.layers if l.id != self.selected_layer.id]
            self.selected_layer = self.layers[-1] if self.layers else None
            self.push_state()
            self.layer_selected.emit(self.selected_layer)
            self.update()

    def duplicate_selected_layer(self):
        if self.selected_layer:
            dup = self.selected_layer.copy()
            self.add_layer(dup)

    def copy_selected_layer(self):
        if hasattr(self, 'multi_selected_layers') and self.multi_selected_layers:
            self.clipboard_layers = [l.copy() for l in self.multi_selected_layers if not l.locked]
        elif self.selected_layer and not self.selected_layer.locked:
            self.clipboard_layers = [self.selected_layer.copy()]

    def paste_selected_layer(self):
        if hasattr(self, 'clipboard_layers') and self.clipboard_layers:
            new_selection = []
            for l in self.clipboard_layers:
                dup = l.copy()
                dup.x += 20
                dup.y += 20
                self.layers.append(dup)
                new_selection.append(dup)
            
            self.clipboard_layers = new_selection
            self.multi_selected_layers = new_selection
            self.selected_layer = new_selection[-1]
            self.push_state()
            self.layer_selected.emit(self.selected_layer)
            self.update()

    def select_all_layers(self):
        self.multi_selected_layers = [l for l in self.layers if not l.locked and l.visible]
        if self.multi_selected_layers:
            self.selected_layer = self.multi_selected_layers[-1]
            self.multi_initial_rects = {l: QRectF(l.x, l.y, l.w, l.h) for l in self.multi_selected_layers}
        else:
            self.selected_layer = None
        self.layer_selected.emit(self.selected_layer)
        self.update()

    def move_selected_up(self):
        self._nudge_selected(0, -1)
        
    def move_selected_down(self):
        self._nudge_selected(0, 1)
        
    def move_selected_left(self):
        self._nudge_selected(-1, 0)
        
    def move_selected_right(self):
        self._nudge_selected(1, 0)
        
    def _nudge_selected(self, dx, dy):
        if not hasattr(self, 'multi_selected_layers') or not self.multi_selected_layers:
            return
            
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            dx *= 10
            dy *= 10

        moved = False
        for l in self.multi_selected_layers:
            if not l.locked:
                l.x += dx
                l.y += dy
                moved = True
                
        if moved:
            self.layer_selected.emit(self.selected_layer)
            self.update()

    def get_canvas_origin(self):
        vw = self.width()
        vh = self.height()
        cw = self.canvas_width * self.zoom
        ch = self.canvas_height * self.zoom
        ox = max(20.0, (vw - cw) / 2.0)
        oy = max(20.0, (vh - ch) / 2.0)
        return QPointF(ox, oy)

    def screen_to_canvas(self, pos):
        orig = self.get_canvas_origin()
        cx = (pos.x() - orig.x()) / self.zoom
        cy = (pos.y() - orig.y()) / self.zoom
        return QPointF(cx, cy)

    def canvas_to_screen(self, pos):
        orig = self.get_canvas_origin()
        sx = orig.x() + pos.x() * self.zoom
        sy = orig.y() + pos.y() * self.zoom
        return QPointF(sx, sy)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # 1. Dark workspace background
        painter.fillRect(self.rect(), QColor("#121218"))

        orig = self.get_canvas_origin()
        cw = self.canvas_width * self.zoom
        ch = self.canvas_height * self.zoom
        canvas_screen_rect = QRectF(orig.x(), orig.y(), cw, ch)

        # Canvas Outer Drop Shadow
        painter.save()
        shadow_rect = canvas_screen_rect.adjusted(-2, -2, 2, 2)
        painter.setPen(QPen(QColor(0, 0, 0, 80), 3))
        painter.drawRect(shadow_rect)
        painter.restore()

        # Canvas Base
        painter.fillRect(canvas_screen_rect, QColor("#000000"))

        # Setup coordinate system for Canvas
        painter.save()
        painter.translate(orig)
        painter.scale(self.zoom, self.zoom)

        # Clip rendering to Canvas
        canvas_rect = QRectF(0, 0, self.canvas_width, self.canvas_height)
        painter.setClipRect(canvas_rect)

        # 2. Render Layers Bottom to Top
        for l in self.layers:
            if not l.visible:
                continue
            self.draw_layer(painter, l)

        # 3. Grid Overlay
        if self.show_grid:
            painter.save()
            normal_pen = QPen(QColor(255, 255, 255, 80), 1, Qt.PenStyle.DashLine)
            center_pen = QPen(QColor(255, 255, 255, 200), 1, Qt.PenStyle.SolidLine)
            
            for x in range(0, self.canvas_width, 40):
                if x == self.canvas_width // 2:
                    painter.setPen(center_pen)
                else:
                    painter.setPen(normal_pen)
                painter.drawLine(x, 0, x, self.canvas_height)
                
            for y in range(0, self.canvas_height, 40):
                if y == self.canvas_height // 2:
                    painter.setPen(center_pen)
                else:
                    painter.setPen(normal_pen)
                painter.drawLine(0, y, self.canvas_width, y)
            painter.restore()

        # 4. YouTube Safe Zone (Bottom-Right Duration Timestamp 12:34)
        if self.show_safe_zone:
            painter.save()
            sz_w, sz_h = 240, 90
            sz_x = self.canvas_width - sz_w - 24
            sz_y = self.canvas_height - sz_h - 24
            sz_rect = QRectF(sz_x, sz_y, sz_w, sz_h)

            painter.setPen(QPen(QColor("#ff0055"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(255, 0, 85, 40)))
            painter.drawRoundedRect(sz_rect, 10, 10)

            pill_rect = QRectF(sz_x + sz_w - 110, sz_y + sz_h - 46, 96, 36)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 220)))
            painter.drawRoundedRect(pill_rect, 6, 6)

            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, "12:34")

            painter.setPen(QColor("#ff7799"))
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
            painter.drawText(QRectF(sz_x + 10, sz_y + 10, sz_w - 20, 24), Qt.AlignmentFlag.AlignLeft, "⚠️ YouTube Safe Zone")
            painter.restore()

        painter.restore()

        # 5. Selection Bounding Box & Handles
        if not hasattr(self, 'multi_selected_layers'):
            self.multi_selected_layers = [self.selected_layer] if self.selected_layer else []
        elif self.selected_layer and self.selected_layer not in self.multi_selected_layers:
            self.multi_selected_layers = [self.selected_layer]

        for layer in self.multi_selected_layers:
            if layer and layer.visible:
                self.draw_selection_handles(painter, layer, orig)

    def draw_layer(self, painter, l):
        painter.save()
        painter.setOpacity(l.opacity / 100.0)

        cx = l.x + l.w / 2.0
        cy = l.y + l.h / 2.0

        painter.translate(cx, cy)
        if l.rotation != 0:
            painter.rotate(l.rotation)
        if l.flip_h or l.flip_v:
            painter.scale(-1 if l.flip_h else 1, -1 if l.flip_v else 1)
        painter.translate(-l.w / 2.0, -l.h / 2.0)

        local_rect = QRectF(0, 0, l.w, l.h)

        if l.type == "shape":
            self.draw_shape_layer(painter, l, local_rect)
        elif l.type == "text":
            self.draw_text_layer(painter, l, local_rect)
        elif l.type == "image":
            self.draw_image_layer(painter, l, local_rect)

        painter.restore()

    def get_shape_path(self, l, r):
        path = QPainterPath()
        st = l.shape_type

        if st == "rect":
            path.addRect(r)
        elif st == "rounded_rect":
            cr = min(l.corner_radius, min(r.width(), r.height()) / 2.0)
            path.addRoundedRect(r, cr, cr)
        elif st == "circle":
            path.addEllipse(r)
        elif st == "ring":
            outer = QPainterPath()
            outer.addEllipse(r)
            inner_ratio = max(0.1, min(0.9, l.inner_radius_ratio))
            iw = r.width() * inner_ratio
            ih = r.height() * inner_ratio
            ix = r.x() + (r.width() - iw) / 2.0
            iy = r.y() + (r.height() - ih) / 2.0
            inner = QPainterPath()
            inner.addEllipse(QRectF(ix, iy, iw, ih))
            path = outer.subtracted(inner)
        elif st == "polygon":
            sides = max(3, min(12, l.sides))
            cx, cy = r.center().x(), r.center().y()
            rx, ry = r.width() / 2.0, r.height() / 2.0
            for i in range(sides):
                angle = (i * 2 * math.pi / sides) - (math.pi / 2)
                px = cx + rx * math.cos(angle)
                py = cy + ry * math.sin(angle)
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            path.closeSubpath()
        elif st == "star":
            cx, cy = r.center().x(), r.center().y()
            rx, ry = r.width() / 2.0, r.height() / 2.0
            points = 5
            for i in range(points * 2):
                radius_x = rx if i % 2 == 0 else rx * 0.45
                radius_y = ry if i % 2 == 0 else ry * 0.45
                angle = (i * math.pi / points) - (math.pi / 2)
                px = cx + radius_x * math.cos(angle)
                py = cy + radius_y * math.sin(angle)
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            path.closeSubpath()
        elif st == "arrow":
            w, h = r.width(), r.height()
            path.moveTo(0, h * 0.35)
            path.lineTo(w * 0.6, h * 0.35)
            path.lineTo(w * 0.6, h * 0.1)
            path.lineTo(w, h * 0.5)
            path.lineTo(w * 0.6, h * 0.9)
            path.lineTo(w * 0.6, h * 0.65)
            path.lineTo(0, h * 0.65)
            path.closeSubpath()
        elif st == "badge":
            cr = min(14.0, min(r.width(), r.height()) / 2.0)
            path.addRoundedRect(r, cr, cr)
        else:
            path.addRect(r)

        return path

    def get_fill_brush(self, l, r):
        if getattr(l, 'fill_transparent', False):
            return QBrush(Qt.BrushStyle.NoBrush)
            
        if l.fill_type == "linear_gradient":
            rad = math.radians(l.gradient_angle)
            cx, cy = r.center().x(), r.center().y()
            dx = math.cos(rad) * r.width() / 2.0
            dy = math.sin(rad) * r.height() / 2.0
            grad = QLinearGradient(cx - dx, cy - dy, cx + dx, cy + dy)
            grad.setColorAt(0.0, QColor(l.gradient_color1))
            grad.setColorAt(1.0, QColor(l.gradient_color2))
            return QBrush(grad)
        elif l.fill_type == "radial_gradient":
            cx, cy = r.center().x(), r.center().y()
            grad = QRadialGradient(cx, cy, max(r.width(), r.height()) / 2.0)
            grad.setColorAt(0.0, QColor(l.gradient_color1))
            grad.setColorAt(1.0, QColor(l.gradient_color2))
            return QBrush(grad)
        else:
            return QBrush(QColor(l.fill_color))

    def draw_shape_layer(self, painter, l, r):
        path = self.get_shape_path(l, r)

        if l.shadow_enabled and l.shadow_blur > 0:
            painter.save()
            shadow_path = QPainterPath(path)
            shadow_path.translate(l.shadow_x, l.shadow_y)
            sc = QColor(l.shadow_color)
            sc.setAlpha(160)
            painter.fillPath(shadow_path, QBrush(sc))
            painter.restore()

        if l.stroke_width > 0:
            pen = QPen(QColor(l.gradient_color2), l.stroke_width * 2)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.strokePath(path, pen)

        brush = self.get_fill_brush(l, r)
        painter.fillPath(path, brush)

    def draw_text_layer(self, painter, l, r):
        font = QFont(l.font_family, l.font_size)
        font.setWeight(QFont.Weight(l.font_weight))
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        painter.setFont(font)

        fm = QFontMetricsF(font)
        
        bw = fm.horizontalAdvance(l.text) if hasattr(fm, 'horizontalAdvance') else fm.boundingRect(l.text).width()
        bh = fm.height()
        l.w = float(bw + 10)
        l.h = float(bh + 10)
        r.setWidth(l.w)
        r.setHeight(l.h)

        path = QPainterPath()
        baseline_y = r.y() + fm.ascent() + 5
        path.addText(r.x() + 5, baseline_y, font, l.text)

        if l.shadow_enabled:
            painter.save()
            shadow_path = QPainterPath(path)
            shadow_path.translate(l.shadow_x, l.shadow_y)
            sc = QColor(l.shadow_color)
            sc.setAlpha(180)
            painter.fillPath(shadow_path, QBrush(sc))
            painter.restore()

        if l.stroke_width > 0:
            pen = QPen(QColor(l.stroke_color), l.stroke_width * 2)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.strokePath(path, pen)

        painter.fillPath(path, QBrush(QColor(l.fill_color)))

    def draw_image_layer(self, painter, l, r):
        if l.pixmap and not l.pixmap.isNull():
            if not hasattr(l, '_last_blur') or l._last_blur != l.blur or not hasattr(l, '_blurred_pixmap'):
                l._last_blur = l.blur
                if l.blur == 0:
                    l._blurred_pixmap = l.pixmap
                else:
                    from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect
                    effect = QGraphicsBlurEffect()
                    # QGraphicsBlurEffect radius is strong; max 100 on slider -> 20.0 radius is plenty.
                    effect.setBlurRadius(l.blur / 5.0)
                    
                    scene = QGraphicsScene()
                    item = QGraphicsPixmapItem(l.pixmap)
                    item.setGraphicsEffect(effect)
                    scene.addItem(item)
                    
                    res = QPixmap(l.pixmap.size())
                    res.fill(Qt.GlobalColor.transparent)
                    ptr = QPainter(res)
                    # Use Antialiasing for better quality
                    ptr.setRenderHint(QPainter.RenderHint.Antialiasing)
                    scene.render(ptr)
                    ptr.end()
                    
                    l._blurred_pixmap = res
            
            painter.drawPixmap(r.toRect(), l._blurred_pixmap)
            
            if hasattr(l, 'whiteness') and l.whiteness > 0:
                painter.fillRect(r, QColor(255, 255, 255, int((l.whiteness / 100.0) * 255)))
        else:
            painter.setPen(QPen(QColor("#3f3f50"), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor("#1e1e28")))
            painter.drawRect(r)
            painter.setPen(QColor("#a1a1aa"))
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, "🖼️ 이미지 없음")

    def draw_selection_handles(self, painter, l, orig):
        painter.save()
        cx = orig.x() + (l.x + l.w / 2.0) * self.zoom
        cy = orig.y() + (l.y + l.h / 2.0) * self.zoom
        sw = l.w * self.zoom
        sh = l.h * self.zoom

        painter.translate(cx, cy)
        if l.rotation != 0:
            painter.rotate(l.rotation)
        painter.translate(-sw / 2.0, -sh / 2.0)

        # Bounding border
        painter.setPen(QPen(QColor("#0d99ff"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(0, 0, sw, sh))

        # 8 Resize Handles
        handle_size = 10
        half = handle_size / 2.0
        handles = [
            (0, 0), (sw / 2.0, 0), (sw, 0),
            (sw, sh / 2.0), (sw, sh), (sw / 2.0, sh),
            (0, sh), (0, sh / 2.0)
        ]

        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor("#0d99ff"), 2))
        for hx, hy in handles:
            painter.drawRect(QRectF(hx - half, hy - half, handle_size, handle_size))

        # Rotation Handle
        rot_handle_y = -24
        painter.drawLine(QPointF(sw / 2.0, 0), QPointF(sw / 2.0, rot_handle_y))
        painter.drawEllipse(QRectF(sw / 2.0 - half, rot_handle_y - half, handle_size, handle_size))

        # Dimensions Badge
        badge_text = f"{int(l.w)} × {int(l.h)}"
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(13, 153, 255, 230)))
        badge_w, badge_h = 70, 20
        badge_rect = QRectF(sw / 2.0 - badge_w / 2.0, sh + 8, badge_w, badge_h)
        painter.drawRoundedRect(badge_rect, 4, 4)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        painter.restore()

    def mousePressEvent(self, event):
        pos = event.position()
        c_pos = self.screen_to_canvas(pos)
        is_ctrl_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        
        if not hasattr(self, 'multi_selected_layers'):
            self.multi_selected_layers = []

        if self.selected_layer and not self.selected_layer.locked:
            handle = self.get_handle_at(pos, self.selected_layer)
            if handle == "rot":
                self.is_rotating = True
                self.drag_start_pos = pos
                self.initial_layer_rot = self.selected_layer.rotation
                self.multi_initial_rects = {l: QRectF(l.x, l.y, l.w, l.h) for l in self.multi_selected_layers}
                return
            elif handle:
                self.is_resizing = True
                self.active_handle = handle
                self.drag_start_pos = c_pos
                self.initial_layer_rect = QRectF(self.selected_layer.x, self.selected_layer.y, self.selected_layer.w, self.selected_layer.h)
                self.multi_initial_rects = {l: QRectF(l.x, l.y, l.w, l.h) for l in self.multi_selected_layers}
                return

        clicked_layer = None
        for l in reversed(self.layers):
            if l.visible and not l.locked:
                rect = QRectF(l.x, l.y, l.w, l.h)
                if rect.contains(c_pos):
                    clicked_layer = l
                    break

        if clicked_layer:
            if is_ctrl_pressed:
                if clicked_layer in self.multi_selected_layers:
                    self.multi_selected_layers.remove(clicked_layer)
                    self.selected_layer = self.multi_selected_layers[-1] if self.multi_selected_layers else None
                else:
                    self.multi_selected_layers.append(clicked_layer)
                    self.selected_layer = clicked_layer
            else:
                if clicked_layer not in self.multi_selected_layers:
                    self.multi_selected_layers = [clicked_layer]
                self.selected_layer = clicked_layer

            self.is_dragging = True
            self.drag_start_pos = c_pos
            self.initial_layer_rect = QRectF(self.selected_layer.x, self.selected_layer.y, self.selected_layer.w, self.selected_layer.h)
            self.multi_initial_rects = {l: QRectF(l.x, l.y, l.w, l.h) for l in self.multi_selected_layers}
            self.layer_selected.emit(self.selected_layer)
        else:
            if not is_ctrl_pressed:
                self.multi_selected_layers = []
                self.selected_layer = None
                self.layer_selected.emit(None)

        self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        c_pos = self.screen_to_canvas(pos)

        if self.selected_layer and not self.selected_layer.locked:
            handle = self.get_handle_at(pos, self.selected_layer)
            if handle in ("nw", "se"):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif handle in ("ne", "sw"):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif handle in ("n", "s"):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif handle in ("e", "w"):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif handle == "rot":
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        if self.is_dragging and self.selected_layer:
            dx = c_pos.x() - self.drag_start_pos.x()
            dy = c_pos.y() - self.drag_start_pos.y()
            
            nx = self.initial_layer_rect.x() + dx
            ny = self.initial_layer_rect.y() + dy

            if self.show_grid:
                # Snap to 40px grid spacing
                snapped_x = round(nx / 40.0) * 40.0
                snapped_y = round(ny / 40.0) * 40.0
                dx = snapped_x - self.initial_layer_rect.x()
                dy = snapped_y - self.initial_layer_rect.y()
                nx = self.initial_layer_rect.x() + dx
                ny = self.initial_layer_rect.y() + dy

            # Magnetic snap based on the main selected layer
            if abs(nx + self.selected_layer.w / 2.0 - self.canvas_width / 2.0) < 10:
                dx = (self.canvas_width / 2.0 - self.selected_layer.w / 2.0) - self.initial_layer_rect.x()
            if abs(ny + self.selected_layer.h / 2.0 - self.canvas_height / 2.0) < 10:
                dy = (self.canvas_height / 2.0 - self.selected_layer.h / 2.0) - self.initial_layer_rect.y()

            for l in self.multi_selected_layers:
                init_r = self.multi_initial_rects.get(l)
                if init_r:
                    l.x = round(init_r.x() + dx)
                    l.y = round(init_r.y() + dy)

            self.layer_selected.emit(self.selected_layer)
            self.update()

        elif self.is_resizing and self.selected_layer:
            dx = c_pos.x() - self.drag_start_pos.x()
            dy = c_pos.y() - self.drag_start_pos.y()
            h = self.active_handle

            for l in self.multi_selected_layers:
                r = self.multi_initial_rects.get(l)
                if not r: continue
                
                if "e" in h:
                    l.w = max(20, round(r.width() + dx))
                if "s" in h:
                    l.h = max(20, round(r.height() + dy))
                if "w" in h:
                    new_w = max(20, round(r.width() - dx))
                    l.x = r.right() - new_w
                    l.w = new_w
                if "n" in h:
                    new_h = max(20, round(r.height() - dy))
                    l.y = r.bottom() - new_h
                    l.h = new_h

            self.layer_selected.emit(self.selected_layer)
            self.update()

        elif self.is_rotating and self.selected_layer:
            orig = self.get_canvas_origin()
            cx = orig.x() + (self.selected_layer.x + self.selected_layer.w / 2.0) * self.zoom
            cy = orig.y() + (self.selected_layer.y + self.selected_layer.h / 2.0) * self.zoom
            angle = math.degrees(math.atan2(pos.y() - cy, pos.x() - cx)) + 90
            self.selected_layer.rotation = round(angle % 360)
            self.layer_selected.emit(self.selected_layer)
            self.update()

    def mouseReleaseEvent(self, event):
        if self.is_dragging or self.is_resizing or self.is_rotating:
            self.push_state()
        self.is_dragging = False
        self.is_resizing = False
        self.is_rotating = False
        self.active_handle = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def get_handle_at(self, screen_pos, l):
        orig = self.get_canvas_origin()
        cx = orig.x() + (l.x + l.w / 2.0) * self.zoom
        cy = orig.y() + (l.y + l.h / 2.0) * self.zoom
        sw = l.w * self.zoom
        sh = l.h * self.zoom

        t = QTransform()
        t.translate(cx, cy)
        if l.rotation != 0:
            t.rotate(l.rotation)
        t.translate(-sw / 2.0, -sh / 2.0)
        inv_t, ok = t.inverted()
        if not ok:
            return None

        local_p = inv_t.map(screen_pos)
        x, y = local_p.x(), local_p.y()
        tol = 12

        if abs(x - sw / 2.0) < tol and abs(y - (-24)) < tol:
            return "rot"
        if abs(x) < tol and abs(y) < tol:
            return "nw"
        if abs(x - sw / 2.0) < tol and abs(y) < tol:
            return "n"
        if abs(x - sw) < tol and abs(y) < tol:
            return "ne"
        if abs(x - sw) < tol and abs(y - sh / 2.0) < tol:
            return "e"
        if abs(x - sw) < tol and abs(y - sh) < tol:
            return "se"
        if abs(x - sw / 2.0) < tol and abs(y - sh) < tol:
            return "s"
        if abs(x) < tol and abs(y - sh) < tol:
            return "sw"
        if abs(x) < tol and abs(y - sh / 2.0) < tol:
            return "w"

        return None

    def export_qimage(self, scale=1.0):
        w = int(self.canvas_width * scale)
        h = int(self.canvas_height * scale)
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(0, 0, 0, 255))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.scale(scale, scale)

        for l in self.layers:
            if l.visible:
                self.draw_layer(painter, l)

        painter.end()
        return img


class VideoFrameExtractorDialog(QDialog):
    frame_captured = pyqtSignal(QPixmap, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎬 동영상 프레임 캡처 (Video Frame Extractor)")
        self.resize(800, 560)
        self.cap = None
        self.video_path = ""
        self.total_frames = 0
        self.fps = 30.0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        self.open_btn = QPushButton("📂 동영상 파일 열기 (MP4, MOV, MKV, AVI)")
        self.open_btn.clicked.connect(self.open_video_file)
        top_bar.addWidget(self.open_btn)

        self.file_label = QLabel("선택된 파일 없음")
        self.file_label.setStyleSheet("color: #a1a1aa;")
        top_bar.addWidget(self.file_label)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.preview_label = QLabel("동영상 파일을 열어 원하는 프레임을 캡처하세요.")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background: #000; border-radius: 8px; color: #71717a; font-size: 14px;")
        self.preview_label.setMinimumHeight(340)
        layout.addWidget(self.preview_label, 1)

        time_bar = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.seek_frame)
        time_bar.addWidget(self.slider)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("font-weight: bold; min-width: 90px;")
        time_bar.addWidget(self.time_label)
        layout.addLayout(time_bar)

        bot_bar = QHBoxLayout()
        self.capture_btn = QPushButton("📸 현재 프레임을 썸네일 레이어로 캡처")
        self.capture_btn.setProperty("class", "primary")
        self.capture_btn.setEnabled(False)
        self.capture_btn.clicked.connect(self.do_capture)
        bot_bar.addWidget(self.capture_btn)

        bot_bar.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        bot_bar.addWidget(close_btn)
        layout.addLayout(bot_bar)

    def open_video_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "동영상 파일 선택", "", "Video Files (*.mp4 *.mov *.avi *.mkv *.webm);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not filepath:
            return

        try:
            import cv2
            self.cap = cv2.VideoCapture(filepath)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "오류", "동영상 파일을 열 수 없습니다.")
                return

            self.video_path = filepath
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.file_label.setText(os.path.basename(filepath))

            self.slider.setRange(0, max(1, self.total_frames - 1))
            self.slider.setEnabled(True)
            self.capture_btn.setEnabled(True)
            self.seek_frame(0)
        except ImportError:
            QMessageBox.warning(self, "안내", "OpenCV(cv2) 라이브러리가 필요합니다.")

    def seek_frame(self, frame_idx):
        if not self.cap:
            return
        import cv2
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(
                self.preview_label.width(), self.preview_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(pix)

            sec = frame_idx / self.fps
            tot_sec = self.total_frames / self.fps
            self.time_label.setText(f"{int(sec//60):02d}:{int(sec%60):02d} / {int(tot_sec//60):02d}:{int(tot_sec%60):02d}")

    def do_capture(self):
        if not self.cap:
            return
        import cv2
        ret, frame = self.cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
            pix = QPixmap.fromImage(qimg)
            self.frame_captured.emit(pix, os.path.basename(self.video_path))
            QMessageBox.information(self, "성공", "캡처된 영상 프레임이 썸네일 레이어로 추가되었습니다!")
            self.close()

class YouTubeUploadDialog(QDialog):
    def __init__(self, canvas_widget, parent=None):
        super().__init__(parent)
        self.canvas = canvas_widget
        self.setWindowTitle("🚀 유튜브 스튜디오 업로드 (YouTube Studio Direct)")
        self.resize(850, 740)
        self.tts = None
        if QTextToSpeech is not None:
            try:
                self.tts = QTextToSpeech(self)
            except Exception:
                self.tts = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Left: Thumbnail Preview
        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("<b>선택된 썸네일 이미지</b>"))
        self.thumb_preview = QLabel()
        self.thumb_preview.setFixedSize(280, 158)
        self.thumb_preview.setStyleSheet("background: #000; border-radius: 6px; border: 1px solid #333;")
        self.thumb_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left_box.addWidget(self.thumb_preview)

        size_badge = QLabel("업로드할 썸네일 미리보기")
        size_badge.setStyleSheet("color: #34c759; font-size: 11px; font-weight: bold;")
        left_box.addWidget(size_badge)
        
        left_box.addSpacing(10)
        left_box.addWidget(QLabel("<b>🤖 Gemini AI (제목/설명 추천 도우미)</b>"))
        
        api_key_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("여기에 무료 Gemini API Key 입력 (필수)")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.api_key_file = os.path.join(BASE_DIR, "gemini_api_key.txt")
        if os.path.exists(self.api_key_file):
            try:
                with open(self.api_key_file, "r", encoding="utf-8") as f:
                    saved_key = f.read().strip()
                    if saved_key:
                        self.api_key_input.setText(saved_key)
            except Exception:
                pass
                
        api_key_layout.addWidget(self.api_key_input)
        
        self.api_key_save_btn = QPushButton("저장")
        self.api_key_save_btn.clicked.connect(self.save_api_key)
        api_key_layout.addWidget(self.api_key_save_btn)
        
        left_box.addLayout(api_key_layout)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMinimumHeight(280)
        self.chat_history.setPlaceholderText("Gemini AI에게 유튜브 제목과 설명 추천을 요청해보세요!\n예: 이 영상의 조회수 폭발하는 어그로 제목 3개 추천해줘.")
        self.chat_history.setStyleSheet("background: #1e1e28; border: 1px solid #3f3f50; border-radius: 4px; padding: 4px; color: #ffffff;")
        left_box.addWidget(self.chat_history)

        chat_input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("메시지 입력...")
        self.chat_input.returnPressed.connect(self.send_gemini_message)
        chat_input_layout.addWidget(self.chat_input)

        self.chat_send_btn = QPushButton("전송")
        self.chat_send_btn.clicked.connect(self.send_gemini_message)
        chat_input_layout.addWidget(self.chat_send_btn)
        
        left_box.addLayout(chat_input_layout)

        grid.addLayout(left_box, 0, 0, 10, 1)

        # Right: Video Metadata Form
        grid.addWidget(QLabel("<b>업로드할 영상 선택 (Video)</b>"), 0, 1)
        self.video_combo = QComboBox()
        grid.addWidget(self.video_combo, 1, 1)

        grid.addWidget(QLabel("<b>업로드할 썸네일 선택 (Thumbnail)</b>"), 2, 1)
        self.thumb_combo = QComboBox()
        self.thumb_combo.currentTextChanged.connect(self.update_thumb_preview)
        grid.addWidget(self.thumb_combo, 3, 1)

        grid.addWidget(QLabel("<b>동영상 제목 (Title)</b>"), 4, 1)
        self.title_input = QLineEdit("유튜브 썸네일 디자인 제작 프로젝트")
        grid.addWidget(self.title_input, 5, 1)

        grid.addWidget(QLabel("<b>동영상 설명 (Description)</b>"), 6, 1)
        self.desc_input = QTextEdit("유튜브 썸네일 디자이너 Pro로 제작된 고화질 썸네일입니다.")
        self.desc_input.setMaximumHeight(80)
        grid.addWidget(self.desc_input, 7, 1)

        grid.addWidget(QLabel("<b>공개 상태 (Privacy)</b>"), 8, 1)
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["공개 (Public)", "일부공개 (Unlisted)", "비공개 (Private)"])
        grid.addWidget(self.privacy_combo, 9, 1)
        
        grid.addWidget(QLabel("<b>재생목록 (Playlist) - 선택</b>"), 10, 1)
        self.playlist_input = QLineEdit()
        self.playlist_input.setPlaceholderText("재생목록 이름을 입력하세요 (없으면 자동 생성)")
        grid.addWidget(self.playlist_input, 11, 1)
        
        self.populate_combos()

        layout.addLayout(grid)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #0d99ff; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons
        btn_bar = QHBoxLayout()
        self.upload_btn = QPushButton("🚀 유튜브 업로드 실행")
        self.upload_btn.setProperty("class", "primary")
        self.upload_btn.clicked.connect(self.start_upload)
        btn_bar.addWidget(self.upload_btn)

        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.close)
        btn_bar.addWidget(cancel_btn)
        layout.addLayout(btn_bar)

    def populate_combos(self):
        self.video_combo.addItem("선택 안 함 (영상 없음)")
        self.thumb_combo.addItem("현재 작업중인 캔버스 (기본)")
        
        if os.path.exists(EXPORTS_DIR):
            for f in sorted(os.listdir(EXPORTS_DIR), reverse=True):
                if f.lower().endswith(('.mp4', '.avi')):
                    self.video_combo.addItem(f)
                elif f.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.thumb_combo.addItem(f)
                    
        self.update_thumb_preview(self.thumb_combo.currentText())

    def update_thumb_preview(self, text):
        if text == "현재 작업중인 캔버스 (기본)":
            qimg = self.canvas.export_qimage(0.3)
            self.thumb_preview.setPixmap(QPixmap.fromImage(qimg).scaled(280, 158, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        elif text and text != "선택 안 함 (영상 없음)":
            filepath = os.path.join(EXPORTS_DIR, text)
            if os.path.exists(filepath):
                pix = QPixmap(filepath)
                self.thumb_preview.setPixmap(pix.scaled(280, 158, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def start_upload(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "입력 오류", "동영상 제목을 입력하세요.")
            return

        vid_file = self.video_combo.currentText()
        if vid_file == "선택 안 함 (영상 없음)":
            QMessageBox.warning(self, "입력 오류", "업로드할 영상 파일을 선택하세요.")
            return

        video_path = os.path.join(EXPORTS_DIR, vid_file)
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "오류", "선택한 영상 파일을 찾을 수 없습니다.")
            return

        self.upload_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.status_label.setText("유튜브 보안 인증 진행 중... 브라우저 창에서 계정 및 채널을 선택해주세요.")
        QApplication.processEvents()

        try:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                QMessageBox.critical(self, "오류", f"client_secret.json 파일이 존재하지 않습니다.\n{CLIENT_SECRETS_FILE}\n구글 클라우드 콘솔에서 OAuth 2.0 클라이언트 ID를 생성하고 다운로드하여 위 경로에 넣어주세요.")
                self.upload_btn.setEnabled(True)
                self.progress_bar.setVisible(False)
                self.progress_bar.setValue(0)
                self.status_label.setText("")
                return

            # 구글 계정/채널 선택 강제 프롬프트
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, YOUTUBE_SCOPES)
                credentials = flow.run_local_server(port=0, prompt='select_account')
            except ValueError as e:
                if "web or installed app" in str(e).lower():
                    raise ValueError("잘못된 유형의 인증 파일입니다. (현재 '서비스 계정' 키가 사용됨)\n구글 클라우드 콘솔에서 반드시 'OAuth 2.0 클라이언트 ID (데스크톱 앱)'를 생성하여 다운로드한 후 교체해주세요.")
                raise e
            youtube = build("youtube", "v3", credentials=credentials)

            # 채널 이름 확인
            channel_req = youtube.channels().list(part="snippet", mine=True)
            channel_res = channel_req.execute()
            channel_name = "알 수 없음"
            if channel_res.get("items"):
                channel_name = channel_res["items"][0]["snippet"]["title"]

            self.status_label.setText(f"'{channel_name}' 채널로 전송 중...")
            self.progress_bar.setValue(40)
            QApplication.processEvents()

            desc = self.desc_input.toPlainText().strip()
            privacy_map = {
                "공개 (Public)": "public",
                "일부공개 (Unlisted)": "unlisted",
                "비공개 (Private)": "private"
            }
            privacy_status = privacy_map.get(self.privacy_combo.currentText(), "public")

            request_body = {
                "snippet": {
                    "categoryId": "22",
                    "title": title,
                    "description": desc,
                    "tags": ["썸네일", "디자이너"]
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }

            media_file = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media_file)
            
            self.progress_bar.setValue(70)
            QApplication.processEvents()
            
            response = request.execute()
            video_id = response["id"]

            # 재생목록 처리
            playlist_name = self.playlist_input.text().strip()
            if playlist_name:
                self.progress_bar.setValue(80)
                self.status_label.setText(f"재생목록 '{playlist_name}' 확인 중...")
                QApplication.processEvents()
                
                try:
                    # 재생목록 검색
                    playlists_req = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
                    playlists_res = playlists_req.execute()
                    
                    playlist_id = None
                    for item in playlists_res.get("items", []):
                        if item["snippet"]["title"] == playlist_name:
                            playlist_id = item["id"]
                            break
                    
                    # 재생목록이 없으면 새로 생성
                    if not playlist_id:
                        self.status_label.setText(f"재생목록 '{playlist_name}' 생성 중...")
                        QApplication.processEvents()
                        pl_req = youtube.playlists().insert(
                            part="snippet,status",
                            body={
                                "snippet": {
                                    "title": playlist_name
                                },
                                "status": {
                                    "privacyStatus": privacy_status
                                }
                            }
                        )
                        pl_res = pl_req.execute()
                        playlist_id = pl_res["id"]
                    
                    # 동영상을 재생목록에 추가
                    self.status_label.setText("재생목록에 동영상 추가 중...")
                    QApplication.processEvents()
                    youtube.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": playlist_id,
                                "resourceId": {
                                    "kind": "youtube#video",
                                    "videoId": video_id
                                }
                            }
                        }
                    ).execute()
                except Exception as pe:
                    print(f"재생목록 등록 실패: {pe}")

            self.progress_bar.setValue(90)
            self.status_label.setText("썸네일 등록 중...")
            QApplication.processEvents()

            # 썸네일 등록
            thm_file = self.thumb_combo.currentText()
            thumb_path = None
            if thm_file == "현재 작업중인 캔버스 (기본)":
                # 고해상도 FHD 1080p (1.5x, 1920x1080)로 선명하게 렌더링하고 유튜브 2MB 한도 내로 최적화
                qimg = self.canvas.export_qimage(1.5)
                thumb_path = os.path.join(EXPORTS_DIR, "temp_upload_thumb.jpg")
                quality = 95
                qimg.save(thumb_path, "JPG", quality)
                # 유튜브 썸네일 최대 파일 크기는 2MB 제한
                while os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 1.95 * 1024 * 1024 and quality > 70:
                    quality -= 5
                    qimg.save(thumb_path, "JPG", quality)
            elif thm_file != "선택 안 함 (영상 없음)":
                thumb_path = os.path.join(EXPORTS_DIR, thm_file)

            if thumb_path and os.path.exists(thumb_path):
                try:
                    thumb_media = MediaFileUpload(thumb_path, mimetype='image/jpeg', resumable=True)
                    youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                except Exception as te:
                    print(f"썸네일 업로드 실패: {te}")

            self.progress_bar.setValue(100)
            self.status_label.setText("업로드 완료!")
            
            msg = f"🎉 유튜브 채널 업로드 완료!\n\n"
            msg += f"• 선택된 채널: {channel_name}\n"
            msg += f"• 동영상 제목: {title}\n"
            msg += f"• 공개 상태: {self.privacy_combo.currentText()}\n"
            if playlist_name:
                msg += f"• 재생목록: {playlist_name}\n"
            msg += "\n💡 [유튜브 고화질(HD) 처리 필독 안내]:\n"
            msg += "• 유튜브는 업로드 직후 저화질(SD 360p) 버전을 먼저 스트리밍 제공합니다.\n"
            msg += "• 고화질(HD 1080p) 인코딩은 유튜브 서버에서 약 5~15분 동안 백그라운드로 처리됩니다.\n"
            msg += "• 업로드 직후 재생 시 일시적으로 흐려 보일 수 있으니, 유튜브 영상 우측 하단 ⚙️ 설정 아이콘에 [HD] 마크가 활성화될 때까지 잠시 기다려주세요!"

            # TTS 음성 재생 (QMessageBox가 떠 있는 동안 자연스럽게 배경에서 재생됩니다)
            if self.tts:
                try:
                    self.tts.say("축하합니다. 유튜브 채널에 업로드 되었습니다.")
                except Exception:
                    pass

            QMessageBox.information(
                self, "업로드 성공", msg
            )
            self.close()

        except Exception as e:
            self.upload_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.status_label.setText("업로드 실패")
            QMessageBox.critical(self, "유튜브 업로드 오류", f"업로드 중 오류가 발생했습니다:\n{str(e)}")

    def save_api_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "입력 오류", "저장할 API Key를 입력해주세요.")
            return
        try:
            with open(self.api_key_file, "w", encoding="utf-8") as f:
                f.write(key)
            QMessageBox.information(self, "저장 성공", "Gemini API Key가 성공적으로 저장되었습니다.\n다음 번 실행 시 자동으로 불러옵니다.")
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"API Key 저장에 실패했습니다:\n{str(e)}")

    def send_gemini_message(self):
        api_key = self.api_key_input.text().strip()
        user_msg = self.chat_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "API 키 필요", "Gemini API 키를 먼저 입력해주세요.")
            return
        if not user_msg:
            return
            
        self.chat_history.append(f"<b style='color:#0d99ff;'>나:</b> {user_msg}<br>")
        self.chat_input.clear()
        self.chat_send_btn.setEnabled(False)
        self.chat_input.setEnabled(False)
        
        from PyQt6.QtCore import QThread, pyqtSignal
        import urllib.request
        import urllib.error
        import json
        
        class GeminiWorker(QThread):
            result_ready = pyqtSignal(str)
            error_occurred = pyqtSignal(str)
            
            def __init__(self, key, prompt):
                super().__init__()
                self.key = key
                self.prompt = prompt
                
            def run(self):
                try:
                    models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.key}"
                    req_models = urllib.request.Request(models_url)
                    with urllib.request.urlopen(req_models) as response:
                        data_models = json.loads(response.read().decode('utf-8'))
                        
                    candidate_models = []
                    for m in data_models.get('models', []):
                        name = m.get('name', '')
                        methods = m.get('supportedGenerationMethods', [])
                        if 'generateContent' in methods and 'gemini' in name.lower() and 'flash' in name.lower():
                            if 'embedding' not in name.lower() and 'tts' not in name.lower() and 'audio' not in name.lower() and 'image' not in name.lower():
                                candidate_models.append(name)
                    
                    if not candidate_models:
                        candidate_models = ["models/gemini-flash-latest", "models/gemini-3.5-flash"]
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0'
                    }
                    data = json.dumps({
                        "contents": [{"parts": [{"text": self.prompt}]}]
                    }).encode('utf-8')

                    success = False
                    last_error = "사용 가능한 모델이 없습니다."
                    
                    for model_name in candidate_models:
                        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={self.key}"
                        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
                        try:
                            with urllib.request.urlopen(req) as response:
                                res_data = json.loads(response.read().decode('utf-8'))
                                text = res_data['candidates'][0]['content']['parts'][0]['text']
                                self.result_ready.emit(text)
                                success = True
                                break
                        except Exception as e:
                            last_error = f"[{model_name}] {str(e)}"
                            continue
                            
                    if not success:
                        self.error_occurred.emit(f"모든 버전 연결 실패: {last_error}")
                except Exception as e:
                    self.error_occurred.emit(str(e))
                    
        self.gemini_worker = GeminiWorker(api_key, user_msg)
        self.gemini_worker.result_ready.connect(self.on_gemini_reply)
        self.gemini_worker.error_occurred.connect(self.on_gemini_error)
        self.gemini_worker.start()

    def on_gemini_reply(self, text):
        formatted_text = text.replace('\n', '<br>')
        self.chat_history.append(f"<b style='color:#34c759;'>Gemini:</b> {formatted_text}<br><br>")
        self.chat_send_btn.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.chat_input.setFocus()

    def on_gemini_error(self, err):
        self.chat_history.append(f"<b style='color:#ff3b30;'>오류:</b> {err}<br><br>")
        self.chat_send_btn.setEnabled(True)
        self.chat_input.setEnabled(True)
        self.chat_input.setFocus()


class NativeThumbnailDesignerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("유튜브 썸네일 디자이너 Pro (Native PyQt6 v2.0)")
        self.setWindowIcon(QIcon(os.path.join(RESOURCE_DIR, "icon.png")))
        self.resize(1520, 940)
        self.setMinimumSize(1100, 720)

        self.load_fonts()

        # Canvas Widget
        self.canvas = ThumbnailCanvasWidget(self)
        self.canvas.layer_selected.connect(self.on_layer_selected)
        self.canvas.history_changed.connect(self.on_history_changed)

        self.init_ui()
        self.setup_shortcuts()

        # Initial Inspector sync
        self.on_layer_selected(self.canvas.selected_layer)

    def load_fonts(self):
        if os.path.exists(CUSTOM_FONTS_DIR):
            for ext in ("*.ttf", "*.otf"):
                for font_file in glob.glob(os.path.join(CUSTOM_FONTS_DIR, ext)):
                    QFontDatabase.addApplicationFont(font_file)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # 1. TOP HEADER & MULTI-TAB BAR
        top_bar = self.create_top_header()
        main_layout.addLayout(top_bar)

        # 2. MAIN 3-COLUMN WORKSPACE
        workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        workspace_splitter.setHandleWidth(8)
        workspace_splitter.setStyleSheet("QSplitter::handle { background-color: #272732; border-radius: 4px; margin: 4px 2px; }")

        # LEFT SIDEBAR (Tabs: Layers, Templates, Fonts)
        left_panel = self.create_left_panel()
        left_panel.setMinimumWidth(220)
        workspace_splitter.addWidget(left_panel)

        # CENTER CANVAS & FLOATING TOOLBAR
        center_widget = QWidget()
        center_box = QVBoxLayout(center_widget)
        center_box.setContentsMargins(0, 0, 0, 0)
        center_box.setSpacing(8)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setStyleSheet("background-color: #121218; border: 1px solid #272732; border-radius: 8px;")
        center_box.addWidget(self.scroll_area, 1)

        toolbar = self.create_bottom_toolbar()
        center_box.addWidget(toolbar)

        workspace_splitter.addWidget(center_widget)

        # RIGHT PROPERTIES INSPECTOR
        right_panel = self.create_right_inspector()
        right_panel.setMinimumWidth(260)
        workspace_splitter.addWidget(right_panel)
        
        workspace_splitter.setSizes([290, 800, 340])

        main_layout.addWidget(workspace_splitter, 1)

        # STATUS BAR
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("준비 완료 (Native PyQt6 Engine - Crash Proof)")
        self.status_label.setStyleSheet("color: #a1a1aa; font-weight: 500;")
        self.status_bar.addWidget(self.status_label)

    def create_top_header(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        logo_btn = QPushButton("🎨 Thumbnail Studio Pro")
        logo_btn.setStyleSheet("font-weight: 900; font-size: 14px; color: #ffffff; background: transparent; border: none;")
        layout.addWidget(logo_btn)

        save_proj_btn = QPushButton("💾 프로젝트 저장")
        save_proj_btn.clicked.connect(self.save_project)
        layout.addWidget(save_proj_btn)

        open_proj_btn = QPushButton("📂 프로젝트 열기")
        open_proj_btn.clicked.connect(self.load_project)
        layout.addWidget(open_proj_btn)

        # Multi-Tab Bar (Figma Style)
        self.tab_bar = QTabBar()
        self.tab_bar.setTabsClosable(True)
        self.tab_bar.addTab("기능테스트02")
        self.tab_bar.addTab("도형편집")
        self.tab_bar.tabCloseRequested.connect(self.close_tab)
        self.tab_bar.currentChanged.connect(self.switch_tab)
        self.tab_bar.tabBarDoubleClicked.connect(self.rename_tab)
        layout.addWidget(self.tab_bar)

        add_tab_btn = QPushButton("+")
        add_tab_btn.setFixedSize(28, 28)
        add_tab_btn.setToolTip("새 프로젝트 탭 추가")
        add_tab_btn.clicked.connect(self.add_new_tab)
        layout.addWidget(add_tab_btn)

        layout.addStretch()


        # Safe Zone Toggle
        self.safe_zone_btn = QPushButton("🛡️ Safe Zone")
        self.safe_zone_btn.setCheckable(True)
        self.safe_zone_btn.setChecked(True)
        self.safe_zone_btn.clicked.connect(self.toggle_safe_zone)
        layout.addWidget(self.safe_zone_btn)

        # Grid Toggle
        self.grid_btn = QPushButton("▦ Grid")
        self.grid_btn.setCheckable(True)
        self.grid_btn.clicked.connect(self.toggle_grid)
        layout.addWidget(self.grid_btn)

        # Save / Open Images
        save_btn = QPushButton("💾 이미지 저장하기")
        save_btn.setToolTip("완성된 썸네일 이미지 파일(.png, .jpg)로 저장")
        save_btn.clicked.connect(self.execute_export)
        layout.addWidget(save_btn)

        open_btn = QPushButton("🖼️ 이미지 불러오기")
        open_btn.setToolTip("외부 이미지 파일(.png, .jpg)을 캔버스에 추가")
        open_btn.clicked.connect(self.add_image_layer_action)
        layout.addWidget(open_btn)


        # YouTube Push Upload
        yt_btn = QPushButton("🚀 유튜브 업로드")
        yt_btn.setProperty("class", "primary")
        yt_btn.clicked.connect(self.open_youtube_dialog)
        layout.addWidget(yt_btn)

        return layout

    def create_left_panel(self):
        panel = QFrame()
        panel.setProperty("class", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        tab_widget = QTabWidget()

        # TAB 1: LAYERS
        layer_tab = QWidget()
        l_layout = QVBoxLayout(layer_tab)
        l_layout.setContentsMargins(4, 8, 4, 4)
        l_layout.setSpacing(6)

        top_l_bar = QHBoxLayout()
        add_text_btn = QPushButton("+ 텍스트")
        add_text_btn.clicked.connect(self.add_text_layer_action)
        top_l_bar.addWidget(add_text_btn)

        add_shape_btn = QPushButton("+ 도형")
        add_shape_btn.clicked.connect(lambda: self.add_shape_layer_action("rect"))
        top_l_bar.addWidget(add_shape_btn)

        del_btn = QPushButton("🗑️")
        del_btn.setToolTip("선택 레이어 삭제")
        del_btn.clicked.connect(self.canvas.delete_selected_layer)
        top_l_bar.addWidget(del_btn)
        l_layout.addLayout(top_l_bar)

        self.layer_list = LayerListWidget()
        self.layer_list.currentRowChanged.connect(self.on_layer_list_selection)
        self.layer_list.order_changed.connect(self.on_layer_order_changed)
        l_layout.addWidget(self.layer_list, 1)

        tab_widget.addTab(layer_tab, "📑 Layers")

        # TAB 2: TEMPLATES
        tmpl_tab = QWidget()
        t_layout = QVBoxLayout(tmpl_tab)
        t_layout.setContentsMargins(6, 8, 6, 6)
        t_layout.setSpacing(8)

        templates = [
            ("🎮 게임 / 라이브 썸네일", "game"),
            ("🌿 일상 / VLOG 브이로그", "vlog"),
            ("📰 뉴스 / 속보 / 지식 채널", "news"),
            ("⚡ IT / 테크 기기 리뷰", "tech"),
            ("🍕 맛집 / 먹방 요리 레시피", "food")
        ]

        for name, key in templates:
            btn = QPushButton(name)
            btn.setStyleSheet("text-align: left; padding: 10px; font-weight: bold; background-color: #20202d;")
            btn.clicked.connect(lambda ch, k=key: self.apply_preset_template(k))
            t_layout.addWidget(btn)

        t_layout.addStretch()
        tab_widget.addTab(tmpl_tab, "✨ 템플릿")

        # TAB 3: FONTS
        fonts_tab = QWidget()
        f_layout = QVBoxLayout(fonts_tab)
        f_layout.setContentsMargins(6, 8, 6, 6)
        f_layout.setSpacing(6)

        self.font_search = QLineEdit()
        self.font_search.setPlaceholderText("🔍 폰트 검색...")
        self.font_search.textChanged.connect(self.filter_fonts_list)
        f_layout.addWidget(self.font_search)

        self.fonts_list_widget = QListWidget()
        self.all_font_families = QFontDatabase.families()
        for fam in self.all_font_families:
            item = QListWidgetItem(fam)
            self.fonts_list_widget.addItem(item)
        self.fonts_list_widget.itemClicked.connect(self.on_font_item_clicked)
        f_layout.addWidget(self.fonts_list_widget, 1)

        tab_widget.addTab(fonts_tab, "🔤 폰트")

        layout.addWidget(tab_widget)
        return panel

    def create_bottom_toolbar(self):
        frame = QFrame()
        frame.setStyleSheet("background-color: #1a1a24; border: 1px solid #2e2e3e; border-radius: 8px; padding: 4px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        tools = [
            ("🖱️ 선택 (V)", "select"),
            ("⬛ 직사각형", "rect"),
            ("▢ 라운드", "rounded_rect"),
            ("⭕ 원형 (O)", "circle"),
            ("🍩 링/도넛", "ring"),
            ("🔷 다각형", "polygon"),
            ("⭐ 별", "star"),
            ("➡️ 화살표", "arrow"),
            ("🏷️ 뱃지", "badge"),
            ("🔤 텍스트 (T)", "text"),
            ("🖼️ 이미지", "image")
        ]

        for label, tool_id in tools:
            btn = QPushButton(label)
            btn.setProperty("class", "tool-btn")
            btn.clicked.connect(lambda ch, t=tool_id: self.on_tool_clicked(t))
            layout.addWidget(btn)

        layout.addStretch()

        # Zoom Controls
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(lambda: self.change_zoom(-0.1))
        layout.addWidget(zoom_out_btn)

        self.zoom_label = QLabel("65%")
        self.zoom_label.setStyleSheet("font-weight: bold; min-width: 40px;")
        layout.addWidget(self.zoom_label)

        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(lambda: self.change_zoom(0.1))
        layout.addWidget(zoom_in_btn)

        return frame

    def create_right_inspector(self):
        panel = QFrame()
        panel.setProperty("class", "panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        scroll_content = QWidget()
        self.inspector_layout = QVBoxLayout(scroll_content)
        self.inspector_layout.setContentsMargins(4, 4, 12, 20)
        self.inspector_layout.setSpacing(14)

        # 1. Selection Header & Alignment
        align_box = QGroupBox("선택 항목 및 정렬")
        ab_layout = QVBoxLayout(align_box)
        ab_layout.setContentsMargins(12, 12, 12, 16)
        ab_layout.setSpacing(12)

        self.selected_badge = QLabel("Canvas Frame (1280 × 720)")
        self.selected_badge.setStyleSheet("color: #0d99ff; font-weight: bold; font-size: 13px;")
        ab_layout.addWidget(self.selected_badge)

        align_btn_bar = QHBoxLayout()
        align_left_btn = QPushButton("⇤")
        align_left_btn.setToolTip("좌측 정렬")
        align_left_btn.clicked.connect(lambda: self.align_selected("left"))
        align_btn_bar.addWidget(align_left_btn)

        align_ch_btn = QPushButton("⇥⇤")
        align_ch_btn.setToolTip("가로 중앙 정렬")
        align_ch_btn.clicked.connect(lambda: self.align_selected("center_h"))
        align_btn_bar.addWidget(align_ch_btn)

        align_right_btn = QPushButton("⇥")
        align_right_btn.setToolTip("우측 정렬")
        align_right_btn.clicked.connect(lambda: self.align_selected("right"))
        align_btn_bar.addWidget(align_right_btn)

        align_cv_btn = QPushButton("↥↧")
        align_cv_btn.setToolTip("세로 중앙 정렬")
        align_cv_btn.clicked.connect(lambda: self.align_selected("center_v"))
        align_btn_bar.addWidget(align_cv_btn)
        ab_layout.addLayout(align_btn_bar)

        self.inspector_layout.addWidget(align_box)

        # 2. Position & Transform
        trans_box = QGroupBox("위치 및 크기 (Transform)")
        tb_layout = QGridLayout(trans_box)
        tb_layout.setContentsMargins(12, 12, 12, 16)
        tb_layout.setSpacing(12)

        tb_layout.addWidget(QLabel("<b>X / Y</b>"), 0, 0)
        self.spin_x = QSpinBox()
        self.spin_x.setRange(-2000, 4000)
        self.spin_x.valueChanged.connect(self.update_layer_from_inspector)
        tb_layout.addWidget(self.spin_x, 0, 1)

        self.spin_y = QSpinBox()
        self.spin_y.setRange(-2000, 4000)
        self.spin_y.valueChanged.connect(self.update_layer_from_inspector)
        tb_layout.addWidget(self.spin_y, 0, 2)

        tb_layout.addWidget(QLabel("<b>W / H</b>"), 1, 0)
        self.spin_w = QSpinBox()
        self.spin_w.setRange(10, 4000)
        self.spin_w.valueChanged.connect(self.update_layer_from_inspector)
        tb_layout.addWidget(self.spin_w, 1, 1)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(10, 4000)
        self.spin_h.valueChanged.connect(self.update_layer_from_inspector)
        tb_layout.addWidget(self.spin_h, 1, 2)

        tb_layout.addWidget(QLabel("<b>회전 (Rot)</b>"), 2, 0)
        self.spin_rot = QSpinBox()
        self.spin_rot.setRange(0, 360)
        self.spin_rot.valueChanged.connect(self.update_layer_from_inspector)
        tb_layout.addWidget(self.spin_rot, 2, 1)

        # Flip Buttons
        flip_h_btn = QPushButton("↔ 반전")
        flip_h_btn.clicked.connect(self.flip_horizontal)
        tb_layout.addWidget(flip_h_btn, 2, 2)

        self.inspector_layout.addWidget(trans_box)

        # 3. Typography (For Text Layer)
        self.type_box = QGroupBox("텍스트 편집 (Typography)")
        ty_layout = QVBoxLayout(self.type_box)
        ty_layout.setContentsMargins(12, 12, 12, 16)
        ty_layout.setSpacing(12)

        self.text_content_edit = QTextEdit()
        self.text_content_edit.setMaximumHeight(60)
        self.text_content_edit.textChanged.connect(self.update_layer_from_inspector)
        ty_layout.addWidget(self.text_content_edit)

        ty_layout.addWidget(QLabel("폰트 패밀리 (Font Family)"))
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(self.all_font_families)
        self.font_family_combo.currentTextChanged.connect(self.update_layer_from_inspector)
        filter_obj = KeepComboOpenFilter(self.font_family_combo)
        self.font_family_combo.installEventFilter(filter_obj)
        self.font_family_combo.view().installEventFilter(filter_obj)
        self.font_family_combo.view().viewport().installEventFilter(filter_obj)
        ty_layout.addWidget(self.font_family_combo)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("크기:"))
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(10, 300)
        self.spin_font_size.setValue(64)
        self.spin_font_size.valueChanged.connect(self.update_layer_from_inspector)
        size_row.addWidget(self.spin_font_size)

        self.weight_combo = QComboBox()
        self.weight_combo.addItem("Normal (400)", 400)
        self.weight_combo.addItem("Bold (700)", 700)
        self.weight_combo.addItem("Black (900)", 900)
        self.weight_combo.currentIndexChanged.connect(self.update_layer_from_inspector)
        size_row.addWidget(self.weight_combo)
        ty_layout.addLayout(size_row)

        self.inspector_layout.addWidget(self.type_box)

        # 4. Fill & Gradients
        fill_box = QGroupBox("채우기 및 색상 (Fill)")
        fb_layout = QVBoxLayout(fill_box)
        fb_layout.setContentsMargins(12, 12, 12, 16)
        fb_layout.setSpacing(12)

        fill_type_row = QHBoxLayout()
        self.fill_type_combo = QComboBox()
        self.fill_type_combo.addItems(["Solid (단색)", "Linear Gradient", "Radial Gradient"])
        self.fill_type_combo.currentIndexChanged.connect(self.update_layer_from_inspector)
        fill_type_row.addWidget(self.fill_type_combo)
        fb_layout.addLayout(fill_type_row)

        c_row = QHBoxLayout()
        self.color1_btn = QPushButton("■ 색상 1")
        self.color1_btn.clicked.connect(lambda: self.pick_color(1))
        c_row.addWidget(self.color1_btn)

        self.color2_btn = QPushButton("■ 색상 2")
        self.color2_btn.clicked.connect(lambda: self.pick_color(2))
        c_row.addWidget(self.color2_btn)
        fb_layout.addLayout(c_row)
        
        self.fill_transparent_check = QCheckBox("내부 투명")
        self.fill_transparent_check.stateChanged.connect(self.update_layer_from_inspector)
        fb_layout.addWidget(self.fill_transparent_check)

        self.inspector_layout.addWidget(fill_box)

        # 5. Stroke / Outline & Shadow
        effect_box = QGroupBox("외곽선 및 그림자 (Stroke/Shadow)")
        ef_layout = QVBoxLayout(effect_box)
        ef_layout.setContentsMargins(12, 12, 12, 16)
        ef_layout.setSpacing(12)

        stroke_row = QHBoxLayout()
        self.stroke_color_btn = QPushButton("■ 외곽선 색")
        self.stroke_color_btn.clicked.connect(self.pick_stroke_color)
        stroke_row.addWidget(self.stroke_color_btn)

        stroke_row.addWidget(QLabel("두께:"))
        self.spin_stroke_w = QSpinBox()
        self.spin_stroke_w.setRange(0, 50)
        self.spin_stroke_w.valueChanged.connect(self.update_layer_from_inspector)
        stroke_row.addWidget(self.spin_stroke_w)
        ef_layout.addLayout(stroke_row)

        self.inspector_layout.addWidget(effect_box)

        # 6. Blur and Opacity
        op_box = QGroupBox("특수 효과 및 투명도 (Effects)")
        op_layout = QVBoxLayout(op_box)
        op_layout.setContentsMargins(12, 12, 12, 16)
        op_layout.setSpacing(12)
        
        white_row = QHBoxLayout()
        white_row.addWidget(QLabel("<b>밝기 (Bright):</b>"))
        self.white_slider = QSlider(Qt.Orientation.Horizontal)
        self.white_slider.setRange(0, 100)
        self.white_slider.setValue(0)
        self.white_slider.valueChanged.connect(self.update_layer_from_inspector)
        white_row.addWidget(self.white_slider)
        self.white_val_label = QLabel("0%")
        white_row.addWidget(self.white_val_label)
        op_layout.addLayout(white_row)
        
        blur_row = QHBoxLayout()
        blur_row.addWidget(QLabel("<b>블러 (Blur):</b>"))
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(0, 100)
        self.blur_slider.setValue(0)
        self.blur_slider.valueChanged.connect(self.update_layer_from_inspector)
        blur_row.addWidget(self.blur_slider)
        self.blur_val_label = QLabel("0%")
        blur_row.addWidget(self.blur_val_label)
        op_layout.addLayout(blur_row)

        alpha_row = QHBoxLayout()
        alpha_row.addWidget(QLabel("<b>투명도:</b>"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.update_layer_from_inspector)
        alpha_row.addWidget(self.opacity_slider)
        self.opacity_val_label = QLabel("100%")
        alpha_row.addWidget(self.opacity_val_label)
        op_layout.addLayout(alpha_row)

        self.inspector_layout.addWidget(op_box)

        # 7. EXPORT & SIZE OPTIMIZER
        export_box = QGroupBox("🚀 썸네일 및 영상 보관함")
        ex_layout = QVBoxLayout(export_box)
        ex_layout.setContentsMargins(12, 12, 12, 16)
        ex_layout.setSpacing(12)

        ex_row = QHBoxLayout()
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["PNG Image (*.png)", "JPEG Image (*.jpg)"])
        ex_row.addWidget(self.export_format_combo)

        self.export_scale_combo = QComboBox()
        self.export_scale_combo.addItem("1X (1280x720 HD)", 1.0)
        self.export_scale_combo.addItem("2X (2560x1440 4K)", 2.0)
        ex_row.addWidget(self.export_scale_combo)
        ex_layout.addLayout(ex_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        import_btn = QPushButton("📂 썸네일 및 영상 불러오기")
        import_btn.clicked.connect(self.import_to_exports)
        btn_row.addWidget(import_btn)

        export_btn = QPushButton("💾 썸네일 파일 저장")
        export_btn.setProperty("class", "primary")
        export_btn.clicked.connect(self.execute_export)
        btn_row.addWidget(export_btn)
        
        ex_layout.addLayout(btn_row)
        
        self.exports_list_widget = QListWidget()
        self.exports_list_widget.setMaximumHeight(120)
        self.exports_list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.exports_list_widget.itemDoubleClicked.connect(self.open_exported_file)
        
        def _list_keyPressEvent(event):
            if event.key() == Qt.Key.Key_Delete:
                self.delete_selected_export()
            else:
                QListWidget.keyPressEvent(self.exports_list_widget, event)
        self.exports_list_widget.keyPressEvent = _list_keyPressEvent
        
        ex_layout.addWidget(self.exports_list_widget)

        self.inspector_layout.addWidget(export_box)
        
        QTimer.singleShot(100, self.refresh_exports_list)
        
        # Add a stretch at the end to push all panels to the top
        self.inspector_layout.addStretch(1)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return panel

    def handle_delete_key(self):
        if hasattr(self, 'exports_list_widget') and self.exports_list_widget.hasFocus():
            self.delete_selected_export()
        else:
            self.canvas.delete_selected_layer()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_project)
        QShortcut(QKeySequence("Ctrl+O"), self, self.add_image_layer_action)
        QShortcut(QKeySequence("Ctrl+N"), self, self.add_new_tab)
        QShortcut(QKeySequence(Qt.Key.Key_Delete), self, self.handle_delete_key)
        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self, self.handle_delete_key)
        QShortcut(QKeySequence("Ctrl+D"), self, self.canvas.duplicate_selected_layer)
        QShortcut(QKeySequence("Ctrl+C"), self, self.canvas.copy_selected_layer)
        QShortcut(QKeySequence("Ctrl+V"), self, self.canvas.paste_selected_layer)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.canvas.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.canvas.redo)
        QShortcut(QKeySequence("Ctrl+A"), self, self.canvas.select_all_layers)
        
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, self.canvas.move_selected_up)
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, self.canvas.move_selected_down)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self.canvas.move_selected_left)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self.canvas.move_selected_right)
        
        QShortcut(QKeySequence("Shift+Up"), self, self.canvas.move_selected_up)
        QShortcut(QKeySequence("Shift+Down"), self, self.canvas.move_selected_down)
        QShortcut(QKeySequence("Shift+Left"), self, self.canvas.move_selected_left)
        QShortcut(QKeySequence("Shift+Right"), self, self.canvas.move_selected_right)
        
        QShortcut(QKeySequence(Qt.Key.Key_F1), self, lambda: self.pick_color(1))
        QShortcut(QKeySequence(Qt.Key.Key_F2), self, self.pick_font)

    def on_layer_selected(self, layer):
        self.sync_layer_list_ui()
        if not layer:
            self.selected_badge.setText("Canvas Frame (1280 × 720)")
            self.type_box.setVisible(False)
            return

        self.selected_badge.setText(f"{layer.name} ({layer.type})")
        self.type_box.setVisible(layer.type == "text")

        self.spin_x.blockSignals(True)
        self.spin_y.blockSignals(True)
        self.spin_w.blockSignals(True)
        self.spin_h.blockSignals(True)
        self.spin_rot.blockSignals(True)
        self.opacity_slider.blockSignals(True)
        self.blur_slider.blockSignals(True)
        self.white_slider.blockSignals(True)

        self.spin_x.setValue(int(layer.x))
        self.spin_y.setValue(int(layer.y))
        self.spin_w.setValue(int(layer.w))
        self.spin_h.setValue(int(layer.h))
        self.spin_rot.setValue(int(layer.rotation))
        self.opacity_slider.setValue(layer.opacity)
        self.opacity_val_label.setText(f"{layer.opacity}%")
        self.blur_slider.setValue(layer.blur)
        self.blur_val_label.setText(f"{layer.blur}%")
        self.white_slider.setValue(getattr(layer, 'whiteness', 0))
        self.white_val_label.setText(f"{getattr(layer, 'whiteness', 0)}%")

        if layer.type == "text":
            self.text_content_edit.blockSignals(True)
            self.font_family_combo.blockSignals(True)
            self.spin_font_size.blockSignals(True)
            self.weight_combo.blockSignals(True)

            self.text_content_edit.setPlainText(layer.text)
            self.font_family_combo.setCurrentText(layer.font_family)
            self.spin_font_size.setValue(layer.font_size)
            idx = self.weight_combo.findData(layer.font_weight)
            if idx >= 0:
                self.weight_combo.setCurrentIndex(idx)

            self.text_content_edit.blockSignals(False)
            self.font_family_combo.blockSignals(False)
            self.spin_font_size.blockSignals(False)
            self.weight_combo.blockSignals(False)

        self.fill_type_combo.blockSignals(True)
        ft_idx = 0
        if layer.fill_type == "linear_gradient":
            ft_idx = 1
        elif layer.fill_type == "radial_gradient":
            ft_idx = 2
        self.fill_type_combo.setCurrentIndex(ft_idx)
        self.fill_type_combo.blockSignals(False)
        
        self.fill_transparent_check.blockSignals(True)
        self.fill_transparent_check.setChecked(getattr(layer, 'fill_transparent', False))
        self.fill_transparent_check.blockSignals(False)

        self.color1_btn.setStyleSheet(f"background-color: {layer.fill_color}; color: {'#000' if QColor(layer.fill_color).lightness() > 128 else '#fff'};")
        self.color2_btn.setStyleSheet(f"background-color: {layer.gradient_color2}; color: {'#000' if QColor(layer.gradient_color2).lightness() > 128 else '#fff'};")

        self.spin_stroke_w.blockSignals(True)
        self.spin_stroke_w.setValue(layer.stroke_width)
        self.spin_stroke_w.blockSignals(False)
        self.stroke_color_btn.setStyleSheet(f"background-color: {layer.stroke_color}; color: {'#000' if QColor(layer.stroke_color).lightness() > 128 else '#fff'};")

        self.spin_x.blockSignals(False)
        self.spin_y.blockSignals(False)
        self.spin_w.blockSignals(False)
        self.spin_h.blockSignals(False)
        self.spin_rot.blockSignals(False)
        self.opacity_slider.blockSignals(False)
        self.blur_slider.blockSignals(False)
        self.white_slider.blockSignals(False)

    def update_layer_from_inspector(self):
        l = self.canvas.selected_layer
        if not l:
            return

        l.x = self.spin_x.value()
        l.y = self.spin_y.value()
        l.w = self.spin_w.value()
        l.h = self.spin_h.value()
        l.rotation = self.spin_rot.value()
        l.opacity = self.opacity_slider.value()
        self.opacity_val_label.setText(f"{l.opacity}%")
        l.blur = self.blur_slider.value()
        self.blur_val_label.setText(f"{l.blur}%")
        l.whiteness = self.white_slider.value()
        self.white_val_label.setText(f"{l.whiteness}%")

        if l.type == "text":
            l.text = self.text_content_edit.toPlainText()
            l.font_family = self.font_family_combo.currentText()
            l.font_size = self.spin_font_size.value()
            l.font_weight = self.weight_combo.currentData() or 700

            font = QFont(l.font_family, l.font_size)
            font.setWeight(QFont.Weight(l.font_weight))
            fm = QFontMetrics(font)
            bw = fm.horizontalAdvance(l.text) if hasattr(fm, 'horizontalAdvance') else fm.boundingRect(l.text).width()
            bh = fm.height()
            
            l.w = float(bw + 10)
            l.h = float(bh + 10)
            
            self.spin_w.blockSignals(True)
            self.spin_w.setValue(int(l.w))
            self.spin_w.blockSignals(False)
            
            self.spin_h.blockSignals(True)
            self.spin_h.setValue(int(l.h))
            self.spin_h.blockSignals(False)

        ft = self.fill_type_combo.currentIndex()
        if ft == 1:
            l.fill_type = "linear_gradient"
        elif ft == 2:
            l.fill_type = "radial_gradient"
        else:
            l.fill_type = "solid"
            
        l.fill_transparent = self.fill_transparent_check.isChecked()

        l.stroke_width = self.spin_stroke_w.value()

        self.canvas.update()

    def on_layer_order_changed(self):
        new_layers = []
        for i in range(self.layer_list.count()):
            item = self.layer_list.item(i)
            lid = item.data(Qt.ItemDataRole.UserRole)
            matching = [l for l in self.canvas.layers if l.id == lid]
            if matching:
                new_layers.append(matching[0])
        
        self.canvas.layers = list(reversed(new_layers))
        self.canvas.push_state()
        self.canvas.update()

    def sync_layer_list_ui(self):
        self.layer_list.blockSignals(True)
        
        if self.layer_list.count() == len(self.canvas.layers):
            found_idx = -1
            for i, l in enumerate(reversed(self.canvas.layers)):
                item = self.layer_list.item(i)
                item.setData(Qt.ItemDataRole.UserRole, l.id)
                if self.canvas.selected_layer and self.canvas.selected_layer.id == l.id:
                    found_idx = i
            
            self.layer_list.clearSelection()
            if found_idx != -1:
                self.layer_list.setCurrentRow(found_idx)
                self.layer_list.item(found_idx).setSelected(True)
            else:
                self.layer_list.setCurrentRow(-1)
                
            self.layer_list.blockSignals(False)
            return

        self.layer_list.clear()

        found_idx = -1
        for i, l in enumerate(reversed(self.canvas.layers)):
            icon_str = "🔤" if l.type == "text" else ("🖼️" if l.type == "image" else "🔷")
            item = QListWidgetItem(f"{icon_str} {l.name}")
            item.setData(Qt.ItemDataRole.UserRole, l.id)
            self.layer_list.addItem(item)
            if self.canvas.selected_layer and self.canvas.selected_layer.id == l.id:
                found_idx = i
                
        self.layer_list.clearSelection()
        if found_idx != -1:
            self.layer_list.setCurrentRow(found_idx)
            self.layer_list.item(found_idx).setSelected(True)
        else:
            self.layer_list.setCurrentRow(-1)
            
        self.layer_list.blockSignals(False)

    def on_layer_list_selection(self, row):
        if row >= 0:
            item = self.layer_list.item(row)
            if item:
                lid = item.data(Qt.ItemDataRole.UserRole)
                matching = [l for l in self.canvas.layers if l.id == lid]
                if matching:
                    self.canvas.selected_layer = matching[0]
                    self.on_layer_selected(self.canvas.selected_layer)
                    self.canvas.update()

    def on_history_changed(self):
        pass

    def pick_color(self, idx=1):
        l = self.canvas.selected_layer
        if not l:
            return
        initial = QColor(l.fill_color if idx == 1 else l.gradient_color2)
        color = QColorDialog.getColor(
            initial, self, f"색상 {idx} 선택",
            options=QColorDialog.ColorDialogOption.DontUseNativeDialog
        )
        if color.isValid():
            targets = self.canvas.multi_selected_layers if hasattr(self.canvas, 'multi_selected_layers') and self.canvas.multi_selected_layers else [l]
            for target_layer in targets:
                if idx == 1:
                    target_layer.fill_color = color.name()
                    target_layer.gradient_color1 = color.name()
                else:
                    target_layer.gradient_color2 = color.name()
            self.on_layer_selected(l)
            self.canvas.push_state()
            self.canvas.update()

    def pick_font(self):
        l = self.canvas.selected_layer
        if not l or l.type != "text":
            return
            
        initial_font = QFont(l.font_family, l.font_size)
        font, ok = QFontDialog.getFont(
            initial_font, self, "폰트 선택",
            options=QFontDialog.FontDialogOption.DontUseNativeDialog
        )
        if ok:
            targets = self.canvas.multi_selected_layers if hasattr(self.canvas, 'multi_selected_layers') and self.canvas.multi_selected_layers else [l]
            for target_layer in targets:
                if target_layer.type == "text":
                    target_layer.font_family = font.family()
                    target_layer.font_size = font.pointSize()
            
            self.on_layer_selected(l)
            self.canvas.push_state()
            self.canvas.update()

    def pick_stroke_color(self):
        l = self.canvas.selected_layer
        if not l:
            return
        initial = QColor(l.stroke_color)
        color = QColorDialog.getColor(
            initial, self, "외곽선 색상 선택",
            options=QColorDialog.ColorDialogOption.DontUseNativeDialog
        )
        if color.isValid():
            l.stroke_color = color.name()
            self.on_layer_selected(l)
            self.canvas.push_state()
            self.canvas.update()

    def flip_horizontal(self):
        if self.canvas.selected_layer:
            self.canvas.selected_layer.flip_h = not self.canvas.selected_layer.flip_h
            self.canvas.push_state()
            self.canvas.update()

    def align_selected(self, mode):
        l = self.canvas.selected_layer
        if not l:
            return
        cw, ch = self.canvas.canvas_width, self.canvas.canvas_height
        if mode == "left":
            l.x = 0
        elif mode == "center_h":
            l.x = (cw - l.w) / 2.0
        elif mode == "right":
            l.x = cw - l.w
        elif mode == "center_v":
            l.y = (ch - l.h) / 2.0
        self.on_layer_selected(l)
        self.canvas.push_state()
        self.canvas.update()

    def change_zoom(self, delta):
        self.canvas.zoom = max(0.25, min(2.0, self.canvas.zoom + delta))
        self.zoom_label.setText(f"{int(self.canvas.zoom * 100)}%")
        self.canvas.update()

    def toggle_safe_zone(self, checked):
        self.canvas.show_safe_zone = checked
        self.canvas.update()

    def toggle_grid(self, checked):
        self.canvas.show_grid = checked
        self.canvas.update()

    def on_tool_clicked(self, tool_id):
        if tool_id == "text":
            self.add_text_layer_action()
        elif tool_id == "image":
            self.add_image_layer_action()
        elif tool_id in ("rect", "rounded_rect", "circle", "ring", "polygon", "star", "arrow", "badge"):
            self.add_shape_layer_action(tool_id)

    def add_text_layer_action(self):
        t = Layer("text", "새 텍스트 레이어")
        t.text = "클릭하여 텍스트 입력"
        t.font_family = "Pretendard"
        t.font_size = 56
        t.x, t.y, t.w, t.h = 400, 300, 500, 80
        t.fill_color = "#ffffff"
        t.stroke_color = "#000000"
        t.stroke_width = 4
        self.canvas.add_layer(t)

    def add_shape_layer_action(self, shape_type):
        s = Layer("shape", f"도형 ({shape_type})")
        s.shape_type = shape_type
        s.x, s.y, s.w, s.h = 440, 240, 280, 280
        s.fill_color = "#0d99ff"
        s.stroke_color = "#ffffff"
        s.stroke_width = 4
        self.canvas.add_layer(s)

    def add_image_layer_action(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "이미지 파일 선택", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.svg);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not filepath:
            return
        pix = QPixmap(filepath)
        if not pix.isNull():
            l = Layer("image", f"이미지: {os.path.basename(filepath)}")
            l.image_path = filepath
            l.pixmap = pix
            l.x, l.y = 100, 100
            l.w = min(pix.width(), 800)
            l.h = min(pix.height(), 450)
            self.canvas.add_layer(l)

    def apply_preset_template(self, key):
        reply = QMessageBox.question(
            self, "템플릿 적용",
            "현재 작업 중인 레이어가 템플릿 레이아웃으로 변경됩니다. 적용하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if key == "game":
            bg = Layer("shape", "게임 배경")
            bg.x, bg.y, bg.w, bg.h = 0, 0, 1280, 720
            bg.fill_type = "linear_gradient"
            bg.gradient_color1, bg.gradient_color2 = "#831843", "#1e3a8a"
            bg.locked = True

            ring = Layer("shape", "포인트 도넛")
            ring.shape_type = "ring"
            ring.x, ring.y, ring.w, ring.h = 800, 80, 400, 400
            ring.fill_type = "linear_gradient"
            ring.gradient_color1, ring.gradient_color2 = "#f43f5e", "#3b82f6"
            ring.stroke_color = "#ffffff"
            ring.stroke_width = 6

            t1 = Layer("text", "게임 메인 타이틀")
            t1.text = "역대급 랭크전 펜타킬!!"
            t1.font_family = "Black Han Sans"
            t1.font_size = 90
            t1.x, t1.y, t1.w, t1.h = 80, 160, 760, 120
            t1.fill_color = "#facc15"
            t1.stroke_color = "#000000"
            t1.stroke_width = 10
            t1.shadow_enabled = True

            t2 = Layer("text", "서브 문구")
            t2.text = "솔로 랭크 1위 달성 하이라이트"
            t2.font_family = "Pretendard"
            t2.font_size = 44
            t2.x, t2.y, t2.w, t2.h = 80, 300, 650, 70
            t2.fill_color = "#ffffff"
            t2.stroke_color = "#000000"
            t2.stroke_width = 6

            self.canvas.layers = [bg, ring, t1, t2]
            self.canvas.selected_layer = t1

        elif key == "vlog":
            bg = Layer("shape", "일상 배경")
            bg.x, bg.y, bg.w, bg.h = 0, 0, 1280, 720
            bg.fill_type = "linear_gradient"
            bg.gradient_color1, bg.gradient_color2 = "#064e3b", "#022c22"
            bg.locked = True

            badge = Layer("shape", "감성 뱃지")
            badge.shape_type = "badge"
            badge.x, badge.y, badge.w, badge.h = 80, 120, 220, 60
            badge.fill_color = "#10b981"

            t1 = Layer("text", "VLOG 타이틀")
            t1.text = "주말 일상 브이로그 ✨"
            t1.font_family = "Pretendard"
            t1.font_size = 72
            t1.font_weight = 900
            t1.x, t1.y, t1.w, t1.h = 80, 210, 750, 90
            t1.fill_color = "#ffffff"
            t1.stroke_color = "#000000"
            t1.stroke_width = 6

            t2 = Layer("text", "서브 자막")
            t2.text = "성수동 핫플 카페 & 쇼핑 하울"
            t2.font_family = "Pretendard"
            t2.font_size = 38
            t2.x, t2.y, t2.w, t2.h = 80, 320, 600, 60
            t2.fill_color = "#a7f3d0"

            self.canvas.layers = [bg, badge, t1, t2]
            self.canvas.selected_layer = t1

        elif key == "news":
            bg = Layer("shape", "뉴스 배경")
            bg.x, bg.y, bg.w, bg.h = 0, 0, 1280, 720
            bg.fill_type = "linear_gradient"
            bg.gradient_color1, bg.gradient_color2 = "#0f172a", "#1e293b"
            bg.locked = True

            bar = Layer("shape", "속보 자막 바")
            bar.shape_type = "rect"
            bar.x, bar.y, bar.w, bar.h = 0, 560, 1280, 160
            bar.fill_color = "#dc2626"

            t1 = Layer("text", "메인 헤드라인")
            t1.text = "[속보] 긴급 발표 전격 공개!"
            t1.font_family = "Black Han Sans"
            t1.font_size = 80
            t1.x, t1.y, t1.w, t1.h = 80, 200, 900, 110
            t1.fill_color = "#fef08a"
            t1.stroke_color = "#000000"
            t1.stroke_width = 8

            self.canvas.layers = [bg, bar, t1]
            self.canvas.selected_layer = t1

        self.canvas.push_state()
        self.on_layer_selected(self.canvas.selected_layer)
        self.canvas.update()

    def filter_fonts_list(self, text):
        self.fonts_list_widget.clear()
        query = text.strip().lower()
        matched = [f for f in self.all_font_families if query in f.lower()] if query else self.all_font_families[:100]
        for f in matched:
            self.fonts_list_widget.addItem(QListWidgetItem(f))

    def on_font_item_clicked(self, item):
        fam = item.text()
        if self.canvas.selected_layer and self.canvas.selected_layer.type == "text":
            self.canvas.selected_layer.font_family = fam
            self.font_family_combo.setCurrentText(fam)
            self.canvas.push_state()
            self.canvas.update()
        else:
            t = Layer("text", f"텍스트 ({fam})")
            t.text = "새 텍스트 입력"
            t.font_family = fam
            t.font_size = 64
            t.x, t.y, t.w, t.h = 350, 300, 550, 90
            self.canvas.add_layer(t)

    def add_new_tab(self):
        tab_num = self.tab_bar.count() + 1
        name = f"프로젝트 {tab_num}"
        idx = self.tab_bar.addTab(name)
        self.tab_bar.setCurrentIndex(idx)
        self.canvas.setup_initial_layers()
        self.canvas.push_state()
        self.on_layer_selected(self.canvas.selected_layer)
        self.canvas.update()

    def close_tab(self, index):
        if self.tab_bar.count() <= 1:
            QMessageBox.warning(self, "안내", "최소 1개의 프로젝트 탭이 유지되어야 합니다.")
            return
        self.tab_bar.removeTab(index)

    def switch_tab(self, index):
        if index >= 0:
            self.canvas.active_tab_name = self.tab_bar.tabText(index)
            self.canvas.update()

    def rename_tab(self, index):
        if index < 0:
            return
        old_name = self.tab_bar.tabText(index)
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "프로젝트 이름 변경", "새 프로젝트 이름:", text=old_name)
        if ok and new_name.strip():
            self.tab_bar.setTabText(index, new_name.strip())
            if self.tab_bar.currentIndex() == index:
                self.canvas.active_tab_name = new_name.strip()
                self.canvas.update()

    def save_project(self):
        current_tab_name = self.tab_bar.tabText(self.tab_bar.currentIndex()) if self.tab_bar.count() > 0 else "Untitled"
        default_path = os.path.join(PROJECTS_DIR, f"{current_tab_name}.tdp")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "프로젝트 저장 (Save Project)", default_path,
            "TDP Project (*.tdp)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not filepath:
            return
        if not filepath.lower().endswith(".tdp"):
            filepath += ".tdp"
        try:
            state = [l.to_dict() for l in self.canvas.layers]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "저장 완료", "프로젝트 파일(.tdp)이 안전하게 저장되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"프로젝트 저장 중 오류가 발생했습니다:\n{str(e)}")

    def load_project(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "프로젝트 열기 (Open Project)", PROJECTS_DIR,
            "TDP Project (*.tdp)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.canvas.restore_state(state)
            self.canvas.push_state()
            self.on_layer_selected(self.canvas.selected_layer)
            QMessageBox.information(self, "열기 완료", "프로젝트 파일(.tdp)을 성공적으로 불러왔습니다.")
        except Exception as e:
            QMessageBox.critical(self, "열기 오류", f"프로젝트 불러오기 중 오류가 발생했습니다:\n{str(e)}")



    def open_video_dialog(self):
        dlg = VideoFrameExtractorDialog(self)
        def on_captured(pix, name):
            l = Layer("image", f"영상 프레임 ({name})")
            l.pixmap = pix
            l.x, l.y = 0, 0
            l.w, l.h = 1280, 720
            self.canvas.layers.insert(0, l)
            self.canvas.selected_layer = l
            self.canvas.push_state()
            self.on_layer_selected(l)
            self.canvas.update()
        dlg.frame_captured.connect(on_captured)
        dlg.exec()

    def open_youtube_dialog(self):
        dlg = YouTubeUploadDialog(self.canvas, self)
        dlg.exec()

    def execute_export(self):
        scale = self.export_scale_combo.currentData() or 1.0
        fmt_text = self.export_format_combo.currentText()
        is_jpeg = "JPEG" in fmt_text

        ext = ".jpg" if is_jpeg else ".png"
        default_name = f"{self.canvas.active_tab_name}{ext}"
        default_path = os.path.join(EXPORTS_DIR, default_name)

        filepath, _ = QFileDialog.getSaveFileName(
            self, "썸네일 내보내기 (Save Thumbnail)", default_path,
            "JPEG Image (*.jpg);;PNG Image (*.png);;All Files (*)" if is_jpeg else "PNG Image (*.png);;JPEG Image (*.jpg);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not filepath:
            return

        # 확장자가 입력되지 않은 경우 자동으로 추가
        if not filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
            if "JPEG" in _:
                filepath += ".jpg"
            elif "PNG" in _:
                filepath += ".png"
            else:
                filepath += ext


        try:
            qimg = self.canvas.export_qimage(scale)
            
            buf = QByteArray()
            qbuf = QBuffer(buf)
            qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
            qimg.save(qbuf, "PNG")
            qbuf.close()

            pil_img = Image.open(io.BytesIO(buf.data()))

            if filepath.lower().endswith(".jpg") or filepath.lower().endswith(".jpeg"):
                if pil_img.mode in ("RGBA", "P"):
                    pil_img = pil_img.convert("RGB")
                pil_img.save(filepath, "JPEG", quality=95, optimize=True)
            else:
                pil_img.save(filepath, "PNG", optimize=True)

            size_bytes = os.path.getsize(filepath)
            size_mb = round(size_bytes / (1024 * 1024), 2)
            is_under_2mb = size_mb <= 2.0

            res_str = "2560x1440 (4K)" if scale == 2.0 else "1280x720 (HD)"
            status_str = "✅ 유튜브 2MB 규격 충족" if is_under_2mb else "⚠️ 2MB 초과 (JPEG 저장을 권장합니다)"

            QMessageBox.information(
                self, "내보내기 완료",
                f"🎉 썸네일 이미지가 성공적으로 저장되었습니다!\n\n"
                f"• 파일 경로: {filepath}\n"
                f"• 해상도: {res_str}\n"
                f"• 파일 크기: {size_mb} MB ({status_str})"
            )
            self.refresh_exports_list()
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"썸네일 저장 중 오류가 발생했습니다:\n{str(e)}")

    def import_to_exports(self):
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, "파일 불러오기", "",
            "Images/Videos (*.png *.jpg *.jpeg *.mp4 *.avi);;All Files (*)",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if not filepaths:
            return
            
        success_count = 0
        for fp in filepaths:
            try:
                dest = os.path.join(EXPORTS_DIR, os.path.basename(fp))
                shutil.copy2(fp, dest)
                success_count += 1
            except Exception as e:
                print(f"Failed to copy {fp}: {e}")
                
        if success_count > 0:
            self.refresh_exports_list()

    def refresh_exports_list(self):
        if not hasattr(self, 'exports_list_widget'):
            return
        self.exports_list_widget.clear()
        if os.path.exists(EXPORTS_DIR):
            for f in sorted(os.listdir(EXPORTS_DIR), reverse=True):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.avi')):
                    self.exports_list_widget.addItem(QListWidgetItem(f))

    def open_exported_file(self, item):
        filename = item.text()
        filepath = os.path.join(EXPORTS_DIR, filename)
        if os.path.exists(filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))

    def delete_selected_export(self):
        selected_items = self.exports_list_widget.selectedItems()
        if not selected_items:
            return
        
        reply = QMessageBox.question(
            self, "파일 삭제", 
            f"선택한 {len(selected_items)}개의 파일을 삭제하시겠습니까?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                filename = item.text()
                filepath = os.path.join(EXPORTS_DIR, filename)
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f"Failed to delete {filepath}: {e}")
            self.refresh_exports_list()

def main():
    # 1. Unhandled exception handler to prevent PyQt6 std::abort() / 0xC0000409 crashes in slots
    def exception_hook(exctype, value, tb):
        import traceback
        traceback.print_exception(exctype, value, tb)
        sys.stderr.flush()

    sys.excepthook = exception_hook

    # 2. Set Application Attributes before/during QApplication creation
    from PyQt6.QtCore import QCoreApplication
    try:
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs, True)
    except Exception:
        pass

    import ctypes
    myappid = 'thumbnail.designer.pro.v2.0'
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        
    app.setWindowIcon(QIcon(os.path.join(RESOURCE_DIR, "icon.png")))

    # 3. Safe custom local font loading
    font_dir = r"C:\Users\DiCiA\AppData\Local\Microsoft\Windows\Fonts"
    if os.path.exists(font_dir):
        for f in os.listdir(font_dir):
            if f.lower().endswith(('.ttf', '.otf')):
                try:
                    QFontDatabase.addApplicationFont(os.path.join(font_dir, f))
                except Exception:
                    pass

    app.setApplicationName("유튜브 썸네일 디자이너 Pro")
    app.setStyleSheet(DARK_STYLESHEET)

    window = NativeThumbnailDesignerApp()
    window.show()

    exit_code = app.exec()
    try:
        del window
        del app
    except Exception:
        pass
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
    main()
