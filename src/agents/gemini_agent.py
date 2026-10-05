import json
import re
from google import genai
from google.genai import types
from src.config import Config

class GeminiPromptAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.get_gemini_key()
        if not self.api_key:
            raise ValueError("Gemini API Key가 설정되지 않았습니다. .env 또는 설정창에서 입력해주세요.")
        self.client = genai.Client(api_key=self.api_key)

    # 쿼터 제한 방지를 위한 모든 무료 Gemini 엔진 풀 (가용성/속도 우선 순위)
    FREE_GEMINI_ENGINES = [
        # 1. 고속 & 저쿼터 소모 Flash-Lite 계열 (RPM/RPD 여유 높음)
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite-preview",
        "gemini-3-flash-preview",
        # 2. 고성능 Flash 표준 계열
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-flash-latest",
        # 3. 확장 Pro / Omni 계열
        "gemini-3.1-pro-preview",
        "gemini-omni-flash-preview",
        "gemini-omni-1.1-flash",
        "gemini-pro-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    ]

    def get_all_free_models(self) -> list:
        """계정에서 활성화된 무료 Gemini 엔진 목록을 동적으로 탐색하여 확장 목록을 구성합니다."""
        models = list(self.FREE_GEMINI_ENGINES)
        try:
            discovered = []
            for m in self.client.models.list():
                name = m.name[7:] if m.name.startswith("models/") else m.name
                lower = name.lower()
                if "gemini" in lower and not any(ex in lower for ex in ["embedding", "tts", "live", "transcribe", "robotics", "computer-use"]):
                    discovered.append(name)
            for dm in discovered:
                if dm not in models:
                    models.append(dm)
        except Exception:
            pass
        return models

    def plan_prompts(self, mood: str, genre: str = "New Age", is_instrumental: bool = True, custom_lyrics: str = "", log_callback=None) -> dict:
        """
        사용자의 한국어 입력(분위기, 장르 등)을 분석하여
        Suno 음악 프롬프트와 Nano Banana 3x3 그리드 스토리보드 프롬프트를 동시 기획합니다.
        가사 유무(is_instrumental) 및 사용자 지정 가사(custom_lyrics)를 완벽 지원하며,
        무료 Gemini API의 쿼터 제한을 우회하기 위해 모든 무료 Gemini 엔진을 순차 탐색합니다.
        """
        if is_instrumental:
            suno_prompt_rule = (
                "Detailed description of melody, instruments (e.g. acoustic piano, warm cello, soft ambient pads), "
                "BPM, emotion, atmosphere. 30-60 words. Emphasize pure instrumental BGM, serene and peaceful, no vocals."
            )
            suno_style_rule = "Comma separated genre tags e.g. new age, piano solo, ambient neoclassical, instrumental"
        else:
            if custom_lyrics:
                escaped_lyrics = custom_lyrics.replace('"', '\\"').replace('\n', ' ')
                suno_prompt_rule = (
                    f"Format and polish the user-provided lyrics into cohesive song lyrics with standard section tags ([Verse], [Chorus], [Outro]). Lyrics: {escaped_lyrics}"
                )
            else:
                suno_prompt_rule = (
                    "Poetic, emotionally resonant song lyrics matching the mood and genre (Korean or English). "
                    "Structured into standard song sections: [Verse 1], [Chorus], [Verse 2], [Chorus], [Outro]. 15-25 lines."
                )
            suno_style_rule = "Comma separated genre and vocal tags e.g. acoustic ballad, gentle female vocal, emotional, soothing, soft piano"

        system_instruction = (
            "You are an expert Creative Director & AI Prompt Engineer for YouTube music channels "
            "(specializing in healing, new age, lo-fi, sleep, and meditation music like 'Dancing with Angels' or 'Gentle Mind').\n"
            "Your mission is to take the user's brief concept and produce perfectly aligned prompts for:\n"
            "1. Suno AI (Music generation): optimized English music description and genre/style tags (or structured lyrics if vocal mode).\n"
            "2. Nano Banana 2 Lite (Image generation): a prompt specifically requesting a '3x3 grid storyboard' "
            "with 9 distinct sequential cinematic scenes. Each individual scene frame MUST be in 16:9 widescreen ratio, "
            "and the entire storyboard image MUST be in crisp Ultra-HD 4K resolution (3840x2160), "
            "sharing identical artistic style, character/scenery consistency, and color palette.\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "title": "English or Korean poetic title",\n'
            f'  "suno_prompt": "{suno_prompt_rule}",\n'
            f'  "suno_style": "{suno_style_rule}",\n'
            '  "image_prompt": "Prompt for generating a 3x3 grid (9 distinct scenes) storyboard illustration in 4K resolution (3840x2160). Must begin with \'3x3 grid storyboard, 9 sequential cinematic scenes, each scene in 16:9 widescreen ratio, 4K resolution, ultra-detailed...\' and specify art style (e.g. soft pastel watercolor, Studio Ghibli inspired, or warm dreamy digital painting), lighting, and serene healing mood. High quality, 4K UHD, 16:9 aspect ratio per scene, razor-sharp details."\n'
            "}"
        )

        lyrics_info = f"\n- Custom Lyrics: {custom_lyrics}" if (not is_instrumental and custom_lyrics) else ""
        user_content = (
            f"User Concept:\n"
            f"- Mood / Theme: {mood}\n"
            f"- Genre: {genre}\n"
            f"- Mode: {'Instrumental (Pure BGM, No Vocals)' if is_instrumental else 'Vocal Song (With Lyrics)'}{lyrics_info}\n\n"
            f"Generate the cohesive multimedia creative plan in JSON format."
        )

        models = self.get_all_free_models()
        last_err = None

        for model_name in models:
            try:
                if log_callback:
                    log_callback(f"🤖 [Gemini 엔진 시도] 무료 엔진 '{model_name}'으로 기획을 시작합니다...")

                response = self.client.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        response_mime_type="application/json",
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                    )
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]

                result = json.loads(raw_text.strip())
                if result.get("title") and result.get("suno_prompt") and result.get("image_prompt"):
                    result["engine"] = model_name
                    if log_callback:
                        log_callback(f"✅ [Gemini 엔진 가동 성공] 무료 엔진 '{model_name}'으로 기획 완료!")
                    return result
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    reason = "무료 쿼터 소진(429)"
                elif "503" in err_str or "UNAVAILABLE" in err_str:
                    reason = "서버 일시 부하(503)"
                elif "404" in err_str or "NOT_FOUND" in err_str:
                    reason = "미지원(404)"
                else:
                    reason = "응답 오류"
                
                if log_callback:
                    log_callback(f"⚠️ [{model_name} {reason}] 다음 무료 Gemini 엔진으로 즉시 자동 전환합니다...")
                continue

        # 모든 모델 일시 부하/쿼터 소진 시 중단 없는 지능형 백업 플랜 가동
        if log_callback:
            log_callback("🛡️ 모든 원격 모델 제한 도달 시 중단 방지 지능형 백업 플랜으로 즉시 완성합니다.")
        return self._smart_fallback_plan(mood, genre, is_instrumental, custom_lyrics)

    @staticmethod
    def _smart_fallback_plan(mood: str, genre: str, is_instrumental: bool, custom_lyrics: str = "") -> dict:
        """Gemini 서버 일시 부하(503) 시에도 제작이 중단되지 않도록 하는 지능형 백업 플래너"""
        title = f"{genre} - Autumn Serenity" if any(w in mood for w in ["가을", "단풍", "10월"]) else f"{genre} - Peaceful Healing"
        
        if is_instrumental:
            suno_prompt = (
                f"Relaxing {genre.lower()} music, warm acoustic piano chords, soft gentle cello melodies, "
                f"subtle background vinyl warmth, calm healing atmosphere, instrumental, soothing, no vocals. 72 BPM."
            )
            suno_style = f"{genre.lower()}, acoustic, piano, ambient, healing, instrumental"
        else:
            if custom_lyrics:
                suno_prompt = custom_lyrics
            else:
                suno_prompt = (
                    f"[Verse 1]\n"
                    f"창가에 스며든 따스한 바람\n"
                    f"지친 마음에 건네는 작은 위로처럼\n"
                    f"조용히 흐르는 시간 속에서\n"
                    f"온전한 평온을 마주해요\n\n"
                    f"[Chorus]\n"
                    f"기억해요 그대의 소중한 순간\n"
                    f"따뜻한 별빛이 감싸 안듯\n"
                    f"이 노래가 마음에 머물러\n"
                    f"포근한 안식이 되길\n\n"
                    f"[Outro]\n"
                    f"편안한 꿈결 속으로..."
                )
            suno_style = f"{genre.lower()}, acoustic, gentle female vocal, healing ballad, emotional piano"
        
        image_prompt = (
            f"3x3 grid storyboard, 9 sequential cinematic scenes, each scene in 16:9 widescreen ratio, 4K resolution, ultra-detailed. "
            f"Serene and cozy scene of {mood}. Warm amber sunlight streaming through cafe windows, glowing autumn leaves, steaming coffee mugs. "
            f"Studio Ghibli aesthetic, watercolor digital painting, highly consistent lighting and character across all 9 panels, 4K UHD, razor-sharp details."
        )
        
        return {
            "title": title,
            "suno_prompt": suno_prompt,
            "suno_style": suno_style,
            "image_prompt": image_prompt
        }
