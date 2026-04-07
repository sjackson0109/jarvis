# Hardware Requirements and Model Selection Guide

Jarvis runs entirely on your local machine — no cloud, no GPU cloud rental required.
Performance scales with your hardware, but the app is designed to degrade gracefully
so that even modest machines can run a useful subset of features.

---

## Minimum requirements (any tier)

| Component | Minimum | Notes |
|-----------|---------|-------|
| OS | Windows 10, macOS 12, Ubuntu 22.04 | 64-bit only |
| RAM | 8 GB | 16 GB strongly recommended |
| Storage | 5 GB free | Model downloads are separate and stored in `~/.ollama` |
| CPU | x86-64 or Apple Silicon | AVX2 support required for faster-whisper |
| Microphone | Any | Required for voice input |
| Python | 3.11 – 3.13 | |
| Ollama | Latest | [ollama.com](https://ollama.com) |

---

## Hardware tiers and recommended models

### Tier 1 — Integrated graphics / no dedicated GPU
*Examples: Intel UHD, AMD Radeon Vega (APU), Apple M-series (unified memory)*

All inference runs on CPU (or unified memory for Apple Silicon).
Expect 2–8 tokens/second for the chat model and ~5–15 s for a Whisper transcription.

| Component | Recommended | Ollama pull command |
|-----------|-------------|---------------------|
| Chat model | `gemma3n:e2b` | `ollama pull gemma3n:e2b` |
| Chat model (alt) | `llama3.2:3b` | `ollama pull llama3.2:3b` |
| Intent judge | `llama3.2:3b` | `ollama pull llama3.2:3b` |
| Embedding | `nomic-embed-text` | `ollama pull nomic-embed-text` |
| Whisper | `tiny` or `base` | set `whisper_model` in config |

**Config snippet:**
```json
{
  "ollama_chat_model": "gemma3n:e2b",
  "ollama_embed_model": "nomic-embed-text",
  "whisper_model": "base"
}
```

> **Apple Silicon note:** Unified memory is shared between CPU and GPU.
> An M2/M3 with 16 GB can comfortably run `gemma3n:e4b` or `llama3.2:3b`
> with near-GPU speeds thanks to Metal acceleration in Ollama.

---

### Tier 2 — Entry-level dedicated GPU (4–8 GB VRAM)
*Examples: NVIDIA GTX 1660, RTX 3060, AMD RX 6600*

The chat model fits in VRAM; expect 15–40 tokens/second.

| Component | Recommended | Ollama pull command |
|-----------|-------------|---------------------|
| Chat model | `gemma3n:e4b` | `ollama pull gemma3n:e4b` |
| Chat model (alt) | `llama3.2:3b` | `ollama pull llama3.2:3b` |
| Intent judge | `llama3.2:3b` | `ollama pull llama3.2:3b` |
| Embedding | `nomic-embed-text` | `ollama pull nomic-embed-text` |
| Whisper | `small` | set `whisper_model` in config |

**Config snippet:**
```json
{
  "ollama_chat_model": "gemma3n:e4b",
  "ollama_embed_model": "nomic-embed-text",
  "whisper_model": "small"
}
```

---

### Tier 3 — Mid-range GPU (10–16 GB VRAM)
*Examples: NVIDIA RTX 3080, RTX 4070, AMD RX 7900 GRE*

Larger models fit comfortably; expect 30–80 tokens/second.

| Component | Recommended | Ollama pull command |
|-----------|-------------|---------------------|
| Chat model | `gemma4:12b` | `ollama pull gemma4:12b` |
| Chat model (alt) | `llama3.1:8b` | `ollama pull llama3.1:8b` |
| Intent judge | `llama3.2:3b` | `ollama pull llama3.2:3b` |
| Embedding | `nomic-embed-text` | `ollama pull nomic-embed-text` |
| Whisper | `medium` | set `whisper_model` in config |

**Config snippet:**
```json
{
  "ollama_chat_model": "gemma4:12b",
  "ollama_embed_model": "nomic-embed-text",
  "whisper_model": "medium"
}
```

---

### Tier 4 — High-end GPU (24 GB+ VRAM) or multi-GPU
*Examples: NVIDIA RTX 3090/4090, RTX 6000 Ada, dual-GPU rigs*

Best quality; expect 60–120 tokens/second on a 4090.

| Component | Recommended | Ollama pull command |
|-----------|-------------|---------------------|
| Chat model | `gpt-oss:20b` | `ollama pull gpt-oss:20b` |
| Chat model (alt) | `gemma4:27b` | `ollama pull gemma4:27b` |
| Intent judge | `llama3.2:3b` | `ollama pull llama3.2:3b` |
| Embedding | `nomic-embed-text` | `ollama pull nomic-embed-text` |
| Whisper | `large-v3` | set `whisper_model` in config |

**Config snippet:**
```json
{
  "ollama_chat_model": "gpt-oss:20b",
  "ollama_embed_model": "nomic-embed-text",
  "whisper_model": "large-v3"
}
```

---

### Tier 5 — Workstation / server (32 GB+ RAM, no dedicated GPU required)
*Examples: Threadripper / Xeon workstation, Mac Studio / Mac Pro, cloud VM with 32–512 GB RAM*

With enough RAM, Ollama can run large quantised models entirely on CPU.
Speed is lower than GPU (5–20 tokens/second depending on core count and model size),
but quality matches or beats Tier 3–4 for reasoning-heavy tasks.

| RAM | Recommended chat model | Ollama pull command |
|-----|----------------------|---------------------|
| 32 GB | `gemma4:12b` or `llama3.1:8b` | `ollama pull gemma4:12b` |
| 64 GB | `gemma4:27b` or `llama3.1:70b` (Q4) | `ollama pull gemma4:27b` |
| 128 GB+ | `llama3.1:70b` (Q8) or `llama3.3:70b` | `ollama pull llama3.3:70b` |

| Component | Recommended | Ollama pull command |
|-----------|-------------|---------------------|
| Intent judge | `llama3.2:3b` | `ollama pull llama3.2:3b` |
| Embedding | `nomic-embed-text` | `ollama pull nomic-embed-text` |
| Whisper | `medium` or `large-v3` | set `whisper_model` in config |

**Config snippet (32 GB machine):**
```json
{
  "ollama_chat_model": "gemma4:12b",
  "ollama_embed_model": "nomic-embed-text",
  "whisper_model": "medium"
}
```

**Config snippet (64 GB machine):**
```json
{
  "ollama_chat_model": "gemma4:27b",
  "ollama_embed_model": "nomic-embed-text",
  "whisper_model": "large-v3"
}
```

> **CPU core count matters here.** Ollama uses all available threads for CPU inference.
> A 16-core workstation will be roughly 2× faster than an 8-core laptop at the same model size.
> Check your thread count: `(Get-WmiObject Win32_Processor).NumberOfLogicalProcessors`

> **Best of both worlds:** If a Tier 5 machine also has a dedicated GPU, Ollama will
> offload as many layers as fit in VRAM and spill the rest to RAM — giving GPU-class
> speed for most of the model even when VRAM is insufficient to hold it all.

---

## Whisper model reference

Whisper handles speech-to-text and runs independently of the chat model.
Larger models are more accurate but use more RAM and take longer.

| Model | RAM usage | Speed (CPU) | Accuracy | Recommended for |
|-------|-----------|-------------|----------|-----------------|
| `tiny` | ~400 MB | Very fast | Low | Tier 1 with limited RAM |
| `base` | ~700 MB | Fast | Fair | Tier 1 |
| `small` | ~1.5 GB | Moderate | Good | Tier 2 |
| `medium` | ~3 GB | Slow on CPU | Very good | Tier 3 / Tier 5 |
| `large-v3` | ~6 GB | Very slow on CPU | Best | Tier 4 / Tier 5 (16+ core CPU or GPU) |

Set the model in your config:
```json
{ "whisper_model": "base" }
```

---

## Feature degradation by tier

Some features require more headroom than the base chat loop.

| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 (CPU) |
|---------|--------|--------|--------|--------|--------------|
| Basic Q&A | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tool use (web search, files) | ✅ slow | ✅ | ✅ | ✅ | ✅ |
| Voice wake word | ✅ | ✅ | ✅ | ✅ | ✅ |
| Real-time voice transcription | ⚠️ lag | ✅ | ✅ | ✅ | ⚠️ medium model is slow |
| Diary / long-term memory | ⚠️ slow writes | ✅ | ✅ | ✅ | ✅ |
| Chatterbox TTS (neural) | ❌ too slow | ⚠️ slow | ✅ | ✅ | ⚠️ slow on <16 cores |
| Piper TTS (fast, English-only) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multi-step agentic tasks | ⚠️ slow | ⚠️ | ✅ | ✅ | ✅ large model quality |

> ⚠️ = works but noticeably slower than real-time  
> ❌ = technically possible but impractical; use Piper TTS instead

---

## RAM guide (total system RAM)

| System RAM | Best CPU-only model | Notes |
|------------|--------------------:|-------|
| 8 GB | `gemma3n:e2b` | Disable Chatterbox TTS; use `tiny` Whisper; close other apps |
| 16 GB | `llama3.2:3b` | Comfortable; `small` Whisper works well |
| 32 GB | `gemma4:12b` | Tier 3 quality without any GPU; `medium` Whisper fine |
| 64 GB | `gemma4:27b` | Near Tier 4 quality on CPU; use `large-v3` Whisper |
| 128 GB | `llama3.1:70b` Q4 | High-end reasoning CPU-only; ~10–15 tok/s on 16+ cores |
| 256 GB+ | `llama3.1:70b` Q8 | Full-precision large model; pairs well with multi-GPU |

---

## VRAM guide (dedicated GPU)

| VRAM | Max model size | Notes |
|------|---------------|-------|
| 4 GB | `llama3.2:3b`, `gemma3n:e2b` | Tight; close other GPU workloads |
| 6 GB | `gemma3n:e4b` | Comfortable |
| 8 GB | `gemma3n:e4b`, `llama3.1:8b` (quantised) | |
| 12 GB | `gemma4:12b`, `llama3.1:8b` | |
| 16 GB | `gemma4:12b`, `llama3.1:8b` | Comfortable; headroom for context |
| 24 GB+ | `gpt-oss:20b`, `gemma4:27b` | Best quality available |

---

## Checking your hardware (Windows)

```powershell
# GPU and VRAM
(Get-WmiObject Win32_VideoController) | Select-Object Name, AdapterRAM

# Total system RAM (GB)
[math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)

# Check if Ollama can see your GPU
ollama run llama3.2:3b "hello" --verbose
```

After the first run, Ollama's output will show whether it is using a GPU
(`[cuda]` / `[metal]` / `[rocm]`) or falling back to CPU.

---

## Frequently asked questions

**Can I run Jarvis without a GPU?**  
Yes. CPU-only works fine for Tier 1 models. Responses will be slower
(seconds rather than subseconds) but perfectly usable for non-real-time tasks.

**What is the minimum to get voice interaction working?**  
8 GB RAM, a microphone, `gemma3n:e2b` or `llama3.2:3b` for chat,
`llama3.2:3b` for intent judging, `nomic-embed-text` for embeddings,
and `base` Whisper. Piper TTS handles speech output without GPU.

**Does Jarvis use the internet for model inference?**  
No. All inference is local via Ollama. The only optional internet activity
is web search (if enabled) and model downloads during initial setup.

**Will a larger model always give better results?**  
In general yes, but Jarvis applies size-aware prompts — smaller models
receive more explicit instructions to compensate for reduced reasoning
capability. A well-tuned 3B model often out-performs a poorly-prompted 7B.
