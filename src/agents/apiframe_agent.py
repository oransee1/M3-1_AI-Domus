import time
import requests
from pathlib import Path
from src.config import Config

class ApiframeClient:
    BASE_URL = "https://api.apiframe.ai/v2"

    def __init__(self, suno_key: str = None, nano_key: str = None):
        self.suno_key = suno_key or Config.get_suno_key()
        self.nano_key = nano_key or Config.get_nano_key()

    def create_music_task(self, prompt: str, style: str, title: str = "Healing BGM", instrumental: bool = True) -> str:
        """
        Suno 음악 생성을 요청하고 jobId를 반환합니다.
        """
        if not self.suno_key:
            raise ValueError("Apiframe Suno API 키가 설정되지 않았습니다.")

        url = f"{self.BASE_URL}/music/generate"
        headers = {
            "X-API-Key": self.suno_key,
            "Content-Type": "application/json"
        }
        payload = {
            "model": "suno",
            "prompt": prompt,
            "sunoParams": {
                "custom_mode": True,
                "model_version": "V5_5",
                "style": style,
                "title": title,
                "instrumental": instrumental
            }
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code not in (200, 201, 202):
            raise RuntimeError(f"Suno 작업 생성 실패 (HTTP {resp.status_code}): {resp.text}")

        data = resp.json()
        job_id = data.get("jobId") or data.get("id")
        if not job_id:
            raise RuntimeError(f"응답에서 jobId를 찾을 수 없습니다: {data}")
        return job_id

    def create_image_task(
        self,
        prompt: str,
        model: str = "nano-banana-2",
        aspect_ratio: str = "16:9",
        resolution: str = "4K"
    ) -> str:
        """
        Nano Banana 2 초고화질 4K 이미지 생성을 요청하고 jobId를 반환합니다.
        각 씬 16:9 비율 9장 및 전체 4K(3840x2160) 고해상도 생성을 위해 nanoBananaParams를 적용합니다.
        """
        if not self.nano_key:
            raise ValueError("Apiframe Nano Banana API 키가 설정되지 않았습니다.")

        url = f"{self.BASE_URL}/images/generate"
        headers = {
            "X-API-Key": self.nano_key,
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "nanoBananaParams": {
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "output_format": "png"
            }
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        # 만약 nano-banana-2 모델 호출 시 에러가 발생할 경우 nano-banana-2-lite로 fallback 시도
        if resp.status_code not in (200, 201, 202) and model != "nano-banana-2-lite":
            fallback_payload = dict(payload)
            fallback_payload["model"] = "nano-banana-2-lite"
            resp = requests.post(url, json=fallback_payload, headers=headers, timeout=30)

        if resp.status_code not in (200, 201, 202):
            raise RuntimeError(f"이미지 작업 생성 실패 (HTTP {resp.status_code}): {resp.text}")

        data = resp.json()
        job_id = data.get("jobId") or data.get("id")
        if not job_id:
            raise RuntimeError(f"응답에서 jobId를 찾을 수 없습니다: {data}")
        return job_id

    def poll_job(self, job_id: str, api_key: str, max_wait_sec: int = 400, poll_interval: int = 5, callback=None) -> dict:
        """
        jobId의 완료 여부를 폴링하여 완료 시 결과 dict를 반환합니다.
        """
        url = f"{self.BASE_URL}/jobs/{job_id}"
        headers = {"X-API-Key": api_key}
        start_time = time.time()

        while time.time() - start_time < max_wait_sec:
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "").upper()
                    progress = data.get("progress", 0)

                    if callback:
                        callback(status, progress)

                    if status in ("COMPLETED", "SUCCESS"):
                        return data.get("result", {})
                    elif status in ("FAILED", "ERROR"):
                        error_msg = data.get("error") or "알 수 없는 오류"
                        raise RuntimeError(f"작업 실행 실패 ({job_id}): {error_msg}")
            except requests.RequestException as e:
                if callback:
                    callback(f"연결 재시도 중 ({e})", 0)

            time.sleep(poll_interval)

        raise TimeoutError(f"작업이 {max_wait_sec}초 내에 완료되지 않았습니다 (Job ID: {job_id})")

    @staticmethod
    def download_asset(url: str, save_path: Path, callback=None) -> Path:
        """
        원격 CDN URL로부터 파일을 스트리밍 다운로드합니다.
        """
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total_length = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if callback and total_length > 0:
                            callback(downloaded, total_length)

        if not save_path.exists() or save_path.stat().st_size == 0:
            raise IOError(f"다운로드된 파일이 비어 있습니다 (0바이트): {url}")

        return save_path
