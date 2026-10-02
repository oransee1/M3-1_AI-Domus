import time
import re
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

from src.config import Config, OUTPUT_DIR
from src.agents.gemini_agent import GeminiPromptAgent
from src.agents.apiframe_agent import ApiframeClient
from src.media.image_processor import ImageProcessor
from src.media.video_renderer import VideoRenderer

class AutomationWorker(QThread):
    progress_signal = pyqtSignal(int, str)
    step_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    scenes_ready_signal = pyqtSignal(list)
    finished_signal = pyqtSignal(str, str, list)
    error_signal = pyqtSignal(str)

    def __init__(self, mood: str, genre: str, is_instrumental: bool, fade_duration: float = 1.5):
        super().__init__()
        self.mood = mood
        self.genre = genre
        self.is_instrumental = is_instrumental
        self.fade_duration = fade_duration

    def run(self):
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            work_dir = OUTPUT_DIR / f"project_{timestamp}"
            work_dir.mkdir(parents=True, exist_ok=True)

            self.log_signal.emit(f"🚀 [작업 시작] 프로젝트 세션 생성: {work_dir.name}")
            self.step_signal.emit(1)
            self.progress_signal.emit(5, "1단계: Gemini AI 기획 에이전트 가동 중...")

            # 1. Gemini AI 기획
            self.log_signal.emit("🧠 Gemini 3.8 Flash가 무드 분석 및 멀티모달 프롬프트 동시 기획을 시작합니다...")
            gemini_agent = GeminiPromptAgent()
            plan = gemini_agent.plan_prompts(self.mood, self.genre, self.is_instrumental)

            raw_title = plan.get("title", f"Healing_{timestamp}")
            # 윈도우 금지 특수문자(: * ? " < > | / \) 정제하여 NTFS 대체 스트림 오류 완벽 차단
            safe_title = re.sub(r'[\\/*?:"<>|\r\n\t]', "_", raw_title).strip()
            safe_title = re.sub(r'_+', '_', safe_title).strip('_')
            title = safe_title if safe_title else f"Healing_{timestamp}"

            suno_prompt = plan.get("suno_prompt", "")
            suno_style = plan.get("suno_style", self.genre)
            image_prompt = plan.get("image_prompt", "")

            self.log_signal.emit(f"✨ [AI 기획 완료] 곡명: {title}")
            self.log_signal.emit(f"🎵 Suno 음악 프롬프트: {suno_prompt}")
            self.log_signal.emit(f"🎨 Nano Banana 3x3 이미지 프롬프트: {image_prompt[:90]}...")
            
            self.step_signal.emit(2)
            self.progress_signal.emit(20, "2단계: Apiframe 미디어 생성 발주 중...")

            # 2. Apiframe 작업 발주
            client = ApiframeClient()
            self.log_signal.emit("📡 Apiframe을 통해 Suno 오디오 작업을 요청합니다...")
            suno_job_id = client.create_music_task(suno_prompt, suno_style, title, self.is_instrumental)
            self.log_signal.emit(f"✅ Suno Job ID 발급 완료: {suno_job_id}")

            self.log_signal.emit("📡 Apiframe을 통해 Nano Banana 2 Lite 이미지 작업을 요청합니다...")
            image_job_id = client.create_image_task(image_prompt)
            self.log_signal.emit(f"✅ Nano Banana Job ID 발급 완료: {image_job_id}")

            self.step_signal.emit(3)
            self.progress_signal.emit(35, "3단계: AI 오디오 및 비주얼 에셋 생성 대기 중...")

            # 3. 폴링 및 완료 대기
            self.log_signal.emit("⏳ Suno 음악 생성 완료 대기 중 (약 30~90초 소요)...")
            suno_res = client.poll_job(
                suno_job_id,
                client.suno_key,
                max_wait_sec=300,
                callback=lambda s, p: self.log_signal.emit(f"  [Suno 상태] {s} ({p}%)")
            )
            self.log_signal.emit("🎉 Suno 음원 생성 완료!")

            self.log_signal.emit("⏳ Nano Banana 이미지 생성 완료 대기 중...")
            image_res = client.poll_job(
                image_job_id,
                client.nano_key,
                max_wait_sec=300,
                callback=lambda s, p: self.log_signal.emit(f"  [Image 상태] {s} ({p}%)")
            )
            self.log_signal.emit("🎉 Nano Banana 스토리보드 이미지 생성 완료!")

            self.progress_signal.emit(60, "4단계: 에셋 다운로드 및 이미지 9분할 슬라이싱 중...")

            # URL 파싱
            tracks = suno_res.get("tracks", [])
            if not tracks:
                raise RuntimeError("Suno 응답에 오디오 트랙 정보가 없습니다.")
            audio_url = tracks[0].get("audioUrl")
            audio_duration = tracks[0].get("duration", 0)

            # 이미지 URL 파싱 (Apiframe 이미지 결과 구조 지원)
            image_url = None
            if isinstance(image_res, dict):
                if "images" in image_res and len(image_res["images"]) > 0:
                    first_img = image_res["images"][0]
                    image_url = first_img.get("url") if isinstance(first_img, dict) else first_img
                elif "imageUrl" in image_res:
                    image_url = image_res["imageUrl"]
                elif "url" in image_res:
                    image_url = image_res["url"]
            elif isinstance(image_res, list) and len(image_res) > 0:
                image_url = image_res[0].get("url") if isinstance(image_res[0], dict) else image_res[0]

            if not audio_url:
                raise RuntimeError("오디오 다운로드 URL을 획득하지 못했습니다.")
            if not image_url:
                raise RuntimeError(f"이미지 다운로드 URL을 획득하지 못했습니다. 응답 데이터: {image_res}")

            # 파일 다운로드 (안전한 파일명 기반)
            audio_file = work_dir / f"{title}.mp3"
            raw_image_file = work_dir / "storyboard_3x3.png"

            self.log_signal.emit(f"📥 MP3 음원 다운로드 중... ({title}.mp3)")
            client.download_asset(audio_url, audio_file)
            if not audio_file.exists() or audio_file.stat().st_size == 0:
                raise RuntimeError(f"음원 파일 다운로드 실패 (0바이트 또는 파일 누락): {audio_url}")

            self.log_signal.emit("📥 3x3 스토리보드 이미지 다운로드 중...")
            client.download_asset(image_url, raw_image_file)
            if not raw_image_file.exists() or raw_image_file.stat().st_size == 0:
                raise RuntimeError(f"이미지 파일 다운로드 실패 (0바이트 또는 파일 누락): {image_url}")

            # 4. 이미지 9분할 크롭 (StoryBoard-Division 정밀 분할)
            self.step_signal.emit(4)
            self.log_signal.emit("✂️ StoryBoard-Division 정밀 분할 엔진: 3x3 스토리보드를 9장의 씬 이미지로 자동 슬라이싱합니다...")
            scenes_dir = work_dir / "scenes"
            sliced_paths = ImageProcessor.split_3x3_grid(raw_image_file, scenes_dir)
            self.log_signal.emit(f"✅ 9장의 고화질 씬 이미지 생성 완료 ({len(sliced_paths)}개 프레임)")

            # GUI 실시간 3x3 프리뷰용 썸네일 생성 및 시그널 방출
            thumb_dir = work_dir / "thumbnails"
            thumb_paths = ImageProcessor.generate_thumbnails(sliced_paths, thumb_dir)
            self.scenes_ready_signal.emit([str(p) for p in thumb_paths])

            frames_dir = work_dir / "frames_1080p"
            fhd_frames = ImageProcessor.prepare_16_9_frames(sliced_paths, frames_dir)
            self.log_signal.emit("✅ 1080p 유튜브 와이드 프레임(배경 블러 확장) 구성 완료")

            self.step_signal.emit(5)
            self.progress_signal.emit(75, "5단계: MoveEditor 영상 합성 및 페이드 인/아웃 인코딩 중...")

            # 5. FFmpeg 영상 렌더링 (MoveEditor 페이드 인/페이드 아웃 크로스페이드)
            self.log_signal.emit(f"🎬 MoveEditor 합성 엔진 가동: 페이드 효과({self.fade_duration}s) 및 1080p MP4 인코딩 시작...")
            renderer = VideoRenderer()
            final_mp4 = work_dir / f"{title}_FHD.mp4"

            def render_callback(percent, msg):
                # 75% ~ 100% 범위로 매핑
                overall = 75 + int(percent * 0.25)
                self.progress_signal.emit(overall, msg)
                if percent % 25 == 0 or percent == 100:
                    self.log_signal.emit(f"  [인코딩] {msg}")

            renderer.render_slideshow(
                image_paths=fhd_frames,
                audio_path=audio_file,
                output_mp4=final_mp4,
                total_duration=audio_duration if audio_duration > 0 else None,
                fade_duration=self.fade_duration,
                progress_callback=render_callback
            )

            if not final_mp4.exists() or final_mp4.stat().st_size == 0:
                raise RuntimeError(f"최종 비디오 파일({final_mp4.name}) 생성에 실패했습니다.")

            self.step_signal.emit(6)
            self.progress_signal.emit(100, "🎉 모든 제작 공정이 성공적으로 완료되었습니다!")
            self.log_signal.emit(f"🏆 [완료] 최종 1080p 영상 생성 성공:\n  {final_mp4}")
            self.finished_signal.emit(str(final_mp4), str(audio_file), [str(p) for p in sliced_paths])

        except Exception as e:
            self.log_signal.emit(f"❌ [에러 발생] {str(e)}")
            self.error_signal.emit(str(e))
