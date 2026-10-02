from pathlib import Path
from typing import List
from PIL import Image, ImageFilter

class ImageProcessor:
    @staticmethod
    def split_3x3_grid(image_path: Path, output_dir: Path) -> List[Path]:
        """
        3x3 스토리보드 원본 이미지를 9개의 고화질 씬 이미지로 자동 슬라이싱합니다.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        img = Image.open(image_path).convert("RGB")
        width, height = img.size

        tile_w = width // 3
        tile_h = height // 3

        scene_paths = []
        count = 1
        for row in range(3):
            for col in range(3):
                left = col * tile_w
                top = row * tile_h
                right = left + tile_w if col < 2 else width
                bottom = top + tile_h if row < 2 else height

                cropped = img.crop((left, top, right, bottom))
                scene_file = output_dir / f"scene_{count:02d}.png"
                cropped.save(scene_file, "PNG", quality=95)
                scene_paths.append(scene_file)
                count += 1

        return scene_paths

    @staticmethod
    def prepare_16_9_frames(scene_paths: List[Path], target_dir: Path, width: int = 1920, height: int = 1080) -> List[Path]:
        """
        9장의 씬 이미지를 1920x1080 (16:9 FHD) 규격으로 변환합니다.
        배경은 원본을 블러 확장하여 채우고 중앙에 선명한 씬을 배치하여
        유튜브 힐링 음악 채널 특유의 고급스러운 시각 효과를 연출합니다.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        fhd_paths = []

        for idx, sp in enumerate(scene_paths, start=1):
            scene_img = Image.open(sp).convert("RGB")
            sw, sh = scene_img.size

            # 1. 배경 생성: 화면 전체를 채우도록 리사이즈 후 가우시안 블러
            bg_scale = max(width / sw, height / sh)
            bg_size = (int(sw * bg_scale), int(sh * bg_scale))
            bg_img = scene_img.resize(bg_size, Image.Resampling.LANCZOS)
            
            # 중앙 크롭하여 1920x1080
            bg_left = (bg_img.width - width) // 2
            bg_top = (bg_img.height - height) // 2
            bg_cropped = bg_img.crop((bg_left, bg_top, bg_left + width, bg_top + height))
            blurred_bg = bg_cropped.filter(ImageFilter.GaussianBlur(radius=25))

            # 2. 전면 이미지: 높이에 맞춰 비율 유지 리사이즈 (1080 높이에 맞춤)
            fg_scale = height / sh
            fg_w = int(sw * fg_scale)
            fg_h = height
            fg_resized = scene_img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

            # 3. 합성 (중앙 배치)
            pos_x = (width - fg_w) // 2
            pos_y = 0
            blurred_bg.paste(fg_resized, (pos_x, pos_y))

            out_path = target_dir / f"frame_{idx:02d}.png"
            blurred_bg.save(out_path, "PNG", quality=95)
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
    def prepare_logo(logo_path: Path, output_file: Path, max_width: int = 240, max_height: int = 100) -> Path:
        """
        사용자가 지정한 외부 로고 이미지를 1080p FHD 영상 우측 상단 규격에 맞게
        원본 종횡비를 유지하며 리사이즈하고 투명 알파(RGBA) PNG로 정제합니다.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(logo_path).convert("RGBA")
        w, h = img.size

        # 가로 및 세로 최대 크기 제한에 맞추어 종횡비 유지 스케일 계산
        scale = min(max_width / w, max_height / h, 1.0)
        target_w = max(1, int(w * scale))
        target_h = max(1, int(h * scale))

        resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        resized.save(output_file, "PNG")
        return output_file

