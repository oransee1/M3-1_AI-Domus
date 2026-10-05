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
        9장의 씬 이미지를 1920x1080 (16:9 FHD) 초고화질 규격으로 변환합니다.
        16:9 와이드스크린 씬은 화면 전체를 꽉 채우는 풀스크린 시네마틱 프레이밍과
        고해상도 언샤프 마스크(Unsharp Mask) 필터를 적용하여 칼같은 선명도와 디테일을 구현합니다.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        fhd_paths = []

        for idx, sp in enumerate(scene_paths, start=1):
            scene_img = Image.open(sp).convert("RGB")
            sw, sh = scene_img.size
            aspect_ratio = sw / sh

            # 1. 16:9 와이드스크린 씬 (1.5 ~ 2.1 비율):
            # 블러 여백 없이 1920x1080 전체 화면을 선명하게 채우는 풀스크린 시네마틱 구도
            if 1.5 <= aspect_ratio <= 2.1:
                scale = max(width / sw, height / sh)
                nw = int(round(sw * scale))
                nh = int(round(sh * scale))
                resized = scene_img.resize((nw, nh), Image.Resampling.LANCZOS)
                left = (nw - width) // 2
                top = (nh - height) // 2
                frame = resized.crop((left, top, left + width, top + height))
            else:
                # 정사각/세로형 등 특수 비율인 경우: 배경 블러 확장 + 전면 중앙 배치
                bg_scale = max(width / sw, height / sh)
                bg_size = (int(sw * bg_scale), int(sh * bg_scale))
                bg_img = scene_img.resize(bg_size, Image.Resampling.LANCZOS)
                bg_left = (bg_img.width - width) // 2
                bg_top = (bg_img.height - height) // 2
                frame = bg_img.crop((bg_left, bg_top, bg_left + width, bg_top + height)).filter(ImageFilter.GaussianBlur(radius=25))

                fg_scale = min(width / sw, height / sh)
                fg_w = int(sw * fg_scale)
                fg_h = int(sh * fg_scale)
                fg_resized = scene_img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
                pos_x = (width - fg_w) // 2
                pos_y = (height - fg_h) // 2
                frame.paste(fg_resized, (pos_x, pos_y))

            # 2. 초고화질 선명도(Sharpness) 및 질감 디테일 보정:
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
    def prepare_logo(logo_path: Path, output_file: Path, max_width: int = 50, max_height: int = 50) -> Path:
        """
        사용자가 지정한 외부 로고 이미지를 1080p FHD 영상 좌측 상단 규격(50x50px)에 맞게
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

    @staticmethod
    def prepare_bottom_image(image_path: Path, output_file: Path, max_width: int = 180, max_height: int = 80) -> Path:
        """
        사용자가 지정한 외부 하단 이미지를 1080p FHD 영상 좌측 하단 규격에 맞게
        원본 종횡비를 유지하며 리사이즈하고 투명 알파(RGBA) PNG로 정제합니다.
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        img = Image.open(image_path).convert("RGBA")
        w, h = img.size

        scale = min(max_width / w, max_height / h, 1.0)
        target_w = max(1, int(w * scale))
        target_h = max(1, int(h * scale))

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

