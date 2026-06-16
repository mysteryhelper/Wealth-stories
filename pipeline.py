"""
Wealth Stories — YouTube Automation Pipeline
Channel: @WealthStoriesWS

IMAGE PROVIDERS (tried in order):
  1. Gemini 2.5 Flash Image  — FREE, rotates across multiple Gmail API keys
  2. Cloudflare Workers AI   — FREE 10k/day, FLUX model (CF_API_TOKEN + CF_ACCOUNT_ID)
  3. ByteDance Seedream 3.0  — via HuggingFace (may be blocked on some runners)

SCRIPT PROVIDERS: Gemini 2.5 Flash → Groq → Cerebras
VOICE: Edge TTS en-US-AriaNeural

GITHUB ACTIONS SECRETS:
  GEMINI_API_KEY    ← Google AI Studio key (required)
  GEMINI_API_KEY_1  ← 2nd Gmail key (optional)
  GEMINI_API_KEY_2  ← 3rd Gmail key (optional)
  GROQ_API_KEY      ← Groq (required for script fallback)
  CEREBRAS_API_KEY  ← Cerebras (script fallback)
  HF_API_KEY        ← HuggingFace (image fallback, may be blocked)
  CF_API_TOKEN      ← Cloudflare API token (image fallback)
  CF_ACCOUNT_ID     ← Cloudflare Account ID (image fallback)
"""

import os, json, time, requests, subprocess, base64
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ── API keys ──────────────────────────────────────────────────────────────────

GEMINI_KEYS = []
for env_name in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2"]:
    k = os.environ.get(env_name, "").strip()
    if k and k not in GEMINI_KEYS:
        GEMINI_KEYS.append(k)

GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
HF_API_KEY       = os.environ.get("HF_API_KEY", "")
CF_API_TOKEN     = os.environ.get("CF_API_TOKEN", "")
CF_ACCOUNT_ID    = os.environ.get("CF_ACCOUNT_ID", "")

# ── characters ────────────────────────────────────────────────────────────────

CHAR = {
    1: "Arjun 22yo Indian male dark wavy hair torn beige kurta barefoot poor village",
    2: "Arjun 22yo Indian male dark wavy hair torn beige kurta barefoot poor village",
    3: "Arjun 22yo Indian male white shirt worn jeans determined face city",
    4: "Arjun 22yo Indian male white shirt worn jeans walking rain city",
    5: "Arjun 22yo Indian male clean formal shirt focused working laptop",
    6: "Arjun 22yo Indian male clean formal shirt shocked happy phone",
    7: "Arjun 22yo Indian male neat kurta confident proud returning village",
    8: "Arjun 22yo Indian male neat kurta confident looking sunrise city",
}

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
    '"image_prompt":"Pixar 3D cinematic, {c3}, street at night studying under lamp, dramatic light, 16:9"}},'
    '{{"scene_no":4,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c4}, city street rejected walking in rain, emotional mood, 16:9"}},'
    '{{"scene_no":5,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c5}, small rented room laptop glowing, focused night, 16:9"}},'
    '{{"scene_no":6,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c6}, phone showing first payment, shocked happy, 16:9"}},'
    '{{"scene_no":7,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c7}, village new house family reunion, golden sunset, 16:9"}},'
    '{{"scene_no":8,"narration":"3 sentences emotional","dialogue":"",'
    '"image_prompt":"Pixar 3D cinematic, {c8}, city skyline sunrise view, triumphant mood, wide shot, 16:9"}}'
    '],'
    '"narration_outro":"closing motivational English line",'
    '"moral":"one line moral of the story"}}'
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_json(raw):
    raw = raw.strip()
    for m in ["```json", "```"]:
        if m in raw:
            raw = raw.split(m)[1].split("```")[0].strip()
            break
    s, e = raw.find("{"), raw.rfind("}") + 1
    if s != -1 and e > s:
        raw = raw[s:e]
    return json.loads(raw)

def _get_prompt(topic):
    return SCRIPT_PROMPT.format(
        topic=topic,
        c1=CHAR[1], c2=CHAR[2], c3=CHAR[3], c4=CHAR[4],
        c5=CHAR[5], c6=CHAR[6], c7=CHAR[7], c8=CHAR[8],
    )

def _save_img(content, n):
    if len(content) < 10000:
        raise ValueError(f"Too small ({len(content)} bytes) — not a real image")
    path = OUTPUT_DIR / f"scene_{n:02d}.jpg"
    path.write_bytes(content)
    return str(path)

# ── script generation ─────────────────────────────────────────────────────────

def _gemini_script(topic, api_key):
    from google import genai
    client = genai.Client(api_key=api_key)
    r = client.models.generate_content(
        model="gemini-2.5-flash", contents=_get_prompt(topic)
    )
    return _parse_json(r.text)

def _groq_script(topic):
    if not GROQ_API_KEY: raise ValueError("No GROQ_API_KEY")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                 "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile",
              "messages": [{"role": "user", "content": _get_prompt(topic)}],
              "temperature": 0.8, "max_tokens": 4000},
        timeout=60
    )
    r.raise_for_status()
    return _parse_json(r.json()["choices"][0]["message"]["content"])

def _cerebras_script(topic):
    if not CEREBRAS_API_KEY: raise ValueError("No CEREBRAS_API_KEY")
    r = requests.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}",
                 "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b",
              "messages": [{"role": "user", "content": _get_prompt(topic)}],
              "temperature": 0.8, "max_tokens": 4000},
        timeout=60
    )
    r.raise_for_status()
    return _parse_json(r.json()["choices"][0]["message"]["content"])

def generate_script(topic):
    for i, key in enumerate(GEMINI_KEYS):
        try:
            print(f"\n  Script -> Gemini key #{i+1}...")
            result = _gemini_script(topic, key)
            assert "scenes" in result and len(result["scenes"]) >= 6
            result["_provider"] = f"Gemini key #{i+1}"
            print(f"   OK")
            with open(OUTPUT_DIR / "script.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return result
        except Exception as e:
            print(f"   FAIL Gemini key #{i+1}: {e}")
            time.sleep(2)

    for name, fn in [("Groq", lambda: _groq_script(topic)),
                     ("Cerebras", lambda: _cerebras_script(topic))]:
        try:
            print(f"\n  Script -> {name}...")
            result = fn()
            assert "scenes" in result and len(result["scenes"]) >= 6
            result["_provider"] = name
            print(f"   OK")
            with open(OUTPUT_DIR / "script.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return result
        except Exception as e:
            print(f"   FAIL {name}: {e}")
            time.sleep(2)

    raise RuntimeError("ALL script providers failed")

# ── image providers ───────────────────────────────────────────────────────────

def _gemini_image(prompt, n, api_key, retries=2):
    """PRIMARY — Gemini 2.5 Flash Image. FREE 500/day per Gmail key."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    for attempt in range(1, retries + 1):
        try:
            print(f"   Gemini Image attempt {attempt}/{retries}...")
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-image-generation",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                )
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data and "image" in part.inline_data.mime_type:
                    img_bytes = part.inline_data.data
                    if isinstance(img_bytes, str):
                        img_bytes = base64.b64decode(img_bytes)
                    return _save_img(img_bytes, n)
            raise ValueError("No image part found in Gemini response")
        except Exception as e:
            print(f"   Gemini attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(8 * attempt)
    raise RuntimeError("Gemini Image failed")


def _cloudflare_image(prompt, n, retries=3):
    """
    FALLBACK 1 — Cloudflare Workers AI FLUX.1 Schnell
    FREE forever, 10k neurons/day, no DNS issues on GitHub Actions
    api.cloudflare.com is always accessible from GitHub Actions runners
    """
    if not CF_API_TOKEN or not CF_ACCOUNT_ID:
        raise ValueError("CF_API_TOKEN or CF_ACCOUNT_ID not set")
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    for attempt in range(1, retries + 1):
        try:
            print(f"   Cloudflare FLUX attempt {attempt}/{retries}...")
            r = requests.post(
                url,
                headers={"Authorization": f"Bearer {CF_API_TOKEN}",
                         "Content-Type": "application/json"},
                json={"prompt": prompt[:500], "num_steps": 8},
                timeout=90
            )
            r.raise_for_status()
            data = r.json()
            img_b64 = data.get("result", {}).get("image")
            if not img_b64:
                raise ValueError(f"No image in CF response: {str(data)[:300]}")
            return _save_img(base64.b64decode(img_b64), n)
        except Exception as e:
            print(f"   Cloudflare attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(10 * attempt)
    raise RuntimeError("Cloudflare FLUX failed")


def _huggingface_image(prompt, n, retries=2):
    """
    FALLBACK 2 — HuggingFace Seedream 3.0
    NOTE: May fail with DNS error on GitHub Actions Azure runners
    Kept as last resort in case runner has access
    """
    if not HF_API_KEY:
        raise ValueError("No HF_API_KEY")
    for attempt in range(1, retries + 1):
        try:
            print(f"   HuggingFace attempt {attempt}/{retries}...")
            r = requests.post(
                "https://api-inference.huggingface.co/models/ByteDance-Seed/Seedream-3.0",
                headers={"Authorization": f"Bearer {HF_API_KEY}"},
                json={"inputs": prompt[:500]},
                timeout=120
            )
            r.raise_for_status()
            ct = r.headers.get("Content-Type", "")
            if "image" not in ct:
                raise ValueError(f"Non-image response: {ct} — {r.text[:200]}")
            return _save_img(r.content, n)
        except Exception as e:
            print(f"   HuggingFace attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(15 * attempt)
    raise RuntimeError("HuggingFace failed")


def generate_images(script):
    """
    Provider order (optimized for GitHub Actions):
      1. Gemini Image     — primary, best quality
      2. Cloudflare FLUX  — reliable fallback, no DNS issues
      3. HuggingFace      — last resort, may have DNS issues

    NO placeholder fallback — fails loudly if all providers fail.
    """
    print(f"\n  Image providers available:")
    print(f"   Gemini keys : {len(GEMINI_KEYS)}")
    print(f"   Cloudflare  : {'YES' if CF_API_TOKEN and CF_ACCOUNT_ID else 'NO - add CF_API_TOKEN + CF_ACCOUNT_ID'}")
    print(f"   HuggingFace : {'YES' if HF_API_KEY else 'NO'}")

    if not GEMINI_KEYS and not (CF_API_TOKEN and CF_ACCOUNT_ID) and not HF_API_KEY:
        raise RuntimeError(
            "NO image providers configured!\n"
            "Add GEMINI_API_KEY and/or CF_API_TOKEN+CF_ACCOUNT_ID to GitHub Secrets"
        )

    image_paths = []

    for scene in script["scenes"]:
        n      = scene["scene_no"]
        prompt = scene["image_prompt"]
        print(f"\n  Image scene {n}/8...")
        path = None

        # 1. Gemini Image (rotate keys across scenes)
        if GEMINI_KEYS:
            key_idx = (n - 1) % len(GEMINI_KEYS)
            key     = GEMINI_KEYS[key_idx]
            try:
                path = _gemini_image(prompt, n, key)
                print(f"   OK Gemini key #{key_idx+1} -> {path}")
            except Exception as e:
                print(f"   FAIL Gemini: {e}")
                # Try other Gemini keys
                for alt_i, alt_key in enumerate(GEMINI_KEYS):
                    if alt_i == key_idx:
                        continue
                    try:
                        path = _gemini_image(prompt, n, alt_key)
                        print(f"   OK Gemini key #{alt_i+1} (retry) -> {path}")
                        break
                    except Exception as e2:
                        print(f"   FAIL Gemini key #{alt_i+1}: {e2}")

        # 2. Cloudflare FLUX (reliable on GitHub Actions — no DNS issues)
        if not path and CF_API_TOKEN and CF_ACCOUNT_ID:
            try:
                path = _cloudflare_image(prompt, n)
                print(f"   OK Cloudflare -> {path}")
            except Exception as e:
                print(f"   FAIL Cloudflare: {e}")

        # 3. HuggingFace (last resort — may have DNS issues on Azure runners)
        if not path and HF_API_KEY:
            try:
                path = _huggingface_image(prompt, n)
                print(f"   OK HuggingFace -> {path}")
            except Exception as e:
                print(f"   FAIL HuggingFace: {e}")

        # Hard stop — no silent color placeholder ever
        if not path:
            raise RuntimeError(
                f"\n  FATAL: Scene {n} — all image providers failed!\n"
                f"  Gemini keys: {len(GEMINI_KEYS)}\n"
                f"  Cloudflare set: {bool(CF_API_TOKEN and CF_ACCOUNT_ID)}\n"
                f"  HuggingFace set: {bool(HF_API_KEY)}\n"
                f"  Check GitHub Secrets and re-run."
            )

        image_paths.append(path)
        time.sleep(3)

    return image_paths

# ── voiceover ─────────────────────────────────────────────────────────────────

def generate_voiceover(script):
    parts = [script.get("hook", ""), script["narration_intro"], ""]
    for s in script["scenes"]:
        parts.append(s["narration"])
        if s.get("dialogue", "").strip():
            parts.append(f'"{s["dialogue"]}"')
        parts.append("")
    parts += [script["narration_outro"], f'The moral: {script.get("moral", "")}']
    full_text = "\n".join(parts)

    audio_path = OUTPUT_DIR / "voiceover.mp3"
    print(f"\n  Voiceover — {len(full_text)} chars...")

    r = subprocess.run([
        "edge-tts", "--voice", "en-US-AriaNeural",
        "--rate", "+0%", "--text", full_text,
        "--write-media", str(audio_path)
    ], capture_output=True, text=True)

    if r.returncode != 0:
        raise RuntimeError(f"Edge TTS failed: {r.stderr}")
    print("   OK")
    return str(audio_path)

# ── video assembly ────────────────────────────────────────────────────────────

def assemble_video(image_paths, audio_path):
    valid = [p for p in image_paths if p and Path(p).exists()]
    if not valid:
        raise ValueError("No valid images!")

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True, check=True
    )
    total   = float(probe.stdout.strip())
    per_img = total / len(valid)
    fps     = 25
    frames  = int(per_img * fps)

    print(f"\n  Video: {len(valid)} scenes x {per_img:.1f}s = {total:.0f}s total")

    input_args, filters = [], []
    zooms = [
        "z='min(zoom+0.0012,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "z='if(lte(zoom,1.0),1.25,max(1.0,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "z='min(zoom+0.0010,1.20)':x='0':y='ih/2-(ih/zoom/2)'",
    ]
    for i, img in enumerate(valid):
        input_args += ["-loop", "1", "-t", str(per_img), "-i", img]
        filters.append(
            f"[{i}:v]scale=1280:720,"
            f"zoompan={zooms[i%3]}:d={frames}:s=1280x720:fps={fps}[v{i}]"
        )

    concat = "".join(f"[v{i}]" for i in range(len(valid)))
    filters.append(f"{concat}concat=n={len(valid)}:v=1:a=0[outv]")

    out = OUTPUT_DIR / "final_video.mp4"
    cmd = (
        ["ffmpeg", "-y"] + input_args + ["-i", audio_path]
        + ["-filter_complex", ";".join(filters)]
        + ["-map", "[outv]", "-map", f"{len(valid)}:a"]
        + ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]
        + ["-c:a", "aac", "-b:a", "192k", "-shortest", str(out)]
    )
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {r.stderr[-800:]}")

    size_mb = out.stat().st_size // 1024 // 1024
    print(f"   OK {out} ({size_mb} MB)")
    return str(out)

# ── metadata ──────────────────────────────────────────────────────────────────

def generate_metadata(script):
    prompt = (
        f'YouTube metadata for: "{script["title"]}"\n'
        f'Summary: {script["narration_intro"][:200]}\n'
        f'Return ONLY JSON: {{"youtube_title":"title with emojis max 70 chars",'
        f'"description":"3 paragraphs English","tags":["wealth stories","rags to riches",'
        f'"indian success story","motivational","financial freedom","struggle to success",'
        f'"inspirational","money story","success motivation","emotional story"]}}'
    )

    def _gemini_meta(key):
        from google import genai
        c = genai.Client(api_key=key)
        return _parse_json(
            c.models.generate_content(model="gemini-2.5-flash", contents=prompt).text
        )

    def _groq_meta():
        if not GROQ_API_KEY: raise ValueError("No GROQ_API_KEY")
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 800},
            timeout=30
        )
        r.raise_for_status()
        return _parse_json(r.json()["choices"][0]["message"]["content"])

    for i, key in enumerate(GEMINI_KEYS):
        try:
            print(f"\n  Metadata -> Gemini key #{i+1}...")
            result = _gemini_meta(key)
            with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("   OK")
            return result
        except Exception as e:
            print(f"   FAIL: {e}")
            time.sleep(2)

    try:
        print(f"\n  Metadata -> Groq...")
        result = _groq_meta()
        with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("   OK")
        return result
    except Exception as e:
        print(f"   FAIL Groq: {e}")

    # Always-works fallback
    print("   Using basic fallback metadata")
    fallback = {
        "youtube_title": f"💰 {script['title']} | Wealth Stories",
        "description": (
            f"{script.get('hook','')}\n\n"
            f"{script['narration_intro']}\n\n"
            f"Moral: {script.get('moral','')}\n\n"
            "#WealthStories #RagsToRiches #MotivationalStory #IndianSuccessStory"
        ),
        "tags": [
            "wealth stories", "rags to riches", "indian success story",
            "motivational", "financial freedom", "struggle to success",
            "inspirational", "money story", "success motivation", "emotional story"
        ]
    }
    with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(fallback, f, ensure_ascii=False, indent=2)
    return fallback

# ── main ──────────────────────────────────────────────────────────────────────

def run_pipeline(topic):
    print(f"\n{'='*52}")
    print(f"  WEALTH STORIES PIPELINE")
    print(f"  Topic: {topic}")
    print(f"  Gemini keys: {len(GEMINI_KEYS)}")
    print(f"  Cloudflare : {'YES' if CF_API_TOKEN and CF_ACCOUNT_ID else 'NO'}")
    print(f"  HuggingFace: {'YES' if HF_API_KEY else 'NO'}")
    print(f"{'='*52}")

    script   = generate_script(topic)
    images   = generate_images(script)
    audio    = generate_voiceover(script)
    video    = assemble_video(images, audio)
    metadata = generate_metadata(script)

    print(f"\n{'='*52}")
    print(f"  DONE!")
    print(f"  Script  : {script.get('_provider')}")
    print(f"  Title   : {metadata.get('youtube_title')}")
    print(f"  Video   : {video}")
    print(f"{'='*52}")

if __name__ == "__main__":
    import sys
    topic = (
        sys.argv[1] if len(sys.argv) > 1
        else "A poor boy from a village who became a millionaire"
    )
    run_pipeline(topic)
