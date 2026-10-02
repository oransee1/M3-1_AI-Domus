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
