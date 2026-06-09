# 💰 Wealth Stories — YouTube Automation

**Channel:** @WealthStoriesWS  
**Niche:** Emotional rags-to-riches stories (English narration, Indian characters)  
**Style:** Cinematic Pixar/CGI — Poor Indian boy → Wealth transformation

---

## Pipeline Flow

```
Topic
  ↓
[Script] Gemini Flash → Groq → Cerebras (fallback chain)
  ↓ (script includes image_prompt for each scene)
[Images] Pollinations Default → Pollinations Flux → Placeholder
  ↓
[Voice] Edge TTS — en-US-AriaNeural (warm, emotional English)
  ↓
[Video] FFmpeg Ken Burns zoom + audio assembly
  ↓
Final MP4 + metadata.json → GitHub Artifacts
```

---

## GitHub Secrets Required

| Secret | Where to get | Free? |
|--------|-------------|-------|
| `GEMINI_API_KEY` | aistudio.google.com | ✅ Free |
| `GROQ_API_KEY` | console.groq.com | ✅ Free |
| `CEREBRAS_API_KEY` | inference.cerebras.ai | ✅ Free |

**Add secrets:**
```
GitHub Repo → Settings → Secrets → Actions → New repository secret
```

---

## Setup

```bash
# 1. Fork or create repo
git init
git add .
git commit -m "Wealth Stories pipeline"
git remote add origin https://github.com/YOUR_USERNAME/wealth-stories
git push -u origin main

# 2. Add 3 secrets (see above)

# 3. Run manually
Actions → "Wealth Stories — Video Pipeline" → Run workflow
Topic: "A poor boy from a village who became a millionaire"

# 4. Download video
Actions → Latest run → Artifacts → wealth-stories-X → Download
```

---

## Daily Auto Upload
Runs every day at **7:00 AM IST** automatically.  
Random topic picked from `scripts/random_topic.py`

---

## Costs
| Tool | Cost |
|------|------|
| Gemini Flash (script) | Free 500 req/day |
| Groq (fallback) | Free |
| Cerebras (fallback) | Free 1M tokens/day |
| Pollinations (images) | Free unlimited |
| Edge TTS (voice) | Free unlimited |
| GitHub Actions | Free 2000 min/month |
| **Total** | **₹0** |
