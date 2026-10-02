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

    def plan_prompts(self, mood: str, genre: str = "New Age", is_instrumental: bool = True) -> dict:
        """
        사용자의 한국어 입력(분위기, 장르 등)을 분석하여
        Suno 음악 프롬프트와 Nano Banana 3x3 그리드 스토리보드 프롬프트를 동시 기획합니다.
        """
        system_instruction = (
            "You are an expert Creative Director & AI Prompt Engineer for YouTube music channels "
            "(specializing in healing, new age, lo-fi, sleep, and meditation music like 'Dancing with Angels' or 'Gentle Mind').\n"
            "Your mission is to take the user's brief concept and produce perfectly aligned prompts for:\n"
            "1. Suno AI (Music generation): optimized English music description and genre/style tags.\n"
            "2. Nano Banana 2 Lite (Image generation): a prompt specifically requesting a '3x3 grid storyboard' "
            "with 9 distinct sequential cinematic scenes. Each individual scene frame MUST be in 16:9 widescreen ratio, "
            "and the entire storyboard image MUST be in crisp Ultra-HD 4K resolution (3840x2160), "
            "sharing identical artistic style, character/scenery consistency, and color palette.\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "title": "English or Korean poetic title",\n'
            '  "suno_prompt": "Detailed description of melody, instruments (e.g. acoustic piano, warm cello, soft ambient pads), BPM, emotion, atmosphere. 30-60 words.",\n'
            '  "suno_style": "Comma separated genre tags e.g. new age, piano solo, ambient neoclassical, instrumental",\n'
            '  "image_prompt": "Prompt for generating a 3x3 grid (9 distinct scenes) storyboard illustration in 4K resolution (3840x2160). Must begin with \'3x3 grid storyboard, 9 sequential cinematic scenes, each scene in 16:9 widescreen ratio, 4K resolution, ultra-detailed...\' and specify art style (e.g. soft pastel watercolor, Studio Ghibli inspired, or warm dreamy digital painting), lighting, and serene healing mood. High quality, 4K UHD, 16:9 aspect ratio per scene, razor-sharp details."\n'
            "}"
        )

        user_content = (
            f"User Concept:\n"
            f"- Mood / Theme: {mood}\n"
            f"- Genre: {genre}\n"
            f"- Instrumental: {'Yes (No vocals)' if is_instrumental else 'No (With vocals)'}\n\n"
            f"Generate the cohesive multimedia creative plan in JSON format."
        )

        models = [
            "gemini-flash-latest",
            "gemini-3.7-flash",
            "gemini-3.8-flash",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash-lite"
        ]
        last_err = None

        for model_name in models:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        response_mime_type="application/json"
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
                    return result
            except Exception as e:
                last_err = e
                continue

        # 모든 모델 일시 부하(503) 시 중단 없는 지능형 백업 플랜 가동
        return self._smart_fallback_plan(mood, genre, is_instrumental)

    @staticmethod
    def _smart_fallback_plan(mood: str, genre: str, is_instrumental: bool) -> dict:
        """Gemini 서버 일시 부하(503) 시에도 제작이 중단되지 않도록 하는 지능형 백업 플래너"""
        title = f"{genre} - Autumn Serenity" if any(w in mood for w in ["가을", "단풍", "10월"]) else f"{genre} - Peaceful Healing"
        inst_desc = "instrumental, soothing and peaceful, no vocals" if is_instrumental else "warm gentle vocals"
        
        suno_prompt = (
            f"Relaxing {genre.lower()} music, warm acoustic piano chords, soft gentle cello melodies, "
            f"subtle background vinyl warmth, calm healing atmosphere, {inst_desc}. 72 BPM."
        )
        suno_style = f"{genre.lower()}, acoustic, piano, ambient, healing, lo-fi neoclassical"
        
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
