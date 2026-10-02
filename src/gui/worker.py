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

    def __init__(self, mood: str, genre: str, is_instrumental: bool, fade_duration: float = 1.5, custom_lyrics: str = "", logo_path: str = ""):
        super().__init__()
        self.mood = mood
        self.genre = genre
        self.is_instrumental = is_instrumental
        self.fade_duration = fade_duration
        self.custom_lyrics = custom_lyrics
        self.logo_path = logo_path

    def run(self):
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            work_dir = OUTPUT_DIR / f"project_{timestamp}"
            work_dir.mkdir(parents=True, exist_ok=True)

            self.log_signal.emit(f"🚀 [작업 시작] 프로젝트 세션 생성: {work_dir.name}")
            self.step_signal.emit(1)
            self.progress_signal.emit(5, "1단계: Gemini AI 기획 에이전트 가동 중...")

            # 1. Gemini AI 기획
            if self.is_instrumental:
                self.log_signal.emit("🎵 [음악 모드] 보컬 없는 순수 연주곡 (Instrumental BGM)")
            else:
                self.log_signal.emit("🎤 [음악 모드] 보컬 곡 (가사 포함 - Vocal Song with Lyrics)")
            self.log_signal.emit("🧠 Gemini AI 기획 에이전트가 무드 분석 및 멀티모달 프롬프트 동시 기획을 시작합니다...")
            gemini_agent = GeminiPromptAgent()
            plan = gemini_agent.plan_prompts(
                self.mood,
                self.genre,
                self.is_instrumental,
                self.custom_lyrics,
                log_callback=self.log_signal.emit
            )

            raw_title = plan.get("title", f"Healing_{timestamp}")
            # 윈도우 금지 특수문자(: * ? " < > | / \) 정제하여 NTFS 대체 스트림 오류 완벽 차단
            safe_title = re.sub(r'[\\/*?:"<>|\r\n\t]', "_", raw_title).strip()
            safe_title = re.sub(r'_+', '_', safe_title).strip('_')
            title = safe_title if safe_title else f"Healing_{timestamp}"

            suno_prompt = plan.get("suno_prompt", "")
            suno_style = plan.get("suno_style", self.genre)
            image_prompt = plan.get("image_prompt", "")
            used_engine = plan.get("engine", "지능형 백업 엔진")

            self.log_signal.emit(f"✨ [AI 기획 완료] 곡명: {title} (기획 엔진: {used_engine})")
            if self.is_instrumental:
                self.log_signal.emit(f"🎵 Suno 음악 프롬프트: {suno_prompt}")
            else:
                lyrics_preview = suno_prompt.replace('\n', ' ')[:90]
                self.log_signal.emit(f"🎤 Suno 보컬 가사: {lyrics_preview}...")
                self.log_signal.emit(f"🎵 Suno 보컬 스타일: {suno_style}")
            self.log_signal.emit(f"🎨 Nano Banana 3x3 4K(16:9) 이미지 프롬프트: {image_prompt[:90]}...")
            
            self.step_signal.emit(2)
            self.progress_signal.emit(20, "2단계: Apiframe 미디어 생성 발주 중...")

            # 2. Apiframe 작업 발주
            client = ApiframeClient()
            self.log_signal.emit("📡 Apiframe을 통해 Suno 오디오 작업을 요청합니다...")
            suno_job_id = client.create_music_task(suno_prompt, suno_style, title, self.is_instrumental)
            self.log_signal.emit(f"✅ Suno Job ID 발급 완료: {suno_job_id}")

            self.log_signal.emit("📡 Apiframe을 통해 Nano Banana 2 Lite 4K (16:9 씬, 9장) 이미지 작업을 요청합니다...")
            image_job_id = client.create_image_task(image_prompt, aspect_ratio="16:9", resolution="4K")
            self.log_signal.emit(f"✅ Nano Banana 4K Job ID 발급 완료: {image_job_id}")

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
            renderer = VideoRenderer()
            actual_audio_duration = renderer.get_audio_duration(audio_file)
            self.log_signal.emit(f"🎬 MoveEditor 합성 엔진 가동: 오디오 길이({actual_audio_duration:.2f}s), 페이드({self.fade_duration}s) 1080p MP4 인코딩 시작...")
            final_mp4 = work_dir / f"{title}_FHD.mp4"

            def render_callback(percent, msg):
                # 75% ~ 100% 범위로 매핑
                overall = 75 + int(percent * 0.25)
                self.progress_signal.emit(overall, msg)
                if percent % 25 == 0 or percent == 100:
                    self.log_signal.emit(f"  [인코딩] {msg}")

            # 로고 이미지 규격화 및 준비 (지정된 경우 우측 상단 오버레이)
            prepared_logo = None
            if self.logo_path and Path(self.logo_path).exists():
                try:
                    prepared_logo = work_dir / "logo_prepared.png"
                    ImageProcessor.prepare_logo(Path(self.logo_path), prepared_logo, max_width=240, max_height=100)
                    self.log_signal.emit(f"🖼️ [로고 오버레이] 로고 이미지 규격화 완료: {Path(self.logo_path).name} ➜ 영상 우측 상단에 반영됩니다.")
                except Exception as e:
                    self.log_signal.emit(f"⚠️ [로고 처리 경고] 로고 로딩 실패 ({e}) - 로고 없이 렌더링을 진행합니다.")
                    prepared_logo = None

            renderer.render_slideshow(
                image_paths=fhd_frames,
                audio_path=audio_file,
                output_mp4=final_mp4,
                total_duration=actual_audio_duration,
                fade_duration=self.fade_duration,
                logo_path=prepared_logo,
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


class EncodingWorker(QThread):
    """
    개발 프로그램 내의 독립 인코딩 엔진 워커:
    기존 프로젝트 세션 폴더(에셋/오디오)를 대상으로
    StoryBoard-Division 및 MoveEditor 기반 1080p FHD MP4 영상을 직접 인코딩 합성합니다.
    """
    progress_signal = pyqtSignal(int, str)
    step_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    scenes_ready_signal = pyqtSignal(list)
    finished_signal = pyqtSignal(str, str, list)
    error_signal = pyqtSignal(str)

    def __init__(self, project_dir: Path, fade_duration: float = 1.5, logo_path: str = ""):
        super().__init__()
        self.project_dir = Path(project_dir)
        self.fade_duration = fade_duration
        self.logo_path = logo_path

    def run(self):
        try:
            self.log_signal.emit(f"🎬 [인코딩 엔진 가동] 프로젝트 디렉토리: {self.project_dir.name}")
            self.step_signal.emit(4)
            self.progress_signal.emit(10, "에셋 분석 및 1080p 프레임 준비 중...")

            # 1. 오디오 파일 탐색 (audio.mp3 또는 *.mp3)
            audio_files = list(self.project_dir.glob("*.mp3"))
            if not audio_files:
                raise FileNotFoundError(f"프로젝트 폴더 내에 mp3 오디오 파일이 없습니다: {self.project_dir}")
            
            # audio.mp3가 있으면 우선 사용, 없으면 첫 번째 mp3 사용
            audio_file = next((f for f in audio_files if f.name == "audio.mp3"), audio_files[0])
            self.log_signal.emit(f"🎵 대상 오디오 파일 확인: {audio_file.name} ({audio_file.stat().st_size:,} bytes)")

            # 2. 씬 이미지 탐색 및 준비
            frames_dir = self.project_dir / "frames_1080p"
            scenes_dir = self.project_dir / "scenes"
            storyboard = self.project_dir / "storyboard_3x3.png"

            fhd_frames = []
            sliced_paths = []

            if frames_dir.exists() and len(list(frames_dir.glob("*.png"))) >= 9:
                fhd_frames = sorted(list(frames_dir.glob("*.png")))[:9]
                sliced_paths = sorted(list(scenes_dir.glob("*.png")))[:9] if scenes_dir.exists() else fhd_frames
                self.log_signal.emit(f"🖼️ 기존 1080p 와이드 프레임 {len(fhd_frames)}장 확인 완료")
            elif scenes_dir.exists() and len(list(scenes_dir.glob("*.png"))) >= 9:
                sliced_paths = sorted(list(scenes_dir.glob("*.png")))[:9]
                self.log_signal.emit(f"🖼️ 분할 씬 이미지 {len(sliced_paths)}장으로부터 1080p 와이드 프레임 생성 중...")
                fhd_frames = ImageProcessor.prepare_16_9_frames(sliced_paths, frames_dir)
            elif storyboard.exists():
                self.log_signal.emit("✂️ storyboard_3x3.png 감지: 3x3 스토리보드 9분할 슬라이싱 시작...")
                sliced_paths = ImageProcessor.split_3x3_grid(storyboard, scenes_dir)
                fhd_frames = ImageProcessor.prepare_16_9_frames(sliced_paths, frames_dir)
            else:
                raise FileNotFoundError(f"프로젝트 폴더 내에 씬 이미지나 storyboard_3x3.png가 없습니다: {self.project_dir}")

            # 썸네일 생성 및 GUI 3x3 프리뷰 연동
            thumb_dir = self.project_dir / "thumbnails"
            thumb_paths = ImageProcessor.generate_thumbnails(sliced_paths, thumb_dir)
            self.scenes_ready_signal.emit([str(p) for p in thumb_paths])

            # 3. 1080p 비디오 렌더링 실행
            self.step_signal.emit(5)
            self.progress_signal.emit(30, "프로그램 인코딩 엔진: 씬 크로스페이드 및 1080p MP4 합성 시작...")

            renderer = VideoRenderer()
            actual_audio_duration = renderer.get_audio_duration(audio_file)
            self.log_signal.emit(f"⏱️ 오디오 재생시간: {actual_audio_duration:.2f}초 (페이드 {self.fade_duration}초 적용)")

            base_name = audio_file.stem
            if base_name == "audio":
                base_name = self.project_dir.name
            final_mp4 = self.project_dir / f"{base_name}_FHD.mp4"

            def render_callback(percent, msg):
                overall = 30 + int(percent * 0.70)
                self.progress_signal.emit(overall, msg)
                if percent % 20 == 0 or percent == 100:
                    self.log_signal.emit(f"  [인코딩 진행] {msg}")

            # 로고 이미지 규격화 및 준비 (지정된 경우 우측 상단 오버레이)
            prepared_logo = None
            if self.logo_path and Path(self.logo_path).exists():
                try:
                    prepared_logo = self.project_dir / "logo_prepared.png"
                    ImageProcessor.prepare_logo(Path(self.logo_path), prepared_logo, max_width=240, max_height=100)
                    self.log_signal.emit(f"🖼️ [로고 오버레이] 로고 이미지 규격화 완료: {Path(self.logo_path).name} ➜ 영상 우측 상단에 반영됩니다.")
                except Exception as e:
                    self.log_signal.emit(f"⚠️ [로고 처리 경고] 로고 로딩 실패 ({e}) - 로고 없이 렌더링을 진행합니다.")
                    prepared_logo = None

            renderer.render_slideshow(
                image_paths=fhd_frames,
                audio_path=audio_file,
                output_mp4=final_mp4,
                total_duration=actual_audio_duration,
                fade_duration=self.fade_duration,
                logo_path=prepared_logo,
                progress_callback=render_callback
            )

            if not final_mp4.exists() or final_mp4.stat().st_size == 0:
                raise RuntimeError(f"최종 비디오 파일({final_mp4.name}) 생성 실패")

            self.step_signal.emit(6)
            self.progress_signal.emit(100, "🎉 프로그램 인코딩 엔진 렌더링 완료!")
            self.log_signal.emit(f"🏆 [완료] 최종 1080p 영상 생성 성공:\n  {final_mp4}")
            self.finished_signal.emit(str(final_mp4), str(audio_file), [str(p) for p in sliced_paths])

        except Exception as e:
            self.log_signal.emit(f"❌ [인코딩 에러] {str(e)}")
            self.error_signal.emit(str(e))
