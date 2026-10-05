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

    # GUI 음악 장르별 100% 매칭 Suno 사운드 & 스타일 프로필 정의
    GENRE_PROFILES = {
        "New Age / Piano": {
            "primary_tags": "new age, solo piano, peaceful, calm, melodic piano, healing, serene",
            "instruments": "acoustic grand piano, warm ambient pads, gentle cello, soft melodic chords",
            "tempo": "70-76 BPM",
            "vocal_style": "gentle female vocal, soft acoustic ballad, emotional, clear, soothing",
            "description": "serene and emotional new age piano with tranquil melodies and healing harmony"
        },
        "Lo-Fi / Chillhop": {
            "primary_tags": "lo-fi, chillhop, jazzy beats, mellow rhodes, relaxed groove, vinyl crackle, cozy, chill",
            "instruments": "rhodes electric piano, lo-fi drum beats, warm sub bass, subtle vinyl dust, tape warmth",
            "tempo": "75-85 BPM",
            "vocal_style": "lo-fi indie vocal, relaxed, intimate, cozy, warm tone",
            "description": "cozy lo-fi chillhop with relaxing hip-hop beats, warm rhodes chords, and nostalgic tape texture"
        },
        "Ambient / Meditation": {
            "primary_tags": "ambient, meditation, drone, atmospheric pads, deep relaxation, soundscape, peaceful, healing",
            "instruments": "atmospheric synth pads, soft drone, gentle singing bowl, spatial reverb, airy chimes",
            "tempo": "60-68 BPM, slow flowing",
            "vocal_style": "ethereal ambient vocal, airy chanting, soft meditative tones",
            "description": "spacious ambient soundscape designed for deep meditation, mindful breathing, and total peace"
        },
        "Cinematic Neoclassical": {
            "primary_tags": "cinematic, neoclassical, orchestral strings, emotive piano, dramatic, elegant, emotional",
            "instruments": "expressive cello, lush violin orchestra, grand acoustic piano, dynamic orchestral crescendo",
            "tempo": "65-75 BPM",
            "vocal_style": "cinematic vocal, dramatic, emotional, operatic texture, soaring melodies",
            "description": "breathtaking cinematic neoclassical composition with rich orchestral strings and moving grand piano"
        },
        "Smooth Jazz": {
            "primary_tags": "smooth jazz, mellow saxophone, soft rhodes piano, warm upright bass, gentle brush drums, lounge",
            "instruments": "warm tenor saxophone, smooth electric piano, acoustic upright double bass, subtle brush kit",
            "tempo": "80-90 BPM",
            "vocal_style": "smooth jazz vocal, velvety tone, soulful, warm, intimate lounge delivery",
            "description": "sophisticated smooth jazz with warm mellow saxophone, acoustic upright bass, and gentle brush rhythm"
        },
        "Acoustic Guitar": {
            "primary_tags": "acoustic guitar, fingerpicking guitar, warm acoustic folk, gentle strings, soothing melody, serene",
            "instruments": "fingerstyle steel-string acoustic guitar, nylon string warmth, subtle acoustic bass, gentle melodic fingerpicking",
            "tempo": "72-80 BPM",
            "vocal_style": "intimate acoustic folk vocal, heartfelt, soft, warm, natural tone",
            "description": "warm fingerpicking acoustic guitar with intimate folk textures and soothing organic resonance"
        },
        "Glam Rock": {
            "primary_tags": "glam rock, 70s rock, hard rock, energetic electric guitar, stomping rock drums, punchy bass, flamboyant, driving anthem",
            "instruments": "distorted electric guitars, roaring guitar riffs, driving power chords, punchy bass guitar, heavy rock drum kit, energetic vintage synthesizers",
            "tempo": "120-135 BPM",
            "vocal_style": "powerful charismatic rock vocal, theatrical, dynamic, gritty high-energy delivery",
            "description": "flamboyant and energetic 70s glam rock with driving electric guitar riffs, stomping arena beat, and powerful anthem groove"
        },
    }

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

    def plan_prompts(self, mood: str, genre: str = "New Age / Piano", is_instrumental: bool = True, custom_lyrics: str = "", image_style: str = "photo", log_callback=None) -> dict:
        """
        사용자의 한국어 입력(분위기, 장르 등)을 분석하여
        Suno 음악 프롬프트와 Nano Banana 3x3 그리드 스토리보드 프롬프트를 동시 기획합니다.
        가사 유무(is_instrumental), 사용자 지정 가사(custom_lyrics),
        이미지 스타일(image_style: 'photo' 또는 'art')을 완벽 지원하며,
        무료 Gemini API의 쿼터 제한을 우회하기 위해 모든 무료 Gemini 엔진을 순차 탐색합니다.
        """
        # 선택된 장르의 프로필 확인 (미등록 장르일 경우 기본 New Age 프로필 적용)
        genre_info = self.GENRE_PROFILES.get(genre)
        if not genre_info:
            for k, v in self.GENRE_PROFILES.items():
                if k.lower() in genre.lower() or any(w.lower() in genre.lower() for w in k.split()):
                    genre_info = v
                    break
        if not genre_info:
            genre_info = self.GENRE_PROFILES["New Age / Piano"]

        primary_tags = genre_info["primary_tags"]
        inst_desc = genre_info["instruments"]
        tempo_desc = genre_info["tempo"]

        if is_instrumental:
            suno_prompt_rule = (
                f"Detailed musical description tailored strictly to the '{genre}' genre. "
                f"Core instruments MUST feature: {inst_desc}. Tempo: {tempo_desc}. "
                f"BPM, emotion, atmosphere. 30-60 words. Emphasize pure instrumental BGM, serene and peaceful, NO vocals."
            )
            suno_style_rule = f"Comma separated style and genre tags. MUST strictly begin with '{primary_tags}', followed by mood/tempo tags."
        else:
            if custom_lyrics:
                escaped_lyrics = custom_lyrics.replace('"', '\\"').replace('\n', ' ')
                suno_prompt_rule = (
                    f"Format and polish the user-provided lyrics into cohesive song lyrics with standard section tags ([Verse], [Chorus], [Outro]). Lyrics: {escaped_lyrics}"
                )
            else:
                suno_prompt_rule = (
                    f"Poetic, emotionally resonant song lyrics matching the mood and '{genre}' genre (Korean or English). "
                    f"Structured into standard song sections: [Verse 1], [Chorus], [Verse 2], [Chorus], [Outro]. 15-25 lines."
                )
            vocal_style_desc = genre_info["vocal_style"]
            suno_style_rule = f"Comma separated genre and vocal tags. MUST strictly begin with '{primary_tags}, {vocal_style_desc}', followed by mood tags."

        is_art = (image_style == "art")
        if is_art:
            style_instruction = (
                "- [ARTWORK / ILLUSTRATION ONLY]: The style MUST be an emotive, aesthetically captivating artistic illustration or digital painting (such as painterly scenery, soft watercolor textures, cinematic anime background scenery inspired by Studio Ghibli or Makoto Shinkai, warm pastel tones). "
                "NEVER generate real-life camera photographs or stock photos. "
                "Always include negative constraints: 'artistic digital painting, aesthetic illustration, painterly textures, 4K UHD, scenic environment only, no people, no humans, no person, no woman, no man, no silhouette, absolutely no real photograph, no camera photo, no realistic photography'."
            )
            image_prompt_start = "3x3 grid storyboard, 9 sequential cinematic scenes, each scene in 16:9 widescreen ratio, 4K resolution, beautiful aesthetic illustration and painterly artwork..."
            image_prompt_end = "artistic digital painting, vibrant aesthetic illustration, painterly textures, 4K UHD, scenic environment only, no people, no humans, no person, no woman, no man, no silhouette, absolutely no real photograph, no camera photo, no realistic photography."
            visual_guideline_style = "1. Visual Style: Beautiful aesthetic illustration / painterly artwork (NO real photograph, NO camera photo)."
        else:
            style_instruction = (
                "- [REAL PHOTOGRAPHY ONLY]: The style MUST be 100% authentic, photorealistic real-life photography shot on a professional 35mm DSLR camera (f/1.8, natural lighting, realistic textures, authentic depth of field). "
                "NEVER generate paintings, illustrations, drawings, anime, cartoons, Ghibli, sketches, or digital art. "
                "Always include negative constraints: 'real photograph, authentic photography, absolutely no illustration, no anime, no painting, no drawing, no cartoon'."
            )
            image_prompt_start = "3x3 grid storyboard, 9 sequential cinematic scenes, each scene in 16:9 widescreen ratio, 4K resolution, ultra-detailed authentic photography..."
            image_prompt_end = "shot on professional 35mm camera, photorealistic, lifelike textures, 4K UHD, real photograph, scenic nature only, no people, no humans, no person, no woman, no man, no silhouette, absolutely no illustration, no anime, no painting, no drawing, no cartoon."
            visual_guideline_style = "1. Photography Style: 100% Real authentic photograph (NO illustration, NO anime, NO digital painting, NO cartoon)."

        system_instruction = (
            "You are an expert Creative Director & AI Prompt Engineer for YouTube music channels "
            "(specializing in healing, new age, lo-fi, sleep, and meditation music like 'Dancing with Angels' or 'Gentle Mind').\n"
            "Your mission is to take the user's brief concept and produce perfectly aligned prompts for:\n"
            f"1. Suno AI (Music generation): optimized English music description and genre/style tags (or structured lyrics if vocal mode). The musical style and instruments MUST 100% reflect the specified genre: '{genre}'.\n"
            "2. Nano Banana 2 4K (Image generation): a prompt specifically requesting a '3x3 grid storyboard' "
            "with 9 distinct sequential cinematic scenes. Each individual scene frame MUST be in 16:9 widescreen ratio, "
            "and the entire storyboard image MUST be in crisp Ultra-HD 4K resolution (3840x2160).\n\n"
            "CRITICAL VISUAL RULES FOR IMAGE GENERATION (MANDATORY):\n"
            f"{style_instruction}\n"
            "- [STRICTLY NO PEOPLE / SCENERY & NATURE ONLY]: NEVER include any people, persons, human figures, characters, faces, walkers, crowds, or silhouettes in any scene. "
            "Focus 100% on pure scenic beauty: breathtaking natural landscapes, peaceful outdoor walking paths covered in fallen autumn leaves, sunbeams through tree branches, serene empty park benches, cozy indoor cafe tables with steaming coffee, rainy window views, glowing evening lanterns. "
            "Every scene must be a tranquil, unpopulated environment. Always explicitly include negative constraints: 'no people, no humans, no person, no woman, no man, no silhouette, no crowd'.\n"
            "- [CONSISTENCY]: All 9 scenes must share identical visual style, seamless color grading, and scenery consistency.\n\n"
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "title": "English or Korean poetic title",\n'
            f'  "suno_prompt": "{suno_prompt_rule}",\n'
            f'  "suno_style": "{suno_style_rule}",\n'
            f'  "image_prompt": "Prompt for generating a 3x3 grid (9 distinct sequential scenes) storyboard in 4K resolution (3840x2160). Must begin with \'{image_prompt_start}\'. Describe the scenic details, lighting, and mood. MUST NOT have any people or human figures. Conclude with: \'{image_prompt_end}\'"\n'
            "}"
        )

        lyrics_info = f"\n- Custom Lyrics: {custom_lyrics}" if (not is_instrumental and custom_lyrics) else ""
        user_content = (
            f"User Concept:\n"
            f"- Mood / Theme: {mood}\n"
            f"- Genre: {genre} (Mandatory core instruments: {inst_desc})\n"
            f"- Mode: {'Instrumental (Pure BGM, No Vocals)' if is_instrumental else 'Vocal Song (With Lyrics)'}{lyrics_info}\n\n"
            f"Mandatory Visual Guidelines:\n"
            f"{visual_guideline_style}\n"
            f"2. NO People / Human Figures: Strictly scenery, nature, landscape, or environment ONLY (NO humans, NO people, NO characters, NO silhouettes).\n\n"
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
                    # 선택된 이미지 유형(사진 vs 그림) 및 등장 인물 배제(풍경/자연 전용) 보장 후처리 가드
                    result["image_prompt"] = self._enforce_style_and_no_people(result["image_prompt"], image_style=image_style)
                    # 선택된 음악 장르 태그가 Suno style에 100% 최우선 반영되도록 보장하는 후처리 가드
                    result["suno_style"] = self._enforce_suno_genre(result.get("suno_style", genre), genre=genre)
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
        return self._smart_fallback_plan(mood, genre, is_instrumental, custom_lyrics, image_style=image_style)

    @staticmethod
    def _enforce_photo_and_no_people(prompt: str) -> str:
        """하위 호환성 유지용: 실제 사진 및 무인물 가드"""
        return GeminiPromptAgent._enforce_style_and_no_people(prompt, image_style="photo")

    @staticmethod
    def _enforce_style_and_no_people(prompt: str, image_style: str = "photo") -> str:
        """
        나노 바나나 프롬프트가 사용자가 선택한 유형('실제 사진' 또는 '그림')과
        '등장 인물 배제(No People/Scenery Only)' 원칙에 100% 부합하도록 정제 및 제약조건을 강제 보강합니다.
        """
        cleaned = prompt

        if image_style == "art":
            # [그림 모드]
            # 1. 긍정적 맥락의 실사 사진 키워드를 예술 일러스트/회화 키워드로 치환 (부정어 뒤는 보존)
            for photo_word in [
                "shot on professional 35mm camera", "shot on 35mm dslr camera", "35mm camera",
                "dslr photograph", "dslr photo", "real photograph", "authentic photography",
                "realistic photograph", "photorealistic", "raw photo"
            ]:
                cleaned = re.sub(
                    rf"(?<!no\s)(?<!not\s)(?<!without\s)\b{re.escape(photo_word)}\b",
                    "beautiful aesthetic illustration",
                    cleaned,
                    flags=re.IGNORECASE
                )
            # 'no illustration', 'no painting' 등 이전 제약 문구 제거
            cleaned = re.sub(r",?\s*absolutely no illustration,?\s*no anime,?\s*no painting,?\s*no drawing,?\s*no cartoon\.?", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r",?\s*no illustration,?\s*no anime,?\s*no painting,?\s*no drawing,?\s*no cartoon\.?", "", cleaned, flags=re.IGNORECASE)

            # 2. 긍정적 맥락의 인물/인체 관련 묘사 정제 (사람 묘사를 평화로운 풍경/자연 요소로 순화)
            cleaned = re.sub(r"(?<!no\s)(?<!not\s)(?<!without\s)\b(a\s+)?(korean\s+)?(woman|man|girl|boy|person|figure)\s+(walking|sitting|standing|looking|taking a walk)\b", "peaceful scenic landscape", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"(?<!no\s)(?<!not\s)(?<!without\s)\b(a\s+)?(korean\s+)?(woman|man|girl|boy|person|figure|character|couple|people)\b", "peaceful landscape", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"(?<!no\s)(?<!not\s)(?<!without\s)\b(her|his)\s+(hair|hands|eyes|face|fashion|coat|scarf)\b", "warm artistic lighting", cleaned, flags=re.IGNORECASE)

            # 3. 그림 모드 네거티브 및 무인물 제약 보강
            if "no people" not in cleaned.lower():
                cleaned += ", peaceful scenery, empty tranquil environment, no people, no humans, no person, no woman, no man, no silhouette, no crowd, artistic digital painting, aesthetic illustration, 4K UHD, absolutely no real photograph, no camera photo."
            elif "no real photograph" not in cleaned.lower():
                cleaned += ", artistic digital painting, aesthetic illustration, 4K UHD, absolutely no real photograph, no camera photo."

        else:
            # [실제 사진 모드]
            # 1. 긍정적 맥락에서 쓰인 그림/일러스트 관련 키워드만 실사 사진으로 치환 (부정어 뒤는 보존)
            for art_word in [
                "digital painting", "watercolor painting", "watercolor style", "watercolor",
                "illustration", "anime style", "anime", "cartoon style", "cartoon",
                "ghibli inspired", "ghibli aesthetic", "ghibli style", "manga style"
            ]:
                cleaned = re.sub(
                    rf"(?<!no\s)(?<!not\s)(?<!without\s)\b{re.escape(art_word)}\b",
                    "authentic real photograph",
                    cleaned,
                    flags=re.IGNORECASE
                )

            # 2. 긍정적 맥락의 인물/인체 관련 묘사 정제
            cleaned = re.sub(r"(?<!no\s)(?<!not\s)(?<!without\s)\b(a\s+)?(realistic\s+)?(korean\s+)?(woman|man|girl|boy|person|figure)\s+(walking|sitting|standing|looking|taking a walk)\b", "peaceful scenic landscape", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"(?<!no\s)(?<!not\s)(?<!without\s)\b(a\s+)?(realistic\s+)?(korean\s+)?(woman|man|girl|boy|person|figure|character|couple|people)\b", "peaceful landscape", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"(?<!no\s)(?<!not\s)(?<!without\s)\b(her|his)\s+(hair|hands|eyes|face|fashion|coat|scarf)\b", "warm natural sunlight", cleaned, flags=re.IGNORECASE)

            # 3. 'no people' 및 실사 네거티브 제약 강제 보강
            if "no people" not in cleaned.lower():
                cleaned += ", tranquil scenery, pure nature, empty peaceful environment, no people, no humans, no person, no woman, no man, no silhouette, no crowd, real authentic photograph, shot on professional 35mm camera, photorealistic, lifelike textures, 4K UHD, absolutely no illustration, no anime, no painting, no drawing, no cartoon."
            elif "no illustration" not in cleaned.lower():
                cleaned += ", real authentic photograph, shot on professional 35mm camera, photorealistic, lifelike textures, 4K UHD, absolutely no illustration, no anime, no painting, no drawing, no cartoon."

        return cleaned

    @classmethod
    def _enforce_suno_genre(cls, suno_style: str, genre: str) -> str:
        """
        Suno에 전달되는 style 태그에 사용자가 GUI에서 선택한 음악 장르의 핵심 키워드가
        100% 반드시 최우선으로 포함되도록 보장하는 가드 함수
        """
        genre_info = cls.GENRE_PROFILES.get(genre)
        if not genre_info:
            for k, v in cls.GENRE_PROFILES.items():
                if k.lower() in genre.lower() or any(w.lower() in genre.lower() for w in k.split()):
                    genre_info = v
                    break
        if not genre_info:
            genre_info = cls.GENRE_PROFILES["New Age / Piano"]

        primary_tags = genre_info["primary_tags"]
        primary_key = primary_tags.split(",")[0].strip().lower()
        if primary_key not in suno_style.lower():
            combined = f"{primary_tags}, {suno_style.strip()}"
        else:
            combined = suno_style.strip()

        # 중복 태그 정제 및 순서 보존
        tags = [t.strip() for t in combined.split(",") if t.strip()]
        seen = set()
        unique_tags = []
        for t in tags:
            lower_t = t.lower()
            if lower_t not in seen:
                seen.add(lower_t)
                unique_tags.append(t)
        return ", ".join(unique_tags)

    @classmethod
    def _smart_fallback_plan(cls, mood: str, genre: str, is_instrumental: bool, custom_lyrics: str = "", image_style: str = "photo") -> dict:
        """Gemini 서버 일시 부하(503) 시에도 제작이 중단되지 않도록 하는 지능형 백업 플래너 (장르별 맞춤 악기 완벽 적용)"""
        is_rock = "rock" in genre.lower()
        if is_rock:
            title = f"{genre.split('/')[0].strip()} - Electric Anthem"
        else:
            title = f"{genre.split('/')[0].strip()} - Autumn Serenity" if any(w in mood for w in ["가을", "단풍", "10월"]) else f"{genre.split('/')[0].strip()} - Peaceful Healing"
        
        genre_info = cls.GENRE_PROFILES.get(genre)
        if not genre_info:
            for k, v in cls.GENRE_PROFILES.items():
                if k.lower() in genre.lower() or any(w.lower() in genre.lower() for w in k.split()):
                    genre_info = v
                    break
        if not genre_info:
            genre_info = cls.GENRE_PROFILES["New Age / Piano"]

        primary_tags = genre_info["primary_tags"]
        inst_desc = genre_info["instruments"]
        tempo_desc = genre_info["tempo"]
        genre_desc = genre_info["description"]

        if is_instrumental:
            if is_rock:
                suno_prompt = (
                    f"Driving energetic {genre_desc}, featuring {inst_desc}. "
                    f"Powerful rock atmosphere, instrumental, stomping beat, no vocals. {tempo_desc}."
                )
                suno_style = f"{primary_tags}, instrumental, driving anthem"
            else:
                suno_prompt = (
                    f"Relaxing {genre_desc}, featuring {inst_desc}. "
                    f"Calm healing atmosphere, instrumental, soothing, no vocals. {tempo_desc}."
                )
                suno_style = f"{primary_tags}, ambient, healing, instrumental"
        else:
            if custom_lyrics:
                suno_prompt = custom_lyrics
            else:
                if is_rock:
                    suno_prompt = (
                        f"[Verse 1]\n"
                        f"Neon lights flashing in the midnight air\n"
                        f"Electric sound and excitement everywhere\n"
                        f"Feel the boots stomping to the rhythm and beat\n"
                        f"Glamour and fire running down the street\n\n"
                        f"[Chorus]\n"
                        f"Turn up the guitar, let the anthem roll\n"
                        f"Glitter and thunder deep inside your soul\n"
                        f"Shouting together under neon stars\n"
                        f"Forever rock and roll, this world is ours\n\n"
                        f"[Outro]\n"
                        f"Glam rock into the night!"
                    )
                    vocal_style = genre_info["vocal_style"]
                    suno_style = f"{primary_tags}, {vocal_style}, rock anthem"
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
                    vocal_style = genre_info["vocal_style"]
                    suno_style = f"{primary_tags}, {vocal_style}, healing ballad"
        
        if image_style == "art":
            image_prompt = (
                f"3x3 grid storyboard, 9 sequential cinematic scenes, each scene in 16:9 widescreen ratio, 4K resolution, beautiful aesthetic illustration and painterly artwork. "
                f"Cinematic artistic painting of {mood}. Breathtaking pure nature and peaceful outdoor scenery, warm glowing light, vibrant autumn foliage, empty park paths, "
                f"quiet wooden bench, sunbeams through trees, highly consistent artistic illustration style and atmosphere across all 9 panels. "
                f"Artistic digital painting, watercolor details, 4K UHD, painterly textures, "
                f"scenic landscape only, no people, no humans, no person, no woman, no man, no silhouette, absolutely no real photograph, no camera photo, no realistic photography."
            )
        else:
            image_prompt = (
                f"3x3 grid storyboard, 9 sequential cinematic scenes, each scene in 16:9 widescreen ratio, 4K resolution, ultra-detailed authentic photography. "
                f"Cinematic realistic landscape photograph of {mood}. Breathtaking pure nature and outdoor scenery, warm golden hour sunlight, colorful autumn foliage, empty park paths, "
                f"quiet wooden bench, sunbeams through trees, highly consistent photography and atmosphere across all 9 panels. "
                f"Shot on 35mm DSLR camera, f/2.8, award-winning real photograph, 4K UHD, photorealistic textures, "
                f"scenic landscape only, no people, no humans, no person, no woman, no man, no silhouette, absolutely no illustration, no anime, no painting, no drawing, no cartoon."
            )
        
        return {
            "title": title,
            "suno_prompt": suno_prompt,
            "suno_style": suno_style,
            "image_prompt": image_prompt
        }
