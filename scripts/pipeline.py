"""
Wealth Stories — YouTube Automation Pipeline
Channel: @WealthStoriesWS
Niche: Emotional Hindi-inspired Finance Stories (English narration)
Style: Pixar/Cinematic — Poor Indian boy → Rich transformation
"""

import os, json, time, requests, subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── API KEYS ──────────────────────────────────────────────────────────────
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
HF_TOKEN         = os.environ.get("HF_TOKEN", "")

# ════════════════════════════════════════════════════════════════════════════
# SCRIPT PROMPT — Wealth Stories Style
# ════════════════════════════════════════════════════════════════════════════


# ─── CHARACTER BIBLE — Same character across all scenes ──────────────────────
CHARACTER_BIBLE = {
    "scenes_1_2": "Arjun, young Indian male age 22, dark wavy hair, deep brown eyes, sharp jawline, wheatish skin, torn dirty beige kurta, barefoot, dusty village background",
    "scenes_3_4": "Arjun, young Indian male age 22, dark wavy hair, deep brown eyes, sharp jawline, wheatish skin, plain white shirt with worn jeans, worn chappals",
    "scenes_5_6": "Arjun, young Indian male age 22, dark wavy hair, deep brown eyes, sharp jawline, wheatish skin, clean simple formal shirt, focused determined expression",
    "scenes_7_8": "Arjun, young Indian male age 22, dark wavy hair, deep brown eyes, sharp jawline, wheatish skin, neat pressed kurta, confident proud smile",
}

SCRIPT_PROMPT = '''
You are a world-class YouTube scriptwriter for the channel "Wealth Stories".

Write a script for topic: "{topic}"

STYLE RULES:
- Tone: Emotional, cinematic, documentary-style narration
- Voice: English — warm, storytelling, like a Netflix documentary
- Characters: Indian — poor boy/family from village who rises to wealth
- Story arc: Struggle → Turning point → Success → Life lesson
- Each scene image must match: Pixar/CGI cinematic style, Indian characters

CHARACTER CONSISTENCY RULE (VERY IMPORTANT):
Main character "Arjun" must look EXACTLY the same in every scene:
- Scenes 1-2: {char_1_2}
- Scenes 3-4: {char_3_4}
- Scenes 5-6: {char_5_6}
- Scenes 7-8: {char_7_8}

IMPORTANT: Return ONLY valid JSON. No markdown. No backticks. No explanation.

{{
  "title": "Compelling story title (max 60 chars)",
  "hook": "First 2 sentences that grab attention immediately",
  "narration_intro": "Opening narration in English (3-4 emotional lines)",
  "scenes": [
    {{
      "scene_no": 1,
      "narration": "Scene narration in English (3-4 sentences, emotional)",
      "dialogue": "Character dialogue in English (optional, empty string if none)",
      "image_prompt": "Cinematic Pixar 3D style, [CHARACTER from bible above EXACT description], [background — village hut/city/office], [lighting — warm golden/dramatic/sunrise], [mood — hopeful/intense/joyful]"
    }}
  ],
  "narration_outro": "Closing motivational line with life lesson",
  "moral": "One line moral of the story"
}}

SCENE REQUIREMENTS:
- Exactly 8 scenes
- Scene 1-2: Poor background, struggle, village setting
- Scene 3-4: The turning point / decision moment  
- Scene 5-6: Hard work, building wealth
- Scene 7-8: Success, transformation, emotional climax
- EVERY image_prompt MUST start with the exact character description from bible
'''

# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    for marker in ["```json", "```"]:
        if marker in raw:
            raw = raw.split(marker)[1].split("```")[0].strip()
            break
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    return json.loads(raw)


def _get_prompt(topic: str) -> str:
    return SCRIPT_PROMPT.format(
        topic=topic,
        char_1_2=CHARACTER_BIBLE["scenes_1_2"],
        char_3_4=CHARACTER_BIBLE["scenes_3_4"],
        char_5_6=CHARACTER_BIBLE["scenes_5_6"],
        char_7_8=CHARACTER_BIBLE["scenes_7_8"],
    )

def _try_gemini(topic: str) -> dict:
    if not GEMINI_API_KEY:
        raise ValueError("No GEMINI_API_KEY")
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    r = genai.GenerativeModel("gemini-2.5-flash").generate_content(_get_prompt(topic))
    return _parse_json(r.text)


def _try_groq(topic: str) -> dict:
    if not GROQ_API_KEY:
        raise ValueError("No GROQ_API_KEY")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile",
              "messages": [{"role": "user", "content": _get_prompt(topic)}],
              "temperature": 0.8, "max_tokens": 4000},
        timeout=60
    )
    r.raise_for_status()
    return _parse_json(r.json()["choices"][0]["message"]["content"])


def _try_cerebras(topic: str) -> dict:
    if not CEREBRAS_API_KEY:
        raise ValueError("No CEREBRAS_API_KEY")
    r = requests.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b",
              "messages": [{"role": "user", "content": _get_prompt(topic)}],
              "temperature": 0.8, "max_tokens": 4000},
        timeout=60
    )
    r.raise_for_status()
    return _parse_json(r.json()["choices"][0]["message"]["content"])


# ════════════════════════════════════════════════════════════════════════════
# STEP 1: SCRIPT — Fallback chain
# ════════════════════════════════════════════════════════════════════════════

def generate_script(topic: str) -> dict:
    providers = [
        ("Gemini 2.5 Flash", _try_gemini),
        ("Groq Llama 3.3 70B", _try_groq),
        ("Cerebras Llama 3.3 70B", _try_cerebras),
    ]
    last_err = None
    for name, fn in providers:
        try:
            print(f"\n📝 Script → trying {name}...")
            result = fn(topic)
            assert "scenes" in result and len(result["scenes"]) >= 6
            assert all("image_prompt" in s for s in result["scenes"])
            result["_provider"] = name
            print(f"   ✅ Script done via {name}")
            with open(OUTPUT_DIR / "script.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return result
        except Exception as e:
            print(f"   ❌ {name}: {e}")
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"All script providers failed: {last_err}")


# ════════════════════════════════════════════════════════════════════════════
# STEP 2: IMAGES — Free alternatives with Hugging Face as primary
# Style: Cinematic Pixar — matches thumbnail style
# ════════════════════════════════════════════════════════════════════════════

def _huggingface_inference(prompt: str, n: int) -> str:
    """Generate image using Hugging Face Inference API (free tier with HF_TOKEN)"""
    if not HF_TOKEN:
        raise ValueError("No HF_TOKEN environment variable")
    
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=HF_TOKEN)
    
    # Use Stable Diffusion 3.5 Large Turbo for quality cinematic images
    styled = f"{prompt}, cinematic, high quality, detailed, professional lighting"
    image = client.text_to_image(
        styled, 
        model="stabilityai/stable-diffusion-3.5-large-turbo"
    )
    path = OUTPUT_DIR / f"scene_{n:02d}.jpg"
    image.save(str(path))
    return str(path)


def _pollinations_default(prompt: str, n: int) -> str:
    import urllib.parse
    # Add consistent style suffix to every image
    styled = f"{prompt}, consistent character design, same Indian male protagonist throughout, Pixar CGI cinematic quality"
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(styled)}?width=1280&height=720&nologo=true&seed={n*37}"
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    path = OUTPUT_DIR / f"scene_{n:02d}.jpg"
    path.write_bytes(r.content)
    return str(path)


def _pollinations_flux(prompt: str, n: int) -> str:
    import urllib.parse
    styled = f"{prompt}, Pixar animation style, cinematic lighting, Indian characters"
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(styled)}?width=1280&height=720&model=flux&nologo=true&seed={n*73}"
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    path = OUTPUT_DIR / f"scene_{n:02d}.jpg"
    path.write_bytes(r.content)
    return str(path)


def _placeholder(prompt: str, n: int) -> str:
    colors = ["#1a1a2e", "#16213e", "#0f3460", "#533483", "#e94560", "#2b2d42", "#8d99ae", "#ef233c"]
    color = colors[n % len(colors)]
    path = OUTPUT_DIR / f"scene_{n:02d}.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color={color}:size=1280x720:duration=1",
         "-vframes", "1", str(path)],
        capture_output=True
    )
    return str(path)


def generate_images(script: dict) -> list:
    image_paths = []
    providers = [
        ("Hugging Face (Free)", _huggingface_inference),     # Try free Hugging Face first
        ("Placeholder",        _placeholder),                # Fast fallback (no API)
        ("Pollinations Default", _pollinations_default),     # Paid service
        ("Pollinations Flux",    _pollinations_flux),        # Paid service (higher quality)
    ]
    for scene in script["scenes"]:
        n = scene["scene_no"]
        prompt = scene["image_prompt"]
        print(f"\n🎨 Image Scene {n}/8...")
        path = None
        for name, fn in providers:
            try:
                path = fn(prompt, n)
                print(f"   ✅ {name}")
                break
            except Exception as e:
                print(f"   ❌ {name}: {e}")
                time.sleep(3)
        image_paths.append(path)
        time.sleep(1.5)
    return image_paths


# ══════════════════════════════��═════════════════════════════════════════════
# STEP 3: VOICEOVER — Edge TTS English
# Voice: en-US-AriaNeural (warm, emotional female — perfect for storytelling)
# ════════════════════════════════════════════════════════════════════════════

def generate_voiceover(script: dict) -> str:
    # Assemble full narration
    parts = []
    parts.append(script.get("hook", ""))
    parts.append(script["narration_intro"])
    parts.append("")

    for scene in script["scenes"]:
        parts.append(scene["narration"])
        if scene.get("dialogue", "").strip():
            parts.append(f'"{scene["dialogue"]}"')
        parts.append("")

    parts.append(script["narration_outro"])
    parts.append(f'The moral of this story — {script.get("moral", "")}')

    full_text = "\n".join(parts)
    audio_path = OUTPUT_DIR / "voiceover.mp3"

    print(f"\n🎙️ Voiceover ({len(full_text)} chars) — en-US-AriaNeural...")

    result = subprocess.run([
        "edge-tts",
        "--voice", "en-US-AriaNeural",
        "--rate",  "+0%",
        "--pitch", "-3",
        "--text",  full_text,
        "--write-media", str(audio_path)
    ], capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Edge TTS failed: {result.stderr}")

    print(f"   ✅ Voiceover saved")
    return str(audio_path)


# ════════════════════════════════════════════════════════════════════════════
# STEP 4: VIDEO ASSEMBLY — FFmpeg Ken Burns
# ════════════════════════════════════════════════════════════════════════════

def assemble_video(image_paths: list, audio_path: str) -> str:
    valid = [p for p in image_paths if p and Path(p).exists()]
    if not valid:
        raise ValueError("No images!")

    # Get audio duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    total = float(probe.stdout.strip())
    per_img = total / len(valid)
    fps = 25
    frames = int(per_img * fps)

    print(f"\n📹 Assembling {len(valid)} scenes × {per_img:.1f}s = {total:.0f}s...")

    input_args, filter_parts = [], []

    for i, img in enumerate(valid):
        input_args += ["-loop", "1", "-t", str(per_img + 0.5), "-i", img]
        # Alternate zoom directions for cinematic feel
        if i % 3 == 0:
            zoom = "z='min(zoom+0.0012,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        elif i % 3 == 1:
            zoom = "z='if(lte(zoom,1.0),1.25,max(1.0,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        else:
            zoom = "z='min(zoom+0.0012,1.2)':x='0':y='ih/2-(ih/zoom/2)'"
        filter_parts.append(
            f"[{i}:v]scale=1280:720,zoompan={zoom}:d={frames}:s=1280x720:fps={fps}[v{i}]"
        )

    concat = "".join(f"[v{i}]" for i in range(len(valid)))
    filter_parts.append(f"{concat}concat=n={len(valid)}:v=1:a=0[outv]")

    out = OUTPUT_DIR / "final_video.mp4"
    cmd = (["ffmpeg", "-y"]
        + input_args + ["-i", audio_path]
        + ["-filter_complex", ";".join(filter_parts)]
        + ["-map", "[outv]", "-map", f"{len(valid)}:a"]
        + ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]
        + ["-c:a", "aac", "-b:a", "192k", "-shortest"]
        + [str(out)]
    )

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg: {r.stderr[-800:]}")

    size_mb = out.stat().st_size / (1024*1024)
    print(f"   ✅ Video ready: {out} ({size_mb:.1f} MB)")
    return str(out)


# ════════════════════════════════════════════════════════════════════════════
# STEP 5: METADATA
# ════════════════════════════════════════════════════════════════════════════

META_PROMPT = """
Write YouTube metadata for a video titled: "{title}"
Story summary: {intro}
Moral: {moral}

Return ONLY valid JSON, no markdown:

{{
  "youtube_title": "Emotional title with 1-2 emojis, max 70 chars, English",
  "description": "3 paragraphs English description. Para 1: story hook. Para 2: what viewer will learn. Para 3: call to action + moral",
  "tags": ["wealth stories", "rags to riches", "indian success story", "motivational story", "financial freedom", "struggle to success", "inspirational", "money story", "hindi kahani english", "stock market"],
  "category": "Education"
}}
"""

def generate_metadata(script: dict) -> dict:
    prompt = META_PROMPT.format(
        title=script["title"],
        intro=script["narration_intro"],
        moral=script.get("moral", "")
    )

    def _gemini_meta():
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        return _parse_json(genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt).text)

    def _groq_meta():
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}], "max_tokens": 800},
            timeout=30
        )
        r.raise_for_status()
        return _parse_json(r.json()["choices"][0]["message"]["content"])

    def _cerebras_meta():
        r = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b",
                  "messages": [{"role": "user", "content": prompt}], "max_tokens": 800},
            timeout=30
        )
        r.raise_for_status()
        return _parse_json(r.json()["choices"][0]["message"]["content"])

    for name, fn in [("Gemini", _gemini_meta), ("Groq", _groq_meta), ("Cerebras", _cerebras_meta)]:
        try:
            print(f"\n📋 Metadata → {name}...")
            result = fn()
            print(f"   ✅ Done")
            with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return result
        except Exception as e:
            print(f"   ❌ {name}: {e}")

    # Fallback
    fallback = {
        "youtube_title": f"⭐ {script['title']}",
        "description": script["narration_intro"],
        "tags": ["wealth stories", "rags to riches", "indian success story"],
        "category": "Education"
    }
    with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(fallback, f, ensure_ascii=False, indent=2)
    return fallback


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def run_pipeline(topic: str):
    print(f"\n{'═'*55}")
    print(f"  💰 WEALTH STORIES PIPELINE")
    print(f"  Topic: {topic}")
    print(f"{'═'*55}")

    script   = generate_script(topic)
    images   = generate_images(script)
    audio    = generate_voiceover(script)
    video    = assemble_video(images, audio)
    metadata = generate_metadata(script)

    print(f"\n{'═'*55}")
    print(f"  ✅ PIPELINE COMPLETE!")
    print(f"  Script by : {script.get('_provider')}")
    print(f"  YT Title  : {metadata['youtube_title']}")
    print(f"  Video     : {video}")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "A poor boy from a village who became a millionaire"
    run_pipeline(topic)
