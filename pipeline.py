"""
Wealth Stories — YouTube Automation Pipeline
Channel: @WealthStoriesWS
Stack: google-genai (new SDK) + Groq + Cerebras fallback
       HuggingFace SDXL images + placeholder fallback
       Edge TTS + FFmpeg
"""

import os, json, time, requests, subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── API KEYS ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
HF_API_KEY       = os.environ.get("HF_API_KEY", "")   # HuggingFace

# ─── CHARACTER BIBLE (consistent across all scenes) ───────────────────────────
CHAR = {
    1: "Arjun 22yo Indian male dark wavy hair torn beige kurta barefoot poor",
    2: "Arjun 22yo Indian male dark wavy hair torn beige kurta barefoot poor",
    3: "Arjun 22yo Indian male white shirt worn jeans determined face",
    4: "Arjun 22yo Indian male white shirt worn jeans walking rain",
    5: "Arjun 22yo Indian male clean formal shirt focused working",
    6: "Arjun 22yo Indian male clean formal shirt shocked happy",
    7: "Arjun 22yo Indian male neat kurta confident proud returning home",
    8: "Arjun 22yo Indian male neat kurta confident looking at sunrise",
}

# ─── SCRIPT PROMPT ────────────────────────────────────────────────────────────
SCRIPT_PROMPT = (
    'You are a YouTube scriptwriter for "Wealth Stories" channel.\n'
    'Write a rags-to-riches emotional English story for topic: "{topic}"\n\n'
    'Return ONLY valid JSON, no markdown, no backticks, no explanation:\n\n'
    '{{"title":"story title max 60 chars",'
    '"hook":"2 grabbing sentences",'
    '"narration_intro":"3-4 emotional English lines",'
    '"scenes":['
    '{{"scene_no":1,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c1}, mud hut background, warm sunset, hopeful mood, wide shot, 16:9"}},'
    '{{"scene_no":2,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c2}, poor family inside hut, candlelight, sad mood, close-up, 16:9"}},'
    '{{"scene_no":3,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c3}, street at night studying under lamp, dramatic light, determined, 16:9"}},'
    '{{"scene_no":4,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c4}, city street rejected walking in rain, emotional mood, 16:9"}},'
    '{{"scene_no":5,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c5}, small rented room laptop glowing, focused night, 16:9"}},'
    '{{"scene_no":6,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c6}, phone showing first payment, shocked happy expression, 16:9"}},'
    '{{"scene_no":7,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c7}, village new house family reunion, golden sunset, emotional, 16:9"}},'
    '{{"scene_no":8,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c8}, city skyline sunrise view, triumphant mood, wide shot, 16:9"}}'
    '],'
    '"narration_outro":"closing motivational English line",'
    '"moral":"one line moral of the story"}}'
)

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    for marker in ["```json", "```"]:
        if marker in raw:
            raw = raw.split(marker)[1].split("```")[0].strip()
            break
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]
    return json.loads(raw)

def _get_prompt(topic: str) -> str:
    return SCRIPT_PROMPT.format(
        topic=topic,
        c1=CHAR[1], c2=CHAR[2], c3=CHAR[3], c4=CHAR[4],
        c5=CHAR[5], c6=CHAR[6], c7=CHAR[7], c8=CHAR[8],
    )

# ═════════════════════════════════════════════════════════════════════════════
# STEP 1: SCRIPT — Gemini Flash → Groq → Cerebras
# ═════════════════════════════════════════════════════════════════════════════

def _try_gemini(topic: str) -> dict:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    r = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=_get_prompt(topic)
    )
    return _parse_json(r.text)

def _try_groq(topic: str) -> dict:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": _get_prompt(topic)}],
            "temperature": 0.8,
            "max_tokens": 4000
        },
        timeout=60
    )
    r.raise_for_status()
    return _parse_json(r.json()["choices"][0]["message"]["content"])

def _try_cerebras(topic: str) -> dict:
    if not CEREBRAS_API_KEY:
        raise ValueError("CEREBRAS_API_KEY not set")
    r = requests.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {CEREBRAS_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.3-70b",
            "messages": [{"role": "user", "content": _get_prompt(topic)}],
            "temperature": 0.8,
            "max_tokens": 4000
        },
        timeout=60
    )
    r.raise_for_status()
    return _parse_json(r.json()["choices"][0]["message"]["content"])

def generate_script(topic: str) -> dict:
    providers = [
        ("Gemini 2.5 Flash",      _try_gemini),
        ("Groq Llama 3.3 70B",    _try_groq),
        ("Cerebras Llama 3.3 70B", _try_cerebras),
    ]
    last_err = None
    for name, fn in providers:
        try:
            print(f"\n📝 Script → {name}...")
            result = fn(topic)
            assert "scenes" in result and len(result["scenes"]) >= 6
            assert all("image_prompt" in s for s in result["scenes"])
            result["_provider"] = name
            print(f"   ✅ Done via {name}")
            with open(OUTPUT_DIR / "script.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return result
        except Exception as e:
            print(f"   ❌ {name}: {e}")
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"All script providers failed. Last: {last_err}")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 2: IMAGES — HuggingFace SDXL → Solid Color Placeholder
# No Pollinations.
# ═════════════════════════════════════════════════════════════════════════════

def _save_image(content: bytes, scene_no: int) -> str:
    if content.startswith(b'<') or content.startswith(b'{'):
        raise ValueError(f"API returned text instead of image: {content[:200]}")
    if len(content) < 3000:
        raise ValueError(f"Image too small: {len(content)} bytes")
    path = OUTPUT_DIR / f"scene_{scene_no:02d}.jpg"
    path.write_bytes(content)
    return str(path)

def _hf_image(prompt: str, scene_no: int) -> str:
    """HuggingFace SDXL — free tier 30k requests/month"""
    if not HF_API_KEY:
        raise ValueError("HF_API_KEY missing")
    # Shorten prompt to avoid token limit issues
    short_prompt = prompt[:400]
    r = requests.post(
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
        headers={"Authorization": f"Bearer {HF_API_KEY}"},
        json={"inputs": short_prompt},
        timeout=90
    )
    r.raise_for_status()
    return _save_image(r.content, scene_no)

def _placeholder(scene_no: int) -> str:
    """Last resort — solid color block"""
    colors = ["#1a1a2e","#16213e","#0f3460","#533483","#2b2d42","#8d99ae","#e94560","#ef233c"]
    color  = colors[scene_no % len(colors)]
    path   = OUTPUT_DIR / f"scene_{scene_no:02d}.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color={color}:size=1280x720:duration=1",
         "-vframes", "1", str(path)],
        capture_output=True, check=True
    )
    return str(path)

def generate_images(script: dict) -> list:
    image_paths = []
    for scene in script["scenes"]:
        n      = scene["scene_no"]
        prompt = scene["image_prompt"]
        print(f"\n🎨 Image Scene {n}/8...")
        path = None

        # Try HuggingFace only
        if HF_API_KEY:
            try:
                path = _hf_image(prompt, n)
                print(f"   ✅ HuggingFace SDXL")
            except Exception as e:
                print(f"   ❌ HuggingFace failed: {e}")
        else:
            print("   ⚠️  HF_API_KEY not set, skipping HuggingFace")

        # Fallback to placeholder
        if not path:
            path = _placeholder(n)
            print(f"   ⚠️  Placeholder used for scene {n}")

        image_paths.append(path)
        time.sleep(2)   # Respect rate limits
    return image_paths

# ═════════════════════════════════════════════════════════════════════════════
# STEP 3: VOICEOVER — Edge TTS (en-US-AriaNeural)
# ═════════════════════════════════════════════════════════════════════════════

def generate_voiceover(script: dict) -> str:
    parts = [
        script.get("hook", ""),
        script["narration_intro"],
        "",
    ]
    for scene in script["scenes"]:
        parts.append(scene["narration"])
        if scene.get("dialogue", "").strip():
            parts.append(f'"{scene["dialogue"]}"')
        parts.append("")
    parts.append(script["narration_outro"])
    parts.append(f'The moral of this story — {script.get("moral", "")}')

    full_text = "\n".join(parts)
    audio_path = OUTPUT_DIR / "voiceover.mp3"

    print(f"\n🎙️  Voiceover ({len(full_text)} chars) → en-US-AriaNeural...")

    result = subprocess.run(
        ["edge-tts",
         "--voice", "en-US-AriaNeural",
         "--rate",  "+0%",
         "--pitch", "-3Hz",
         "--text",  full_text,
         "--write-media", str(audio_path)],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Edge TTS failed: {result.stderr}")

    print(f"   ✅ Voiceover saved ({audio_path.stat().st_size // 1024} KB)")
    return str(audio_path)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 4: VIDEO — FFmpeg Ken Burns zoom assembly
# ═════════════════════════════════════════════════════════════════════════════

def assemble_video(image_paths: list, audio_path: str) -> str:
    valid = [p for p in image_paths if p and Path(p).exists()]
    if not valid:
        raise ValueError("No images to assemble!")

    # Get audio duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         audio_path],
        capture_output=True, text=True, check=True
    )
    total_dur  = float(probe.stdout.strip())
    per_img    = total_dur / len(valid)
    fps        = 25
    frames     = int(per_img * fps)

    print(f"\n📹 Assembling {len(valid)} scenes × {per_img:.1f}s = {total_dur:.0f}s total...")

    input_args, filters = [], []

    zoom_patterns = [
        "z='min(zoom+0.0012,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "z='if(lte(zoom,1.0),1.25,max(1.0,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "z='min(zoom+0.0010,1.20)':x='0':y='ih/2-(ih/zoom/2)'",
    ]

    for i, img in enumerate(valid):
        input_args += ["-loop", "1", "-t", str(per_img + 0.5), "-i", img]
        zoom = zoom_patterns[i % len(zoom_patterns)]
        filters.append(
            f"[{i}:v]scale=1280:720,"
            f"zoompan={zoom}:d={frames}:s=1280x720:fps={fps}[v{i}]"
        )

    concat = "".join(f"[v{i}]" for i in range(len(valid)))
    filters.append(f"{concat}concat=n={len(valid)}:v=1:a=0[outv]")

    output_path = OUTPUT_DIR / "final_video.mp4"

    cmd = (
        ["ffmpeg", "-y"]
        + input_args
        + ["-i", audio_path]
        + ["-filter_complex", ";".join(filters)]
        + ["-map", "[outv]", "-map", f"{len(valid)}:a"]
        + ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]
        + ["-c:a", "aac", "-b:a", "192k", "-shortest"]
        + [str(output_path)]
    )

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-600:]}")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Video ready: {output_path} ({size_mb:.1f} MB)")
    return str(output_path)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 5: METADATA — Same fallback chain
# ═════════════════════════════════════════════════════════════════════════════

def generate_metadata(script: dict) -> dict:
    prompt = (
        f'YouTube metadata for story: "{script["title"]}"\n'
        f'Summary: {script["narration_intro"][:200]}\n'
        f'Moral: {script.get("moral","")}\n\n'
        'Return ONLY valid JSON:\n'
        '{"youtube_title":"catchy title with 1-2 emojis max 70 chars",'
        '"description":"3 paragraph English description",'
        '"tags":["wealth stories","rags to riches","indian success story","motivational","financial freedom","struggle to success","inspirational","money story","success motivation","emotional story"]}'
    )

    def _gemini_meta():
        from google import genai
        c = genai.Client(api_key=GEMINI_API_KEY)
        return _parse_json(
            c.models.generate_content(model="gemini-2.5-flash", contents=prompt).text
        )

    def _groq_meta():
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 600},
            timeout=30
        )
        r.raise_for_status()
        return _parse_json(r.json()["choices"][0]["message"]["content"])

    def _cerebras_meta():
        r = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 600},
            timeout=30
        )
        r.raise_for_status()
        return _parse_json(r.json()["choices"][0]["message"]["content"])

    for name, fn in [("Gemini", _gemini_meta), ("Groq", _groq_meta), ("Cerebras", _cerebras_meta)]:
        try:
            print(f"\n📋 Metadata → {name}...")
            result = fn()
            # ensure title length
            if "youtube_title" in result and len(result["youtube_title"]) > 70:
                result["youtube_title"] = result["youtube_title"][:70]
            with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("   ✅ Done")
            return result
        except Exception as e:
            print(f"   ❌ {name}: {e}")

    # Fallback metadata
    fallback_title = f"⭐ {script['title']}"[:70]
    fallback = {
        "youtube_title": fallback_title,
        "description": script["narration_intro"],
        "tags": ["wealth stories", "rags to riches", "indian success story",
                 "motivational", "financial freedom"]
    }
    with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(fallback, f, ensure_ascii=False, indent=2)
    return fallback

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

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
    print(f"  Script by : {script.get('_provider', '?')}")
    print(f"  YT Title  : {metadata.get('youtube_title', '?')}")
    print(f"  Video     : {video}")
    print(f"{'═'*55}\n")

if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else \
        "A poor boy from a village who became a millionaire with just 100 rupees"
    run_pipeline(topic)

