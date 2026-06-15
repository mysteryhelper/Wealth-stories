"""
Wealth Stories — YouTube Automation Pipeline
Channel: @WealthStoriesWS
Images: HuggingFace SDXL → Placeholder
Script: Gemini Flash → Groq → Cerebras
Voice:  Edge TTS en-US-AriaNeural
"""

import os, json, time, requests, subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
HF_API_KEY       = os.environ.get("HF_API_KEY", "")

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

def _try_gemini(topic):
    if not GEMINI_API_KEY: 
        raise ValueError("No GEMINI_API_KEY")
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    r = genai.GenerativeModel("gemini-2.5-flash").generate_content(_get_prompt(topic))
    return _parse_json(r.text)

def _try_groq(topic):
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

def _try_cerebras(topic):
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

def generate_script(topic):
    for name, fn in [("Gemini 2.5 Flash", _try_gemini),
                     ("Groq Llama 3.3 70B", _try_groq),
                     ("Cerebras Llama 3.3 70B", _try_cerebras)]:
        try:
            print(f"\n📝 Script → {name}...")
            result = fn(topic)
            assert "scenes" in result and len(result["scenes"]) >= 6
            result["_provider"] = name
            print(f"   ✅ Done via {name}")
            with open(OUTPUT_DIR / "script.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            return result
        except Exception as e:
            print(f"   ❌ {name}: {e}")
            time.sleep(2)
    raise RuntimeError("All script providers failed")

def _save_img(content, n):
    if len(content) < 3000:
        raise ValueError(f"Too small: {len(content)} bytes")
    path = OUTPUT_DIR / f"scene_{n:02d}.jpg"
    path.write_bytes(content)
    return str(path)

def _hf_image(prompt, n):
    if not HF_API_KEY: 
        raise ValueError("No HF_API_KEY")
    r = requests.post(
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
        headers={"Authorization": f"Bearer {HF_API_KEY}"},
        json={"inputs": prompt[:400]},
        timeout=120
    )
    r.raise_for_status()
    return _save_img(r.content, n)

def _placeholder(n):
    colors = ["#1a1a2e","#16213e","#0f3460","#533483","#2b2d42","#8d99ae","#e94560","#ef233c"]
    path = OUTPUT_DIR / f"scene_{n:02d}.jpg"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"color={colors[n%8]}:size=1280x720:duration=1",
                    "-vframes", "1", str(path)], capture_output=True, check=True)
    return str(path)

def generate_images(script):
    image_paths = []
    for scene in script["scenes"]:
        n, prompt = scene["scene_no"], scene["image_prompt"]
        print(f"\n🎨 Image Scene {n}/8...")
        path = None
        try:
            path = _hf_image(prompt, n)
            print(f"   ✅ HuggingFace SDXL")
        except Exception as e:
            print(f"   ❌ HuggingFace: {e}")
        if not path:
            path = _placeholder(n)
            print(f"   ⚠️  Placeholder scene {n}")
        image_paths.append(path)
        time.sleep(2)
    return image_paths

def generate_voiceover(script):
    parts = [script.get("hook",""), script["narration_intro"], ""]
    for s in script["scenes"]:
        parts.append(s["narration"])
        if s.get("dialogue","").strip():
            parts.append(f'"{s["dialogue"]}"')
        parts.append("")
    parts += [script["narration_outro"], f'The moral — {script.get("moral","")}']
    text = "\n".join(parts)
    audio = OUTPUT_DIR / "voiceover.mp3"
    print(f"\n🎙️ Voiceover {len(text)} chars...")
    r = subprocess.run([
        "edge-tts", "--voice", "en-US-AriaNeural",
        "--rate", "+0%",
        "--text", text,
        "--write-media", str(audio)
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Edge TTS: {r.stderr}")
    print("   ✅ Done")
    return str(audio)

def assemble_video(image_paths, audio_path):
    valid = [p for p in image_paths if p and Path(p).exists()]
    if not valid: 
        raise ValueError("No images!")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True, check=True)
    total = float(probe.stdout.strip())
    per_img, fps = total / len(valid), 25
    frames = int(per_img * fps)
    print(f"\n📹 {len(valid)} scenes × {per_img:.1f}s = {total:.0f}s...")
    input_args, filters = [], []
    zooms = [
        "z='min(zoom+0.0012,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "z='if(lte(zoom,1.0),1.25,max(1.0,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        "z='min(zoom+0.0010,1.20)':x='0':y='ih/2-(ih/zoom/2)'",
    ]
    for i, img in enumerate(valid):
        input_args += ["-loop", "1", "-t", str(per_img + 0.5), "-i", img]
        filters.append(f"[{i}:v]scale=1280:720,zoompan={zooms[i%3]}:d={frames}:s=1280x720:fps={fps}[v{i}]")
    concat = "".join(f"[v{i}]" for i in range(len(valid)))
    filters.append(f"{concat}concat=n={len(valid)}:v=1:a=0[outv]")
    out = OUTPUT_DIR / "final_video.mp4"
    cmd = (["ffmpeg", "-y"] + input_args + ["-i", audio_path]
           + ["-filter_complex", ";".join(filters)]
           + ["-map", "[outv]", "-map", f"{len(valid)}:a"]
           + ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]
           + ["-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg: {r.stderr[-500:]}")
    print(f"   ✅ {out} ({out.stat().st_size//1024//1024}MB)")
    return str(out)

def generate_metadata(script):
    prompt = (f'YouTube metadata for: "{script["title"]}"\n'
              f'Summary: {script["narration_intro"][:200]}\n'
              f'Return ONLY JSON: {{"youtube_title":"title with emojis max 70 chars",'
              f'"description":"3 paragraph English description","tags":["wealth stories","rags to riches",'
              f'"indian success story","motivational","financial freedom","struggle to success",'
              f'"inspirational","money story","success motivation","emotional story"]}}'
    )
    
    def _gemini_meta():
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        r = genai.GenerativeModel("gemini-2.5-flash").generate_content(prompt)
        return _parse_json(r.text)
    
    def _groq_meta():
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile",
                  "messages": [{"role": "user", "content": prompt}], "max_tokens": 600}, timeout=30)
        r.raise_for_status()
        return _parse_json(r.json()["choices"][0]["message"]["content"])
    
    def _cerebras_meta():
        r = requests.post("https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b",
                  "messages": [{"role": "user", "content": prompt}], "max_tokens": 600}, timeout=30)
        r.raise_for_status()
        return _parse_json(r.json()["choices"][0]["message"]["content"])
    
    for name, fn in [("Gemini", _gemini_meta), ("Groq", _groq_meta), ("Cerebras", _cerebras_meta)]:
        try:
            print(f"\n📋 Metadata → {name}...")
            result = fn()
            with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("   ✅ Done")
            return result
        except Exception as e:
            print(f"   ❌ {name}: {e}")
    
    fallback = {
        "youtube_title": f"⭐ {script['title']}",
        "description": script["narration_intro"],
        "tags": ["wealth stories", "rags to riches", "indian success story"],
    }
    with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(fallback, f, ensure_ascii=False, indent=2)
    return fallback

def run_pipeline(topic):
    print(f"\n{'═'*50}\n  💰 WEALTH STORIES\n  Topic: {topic}\n{'═'*50}")
    script   = generate_script(topic)
    images   = generate_images(script)
    audio    = generate_voiceover(script)
    video    = assemble_video(images, audio)
    metadata = generate_metadata(script)
    print(f"\n{'═'*50}\n  ✅ DONE!\n  By: {script.get('_provider')}\n  Title: {metadata.get('youtube_title')}\n{'═'*50}\n")

if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "A poor boy from a village who became a millionaire"
    run_pipeline(topic)
