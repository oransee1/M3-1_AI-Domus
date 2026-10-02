import os
import sys
import subprocess
from pathlib import Path

def build():
    print("==================================================")
    print("  AI Domus Music Studio - Standalone .exe Builder")
    print("==================================================")

    # 1. PyInstaller 확인 및 설치
    try:
        import PyInstaller
        print("[1/3] PyInstaller 감지됨.")
    except ImportError:
        print("[1/3] PyInstaller 설치 중...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. 빌드 옵션 구성
    project_root = Path(__file__).resolve().parent
    main_script = project_root / "main.py"
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=AIDomusMusicStudio",
        "--onefile",
        "--windowed",
        f"--paths={project_root}",
        "--add-data=.env;.env",
        "--hidden-import=PyQt5",
        "--hidden-import=google.genai",
        "--hidden-import=imageio_ffmpeg",
        "--hidden-import=PIL",
        str(main_script)
    ]

    print("[2/3] PyInstaller 빌드 실행 중 (수 분 소요)...")
    print(f"명령어: {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=project_root)

    print("==================================================")
    print(f"[3/3] 빌드 완료! 실행 파일 위치: {dist_dir / 'AIDomusMusicStudio.exe'}")
    print("==================================================")

if __name__ == "__main__":
    build()
