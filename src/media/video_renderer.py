import subprocess
import re
from pathlib import Path
from typing import List, Callable, Optional
from src.config import Config

class VideoRenderer:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or Config.get_ffmpeg_path()

    def get_audio_duration(self, audio_path: Path) -> float:
        """
        FFmpeg를 통해 오디오 파일의 총 재생시간(초)을 측정합니다.
        """
        cmd = [self.ffmpeg_path, "-i", str(audio_path)]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors="ignore")
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if match:
            hours = float(match.group(1))
            minutes = float(match.group(2))
            seconds = float(match.group(3))
            return hours * 3600 + minutes * 60 + seconds
        return 180.0  # 기본 3분 대체값

    def render_slideshow(
        self,
        image_paths: List[Path],
        audio_path: Path,
        output_mp4: Path,
        total_duration: Optional[float] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Path:
        """
        9장의 이미지를 오디오 길이에 맞춰 균등 분배한 후 1080p FHD MP4 비디오로 인코딩합니다.
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        if total_duration is None or total_duration <= 0:
            total_duration = self.get_audio_duration(audio_path)

        num_images = len(image_paths)
        if num_images == 0:
            raise ValueError("렌더링할 이미지가 없습니다.")

        time_per_image = total_duration / num_images

        # concat 스크립트 작성
        concat_file = output_mp4.parent / "concat_list.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for img in image_paths:
                # 윈도우 경로 역슬래시 처리
                safe_path = str(img.resolve()).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
                f.write(f"duration {time_per_image:.3f}\n")
            # 마지막 프레임 한번 더 명시 (FFmpeg concat 규격)
            last_path = str(image_paths[-1].resolve()).replace("\\", "/")
            f.write(f"file '{last_path}'\n")

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_mp4)
        ]

        if progress_callback:
            progress_callback(5, "FFmpeg 렌더링 파이프라인 가동...")

        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            errors="ignore",
            bufsize=1
        )

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

        for line in process.stderr:
            match = time_pattern.search(line)
            if match and total_duration > 0:
                h = float(match.group(1))
                m = float(match.group(2))
                s = float(match.group(3))
                cur_sec = h * 3600 + m * 60 + s
                percent = min(99, int((cur_sec / total_duration) * 100))
                if progress_callback:
                    progress_callback(percent, f"영상 인코딩 중... ({percent}% | {int(cur_sec)}s / {int(total_duration)}s)")

        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg 렌더링 실패 (Exit code {process.returncode})")

        # 임시 concat 파일 정리
        try:
            concat_file.unlink(missing_ok=True)
        except Exception:
            pass

        if progress_callback:
            progress_callback(100, "1080p 고화질 영상 렌더링 완료!")

        return output_mp4
