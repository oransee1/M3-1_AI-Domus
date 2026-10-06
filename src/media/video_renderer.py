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
        fade_duration: float = 1.5,
        logo_path: Optional[Path] = None,
        title_path: Optional[Path] = None,
        bottom_image_path: Optional[Path] = None,
        bottom_image_pos: str = "bottom_right",
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Path:
        """
        MoveEditor-AutoProgram 기반:
        9장의 씬 이미지를 BGM 길이에 맞춰 균등 배분하고,
        씬 간 부드러운 크로스페이드(Fade In / Fade Out) 전환 효과 및
        영상 시작/종료 페이드 효과를 적용하여 1080p FHD MP4 비디오로 렌더링합니다.
        외부 로고 이미지가 지정된 경우 영상 좌측 상단(Top-Left: 35:35)에 오버레이 합성하며,
        영상 제목이 지정된 경우 영상 우측 상단(Top-Right: W-w-35:35)에 오버레이 합성하며,
        하단 이미지가 지정된 경우 영상 하단(Bottom-Right: W-w-35:H-h-35 또는 Bottom-Left: 35:H-h-35)에 오버레이 합성합니다.
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        if total_duration is None or total_duration <= 0:
            total_duration = self.get_audio_duration(audio_path)

        num_images = len(image_paths)
        if num_images == 0:
            raise ValueError("렌더링할 이미지가 없습니다.")

        has_logo = bool(logo_path and Path(logo_path).exists())
        has_title = bool(title_path and Path(title_path).exists())
        has_bottom_image = bool(bottom_image_path and Path(bottom_image_path).exists())

        # 페이드 시간이 비활성화되어 있거나 이미지가 1장일 경우 고속 concat 모드
        if fade_duration <= 0 or num_images < 2:
            return self._render_concat_fallback(image_paths, audio_path, output_mp4, total_duration, logo_path, title_path, bottom_image_path, bottom_image_pos, progress_callback)

        # MoveEditor-AutoProgram 방식: 오버랩 페이드 시간을 고려한 씬 지속시간 계산
        # N * scene_dur - (N - 1) * fade_duration = total_duration
        scene_dur = (total_duration + (num_images - 1) * fade_duration) / num_images

        # FFmpeg 파이프라인 구성
        cmd = [self.ffmpeg_path, "-y"]

        # 1. 9개 이미지 인풋 루프 등록
        for img in image_paths:
            safe_path = str(img.resolve()).replace("\\", "/")
            cmd.extend(["-loop", "1", "-t", f"{scene_dur:.3f}", "-i", safe_path])

        # 2. 오디오 인풋 등록
        audio_safe_path = str(audio_path.resolve()).replace("\\", "/")
        audio_index = num_images
        cmd.extend(["-i", audio_safe_path])

        # 3. 추가 오버레이 인풋 등록 (로고: 좌측 상단 / 제목: 우측 상단 / 하단 이미지: 좌측 하단)
        current_input_index = num_images + 1
        logo_index = None
        if has_logo:
            safe_logo_path = str(Path(logo_path).resolve()).replace("\\", "/")
            cmd.extend(["-i", safe_logo_path])
            logo_index = current_input_index
            current_input_index += 1

        title_index = None
        if has_title:
            safe_title_path = str(Path(title_path).resolve()).replace("\\", "/")
            cmd.extend(["-i", safe_title_path])
            title_index = current_input_index
            current_input_index += 1

        bottom_image_index = None
        if has_bottom_image:
            safe_bottom_image_path = str(Path(bottom_image_path).resolve()).replace("\\", "/")
            cmd.extend(["-i", safe_bottom_image_path])
            bottom_image_index = current_input_index
            current_input_index += 1

        # 4. Filter Complex 생성 (씬 간 크로스페이드 + 시작/종료 페이드 + 좌측 상단 로고 + 우측 상단 제목 + 좌측 하단 이미지)
        filter_parts = []
        last_label = "0:v"
        for i in range(1, num_images):
            offset = i * (scene_dur - fade_duration)
            next_input = f"{i}:v"
            out_label = f"v{i}" if i < num_images - 1 else "v_crossfaded"
            filter_parts.append(
                f"[{last_label}][{next_input}]xfade=transition=fade:duration={fade_duration:.3f}:offset={offset:.3f}[{out_label}]"
            )
            last_label = out_label

        # 영상 시작 페이드 인 및 종료 페이드 아웃
        fade_out_st = max(0.0, total_duration - fade_duration)
        if has_logo or has_title or has_bottom_image:
            filter_parts.append(
                f"[v_crossfaded]fade=t=in:st=0:d={fade_duration:.3f},fade=t=out:st={fade_out_st:.3f}:d={fade_duration:.3f}[v_fade]"
            )
            current_v = "v_fade"

            # 좌측 상단 로고 오버레이 (150x150px 규격, 좌측 35px / 상단 35px 여백 - 기존 대비 3배 확대)
            if has_logo:
                filter_parts.append(
                    f"[{logo_index}:v]scale=w='min(150,iw)':h=-1[logo_scaled]"
                )
                next_v = "v_after_logo" if (has_title or has_bottom_image) else "vout"
                filter_parts.append(
                    f"[{current_v}][logo_scaled]overlay=35:35[{next_v}]"
                )
                current_v = next_v

            # 우측 상단 제목 배지 오버레이 (우측 35px / 상단 35px 여백)
            if has_title:
                next_v = "v_after_title" if has_bottom_image else "vout"
                filter_parts.append(
                    f"[{current_v}][{title_index}:v]overlay=W-w-35:35[{next_v}]"
                )
                current_v = next_v

            # 하단 이미지 오버레이 (우측 하단: W-w-35:H-h-35, 좌측 하단: 35:H-h-35 - 기존 대비 1.5배 확대 270x120px)
            if has_bottom_image:
                filter_parts.append(
                    f"[{bottom_image_index}:v]scale=w='min(270,iw)':h='min(120,ih)':force_original_aspect_ratio=decrease[bimg_scaled]"
                )
                bpos_coords = "W-w-35:H-h-35" if bottom_image_pos == "bottom_right" else "35:H-h-35"
                filter_parts.append(
                    f"[{current_v}][bimg_scaled]overlay={bpos_coords}[vout]"
                )
        else:
            filter_parts.append(
                f"[v_crossfaded]fade=t=in:st=0:d={fade_duration:.3f},fade=t=out:st={fade_out_st:.3f}:d={fade_duration:.3f}[vout]"
            )

        # 오디오 페이드 인/아웃 (부드러운 사운드 마감)
        audio_fade_out_st = max(0.0, total_duration - 2.0)
        filter_parts.append(
            f"[{audio_index}:a]afade=t=in:st=0:d=1.0,afade=t=out:st={audio_fade_out_st:.3f}:d=2.0[aout]"
        )

        filter_complex = ";".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "17",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{total_duration:.3f}",
            str(output_mp4)
        ])

        if progress_callback:
            progress_callback(5, "FFmpeg 씬 페이드 트랜지션 및 1080p 인코딩 파이프라인 가동...")

        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
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
                    progress_callback(percent, f"페이드 씬 합성 인코딩 중... ({percent}% | {int(cur_sec)}s / {int(total_duration)}s)")

        process.wait()
        if process.returncode != 0:
            # 실패 시 안전하게 concat fallback 시도
            if progress_callback:
                progress_callback(50, "페이드 필터 오류로 기본 슬라이드 모드로 안전 전환...")
            return self._render_concat_fallback(image_paths, audio_path, output_mp4, total_duration, logo_path, title_path, bottom_image_path, bottom_image_pos, progress_callback)

        if not output_mp4.exists() or output_mp4.stat().st_size == 0:
            raise RuntimeError(f"영상 렌더링 실패: 최종 파일이 생성되지 않았습니다 ({output_mp4.name})")

        if progress_callback:
            progress_callback(100, "1080p 페이드 영상 렌더링 완료!")

        return output_mp4

    def _render_concat_fallback(
        self,
        image_paths: List[Path],
        audio_path: Path,
        output_mp4: Path,
        total_duration: float,
        logo_path: Optional[Path] = None,
        title_path: Optional[Path] = None,
        bottom_image_path: Optional[Path] = None,
        bottom_image_pos: str = "bottom_right",
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Path:
        """기본 슬라이드쇼 concat fallback 엔진 (로고, 제목, 하단 이미지 오버레이 지원)"""
        num_images = len(image_paths)
        time_per_image = total_duration / num_images

        concat_file = output_mp4.parent / "concat_list.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for img in image_paths:
                safe_path = str(img.resolve()).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
                f.write(f"duration {time_per_image:.3f}\n")
            last_path = str(image_paths[-1].resolve()).replace("\\", "/")
            f.write(f"file '{last_path}'\n")

        has_logo = bool(logo_path and Path(logo_path).exists())
        has_title = bool(title_path and Path(title_path).exists())
        has_bottom_image = bool(bottom_image_path and Path(bottom_image_path).exists())

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-i", str(audio_path),
        ]

        curr_idx = 2
        logo_idx = None
        if has_logo:
            safe_logo = str(Path(logo_path).resolve()).replace("\\", "/")
            cmd.extend(["-i", safe_logo])
            logo_idx = curr_idx
            curr_idx += 1

        title_idx = None
        if has_title:
            safe_title = str(Path(title_path).resolve()).replace("\\", "/")
            cmd.extend(["-i", safe_title])
            title_idx = curr_idx
            curr_idx += 1

        bottom_img_idx = None
        if has_bottom_image:
            safe_bimg = str(Path(bottom_image_path).resolve()).replace("\\", "/")
            cmd.extend(["-i", safe_bimg])
            bottom_img_idx = curr_idx
            curr_idx += 1

        if has_logo or has_title or has_bottom_image:
            filter_parts = []
            current_v = "0:v"
            if has_logo:
                filter_parts.append(f"[{logo_idx}:v]scale=w='min(150,iw)':h=-1[logo]")
                next_v = "v_tmp1" if (has_title or has_bottom_image) else "vout"
                filter_parts.append(f"[{current_v}][logo]overlay=35:35[{next_v}]")
                current_v = next_v
            if has_title:
                next_v = "v_tmp2" if has_bottom_image else "vout"
                filter_parts.append(f"[{current_v}][{title_idx}:v]overlay=W-w-35:35[{next_v}]")
                current_v = next_v
            if has_bottom_image:
                filter_parts.append(f"[{bottom_img_idx}:v]scale=w='min(270,iw)':h='min(120,ih)':force_original_aspect_ratio=decrease[bimg]")
                bpos_coords = "W-w-35:H-h-35" if bottom_image_pos == "bottom_right" else "35:H-h-35"
                filter_parts.append(f"[{current_v}][bimg]overlay={bpos_coords}[vout]")

            cmd.extend([
                "-filter_complex", ";".join(filter_parts),
                "-map", "[vout]",
                "-map", "1:a"
            ])
        else:
            cmd.extend([
                "-map", "0:v",
                "-map", "1:a"
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "17",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_mp4)
        ])

        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            errors="ignore"
        )
        _, stderr_data = process.communicate()
        try:
            concat_file.unlink(missing_ok=True)
        except Exception:
            pass

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg fallback 인코딩 실패 (코드 {process.returncode}): {stderr_data[-300:] if stderr_data else ''}")

        if not output_mp4.exists() or output_mp4.stat().st_size == 0:
            raise RuntimeError(f"영상 렌더링 후 최종 파일이 생성되지 않았습니다: {output_mp4.name}")

        if progress_callback:
            progress_callback(100, "1080p 영상 렌더링 완료!")
        return output_mp4
