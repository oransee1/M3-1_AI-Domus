import sys
import argparse
from pathlib import Path

# Windows cp949 인코딩 콘솔 충돌 방지
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import OUTPUT_DIR

def run_cli_encoding(target_dir: str, fade_duration: float = 1.5):
    """프로그램 내부 인코딩 엔진 CLI 직접 실행 모드"""
    from src.gui.worker import EncodingWorker
    from PyQt5.QtCore import QCoreApplication

    app = QCoreApplication(sys.argv)
    p = Path(target_dir)
    if not p.is_absolute():
        p = PROJECT_ROOT / p

    print("==================================================")
    print(f"🎬 [AI Domus] 프로그램 인코딩 엔진 가동")
    print(f"📁 대상 프로젝트 세션: {p}")
    print("==================================================")

    worker = EncodingWorker(p, fade_duration=fade_duration)

    def on_log(msg):
        print(f"  {msg}")

    def on_progress(percent, msg):
        print(f"  [{percent}%] {msg}")

    def on_finished(mp4, mp3, scenes):
        print(f"\n🎉 [성공] 프로그램 인코딩 엔진 제작 완료!")
        print(f"📹 최종 MP4: {mp4}")
        print(f"🎵 오디오: {mp3}")
        print(f"🖼️ 씬 개수: {len(scenes)}개")
        app.quit()

    def on_error(err):
        print(f"\n❌ [오류] 인코딩 엔진 실패: {err}")
        app.quit()

    worker.log_signal.connect(on_log)
    worker.progress_signal.connect(on_progress)
    worker.finished_signal.connect(on_finished)
    worker.error_signal.connect(on_error)

    worker.start()
    app.exec_()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Domus Music Studio")
    parser.add_argument(
        "--encode",
        nargs="?",
        const="latest",
        help="프로그램 내부 인코딩 엔진을 지정 프로젝트 폴더에 직접 실행 (미지정 시 최신 세션)"
    )
    parser.add_argument(
        "--fade",
        type=float,
        default=1.5,
        help="페이드 인/아웃 전환 시간 (초, 기본값: 1.5)"
    )
    args, unknown = parser.parse_known_args()

    if args.encode:
        target = args.encode
        if target == "latest":
            subdirs = [d for d in OUTPUT_DIR.iterdir() if d.is_dir()] if OUTPUT_DIR.exists() else []
            if not subdirs:
                print("❌ output 디렉토리에 프로젝트 세션이 존재하지 않습니다.")
                sys.exit(1)
            subdirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            target = str(subdirs[0])
        run_cli_encoding(target, fade_duration=args.fade)
    else:
        from src.gui.app_window import run_app
        run_app()
