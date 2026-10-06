import numpy as np
from pathlib import Path
from typing import List
from PIL import Image, ImageFilter

class ImageProcessor:
    @staticmethod
    def _detect_grid_spans(prof_mean: np.ndarray, prof_std: np.ndarray, length: int) -> List[tuple]:
        """
        스토리보드 3x3 이미지의 외곽 테두리(Border) 및 내부 격자 분할선(Gutter)을 지능적으로 감지하여
        블랙바, 화이트바 및 불필요한 테두리가 완전히 제거된 순수 콘텐츠 3구간의 [start, end) 좌표를 반환합니다.
        어두운 테두리(검정/어두운 회색)와 밝은 테두리(흰색/연회색), 단색 분할선 모두 완벽하게 식별합니다.
        """
        center_med = float(np.median(prof_mean[int(length * 0.2):int(length * 0.8)]))
        thresh_dark = min(45.0, center_med * 0.45)
        thresh_light = 235.0

        def is_gutter(idx: int) -> bool:
            m = prof_mean[idx]
            s = prof_std[idx]
            return bool(m <= thresh_dark or m >= thresh_light or s <= 8.0)

        # 외곽 시작 테두리 (전체 길이의 최대 12%까지 검색)
        s0 = 0
        while s0 < length * 0.12 and is_gutter(s0):
            s0 += 1

        # 외곽 끝 테두리 (전체 길이의 88% 이후부터 역방향 검색)
        s3 = length - 1
        while s3 > length * 0.88 and is_gutter(s3):
            s3 -= 1
        s3 += 1

        # 1차 내부 분할선 (1/3 지점 부근: 28% ~ 38% 검색 - 표준편차 최소 지점 우선 탐색)
        win1_s, win1_e = int(length * 0.28), int(length * 0.38)
        v1 = win1_s + int(np.argmin(prof_std[win1_s:win1_e]))
        if not is_gutter(v1):
            v1_dark = win1_s + int(np.argmin(prof_mean[win1_s:win1_e]))
            v1_light = win1_s + int(np.argmax(prof_mean[win1_s:win1_e]))
            if is_gutter(v1_dark):
                v1 = v1_dark
            elif is_gutter(v1_light):
                v1 = v1_light

        if is_gutter(v1):
            d1_left = v1
            while d1_left > win1_s and is_gutter(d1_left - 1):
                d1_left -= 1
            d1_right = v1
            while d1_right < win1_e and is_gutter(d1_right + 1):
                d1_right += 1
        else:
            d1_left = int(length / 3)
            d1_right = d1_left

        # 2차 내부 분할선 (2/3 지점 부근: 62% ~ 72% 검색 - 표준편차 최소 지점 우선 탐색)
        win2_s, win2_e = int(length * 0.62), int(length * 0.72)
        v2 = win2_s + int(np.argmin(prof_std[win2_s:win2_e]))
        if not is_gutter(v2):
            v2_dark = win2_s + int(np.argmin(prof_mean[win2_s:win2_e]))
            v2_light = win2_s + int(np.argmax(prof_mean[win2_s:win2_e]))
            if is_gutter(v2_dark):
                v2 = v2_dark
            elif is_gutter(v2_light):
                v2 = v2_light

        if is_gutter(v2):
            d2_left = v2
            while d2_left > win2_s and is_gutter(d2_left - 1):
                d2_left -= 1
            d2_right = v2
            while d2_right < win2_e and is_gutter(d2_right + 1):
                d2_right += 1
        else:
            d2_left = int(length * 2 / 3)
            d2_right = d2_left

        # 안전 검증: 각 셀 크기가 최소 20% 이상 확보되지 않으면 기본 3등분으로 안전 폴백
        min_cell = int(length * 0.2)
        if (d1_left - s0 < min_cell) or (d2_left - (d1_right + 1) < min_cell) or (s3 - (d2_right + 1) < min_cell):
            tile = length // 3
            return [(0, tile), (tile, tile * 2), (tile * 2, length)]

        return [(s0, d1_left), (d1_right + 1, d2_left), (d2_right + 1, s3)]

    @staticmethod
    def split_3x3_grid(image_path: Path, output_dir: Path) -> List[Path]:
        """
        3x3 스토리보드 원본 이미지를 9개의 고화질 씬 이미지로 정밀 슬라이싱합니다.
        외곽 테두리 및 격자 구분선을 지능적으로 감지하여 검은 여백 없는 순수 씬만 크롭합니다.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        img = Image.open(image_path).convert("RGB")
        width, height = img.size

        try:
            arr = np.array(img)
            col_mean = arr.mean(axis=(0, 2))
            col_std = arr.std(axis=(0, 2))
            row_mean = arr.mean(axis=(1, 2))
            row_std = arr.std(axis=(1, 2))

            col_spans = ImageProcessor._detect_grid_spans(col_mean, col_std, width)
            row_spans = ImageProcessor._detect_grid_spans(row_mean, row_std, height)
        except Exception:
            tile_w = width // 3
            tile_h = height // 3
            col_spans = [(0, tile_w), (tile_w, tile_w * 2), (tile_w * 2, width)]
            row_spans = [(0, tile_h), (tile_h, tile_h * 2), (tile_h * 2, height)]

        scene_paths = []
        count = 1
        for r_start, r_end in row_spans:
            for c_start, c_end in col_spans:
                cropped = img.crop((c_start, r_start, c_end, r_end))
                scene_file = output_dir / f"scene_{count:02d}.png"
                cropped.save(scene_file, "PNG", quality=95)
                scene_paths.append(scene_file)
                count += 1

        return scene_paths

    @staticmethod
    def prepare_16_9_frames(scene_paths: List[Path], target_dir: Path, width: int = 1920, height: int = 1080) -> List[Path]:
        """
        9장의 씬 이미지를 1920x1080 (16:9 FHD) 초고화질 규격으로 변환합니다.
        모든 이미지가 화면 전체를 100% 꽉 채우는 풀스크린 시네마틱 프레이밍(Scale-to-Fill)과
        중앙 정렬을 통해 동일한 위치에서 일관되게 렌더링되도록 보장합니다.
        초고해상도 언샤프 마스크(Unsharp Mask) 필터를 적용하여 칼같은 선명도와 디테일을 구현합니다.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        fhd_paths = []

        for idx, sp in enumerate(scene_paths, start=1):
            scene_img = Image.open(sp).convert("RGB")
            sw, sh = scene_img.size

            # 모든 씬 이미지를 1920x1080 전체 화면에 가득 채우는 풀스크린 시네마틱 구도 (Scale-to-Fill)
            # 검은 여백(블랙바)이나 위치 쏠림 없이 모든 씬이 화면 중앙 동일 위치에서 꽉 찬 16:9 화면으로 출력
            scale = max(width / sw, height / sh)
            nw = int(round(sw * scale))
            nh = int(round(sh * scale))
            resized = scene_img.resize((nw, nh), Image.Resampling.LANCZOS)
            left = (nw - width) // 2
            top = (nh - height) // 2
            frame = resized.crop((left, top, left + width, top + height))

            # 초고화질 선명도(Sharpness) 및 질감 디테일 보정:
            # 업스케일링 과정에서의 미세 블러를 제거하고 고해상도 특유의 선명한 질감 연출
            frame = frame.filter(ImageFilter.UnsharpMask(radius=1.2, percent=125, threshold=2))

            out_path = target_dir / f"frame_{idx:02d}.png"
            frame.save(out_path, "PNG", compress_level=1)
            fhd_paths.append(out_path)

        return fhd_paths


    @staticmethod
    def create_thumbnail(img: Image.Image, max_size: tuple = (320, 320)) -> Image.Image:
        """
        StoryBoard-Division 기반: 원본 비율을 보존하며 고품질 썸네일을 생성합니다.
        """
        img_copy = img.copy()
        img_copy.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img_copy

    @staticmethod
    def generate_thumbnails(scene_paths: List[Path], thumb_dir: Path, size: tuple = (240, 240)) -> List[Path]:
        """
        GUI 프리뷰용 9개 씬 썸네일 이미지를 일괄 생성하여 저장합니다.
        """
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_paths = []
        for sp in scene_paths:
            img = Image.open(sp).convert("RGB")
            thumb = ImageProcessor.create_thumbnail(img, size)
            t_path = thumb_dir / f"thumb_{sp.name}"
            thumb.save(t_path, "PNG")
            thumb_paths.append(t_path)
        return thumb_paths

    @staticmethod
    def pil_to_pixmap(pil_img: Image.Image):
        """
        StoryBoard-Division 기반:
        PIL Image를 PyQt5 QPixmap으로 변환할 때 Qt SIMD 컬러 변환 시
        발생할 수 있는 메모리 접근 위반(0xC0000005)을 원천 차단하는 안전 변환기.
        """
        try:
            from PyQt5.QtGui import QPixmap, QImage
            if pil_img is None or pil_img.width <= 0 or pil_img.height <= 0:
                return QPixmap()

            if pil_img.mode != "RGBA":
                converted = pil_img.convert("RGBA")
            else:
                converted = pil_img

            data = converted.tobytes("raw", "BGRA")
            qimg = QImage(
                data,
                converted.width,
                converted.height,
                converted.width * 4,
                QImage.Format_ARGB32,
            ).copy()
            return QPixmap.fromImage(qimg)
        except Exception:
            return None

    @staticmethod
    def prepare_logo(logo_path: Path, output_file: Path, max_width: int = 150, max_height: int = 150) -> Path:
        """
        사용자가 지정한 외부 로고 이미지를 1080p FHD 영상 좌측 상단 규격(150x150px, 기존 50x50px의 3배 확대 규격)에 맞게
        원본 종횡비를 유지하며 리사이즈하고 투명 알파(RGBA) PNG로 정제합니다.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(logo_path).convert("RGBA")
        w, h = img.size

        # 가로 및 세로 최대 크기 제한에 맞추어 종횡비 유지 스케일 계산 (기존 대비 3배 크기 150x150px)
        scale = min(max_width / w, max_height / h)
        target_w = max(1, int(round(w * scale)))
        target_h = max(1, int(round(h * scale)))

        resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        resized.save(output_file, "PNG")
        return output_file

    @staticmethod
    def prepare_bottom_image(image_path: Path, output_file: Path, max_width: int = 270, max_height: int = 120) -> Path:
        """
        사용자가 지정한 외부 하단 이미지를 1080p FHD 영상 하단 규격(270x120px, 기존 180x80px의 1.5배 확대 규격)에 맞게
        원본 종횡비를 유지하며 리사이즈하고 투명 알파(RGBA) PNG로 정제합니다.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(image_path).convert("RGBA")
        w, h = img.size

        # 가로 및 세로 최대 크기 제한에 맞추어 종횡비 유지 스케일 계산 (기존 대비 1.5배 크기 270x120px)
        scale = min(max_width / w, max_height / h)
        target_w = max(1, int(round(w * scale)))
        target_h = max(1, int(round(h * scale)))

        resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        resized.save(output_file, "PNG")
        return output_file

    @staticmethod
    def create_title_overlay(
        title_text: str,
        output_file: Path,
        font_size: int = 24,
        max_width: int = 800
    ) -> Path:
        """
        영상 우측 상단(Top-Right)에 합성할 세련되고 가독성 높은 반투명 배지 형태의
        제목 오버레이(RGBA PNG) 이미지를 자동 생성합니다.
        Windows 시스템 한글 폰트(맑은 고딕 등)를 탐색하여 글자 깨짐 없이 선명하게 렌더링합니다.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        from PIL import ImageDraw, ImageFont

        # 폰트 로드 (맑은 고딕 볼드 -> 맑은 고딕 -> 굴림 -> Arial -> 기본 폰트)
        font_candidates = [
            "C:/Windows/Fonts/malgunbd.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "C:/Windows/Fonts/gulim.ttc",
            "C:/Windows/Fonts/batang.ttc",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        font = None
        for fp in font_candidates:
            if Path(fp).exists():
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except Exception:
                    continue
        if font is None:
            font = ImageFont.load_default()

        # 긴 제목 길이 제한 및 말줄임표 처리
        text = title_text.strip()
        dummy = Image.new("RGBA", (1, 1))
        draw_d = ImageDraw.Draw(dummy)

        while len(text) > 4:
            bbox = draw_d.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                break
            text = text[:-4] + "..."

        bbox = draw_d.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        pad_x = 18
        pad_y = 10
        img_w = text_w + pad_x * 2
        img_h = max(46, text_h + pad_y * 2)

        overlay_img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay_img)

        # 고급스럽고 모던한 다크 반투명 필(Pill) 배지 배경 (보더 포함)
        draw.rounded_rectangle(
            [(0, 0), (img_w - 1, img_h - 1)],
            radius=10,
            fill=(17, 17, 27, 190),
            outline=(255, 255, 255, 45),
            width=1
        )

        # 텍스트 수직 및 수평 중앙 정렬
        tx = pad_x - bbox[0]
        ty = (img_h - text_h) // 2 - bbox[1]
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 245))

        overlay_img.save(output_file, "PNG")
        return output_file

