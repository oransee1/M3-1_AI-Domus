import os
import sys
import time
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QCheckBox, QPushButton,
    QProgressBar, QGroupBox, QMessageBox, QDialog, QFormLayout, QGridLayout,
    QSplitter, QScrollArea, QFrame, QFileDialog
)
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QFont, QDesktopServices, QPixmap
from PIL import Image

from src.config import Config, OUTPUT_DIR
from src.media.image_processor import ImageProcessor
from src.gui.worker import AutomationWorker, EncodingWorker

MODERN_STYLE = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    font-size: 13px;
}
QSplitter::handle {
    background-color: #313244;
    height: 3px;
}
QLabel.StepBadge {
    background-color: #313244;
    color: #a6adc8;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: bold;
}
QLabel.StepBadgeActive {
    background-color: #89b4fa;
    color: #11111b;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: bold;
}
QLabel.StepBadgeDone {
    background-color: #a6e3a1;
    color: #11111b;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: bold;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 15px;
    padding-top: 15px;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
}
QLineEdit, QTextEdit, QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px;
    color: #cdd6f4;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #89b4fa;
}
QPushButton {
    background-color: #45475a;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    color: #cdd6f4;
}
QPushButton:hover {
    background-color: #585b70;
}
QPushButton#GenerateBtn {
    background-color: #89b4fa;
    color: #11111b;
    font-size: 15px;
    padding: 12px;
}
QPushButton#GenerateBtn:hover {
    background-color: #b4befe;
}
QPushButton#PresetBtn {
    background-color: #313244;
    border: 1px solid #45475a;
    font-size: 11px;
    padding: 5px 8px;
}
QPushButton#PresetBtn:hover {
    background-color: #585b70;
    border-color: #89b4fa;
}
QProgressBar {
    border: 1px solid #45475a;
    border-radius: 6px;
    text-align: center;
    background-color: #313244;
    color: #ffffff;
    font-weight: bold;
    height: 22px;
}
QProgressBar::chunk {
    background-color: #a6e3a1;
    border-radius: 5px;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
QLabel#SceneCell {
    background-color: #181825;
    border: 1px dashed #45475a;
    border-radius: 6px;
    font-size: 11px;
    color: #6c7086;
}
QTabWidget::pane {
    border: 1px solid #45475a;
    border-radius: 6px;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #313244;
    color: #cdd6f4;
    padding: 6px 14px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 3px;
}
QTabBar::tab:selected {
    background-color: #45475a;
    color: #89b4fa;
    font-weight: bold;
}
"""

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 키 환경 설정")
        self.resize(520, 220)
        self.setStyleSheet(MODERN_STYLE)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.gemini_input = QLineEdit(Config.get_gemini_key())
        self.suno_input = QLineEdit(Config.get_suno_key())
        self.nano_input = QLineEdit(Config.get_nano_key())

        form.addRow("Gemini API Key:", self.gemini_input)
        form.addRow("Apiframe Suno Key:", self.suno_input)
        form.addRow("Apiframe Nano Banana Key:", self.nano_input)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        save_btn = QPushButton("저장")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

    def save(self):
        Config.set_keys(
            self.gemini_input.text().strip(),
            self.suno_input.text().strip(),
            self.nano_input.text().strip()
        )
        QMessageBox.information(self, "완료", "API 키가 저장되었습니다.")
        self.accept()

class RenderingProgressDialog(QDialog):
    """
    고화질 영상 렌더링 및 미디어 생성 중 사용자가 실수로 프로그램을
    강제 종료하지 않도록 안내하고, 실시간 진행시간, 단계, 프로그레스바, 진행율(%)을
    명확하게 보여주는 전용 진행 안내 창
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⏳ AI 미디어 생성 및 영상 렌더링 진행 중")
        self.resize(600, 360)
        self.setStyleSheet(MODERN_STYLE)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.is_finished = False
        self.elapsed_seconds = 0

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 22, 22, 22)

        # 1. 상단 경고 및 안내 배너
        warn_box = QFrame()
        warn_box.setStyleSheet(
            "background-color: #2e261f; border: 1px solid #fab387; "
            "border-radius: 8px; padding: 12px;"
        )
        warn_layout = QVBoxLayout(warn_box)
        warn_layout.setSpacing(6)
        warn_title = QLabel("⚠️ [필독 안내] 고화질 영상 렌더링 및 생성 파이프라인 가동 중!")
        warn_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #fab387;")
        warn_desc = QLabel(
            "AI 멀티모달 생성과 1080p 영상 합성(FFmpeg)은 시스템 사양 및 음원 길이에 따라\n"
            "수 분에서 최대 17~20분가량 소요될 수 있습니다. 정상적으로 백그라운드 처리 중이오니\n"
            "프로그램을 강제 종료하거나 창을 닫지 마시고 잠시만 기다려주세요."
        )
        warn_desc.setStyleSheet("font-size: 12px; color: #cdd6f4; line-height: 140%;")
        warn_layout.addWidget(warn_title)
        warn_layout.addWidget(warn_desc)
        layout.addWidget(warn_box)

        # 2. 진행 시간 및 단계 정보
        info_layout = QHBoxLayout()
        self.time_label = QLabel("⏱️ 진행 시간: 00:00:00")
        self.time_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #89b4fa;")

        self.step_label = QLabel("📌 진행 단계: [1/5] AI 기획 에이전트")
        self.step_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #a6e3a1;")

        info_layout.addWidget(self.time_label)
        info_layout.addStretch()
        info_layout.addWidget(self.step_label)
        layout.addLayout(info_layout)

        # 3. 프로그레스바 및 진행율 (%)
        prog_header = QHBoxLayout()
        prog_title = QLabel("전체 파이프라인 실시간 진행률:")
        prog_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #bac2de;")
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #a6e3a1;")
        prog_header.addWidget(prog_title)
        prog_header.addStretch()
        prog_header.addWidget(self.percent_label)
        layout.addLayout(prog_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(26)
        layout.addWidget(self.progress_bar)

        # 4. 세부 상태 메시지
        self.detail_label = QLabel("작업 준비 중...")
        self.detail_label.setStyleSheet("font-size: 12px; color: #a6adc8; font-style: italic;")
        layout.addWidget(self.detail_label)

        layout.addStretch()

        # 5. 하단 버튼 (팝업 숨기고 메인 창에서 모니터링)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.hide_btn = QPushButton("🔽 메인 창에서 모니터링하기 (팝업 최소화)")
        self.hide_btn.clicked.connect(self.hide)
        btn_layout.addWidget(self.hide_btn)
        layout.addLayout(btn_layout)

        # 타이머 설정
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start_timer(self):
        self.elapsed_seconds = 0
        self.is_finished = False
        self.time_label.setText("⏱️ 진행 시간: 00:00:00")
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.timer.start(1000)

    def _tick(self):
        self.elapsed_seconds += 1
        mins, secs = divmod(self.elapsed_seconds, 60)
        hrs, mins = divmod(mins, 60)
        self.time_label.setText(f"⏱️ 진행 시간: {hrs:02d}:{mins:02d}:{secs:02d}")

    def update_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.percent_label.setText(f"{percent}%")
        self.detail_label.setText(msg)

    def update_step(self, step_num: int):
        step_names = [
            "AI 기획 에이전트",
            "Suno & Nano 발주",
            "미디어 에셋 다운로드",
            "3x3 스토리보드 분할",
            "1080p 영상 페이드 인코딩"
        ]
        if 1 <= step_num <= 5:
            self.step_label.setText(f"📌 진행 단계: [{step_num}/5] {step_names[step_num - 1]}")
        elif step_num == 6:
            self.step_label.setText("🎉 [완료] 제작 완료!")

    def set_completed(self):
        self.is_finished = True
        self.timer.stop()
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.detail_label.setText("모든 렌더링 작업이 성공적으로 완료되었습니다!")

    def closeEvent(self, event):
        if not self.is_finished:
            # 렌더링 도중 X를 누르면 팝업만 숨기고 메인 창에서 계속 진행되도록 보호
            event.ignore()
            self.hide()
        else:
            event.accept()

class MainWindow(QMainWindow):
    STEP_NAMES = [
        "1. AI 기획",
        "2. 생성 발주",
        "3. 에셋 수집",
        "4. 3x3 분할",
        "5. 영상 렌더링"
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Domus Music Studio - AI 기반 음악 및 영상 제작 자동화")
        self.resize(1200, 820)
        self.setStyleSheet(MODERN_STYLE)

        self.worker = None
        self.last_mp4 = None
        self.scene_labels = []
        self.step_badges = []
        self.progress_dialog = None

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 1. 헤더 영역
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        main_title = QLabel("🎵 AI Domus Music Studio")
        main_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #cdd6f4;")
        sub_title = QLabel("Gemini 프롬프트 기획 ➜ Suno & Nano Banana 멀티모달 생성 ➜ 3x3 9분할 ➜ 1080p MP4 원클릭 자동 렌더링")
        sub_title.setStyleSheet("font-size: 12px; color: #a6adc8;")
        title_box.addWidget(main_title)
        title_box.addWidget(sub_title)
        header.addLayout(title_box)
        header.addStretch()

        settings_btn = QPushButton("⚙️ API 키 설정")
        settings_btn.clicked.connect(self.open_settings)
        header.addWidget(settings_btn)
        main_layout.addLayout(header)

        # 2. 바디 영역 (좌측: 입력 / 우측: 로그 & 상태)
        body_layout = QHBoxLayout()

        # 좌측 패널: 사용자 입력
        left_box = QGroupBox("1. 음악 및 비주얼 테마 기획")
        left_layout = QVBoxLayout(left_box)

        left_layout.addWidget(QLabel("어떤 음악과 영상을 만들고 싶으신가요? (한국어로 자유롭게 입력)"))
        self.mood_input = QTextEdit()
        self.mood_input.setPlaceholderText("예시: 천사와 춤을, 몽환적이고 따뜻한 뉴에이지 피아노, 마음이 편안해지는 힐링 감성")
        self.mood_input.setFixedHeight(90)
        left_layout.addWidget(self.mood_input)

        # 빠른 프리셋
        preset_label = QLabel("⚡ 빠른 무드 프리셋:")
        preset_label.setStyleSheet("font-size: 11px; color: #bac2de;")
        left_layout.addWidget(preset_label)
        preset_layout = QHBoxLayout()
        presets = [
            ("👼 천사와 춤을", "천사와 춤을, 몽환적이고 따뜻한 뉴에이지 피아노 선율, 마음의 안식을 주는 힐링 무드"),
            ("🌧️ 비오는 날 카페", "비 오는 날 아늑한 카페 창가, 따뜻한 커피 향기와 빗소리에 어울리는 차분한 재즈 피아노"),
            ("🌌 깊은 밤 수면", "새벽 2시 깊은 수면을 유도하는 신비롭고 고요한 앰비언트 사운드와 따뜻한 별빛"),
            ("☕ 로파이 스터디", "집중하기 좋은 따뜻한 로파이 비트, 부드러운 일렉트릭 피아노와 빈티지 바이닐 질감")
        ]
        for name, text in presets:
            btn = QPushButton(name)
            btn.setObjectName("PresetBtn")
            btn.clicked.connect(lambda checked, t=text: self.mood_input.setText(t))
            preset_layout.addWidget(btn)
        left_layout.addLayout(preset_layout)

        # 장르 선택
        genre_row = QHBoxLayout()
        genre_row.addWidget(QLabel("음악 장르:"))
        self.genre_combo = QComboBox()
        self.genre_combo.addItems(["New Age / Piano", "Lo-Fi / Chillhop", "Ambient / Meditation", "Cinematic Neoclassical", "Smooth Jazz", "Acoustic Guitar"])
        genre_row.addWidget(self.genre_combo)
        left_layout.addLayout(genre_row)

        # 씬 전환 페이드 효과 (MoveEditor-AutoProgram 연동)
        fade_row = QHBoxLayout()
        fade_row.addWidget(QLabel("씬 전환 페이드:"))
        self.fade_combo = QComboBox()
        self.fade_combo.addItems([
            "1.5초 (부드러운 크로스페이드 - 기본)",
            "2.0초 (감성적 롱 크로스페이드)",
            "1.0초 (빠른 크로스페이드)",
            "0초 (즉시 컷 전환)"
        ])
        fade_row.addWidget(self.fade_combo)
        left_layout.addLayout(fade_row)

        # 가사 유무 선택
        lyrics_row = QHBoxLayout()
        lyrics_row.addWidget(QLabel("가사 유무:"))
        self.lyrics_combo = QComboBox()
        self.lyrics_combo.addItems([
            "가사 없음 (보컬 없는 연주곡 - Instrumental BGM)",
            "가사 있음 (보컬 곡 - Vocal Song with Lyrics)"
        ])
        self.lyrics_combo.currentIndexChanged.connect(self._on_lyrics_changed)
        lyrics_row.addWidget(self.lyrics_combo)
        left_layout.addLayout(lyrics_row)

        # 가사 직접 입력란 (가사 있음 선택 시 노출, 기본 숨김)
        self.lyrics_box = QWidget()
        lyrics_box_layout = QVBoxLayout(self.lyrics_box)
        lyrics_box_layout.setContentsMargins(0, 4, 0, 4)
        lyrics_guide = QLabel("✍️ 보컬 가사 (선택 사항 - 미입력 시 AI가 무드에 맞춰 자동 작사):")
        lyrics_guide.setStyleSheet("font-size: 11px; color: #a6adc8;")
        self.lyrics_input = QTextEdit()
        self.lyrics_input.setPlaceholderText("예시:\n[Verse 1]\n창가에 스며든 따스한 바람\n[Chorus]\n기억해요 그대의 아름다운 날들...")
        self.lyrics_input.setFixedHeight(75)
        lyrics_box_layout.addWidget(lyrics_guide)
        lyrics_box_layout.addWidget(self.lyrics_input)
        left_layout.addWidget(self.lyrics_box)
        self.lyrics_box.setVisible(False)

        left_layout.addSpacing(15)

        # 실행 버튼
        self.gen_btn = QPushButton("🚀 AI 음악 & 영상 자동 생성 시작")
        self.gen_btn.setObjectName("GenerateBtn")
        self.gen_btn.clicked.connect(self.start_generation)
        left_layout.addWidget(self.gen_btn)

        left_layout.addSpacing(8)

        # 인코딩 엔진 직접 실행 버튼 (기존 세션/에셋 렌더링)
        self.encode_btn = QPushButton("🎬 프로그램 인코딩 엔진 실행 (기존 작업 렌더링)")
        self.encode_btn.setStyleSheet(
            "background-color: #fab387; color: #11111b; font-weight: bold; font-size: 13px; padding: 10px; border-radius: 6px;"
        )
        self.encode_btn.clicked.connect(self.start_manual_encoding)
        left_layout.addWidget(self.encode_btn)

        left_layout.addStretch()
        body_layout.addWidget(left_box, 40)

        # 우측 패널: 실시간 모니터링 & 스토리보드
        right_box = QGroupBox("2. 처음부터 끝까지 실시간 진행 모니터링 & 스토리보드")
        right_layout = QVBoxLayout(right_box)

        # 5단계 파이프라인 단계별 진행 바 (Step Indicator)
        step_bar = QHBoxLayout()
        step_bar.setSpacing(6)
        self.step_badges = []
        for i, name in enumerate(self.STEP_NAMES):
            badge = QLabel(name)
            badge.setProperty("class", "StepBadge")
            badge.setAlignment(Qt.AlignCenter)
            self.step_badges.append(badge)
            step_bar.addWidget(badge)
            if i < len(self.STEP_NAMES) - 1:
                arrow = QLabel("➔")
                arrow.setStyleSheet("color: #6c7086; font-size: 13px; font-weight: bold;")
                arrow.setAlignment(Qt.AlignCenter)
                step_bar.addWidget(arrow)
        right_layout.addLayout(step_bar)

        self.status_label = QLabel("대기 중... [생성 시작]을 클릭하세요.")
        self.status_label.setStyleSheet("font-weight: bold; color: #a6e3a1; font-size: 13px;")
        right_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        right_layout.addWidget(self.progress_bar)

        # 상하 스플리터: 상단 실시간 로그 콘솔(상시 노출) / 하단 3x3 스토리보드 씬
        splitter = QSplitter(Qt.Vertical)

        # 1. 상단: 대형 실시간 로그 콘솔 창
        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(0, 4, 0, 4)
        log_title = QLabel("📋 실시간 처리 로그 콘솔 (처음부터 끝까지 전체 진행 상황 실시간 스트리밍):")
        log_title.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 12px;")
        log_layout.addWidget(log_title)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet(
            "background-color: #11111b; color: #cdd6f4; "
            "font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; "
            "border: 1px solid #45475a; border-radius: 6px; padding: 6px;"
        )
        log_layout.addWidget(self.log_console)
        splitter.addWidget(log_panel)

        # 2. 하단: StoryBoard-Division 3x3 분할 씬 프리뷰 창
        scenes_panel = QWidget()
        scenes_layout = QVBoxLayout(scenes_panel)
        scenes_layout.setContentsMargins(0, 4, 0, 4)
        scenes_title = QLabel("🖼️ 3x3 스토리보드 정밀 분할 씬 (StoryBoard-Division):")
        scenes_title.setStyleSheet("font-weight: bold; color: #f9e2af; font-size: 12px;")
        scenes_layout.addWidget(scenes_title)

        scenes_grid = QGridLayout()
        scenes_grid.setSpacing(6)
        scenes_grid.setContentsMargins(0, 0, 0, 0)
        self.scene_labels = []
        for i in range(9):
            lbl = QLabel(f"Scene {i+1}\n(대기 중)")
            lbl.setObjectName("SceneCell")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setMinimumSize(85, 85)
            row, col = divmod(i, 3)
            scenes_grid.addWidget(lbl, row, col)
            self.scene_labels.append(lbl)
        scenes_layout.addLayout(scenes_grid)
        splitter.addWidget(scenes_panel)

        # 스플리터 비율 설정: 로그 창 55%, 3x3 분할 씬 45%
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)
        right_layout.addWidget(splitter)

        # 결과 버튼 행
        action_row = QHBoxLayout()
        self.open_folder_btn = QPushButton("📂 결과 저장 폴더 열기")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.setEnabled(False)

        self.play_video_btn = QPushButton("▶️ 완성된 1080p 영상 재생")
        self.play_video_btn.clicked.connect(self.play_video)
        self.play_video_btn.setEnabled(False)

        action_row.addWidget(self.open_folder_btn)
        action_row.addWidget(self.play_video_btn)
        right_layout.addLayout(action_row)

        body_layout.addWidget(right_box, 60)
        main_layout.addLayout(body_layout)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def _on_lyrics_changed(self, index: int):
        # 0: 가사 없음 (연주곡), 1: 가사 있음 (보컬 곡)
        self.lyrics_box.setVisible(index == 1)

    def start_generation(self):
        mood = self.mood_input.toPlainText().strip()
        if not mood:
            QMessageBox.warning(self, "입력 필요", "원하시는 음악과 영상의 분위기/무드를 입력해주세요.")
            return

        if not Config.get_gemini_key() or not Config.get_suno_key() or not Config.get_nano_key():
            QMessageBox.warning(self, "API 키 필요", "상단 [API 키 설정]에서 Gemini 및 Apiframe 키를 등록해주세요.")
            return

        self.gen_btn.setEnabled(False)
        self.encode_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)
        self.play_video_btn.setEnabled(False)
        self.log_console.clear()
        self.progress_bar.setValue(0)
        self.update_step(0)  # 5단계 뱃지 초기화

        # 3x3 씬 라벨 초기화
        for i, lbl in enumerate(self.scene_labels):
            lbl.setPixmap(QPixmap())
            lbl.setText(f"Scene {i+1}\n(생성 중...)")

        genre = self.genre_combo.currentText()
        is_inst = (self.lyrics_combo.currentIndex() == 0)
        custom_lyrics = self.lyrics_input.toPlainText().strip() if not is_inst else ""

        # 페이드 시간 파싱
        fade_txt = self.fade_combo.currentText()
        fade_dur = 1.5
        if "2.0" in fade_txt:
            fade_dur = 2.0
        elif "1.0" in fade_txt:
            fade_dur = 1.0
        elif "0초" in fade_txt:
            fade_dur = 0.0

        self.worker = AutomationWorker(mood, genre, is_inst, fade_duration=fade_dur, custom_lyrics=custom_lyrics)
        self.worker.step_signal.connect(self.update_step)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.append_log)
        self.worker.scenes_ready_signal.connect(self.display_scenes)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)

        # 렌더링 진행 팝업 창 가동 (실시간 진행시간, 단계, 프로그레스바, 진행율)
        if not self.progress_dialog:
            self.progress_dialog = RenderingProgressDialog(self)
        self.worker.step_signal.connect(self.progress_dialog.update_step)
        self.worker.progress_signal.connect(self.progress_dialog.update_progress)
        self.progress_dialog.start_timer()
        self.progress_dialog.show()

        self.worker.start()

    def start_manual_encoding(self):
        """기존 프로젝트 세션 폴더를 선택하여 프로그램 내부 인코딩 엔진으로 직접 렌더링"""
        default_dir = str(OUTPUT_DIR)
        subdirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir()] if OUTPUT_DIR.exists() else []
        if subdirs:
            subdirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            default_dir = str(subdirs[0])

        target_dir = QFileDialog.getExistingDirectory(
            self,
            "인코딩 엔진으로 렌더링할 프로젝트 세션 폴더 선택",
            default_dir
        )
        if not target_dir:
            return

        p = Path(target_dir)
        if not list(p.glob("*.mp3")):
            QMessageBox.warning(self, "오디오 파일 없음", f"선택한 폴더에 mp3 파일이 없습니다:\n{target_dir}")
            return

        self.gen_btn.setEnabled(False)
        self.encode_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)
        self.play_video_btn.setEnabled(False)
        self.log_console.clear()
        self.progress_bar.setValue(0)
        self.update_step(4)

        # 페이드 시간 파싱
        fade_txt = self.fade_combo.currentText()
        fade_dur = 1.5
        if "2.0" in fade_txt:
            fade_dur = 2.0
        elif "1.0" in fade_txt:
            fade_dur = 1.0
        elif "0초" in fade_txt:
            fade_dur = 0.0

        self.worker = EncodingWorker(p, fade_duration=fade_dur)
        self.worker.step_signal.connect(self.update_step)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.append_log)
        self.worker.scenes_ready_signal.connect(self.display_scenes)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_signal.connect(self.on_error)

        if not self.progress_dialog:
            self.progress_dialog = RenderingProgressDialog(self)
        self.worker.step_signal.connect(self.progress_dialog.update_step)
        self.worker.progress_signal.connect(self.progress_dialog.update_progress)
        self.progress_dialog.start_timer()
        self.progress_dialog.show()

        self.worker.start()

    def update_step(self, step_num: int):
        """처음부터 끝까지 5단계 진행 상태 뱃지를 실시간으로 하이라이트/체크 갱신"""
        for i, badge in enumerate(self.step_badges):
            idx = i + 1
            if step_num == 6:  # 전체 완료
                badge.setText(f"✓ {self.STEP_NAMES[i]}")
                badge.setProperty("class", "StepBadgeDone")
            elif idx < step_num:
                badge.setText(f"✓ {self.STEP_NAMES[i]}")
                badge.setProperty("class", "StepBadgeDone")
            elif idx == step_num:
                badge.setText(f"⏳ {self.STEP_NAMES[i]}")
                badge.setProperty("class", "StepBadgeActive")
            else:
                badge.setText(self.STEP_NAMES[i])
                badge.setProperty("class", "StepBadge")
            badge.style().unpolish(badge)
            badge.style().polish(badge)

    def display_scenes(self, thumb_paths: list):
        """StoryBoard-Division 기반: 9개 분할 씬 썸네일을 3x3 그리드에 시각화"""
        for idx, tp in enumerate(thumb_paths[:9]):
            if idx < len(self.scene_labels):
                try:
                    img = Image.open(tp)
                    pixmap = ImageProcessor.pil_to_pixmap(img)
                    if pixmap and not pixmap.isNull():
                        scaled = pixmap.scaled(
                            self.scene_labels[idx].size(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        self.scene_labels[idx].setPixmap(scaled)
                except Exception:
                    pass

    def update_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(msg)

    def append_log(self, text: str):
        """실시간 콘솔 로그에 타임스탬프를 부여하고 자동 스크롤 유지"""
        timestamp_str = time.strftime("[%H:%M:%S] ")
        self.log_console.append(f"{timestamp_str}{text}")
        self.log_console.verticalScrollBar().setValue(
            self.log_console.verticalScrollBar().maximum()
        )

    def on_finished(self, mp4_path: str, mp3_path: str, scenes: list):
        self.gen_btn.setEnabled(True)
        self.encode_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)
        self.play_video_btn.setEnabled(True)
        self.last_mp4 = mp4_path

        if self.progress_dialog:
            self.progress_dialog.set_completed()

        QMessageBox.information(
            self,
            "🎉 렌더링 제작 완료",
            f"고화질 1080p 영상 제작 및 인코딩이 모두 성공적으로 완료되었습니다!\n\n"
            f"저장 파일: {os.path.basename(mp4_path)}\n"
            f"위치: {mp4_path}"
        )

    def on_error(self, err_msg: str):
        self.gen_btn.setEnabled(True)
        self.encode_btn.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.hide()
        QMessageBox.critical(self, "오류 발생", f"작업 중 오류가 발생했습니다:\n{err_msg}")

    def closeEvent(self, event):
        """렌더링 진행 중 사용자가 실수로 프로그램을 끄지 못하도록 확인 모달 제공"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "⚠️ 렌더링 진행 중 강제 종료 확인",
                "고화질 영상 렌더링 및 생성이 현재 백그라운드에서 진행 중입니다.\n\n"
                "작업은 시스템 사양에 따라 최대 17~20분가량 소요될 수 있으며,\n"
                "지금 프로그램을 강제 종료하시면 생성 중인 모든 영상과 음악이 손실됩니다.\n\n"
                "정말로 작업을 중단하고 프로그램을 강제 종료하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    self.worker.terminate()
                except Exception:
                    pass
                if self.progress_dialog:
                    self.progress_dialog.timer.stop()
                    self.progress_dialog.close()
                event.accept()
            else:
                event.ignore()
        else:
            if self.progress_dialog:
                self.progress_dialog.close()
            event.accept()

    def open_output_folder(self):
        target = Path(self.last_mp4).parent if self.last_mp4 else OUTPUT_DIR
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target.resolve())))

    def play_video(self):
        if self.last_mp4 and os.path.exists(self.last_mp4):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.last_mp4).resolve())))
        else:
            QMessageBox.warning(self, "파일 없음", "재생할 영상 파일이 존재하지 않습니다.")

def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
